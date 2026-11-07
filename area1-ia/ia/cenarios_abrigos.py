"""Métrica antes/depois da recomendação de abrigo, com o histórico do pipeline.

Cenário: em cada hora de crise do histórico (algum rio em atenção ou pior, agora ou na
previsão), 200 pessoas que moram nos bairros de risco alto precisam ir para um abrigo
(família de 4). Três jeitos de escolher:

  A. "mais próximo"        → o abrigo mais perto, sem olhar mais nada (como é sem o sistema);
  B. "regra da fase 1"     → o mais perto com vaga AGORA e fora de área de risco com alerta AGORA;
  C. "IA"                  → o mais perto APTO: vaga prevista na chegada e sem risco PREVISTO para 6 h.

"Alerta agora" é o mesmo da API: a regra de alerta da fase 1 (abre na cota de atenção,
escala, não rebaixa enquanto aberto e só fecha 0,10 m abaixo da atenção), repetida aqui
sobre o nível máximo de cada hora do histórico.

Cada escolha é conferida com o que de fato aconteceu depois (dados do próprio histórico):
  - lotado na chegada: na hora seguinte o abrigo não tinha vaga para a família;
  - alagou: abrigo em área de risco cujo rio passou da cota de inundação nas 6 h seguintes.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from .abrigos import SituacaoAbrigo, distancia_km, minutos_a_pe, recomendar
from .previsao import Cotas
from .repositorio import Bairro
from .vigia import proxima_acao

PESSOAS_POR_GRUPO = 4
PONTOS = 200
DISPERSAO_KM = 0.6
SEMENTE_PONTOS = 2026
HORIZONTE_H = 6
UMA_HORA = timedelta(hours=1)


@dataclass(frozen=True)
class AbrigoFixo:
    abrigo_id: str
    nome: str
    lat: float
    lon: float
    capacidade: int
    em_area_de_risco: bool
    estacao_proxima_id: str


@dataclass(frozen=True)
class Momento:
    hora: datetime
    ocupacao: dict[str, int]  # na hora t
    ocupacao_antes: dict[str, int]  # na hora t-1 (para a tendência)
    ocupacao_chegada: dict[str, int]  # na hora t+1 (o que a pessoa encontra)
    severidade_atual: dict[str, int]  # por estação: alerta da fase 1 aberto na hora t
    severidade_prevista: dict[str, int]  # por estação, previsão da IA feita na hora t
    alaga_em_6h: dict[str, bool]  # por estação: passou da cota de inundação em [t, t+6 h]


def pontos_de_partida(bairros: Sequence[Bairro], n: int = PONTOS, semente: int = SEMENTE_PONTOS) -> list[tuple[float, float]]:
    """Pontos sorteados em volta do centro dos bairros de risco alto (mesma semente → mesmos pontos)."""
    rng = random.Random(semente)
    risco = sorted((b for b in bairros if b.zona_risco == "alta"), key=lambda b: b.bairro_id)
    pontos = []
    for i in range(n):
        b = risco[i % len(risco)]
        dlat = rng.gauss(0, DISPERSAO_KM) / 111.32
        dlon = rng.gauss(0, DISPERSAO_KM) / (111.32 * math.cos(math.radians(b.lat)))
        pontos.append((b.lat + dlat, b.lon + dlon))
    return pontos


def alerta_da_fase1(nivel_max: dict[tuple[str, datetime], float], cotas: dict[str, Cotas]) -> dict[tuple[str, datetime], int]:
    """Severidade do alerta aberto em cada hora, repetindo a regra da fase 1 em ordem cronológica."""
    severidade: dict[tuple[str, datetime], int] = {}
    for estacao_id, c in cotas.items():
        aberto = 0
        for h in sorted(h for (e, h) in nivel_max if e == estacao_id):
            _, aberto = proxima_acao(aberto, nivel_max[estacao_id, h], c)
            severidade[estacao_id, h] = aberto
    return severidade


def montar_momentos(
    abrigos: Sequence[AbrigoFixo],
    ocupacao: dict[tuple[str, datetime], int],
    nivel_max: dict[tuple[str, datetime], float],
    previsto: dict[tuple[str, datetime], float],
    cotas: dict[str, Cotas],
) -> list[Momento]:
    """Uma entrada por hora de crise que tem a hora anterior e a seguinte no histórico."""
    estacoes = sorted(cotas)
    horas = sorted({h for (_, h) in nivel_max})
    alerta = alerta_da_fase1(nivel_max, cotas)
    momentos = []
    for h in horas:
        antes, depois = h - UMA_HORA, h + UMA_HORA
        if not all((a.abrigo_id, x) in ocupacao for a in abrigos for x in (antes, h, depois)):
            continue
        if not all((e, h) in nivel_max and (e, h) in previsto for e in estacoes):
            continue
        sev_atual = {e: alerta[e, h] for e in estacoes}
        sev_prevista = {e: cotas[e].severidade(previsto[e, h]) for e in estacoes}
        if max(*sev_atual.values(), *sev_prevista.values()) == 0:
            continue  # hora calma: ninguém precisa de abrigo
        alaga = {
            e: any(nivel_max.get((e, h + k * UMA_HORA), 0.0) >= cotas[e].inundacao_m for k in range(HORIZONTE_H + 1))
            for e in estacoes
        }
        momentos.append(Momento(
            hora=h,
            ocupacao={a.abrigo_id: ocupacao[a.abrigo_id, h] for a in abrigos},
            ocupacao_antes={a.abrigo_id: ocupacao[a.abrigo_id, antes] for a in abrigos},
            ocupacao_chegada={a.abrigo_id: ocupacao[a.abrigo_id, depois] for a in abrigos},
            severidade_atual=sev_atual, severidade_prevista=sev_prevista, alaga_em_6h=alaga,
        ))
    return momentos


def situacoes(abrigos: Sequence[AbrigoFixo], m: Momento) -> list[SituacaoAbrigo]:
    """O que a IA sabe na hora t (nada do futuro)."""
    return [
        SituacaoAbrigo(
            abrigo_id=a.abrigo_id, nome=a.nome, lat=a.lat, lon=a.lon, capacidade=a.capacidade,
            ocupacao=m.ocupacao[a.abrigo_id], chegando_por_hora=m.ocupacao[a.abrigo_id] - m.ocupacao_antes[a.abrigo_id],
            em_area_de_risco=a.em_area_de_risco, estacao_proxima_id=a.estacao_proxima_id,
            severidade_atual_regiao=m.severidade_atual.get(a.estacao_proxima_id, 0),
            severidade_prevista_regiao=m.severidade_prevista.get(a.estacao_proxima_id, 0),
        )
        for a in abrigos
    ]


def _mais_proximo(candidatos: list[SituacaoAbrigo], lat: float, lon: float) -> SituacaoAbrigo | None:
    return min(candidatos, key=lambda a: (distancia_km(lat, lon, a.lat, a.lon), a.abrigo_id), default=None)


def escolher_mais_proximo(sits: list[SituacaoAbrigo], lat: float, lon: float, pessoas: int) -> SituacaoAbrigo | None:
    return _mais_proximo(sits, lat, lon)


def escolher_regra_fase1(sits: list[SituacaoAbrigo], lat: float, lon: float, pessoas: int) -> SituacaoAbrigo | None:
    ok = [a for a in sits if a.vagas >= pessoas and not (a.em_area_de_risco and a.severidade_atual_regiao >= 2)]
    return _mais_proximo(ok, lat, lon)


def escolher_ia(sits: list[SituacaoAbrigo], lat: float, lon: float, pessoas: int) -> SituacaoAbrigo | None:
    rec = recomendar(sits, lat, lon, pessoas, limite=1)
    return rec.recomendados[0].abrigo if rec.recomendados else None


ESTRATEGIAS = {
    "mais_proximo": ("A. Mais próximo (sem o sistema)", escolher_mais_proximo),
    "regra_fase1": ("B. Regra da fase 1 (vaga e alerta de agora)", escolher_regra_fase1),
    "ia": ("C. IA (vaga na chegada e risco previsto)", escolher_ia),
}


def avaliar(
    abrigos: Sequence[AbrigoFixo],
    momentos: Sequence[Momento],
    pontos: Sequence[tuple[float, float]],
    pessoas: int = PESSOAS_POR_GRUPO,
) -> dict:
    por_id = {a.abrigo_id: a for a in abrigos}
    resultado = {}
    for chave, (nome, escolher) in ESTRATEGIAS.items():
        casos = lotado = alagou = falha = sem_opcao = 0
        km = minutos = 0.0
        for m in momentos:
            sits = situacoes(abrigos, m)
            for lat, lon in pontos:
                escolhido = escolher(sits, lat, lon, pessoas)
                casos += 1
                if escolhido is None:
                    sem_opcao += 1
                    continue
                a = por_id[escolhido.abrigo_id]
                d = distancia_km(lat, lon, a.lat, a.lon)
                km += d
                minutos += minutos_a_pe(d)
                cheio = a.capacidade - m.ocupacao_chegada[a.abrigo_id] < pessoas
                alagado = a.em_area_de_risco and m.alaga_em_6h.get(a.estacao_proxima_id, False)
                lotado += cheio
                alagou += alagado
                falha += cheio or alagado
        com_abrigo = casos - sem_opcao
        resultado[chave] = {
            "estrategia": nome,
            "casos": casos,
            "lotado_na_chegada_pct": _pct(lotado, casos),
            "abrigo_alagou_pct": _pct(alagou, casos),
            "falha_pct": _pct(falha, casos),
            "sem_abrigo_apto_pct": _pct(sem_opcao, casos),
            "distancia_media_km": round(km / com_abrigo, 2) if com_abrigo else None,
            "minutos_a_pe_medio": round(minutos / com_abrigo) if com_abrigo else None,
        }
    return {
        "horas_de_crise": len(momentos),
        "pontos_de_partida": len(pontos),
        "pessoas_por_grupo": pessoas,
        "estrategias": resultado,
    }


def _pct(parte: int, total: int) -> float | None:
    return round(100 * parte / total, 1) if total else None
