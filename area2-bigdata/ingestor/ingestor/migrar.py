"""Cria/atualiza o banco: aplica as migrações SQL pendentes, carrega os cadastros e define as senhas.

Pode rodar quantas vezes quiser (idempotente): migração já aplicada é pulada e os
cadastros são atualizados por upsert. Uma migração já aplicada NÃO deve ser editada:
o hash de cada arquivo fica guardado e, se mudar, o migrar para com erro explicando o
que fazer (criar uma migração nova).

    python -m ingestor.migrar
"""

from __future__ import annotations

import csv
import hashlib
import logging
from pathlib import Path

import psycopg
from psycopg import sql

from .config import achar_pasta, dsn_migrador, variavel
from .db import conectar

log = logging.getLogger("ingestor.migrar")

# Ordem importa por causa das chaves estrangeiras.
SEEDS = [("bairro", "bairros.csv"), ("estacao", "estacoes.csv"), ("abrigo", "abrigos.csv"), ("sensor", "sensores.csv")]


class MigracaoAlterada(RuntimeError):
    """Um .sql já aplicado foi editado. A mudança não seria aplicada, então paramos com erro."""


def hash_da_migracao(arquivo: Path) -> str:
    # CRLF → LF: o mesmo arquivo dá o mesmo hash no Windows e no Linux
    return hashlib.sha256(arquivo.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


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
        cur.execute("ALTER TABLE public.schema_migrations ADD COLUMN IF NOT EXISTS hash char(64)")
        cur.execute("SELECT versao, hash FROM public.schema_migrations")
        feitas = dict(cur.fetchall())
    conn.commit()

    aplicadas = []
    for arquivo in sorted(pasta.glob("*.sql")):
        hash_ = hash_da_migracao(arquivo)
        if arquivo.name in feitas:
            if feitas[arquivo.name] is None:  # aplicada antes de existir a coluna hash
                with conn.transaction(), conn.cursor() as cur:
                    cur.execute("UPDATE public.schema_migrations SET hash = %s WHERE versao = %s", (hash_, arquivo.name))
            elif feitas[arquivo.name] != hash_:
                raise MigracaoAlterada(
                    f"{arquivo.name} foi editada depois de aplicada e a mudança NÃO entraria no banco. "
                    "Desfaça a edição e crie uma migração nova (ex.: 006_minha_mudanca.sql), "
                    "ou zere o banco com 'docker compose down -v'."
                )
            continue
        with conn.transaction(), conn.cursor() as cur:
            cur.execute(arquivo.read_text(encoding="utf-8"))
            cur.execute("INSERT INTO public.schema_migrations (versao, hash) VALUES (%s, %s)", (arquivo.name, hash_))
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
    senhas = {
        "ingestor_rw": variavel("INGESTOR_DB_PASSWORD"),
        "bi_ro": variavel("BI_DB_PASSWORD"),
        "ia_ro": variavel("IA_DB_PASSWORD"),
    }
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
