"""Gera a série histórica (padrão: 30 dias) como arquivo NDJSON na zona de chegada do data lake.

Cada linha segue o contrato de leitura. O arquivo é escrito de forma atômica (arquivo
temporário + renomear), então o carregador nunca lê um arquivo pela metade.

    python -m simuladores.historico --dias 30 --cenario misto --semente 42
    python -m simuladores.historico --se-nao-existir      # usado pelo docker compose
"""

from __future__ import annotations

import argparse
import logging
import os
import random
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from .cadastro import Cadastro, carregar
from .mensagens import FALHAS_PADRAO, SEM_FALHAS, Falhas, GeradorDeMensagens
from .modelo import CENARIOS, PASSO, PASSOS_POR_DIA, Simulacao, calendario_misto

log = logging.getLogger("simuladores.historico")


def fim_alinhado(agora: datetime | None = None) -> datetime:
    """Último múltiplo de 10 minutos antes de agora (UTC)."""
    agora = (agora or datetime.now(UTC)).astimezone(UTC)
    return agora.replace(minute=agora.minute - agora.minute % 10, second=0, microsecond=0)


def gerar_linhas(
    cadastro: Cadastro, dias: int, semente: int, cenario: str, fim: datetime, falhas: Falhas = FALHAS_PADRAO
) -> Iterator[str]:
    simulacao = Simulacao(cadastro, semente)
    gerador = GeradorDeMensagens(cadastro, random.Random(semente + 1), falhas)
    total = dias * PASSOS_POR_DIA
    inicio = fim - total * PASSO
    for i in range(total):
        cenario_do_passo = calendario_misto(i, total) if cenario == "misto" else cenario
        estado = simulacao.passo(cenario_do_passo)
        quando = inicio + (i + 1) * PASSO
        for _sensor_id, conteudo in gerador.mensagens(estado, quando):
            yield conteudo


def nome_do_arquivo(cenario: str, dias: int, semente: int) -> str:
    return f"historico_{cenario}_{dias}d_semente{semente}.ndjson"


def gravar(destino: Path, linhas: Iterator[str]) -> int:
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".tmp")
    n = 0
    with temporario.open("w", encoding="utf-8") as f:
        for linha in linhas:
            f.write(linha + "\n")
            n += 1
    temporario.replace(destino)
    return n


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Gera série histórica simulada (NDJSON)")
    parser.add_argument("--dias", type=int, default=int(os.environ.get("HISTORICO_DIAS", "30")))
    parser.add_argument("--semente", type=int, default=int(os.environ.get("SIM_SEMENTE", "42")))
    parser.add_argument("--cenario", choices=["misto", *CENARIOS], default="misto")
    parser.add_argument("--saida", type=Path, default=Path(os.environ.get("LANDING_DIR", "area2-bigdata/datalake/landing")))
    parser.add_argument("--se-nao-existir", action="store_true", help="não gera se o arquivo já existe")
    parser.add_argument("--sem-falhas", action="store_true", help="não simula defeitos de sensor")
    args = parser.parse_args()

    destino = args.saida / nome_do_arquivo(args.cenario, args.dias, args.semente)
    if args.se_nao_existir and destino.exists():
        log.info("%s já existe na zona de chegada; nada a fazer", destino.name)
        return
    falhas = SEM_FALHAS if args.sem_falhas else FALHAS_PADRAO
    fim = fim_alinhado()
    n = gravar(destino, gerar_linhas(carregar(), args.dias, args.semente, args.cenario, fim, falhas))
    log.info("%s: %s leituras de %s dias até %s", destino, n, args.dias, fim.isoformat())


if __name__ == "__main__":
    main()
