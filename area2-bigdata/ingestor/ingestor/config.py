"""Configuração lida de variáveis de ambiente (definidas no .env / docker-compose)."""

from __future__ import annotations

import os
from pathlib import Path

from psycopg.conninfo import make_conninfo


def variavel(nome: str, padrao: str | None = None) -> str:
    valor = os.environ.get(nome, padrao)
    if valor is None or valor == "":
        raise RuntimeError(f"Variável de ambiente {nome} não definida (veja o .env.example)")
    return valor


def dsn_banco(usuario: str, senha: str) -> str:
    return make_conninfo(
        host=variavel("POSTGRES_HOST", "localhost"),
        port=variavel("POSTGRES_PORT", "55432"),
        dbname=variavel("POSTGRES_DB", "citizentech"),
        user=usuario,
        password=senha,
        application_name="citizentech-ingestor",
    )


def dsn_ingestor() -> str:
    return dsn_banco("ingestor_rw", variavel("INGESTOR_DB_PASSWORD"))


def dsn_migrador() -> str:
    return dsn_banco(variavel("POSTGRES_USER", "migrador"), variavel("POSTGRES_PASSWORD"))


def dsn_bi() -> str:
    return dsn_banco("bi_ro", variavel("BI_DB_PASSWORD"))


def achar_pasta(env: str, relativo: str) -> Path:
    """Acha uma pasta pelo env (dentro do Docker) ou subindo a partir deste arquivo (no repositório)."""
    if os.environ.get(env):
        return Path(os.environ[env])
    for pai in Path(__file__).resolve().parents:
        candidato = pai / relativo
        if candidato.is_dir():
            return candidato
    raise FileNotFoundError(f"Pasta {relativo} não encontrada; defina {env}")
