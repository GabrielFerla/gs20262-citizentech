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


def dsn_ia() -> str:
    """Usuário ia_ro: só lê a camada gold (migração 007)."""
    return make_conninfo(
        host=variavel("POSTGRES_HOST", "localhost"),
        port=variavel("POSTGRES_PORT", "55432"),
        dbname=variavel("POSTGRES_DB", "citizentech"),
        user="ia_ro",
        password=variavel("IA_DB_PASSWORD"),
        application_name="citizentech-ia",
        connect_timeout=5,
    )


def pasta_modelo() -> Path:
    """Onde fica o modelo treinado: /app/modelo na imagem; area1-ia/modelo no repositório."""
    if os.environ.get("MODELO_DIR"):
        return Path(os.environ["MODELO_DIR"])
    return Path(__file__).resolve().parents[1] / "modelo"


# O app do Compose chama a API pelo proxy do nginx (mesmo endereço, sem CORS). Estas origens são as do
# app em desenvolvimento: 5173 (padrão da fase 3) e 8081 (Metro: npx expo start --web).
CORS_PADRAO = "http://localhost:5173,http://localhost:8081"


def origens_cors() -> list[str]:
    return [o.strip() for o in os.environ.get("API_CORS_ORIGENS", CORS_PADRAO).split(",") if o.strip()]
