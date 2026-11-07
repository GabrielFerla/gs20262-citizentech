"""Carga em lote: lê arquivos NDJSON da zona de chegada do data lake (landing).

Cada linha passa pelo MESMO processamento do MQTT. Um arquivo já carregado é ignorado
(controle pelo hash do arquivo em bronze.carga).

    python -m ingestor.lote --pasta area2-bigdata/datalake/landing
    python -m ingestor.lote arquivo1.ndjson arquivo2.ndjson
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import time
from collections import Counter
from pathlib import Path

import psycopg

from .config import dsn_ingestor
from .db import conectar
from .processamento import processar
from .repositorio import Repositorio

log = logging.getLogger("ingestor.lote")


def hash_do_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def carregar_arquivo(conn: psycopg.Connection, caminho: Path, tamanho_lote: int = 1000) -> Counter[str] | None:
    """Carrega um arquivo. Devolve a contagem por status, ou None se ele já tinha sido carregado."""
    repo = Repositorio(conn)
    carga_id, concluida = repo.buscar_ou_criar_carga(caminho.name, hash_do_arquivo(caminho))
    conn.commit()
    if concluida:
        log.info("%s já foi carregado antes; ignorando", caminho.name)
        return None

    contagem: Counter[str] = Counter()
    inicio = time.monotonic()
    with caminho.open(encoding="utf-8") as f:
        for numero, linha in enumerate(f, start=1):
            linha = linha.rstrip("\r\n")
            if not linha.strip():
                continue
            contagem[processar(repo, linha, canal="arquivo", carga_id=carga_id).status] += 1
            if numero % tamanho_lote == 0:
                conn.commit()
            if numero % 20000 == 0:
                log.info("%s: %s linhas (%.0f/s)", caminho.name, numero, numero / (time.monotonic() - inicio))
    repo.concluir_carga(carga_id, contagem)
    conn.commit()
    log.info("%s carregado em %.1fs: %s", caminho.name, time.monotonic() - inicio, dict(contagem))
    return contagem


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Carga em lote de arquivos NDJSON")
    parser.add_argument("arquivos", nargs="*", type=Path)
    parser.add_argument("--pasta", type=Path, help="carrega todos os *.ndjson desta pasta")
    args = parser.parse_args()

    arquivos = list(args.arquivos)
    if args.pasta:
        arquivos += sorted(args.pasta.glob("*.ndjson"))
    if not arquivos:
        log.warning("Nenhum arquivo para carregar")
        return

    with conectar(dsn_ingestor()) as conn:
        for caminho in arquivos:
            carregar_arquivo(conn, caminho)


if __name__ == "__main__":
    main()
