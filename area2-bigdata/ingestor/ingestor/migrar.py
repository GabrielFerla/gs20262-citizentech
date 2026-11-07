"""Cria/atualiza o banco: aplica as migrações SQL pendentes, carrega os cadastros e define as senhas.

Pode rodar quantas vezes quiser (idempotente): migração já aplicada é pulada e os
cadastros são atualizados por upsert.

    python -m ingestor.migrar
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

import psycopg
from psycopg import sql

from .config import achar_pasta, dsn_migrador, variavel
from .db import conectar

log = logging.getLogger("ingestor.migrar")

# Ordem importa por causa das chaves estrangeiras.
SEEDS = [("bairro", "bairros.csv"), ("estacao", "estacoes.csv"), ("abrigo", "abrigos.csv"), ("sensor", "sensores.csv")]


def aplicar_migracoes(conn: psycopg.Connection, pasta: Path) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.schema_migrations (
                versao text PRIMARY KEY,
                aplicada_em timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute("SELECT versao FROM public.schema_migrations")
        feitas = {r[0] for r in cur.fetchall()}
    conn.commit()

    aplicadas = []
    for arquivo in sorted(pasta.glob("*.sql")):
        if arquivo.name in feitas:
            continue
        with conn.transaction(), conn.cursor() as cur:
            cur.execute(arquivo.read_text(encoding="utf-8"))
            cur.execute("INSERT INTO public.schema_migrations (versao) VALUES (%s)", (arquivo.name,))
        log.info("Migração aplicada: %s", arquivo.name)
        aplicadas.append(arquivo.name)
    return aplicadas


def carregar_seeds(conn: psycopg.Connection, pasta: Path) -> dict[str, int]:
    total = {}
    with conn.transaction(), conn.cursor() as cur:
        for tabela, nome_arquivo in SEEDS:
            with (pasta / nome_arquivo).open(encoding="utf-8", newline="") as f:
                linhas = list(csv.DictReader(f))
            colunas = list(linhas[0])
            comando = sql.SQL(
                "INSERT INTO silver.{tabela} ({colunas}) VALUES ({valores}) ON CONFLICT (id) DO UPDATE SET {atualiza}"
            ).format(
                tabela=sql.Identifier(tabela),
                colunas=sql.SQL(", ").join(map(sql.Identifier, colunas)),
                valores=sql.SQL(", ").join(sql.Placeholder() * len(colunas)),
                atualiza=sql.SQL(", ").join(
                    sql.SQL("{c} = EXCLUDED.{c}").format(c=sql.Identifier(c)) for c in colunas if c != "id"
                ),
            )
            cur.executemany(comando, [[v if v != "" else None for v in linha.values()] for linha in linhas])
            total[tabela] = len(linhas)
    return total


def definir_senhas(conn: psycopg.Connection) -> None:
    senhas = {"ingestor_rw": variavel("INGESTOR_DB_PASSWORD"), "bi_ro": variavel("BI_DB_PASSWORD")}
    with conn.transaction(), conn.cursor() as cur:
        for papel, senha in senhas.items():
            cur.execute(sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(sql.Identifier(papel), sql.Literal(senha)))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    with conectar(dsn_migrador()) as conn:
        aplicadas = aplicar_migracoes(conn, achar_pasta("MIGRACOES_DIR", "area2-bigdata/db/migrations"))
        total = carregar_seeds(conn, achar_pasta("SEEDS_DIR", "area2-bigdata/db/seeds"))
        definir_senhas(conn)
    log.info("Banco pronto. Migrações novas: %s. Cadastros: %s", aplicadas or "nenhuma", total)


if __name__ == "__main__":
    main()
