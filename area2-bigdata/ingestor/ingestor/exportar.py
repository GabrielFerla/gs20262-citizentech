"""Exporta as visões da camada gold para CSV (entrada do dashboard Power BI).

Conecta com o usuário bi_ro, que só consegue ler a camada gold.
Formato: UTF-8, separador vírgula, ponto decimal, datas 'AAAA-MM-DD HH:MM:SS'.
No Power BI, importe com a localidade "Inglês (Estados Unidos)" (veja powerbi/README.md).

    python -m ingestor.exportar --saida area2-bigdata/powerbi/dados
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg import sql

from .config import dsn_bi
from .db import conectar

log = logging.getLogger("ingestor.exportar")

VISOES = [
    "dim_bairro", "dim_estacao", "dim_abrigo",
    "v_estacao_horaria", "v_abrigo_horaria", "v_alertas", "v_qualidade",
    "v_estacao_atual", "v_abrigo_status", "v_kpis", "v_ml_features",
]


def formatar(valor: object) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, datetime):
        if valor.tzinfo is not None:
            valor = valor.astimezone(UTC).replace(tzinfo=None)
        return valor.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return format(valor.normalize(), "f") if valor == valor.to_integral() else format(valor, "f")
    return str(valor)


def exportar(conn: psycopg.Connection, pasta: Path) -> dict[str, int]:
    pasta.mkdir(parents=True, exist_ok=True)
    linhas_por_visao = {}
    for visao in VISOES:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("SELECT * FROM gold.{}").format(sql.Identifier(visao)))
            colunas = [c.name for c in cur.description]
            with (pasta / f"{visao}.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(colunas)
                n = 0
                for linha in cur:
                    w.writerow([formatar(v) for v in linha])
                    n += 1
        linhas_por_visao[visao] = n
        log.info("gold.%s → %s (%s linhas)", visao, pasta / f"{visao}.csv", n)
    return linhas_por_visao


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Exporta a camada gold para CSV")
    parser.add_argument("--saida", type=Path, default=Path(os.environ.get("EXPORT_DIR", "area2-bigdata/powerbi/dados")))
    args = parser.parse_args()
    with conectar(dsn_bi()) as conn:
        exportar(conn, args.saida)


if __name__ == "__main__":
    main()
