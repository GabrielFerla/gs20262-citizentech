"""Ponte Wokwi → broker local (gateway IoT).

O ESP32 do Wokwi gratuito só alcança a internet, não o computador local. Por isso ele
publica num broker MQTT público, e esta ponte traz as mensagens para o broker local.

Broker público = qualquer um pode publicar. Por isso a ponte só repassa a mensagem se:
  1. o sensor estiver na lista permitida (wok-nivel, wok-chuva, wok-ocup);
  2. a assinatura HMAC-SHA256 bater com a chave compartilhada (se WOKWI_CHAVE estiver definida);
  3. o "seq" for maior que o último recebido daquele sensor (impede reenvio de mensagem antiga);
  4. o horário estiver a no máximo 2 minutos do relógio da ponte;
  5. o sensor não mandar mais de 1 mensagem por segundo.
E mesmo assim os sensores do Wokwi pertencem a uma estação de demonstração: uma mensagem
falsa nunca dispara alerta de um rio real. O ingestor ainda valida tudo de novo.

    python -m simuladores.ponte_wokwi
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import signal
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

log = logging.getLogger("simuladores.ponte_wokwi")
BATIMENTO = Path(os.environ.get("ARQUIVO_BATIMENTO", "/tmp/simulador-vivo"))

SENSORES_PERMITIDOS = frozenset({"wok-nivel", "wok-chuva", "wok-ocup"})
JANELA_HORARIO = timedelta(minutes=2)
INTERVALO_MINIMO_S = 1.0
TAMANHO_MAXIMO = 1024


class Recusa(Exception):
    pass


def texto_assinado(sensor_id: str, seq: int, medido_em: str, valor: float) -> str:
    """O que o ESP32 assina. O valor vai com 2 casas para os dois lados gerarem o mesmo texto."""
    return f"{sensor_id}|{seq}|{medido_em}|{valor:.2f}"


def assinar(chave: bytes, texto: str) -> str:
    return hmac.new(chave, texto.encode(), hashlib.sha256).hexdigest()


@dataclass
class Verificador:
    chave: bytes | None
    ultimo_seq: dict[str, int] = field(default_factory=dict)
    ultimo_repasse: dict[str, float] = field(default_factory=dict)

    def verificar(self, sensor_topico: str, conteudo: bytes, agora: datetime, relogio_s: float) -> str:
        """Devolve o JSON a repassar (sem a assinatura) ou levanta Recusa."""
        if len(conteudo) > TAMANHO_MAXIMO:
            raise Recusa("mensagem grande demais")
        if sensor_topico not in SENSORES_PERMITIDOS:
            raise Recusa(f"sensor {sensor_topico!r} não permitido")
        try:
            m = json.loads(conteudo)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise Recusa("JSON inválido") from None
        if not isinstance(m, dict) or m.get("sensor_id") != sensor_topico:
            raise Recusa("sensor da mensagem difere do tópico")

        seq, medido_em, valor = m.get("seq"), m.get("medido_em"), m.get("valor")
        if not isinstance(seq, int) or isinstance(seq, bool) or not isinstance(medido_em, str):
            raise Recusa("seq e medido_em são obrigatórios")
        if not isinstance(valor, int | float) or isinstance(valor, bool):
            raise Recusa("valor precisa ser número")
        try:
            quando = datetime.fromisoformat(medido_em)
        except ValueError:
            raise Recusa("medido_em inválido") from None
        if quando.tzinfo is None or abs(quando - agora) > JANELA_HORARIO:
            raise Recusa("horário fora da janela de 2 minutos (relógio errado ou reenvio)")

        if self.chave is not None:
            esperada = assinar(self.chave, texto_assinado(sensor_topico, seq, medido_em, float(valor)))
            if not hmac.compare_digest(esperada, str(m.get("assinatura", ""))):
                raise Recusa("assinatura inválida")
        if seq <= self.ultimo_seq.get(sensor_topico, -1):
            raise Recusa("seq repetido ou antigo (possível reenvio)")
        if relogio_s - self.ultimo_repasse.get(sensor_topico, float("-inf")) < INTERVALO_MINIMO_S:
            raise Recusa("mais de 1 mensagem por segundo")

        self.ultimo_seq[sensor_topico] = seq
        self.ultimo_repasse[sensor_topico] = relogio_s
        m.pop("assinatura", None)  # o contrato do ingestor não tem esse campo
        return json.dumps(m, separators=(",", ":"))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    prefixo = os.environ["WOKWI_PREFIXO"].rstrip("/")
    chave = os.environ.get("WOKWI_CHAVE", "").encode() or None
    verificador = Verificador(chave)
    if chave is None:
        log.warning("WOKWI_CHAVE não definida: mensagens sem assinatura serão aceitas")

    local = mqtt.Client(CallbackAPIVersion.VERSION2, client_id="ponte-wokwi-local", protocol=mqtt.MQTTv311)
    local.username_pw_set("ponte", os.environ["MQTT_PONTE_PASSWORD"])
    local.reconnect_delay_set(1, 30)
    local.connect_async(os.environ.get("MQTT_HOST", "localhost"), int(os.environ.get("MQTT_PORT", "11883")))
    local.loop_start()

    publico = mqtt.Client(CallbackAPIVersion.VERSION2, client_id=f"ponte-{os.urandom(6).hex()}", protocol=mqtt.MQTTv311)
    publico.reconnect_delay_set(1, 60)
    contagem = {"repassadas": 0, "recusadas": 0}

    def ao_conectar(cliente, _u, _f, reason_code, _p):
        if reason_code.is_failure:
            log.error("Broker público recusou: %s", reason_code)
            return
        cliente.subscribe(f"{prefixo}/+", qos=1)
        log.info("Ouvindo %s/+ no broker público", prefixo)

    def ao_receber(_c, _u, msg):
        sensor = msg.topic.rsplit("/", 1)[-1]
        try:
            saida = verificador.verificar(sensor, msg.payload, datetime.now(UTC), time.monotonic())
        except Recusa as recusa:
            contagem["recusadas"] += 1
            log.warning("Recusada (%s): %s", sensor, recusa)
            return
        local.publish(f"citizentech/v1/wokwi/{sensor}", saida, qos=1)
        contagem["repassadas"] += 1
        log.info("Repassada %s → %s", sensor, saida)

    publico.on_connect = ao_conectar
    publico.on_message = ao_receber
    publico.connect_async(os.environ.get("WOKWI_BROKER", "broker.hivemq.com"), 1883, keepalive=30)
    publico.loop_start()

    parar = threading.Event()
    for sinal in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sinal, lambda *_: parar.set())
    while not parar.wait(5):
        if local.is_connected() and publico.is_connected():
            BATIMENTO.touch()
    log.info("Encerrando: %s", contagem)
    publico.loop_stop()
    local.loop_stop()


if __name__ == "__main__":
    main()
