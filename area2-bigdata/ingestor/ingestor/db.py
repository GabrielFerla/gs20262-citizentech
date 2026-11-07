"""Conexão com o PostgreSQL com novas tentativas (o banco pode demorar a subir)."""

from __future__ import annotations

import logging
import time

import psycopg

log = logging.getLogger(__name__)


def conectar(dsn: str, tentativas: int = 30, espera_s: float = 2.0) -> psycopg.Connection:
    for tentativa in range(1, tentativas + 1):
        try:
            return psycopg.connect(dsn)
        except psycopg.OperationalError as erro:
            if tentativa == tentativas:
                raise
            log.warning("Banco indisponível (%s/%s): %s", tentativa, tentativas, str(erro).strip())
            time.sleep(espera_s)
    raise RuntimeError("inalcançável")
