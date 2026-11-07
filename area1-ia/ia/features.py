"""Features horárias da previsão, com a MESMA regra da visão gold.v_ml_features.

Python puro, sem dependências: a imagem dos testes de integração importa este arquivo
para conferir, com os dados do banco, que o Python e o SQL calculam igual (sem isso, o
modelo treinado aqui poderia receber, ao vivo, números calculados de outro jeito).

Regra (004_gold.sql + 006_ml_features_uma_agregacao.sql):
- cada hora cheia (UTC) com alguma leitura vira uma linha;
- nível da hora = média das leituras de nível, arredondada para 2 casas;
- chuva da hora = soma das leituras de chuva, arredondada para 1 casa;
- variação 1 h = nível da hora menos o da linha anterior;
- chuva 6 h e 24 h = soma da chuva das horas [h-5, h] e [h-23, h];
- alvo = nível da hora h+6 (vazio se essa hora não existe).

Os arredondamentos usam Decimal "meio para cima", como o round() do PostgreSQL.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

FEATURES = ("nivel_atual_m", "variacao_1h_m", "chuva_1h_mm", "chuva_6h_mm", "chuva_24h_mm")
HORIZONTE_H = 6
UMA_HORA = timedelta(hours=1)

Serie = Iterable[tuple[datetime, float]]


@dataclass(frozen=True)
class LinhaFeatures:
    estacao_id: str
    hora_utc: datetime
    nivel_atual_m: float | None
    variacao_1h_m: float | None
    chuva_1h_mm: float
    chuva_6h_mm: float
    chuva_24h_mm: float
    nivel_6h_depois_m: float | None

    def completa(self) -> bool:
        """Tem todas as features (dá para prever)."""
        return self.nivel_atual_m is not None and self.variacao_1h_m is not None

    def vetor(self) -> list[float]:
        return [getattr(self, nome) for nome in FEATURES]


def _arredondar(valor: Decimal, casas: int) -> Decimal:
    return valor.quantize(Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP)


def hora_cheia(quando: datetime) -> datetime:
    if quando.tzinfo is None:  # astimezone() leria como horário local da máquina e deslocaria a hora
        raise ValueError(f"horário sem fuso: {quando.isoformat()} (use datetime com tzinfo, como o banco devolve)")
    return quando.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def features_horarias(estacao_id: str, niveis: Serie, chuvas: Serie) -> list[LinhaFeatures]:
    """Leituras de 10 min (horário, valor) de UMA estação → uma linha de features por hora."""
    soma_nivel: dict[datetime, Decimal] = defaultdict(Decimal)
    qtd_nivel: dict[datetime, int] = defaultdict(int)
    soma_chuva: dict[datetime, Decimal] = defaultdict(Decimal)
    for quando, valor in niveis:
        h = hora_cheia(quando)
        soma_nivel[h] += Decimal(str(valor))
        qtd_nivel[h] += 1
    for quando, valor in chuvas:
        soma_chuva[hora_cheia(quando)] += Decimal(str(valor))

    horas = sorted(set(soma_nivel) | set(soma_chuva))
    nivel = {h: _arredondar(soma_nivel[h] / qtd_nivel[h], 2) for h in qtd_nivel}
    chuva = {h: _arredondar(soma_chuva.get(h, Decimal(0)), 1) for h in horas}

    linhas = []
    anterior: datetime | None = None
    for h in horas:
        atual = nivel.get(h)
        antes = nivel.get(anterior) if anterior is not None else None
        variacao = atual - antes if atual is not None and antes is not None else None
        chuva_6h = sum((chuva.get(h - k * UMA_HORA, Decimal(0)) for k in range(6)), Decimal(0))
        chuva_24h = sum((chuva.get(h - k * UMA_HORA, Decimal(0)) for k in range(24)), Decimal(0))
        futuro = nivel.get(h + HORIZONTE_H * UMA_HORA)
        linhas.append(
            LinhaFeatures(
                estacao_id=estacao_id,
                hora_utc=h,
                nivel_atual_m=_float(atual),
                variacao_1h_m=_float(variacao),
                chuva_1h_mm=float(chuva[h]),
                chuva_6h_mm=float(chuva_6h),
                chuva_24h_mm=float(chuva_24h),
                nivel_6h_depois_m=_float(futuro),
            )
        )
        anterior = h
    return linhas


def _float(valor: Decimal | None) -> float | None:
    return None if valor is None else float(valor)
