"""Regra de alerta de cheia (função pura, fácil de testar e de explicar).

Severidades: 0 normal, 1 atenção, 2 alerta, 3 inundação.

- Abre um alerta quando o nível atinge a cota de atenção.
- Escala quando atinge uma cota mais alta (nunca rebaixa enquanto aberto).
- Só fecha quando o nível cai FOLGA metros abaixo da cota de atenção. Essa folga
  (histerese) evita que o alerta fique abrindo e fechando com a oscilação do rio.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FOLGA_M = 0.10
NOMES = {0: "normal", 1: "atencao", 2: "alerta", 3: "inundacao"}

Acao = Literal["nenhuma", "abrir", "escalar", "manter", "fechar"]


@dataclass(frozen=True)
class Cotas:
    atencao: float
    alerta: float
    inundacao: float


def severidade_do_nivel(nivel: float, cotas: Cotas) -> int:
    if nivel >= cotas.inundacao:
        return 3
    if nivel >= cotas.alerta:
        return 2
    if nivel >= cotas.atencao:
        return 1
    return 0


def proximo_alerta(severidade_atual: int, nivel: float, cotas: Cotas, folga: float = FOLGA_M) -> tuple[Acao, int]:
    """Decide o que fazer com o alerta da estação. Devolve (ação, nova severidade)."""
    alvo = severidade_do_nivel(nivel, cotas)
    if severidade_atual == 0:
        return ("abrir", alvo) if alvo > 0 else ("nenhuma", 0)
    if alvo > severidade_atual:
        return "escalar", alvo
    if nivel < cotas.atencao - folga:
        return "fechar", 0
    return "manter", severidade_atual
