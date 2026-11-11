"""Sensores em tempo real: publica as leituras via MQTT (QoS 1).

A simulação é acelerada para a demonstração: com velocidade 600, cada segundo real
equivale a 10 minutos simulados, e uma enchente completa acontece em ~13 minutos.
O horário da mensagem (medido_em) é o horário real do envio.

Antes de começar, a simulação "aquece" repetindo a série histórica com a mesma semente,
para o rio continuar do ponto em que o histórico parou (sem salto de nível). No cenário
"ciclo", cada volta da cheia recomeça desse mesmo estado, como um restart do simulador.

    python -m simuladores.tempo_real --cenario ciclo --velocidade 600
"""

from __future__ import annotations

import argparse
import copy
import itertools
import logging
import os
import random
import signal
import threading
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from .cadastro import carregar
from .mensagens import FALHAS_PADRAO, SEM_FALHAS, GeradorDeMensagens
from .modelo import CENARIOS, PASSO, PASSOS_POR_DIA, Estado, Simulacao, calendario_misto

log = logging.getLogger("simuladores.tempo_real")
BATIMENTO = Path(os.environ.get("ARQUIVO_BATIMENTO", "/tmp/simulador-vivo"))

# Ciclo da demonstração (em passos de 10 min): 12 h normal, 3 dias de enchente, 2 dias de recuperação.
CICLO = [("normal", 72), ("enchente", 432), ("normal", 288)]
PASSOS_DO_CICLO = sum(passos for _, passos in CICLO)


def cenarios(nome: str) -> Iterator[str]:
    if nome == "ciclo":
        return itertools.cycle([c for c, passos in CICLO for _ in range(passos)])
    return itertools.repeat(nome)


def comeca_ciclo_novo(passo: int, cenario: str) -> bool:
    """No cenário "ciclo", o passo que abre a 2ª, a 3ª... volta da cheia (o primeiro passo é o 1)."""
    return cenario == "ciclo" and passo > 1 and (passo - 1) % PASSOS_DO_CICLO == 0


def passos(simulacao: Simulacao, cenario: str) -> Iterator[tuple[str, Estado]]:
    """Os passos da simulação em tempo real: (cenário do passo, estado depois dele).

    No cenário "ciclo", cada volta recomeça do estado de agora (logo depois do aquecimento).
    Os 2 dias de recuperação não bastam para o Guaíba baixar (ele leva semanas): sem isso,
    da 2ª volta em diante o rio ficava acima da cota de alerta e o alerta nunca fechava.
    """
    inicio = copy.deepcopy(simulacao)
    for passo, nome in enumerate(cenarios(cenario), start=1):
        if comeca_ciclo_novo(passo, cenario):
            simulacao = copy.deepcopy(inicio)
            log.info("Ciclo novo: rios e abrigos voltam ao estado do início (igual a um restart)")
        yield nome, simulacao.passo(nome)


def proximo_envio(anterior: float, agora: float, intervalo: float) -> float:
    """Quando publicar o próximo passo.

    Mantém o ritmo sem acumular atraso. Mas, se o processo ficou parado (notebook
    dormindo, container pausado), retoma a partir de agora em vez de disparar de uma
    vez todos os passos atrasados — isso faria dias simulados passarem em segundos.
    """
    proximo = anterior + intervalo
    if proximo < agora - intervalo:
        log.warning("Simulador ficou parado por %.0fs; retomando sem rajada", agora - proximo)
        return agora
    return proximo


def conectar(host: str, porta: int, senha: str) -> mqtt.Client:
    cliente = mqtt.Client(CallbackAPIVersion.VERSION2, client_id=f"simulador-{os.getpid()}", protocol=mqtt.MQTTv311)
    cliente.username_pw_set("simulador", senha)
    cliente.reconnect_delay_set(1, 30)
    for tentativa in range(1, 31):
        try:
            cliente.connect(host, porta, keepalive=30)
            break
        except OSError as erro:
            log.warning("Broker indisponível (%s/30): %s", tentativa, erro)
            time.sleep(2)
    else:
        raise SystemExit("Não foi possível conectar ao broker MQTT")
    cliente.loop_start()
    return cliente


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Publica leituras simuladas em tempo real via MQTT")
    parser.add_argument("--cenario", choices=["ciclo", *CENARIOS], default=os.environ.get("SIM_CENARIO", "ciclo"))
    parser.add_argument("--velocidade", type=float, default=float(os.environ.get("SIM_VELOCIDADE", "600")),
                        help="segundos simulados por segundo real (600 = 10 min simulados por segundo)")
    parser.add_argument("--semente", type=int, default=int(os.environ.get("SIM_SEMENTE", "42")))
    parser.add_argument("--dias-aquecimento", type=int, default=int(os.environ.get("HISTORICO_DIAS", "30")))
    parser.add_argument("--sem-falhas", action="store_true")
    args = parser.parse_args()

    cadastro = carregar()
    simulacao = Simulacao(cadastro, args.semente)
    total = args.dias_aquecimento * PASSOS_POR_DIA
    for i in range(total):
        simulacao.passo(calendario_misto(i, total))
    gerador = GeradorDeMensagens(
        cadastro, random.Random(args.semente + 1000), SEM_FALHAS if args.sem_falhas else FALHAS_PADRAO
    )

    cliente = conectar(os.environ.get("MQTT_HOST", "localhost"), int(os.environ.get("MQTT_PORT", "11883")),
                       os.environ["MQTT_SIMULADOR_PASSWORD"])
    parar = threading.Event()
    for sinal in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sinal, lambda *_: parar.set())

    intervalo = PASSO.total_seconds() / args.velocidade
    log.info("Publicando %s sensores a cada %.2fs (cenário %s)", len(gerador.sensores), intervalo, args.cenario)
    proximo = time.monotonic()
    for passo, (cenario, estado) in enumerate(passos(simulacao, args.cenario), start=1):
        if parar.is_set():
            break
        for sensor_id, conteudo in gerador.mensagens(estado, datetime.now(UTC)):
            cliente.publish(f"citizentech/v1/sim/{sensor_id}", conteudo, qos=1)
        if cliente.is_connected():
            BATIMENTO.touch()
        if passo % 36 == 0:
            niveis = ", ".join(f"{k}={v:.2f} m" for k, v in estado.nivel_m.items())
            log.info("[%s] %s | pessoas em abrigos: %s", cenario, niveis, sum(estado.ocupacao.values()))
        agora = time.monotonic()
        proximo = proximo_envio(proximo, agora, intervalo)
        parar.wait(max(0.0, proximo - agora))

    cliente.loop_stop()
    cliente.disconnect()


if __name__ == "__main__":
    main()
