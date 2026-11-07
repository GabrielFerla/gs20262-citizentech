"""Consumidor MQTT (tempo real): assina citizentech/v1/+/+ e processa cada mensagem.

    python -m ingestor.consumidor
"""

from __future__ import annotations

import logging
import os
import signal
import threading
from collections import Counter
from pathlib import Path

import paho.mqtt.client as mqtt
import psycopg
from paho.mqtt.enums import CallbackAPIVersion

from .config import dsn_ingestor, variavel
from .contrato import TOPICO_ASSINATURA
from .db import conectar
from .processamento import processar
from .repositorio import Repositorio

log = logging.getLogger("ingestor")

# O healthcheck do Docker confere se este arquivo foi tocado nos últimos segundos.
BATIMENTO = Path(os.environ.get("ARQUIVO_BATIMENTO", "/tmp/ingestor-vivo"))


class Consumidor:
    def __init__(self) -> None:
        self.conn = conectar(dsn_ingestor())
        self.repo = Repositorio(self.conn)
        self.contagem: Counter[str] = Counter()
        self.parar = threading.Event()
        self.inscrito = False

        # clean_session=False + client_id fixo: o broker guarda as mensagens QoS 1
        # enquanto o ingestor estiver fora e entrega quando ele voltar.
        self.cliente = mqtt.Client(
            CallbackAPIVersion.VERSION2,
            client_id=variavel("MQTT_CLIENT_ID", "ingestor"),
            clean_session=False,
            protocol=mqtt.MQTTv311,
        )
        self.cliente.username_pw_set("ingestor", variavel("MQTT_INGESTOR_PASSWORD"))
        self.cliente.reconnect_delay_set(min_delay=1, max_delay=30)
        self.cliente.on_connect = self.ao_conectar
        self.cliente.on_disconnect = self.ao_desconectar
        self.cliente.on_message = self.ao_receber

    def ao_conectar(self, cliente, _userdata, _flags, reason_code, _properties) -> None:
        if reason_code.is_failure:
            log.error("Broker recusou a conexão: %s", reason_code)
            return
        cliente.subscribe(TOPICO_ASSINATURA, qos=1)
        self.inscrito = True
        log.info("Conectado ao broker; assinando %s", TOPICO_ASSINATURA)

    def ao_desconectar(self, _cliente, _userdata, _flags, reason_code, _properties) -> None:
        self.inscrito = False
        if not self.parar.is_set():
            log.warning("Desconectado do broker (%s); tentando de novo", reason_code)

    def ao_receber(self, _cliente, _userdata, msg) -> None:
        conteudo = msg.payload.decode("utf-8", errors="replace")
        try:
            resultado = processar(self.repo, conteudo, canal="mqtt", topico=msg.topic)
            self.conn.commit()
        except psycopg.Error:
            log.exception("Erro no banco ao processar %s", msg.topic)
            self._recuperar_banco()
            return

        self.contagem[resultado.status] += 1
        if resultado.status == "rejeitada":
            log.warning("Rejeitada %s → %s", msg.topic, resultado.motivo)
        if resultado.alerta:
            log.warning("ALERTA %s (%s)", resultado.alerta.upper(), msg.topic)
        total = sum(self.contagem.values())
        if total % 500 == 0:
            log.info("%s mensagens processadas: %s", total, dict(self.contagem))

    def _recuperar_banco(self) -> None:
        try:
            self.conn.rollback()
        except psycopg.Error:
            pass
        if self.conn.closed or self.conn.broken:
            log.warning("Reconectando ao banco")
            self.conn = conectar(dsn_ingestor())
            self.repo = Repositorio(self.conn)

    def executar(self) -> None:
        for sinal in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sinal, lambda *_: self.parar.set())

        host, porta = variavel("MQTT_HOST", "localhost"), int(variavel("MQTT_PORT", "11883"))
        self.cliente.connect_async(host, porta, keepalive=30)
        self.cliente.loop_start()
        log.info("Ingestor iniciado (broker %s:%s)", host, porta)

        while not self.parar.wait(5):
            if self.inscrito and not self.conn.closed:
                BATIMENTO.touch()

        log.info("Encerrando. Total: %s", dict(self.contagem))
        self.cliente.disconnect()
        self.cliente.loop_stop()
        self.conn.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    Consumidor().executar()


if __name__ == "__main__":
    main()
