"""Recomendação de abrigo: "onde ficar seguro".

Um abrigo é APTO quando:
1. está ativo, não é de demonstração e o sensor de ocupação mandou leitura recente;
2. não está em área de risco com o rio da região em alerta, agora OU PREVISTO pela IA para as próximas 6 h;
3. tem vagas para o grupo agora E deve continuar tendo quando a pessoa chegar.
   Vagas na chegada = capacidade − ocupação atual − (pessoas chegando por hora × horas de caminhada).

Entre os aptos, o mais perto a pé vem primeiro: haversine × 1,3 (as ruas não são linha
reta), a 4 km/h. A resposta também explica por que os abrigos mais próximos foram evitados.

Privacidade: a posição exata do cidadão não precisa sair do celular. A API usa o centro
do bairro, ou devolve a avaliação de todos os abrigos para o app terminar no aparelho:
apto agora E (não está enchendo OU os minutos a pé ≤ minutos_ate_lotar), e ordenar pela distância.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

RAIO_TERRA_KM = 6371.0088
FATOR_ROTA = 1.3
VELOCIDADE_KMH = 4.0
SEVERIDADE_PERIGOSA = 2  # alerta


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em linha reta (fórmula de haversine)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * RAIO_TERRA_KM * math.asin(math.sqrt(a))


def minutos_a_pe(distancia_reta_km: float) -> int:
    return max(1, round(distancia_reta_km * FATOR_ROTA / VELOCIDADE_KMH * 60))


@dataclass(frozen=True)
class SituacaoAbrigo:
    abrigo_id: str
    nome: str
    lat: float
    lon: float
    capacidade: int
    ocupacao: int
    chegando_por_hora: float  # variação da ocupação na última hora (só conta se positiva)
    em_area_de_risco: bool
    estacao_proxima_id: str
    severidade_atual_regiao: int  # 0..3, alerta aberto na estação da região
    severidade_prevista_regiao: int  # 0..3, nível previsto pela IA para daqui a 6 h
    indisponivel: str | None = None  # motivo (inativo, demonstração, sem leitura recente)

    @property
    def vagas(self) -> int:
        return max(self.capacidade - self.ocupacao, 0)

    def vagas_na_chegada(self, horas_ate_chegar: float) -> int:
        entrando = max(self.chegando_por_hora, 0.0) * horas_ate_chegar
        return max(math.floor(self.capacidade - self.ocupacao - entrando), 0)

    def minutos_ate_lotar(self, pessoas: int = 1) -> int | None:
        """Em quantos minutos deixa de ter vaga para o grupo (None = não está enchendo)."""
        if self.chegando_por_hora <= 0:
            return None
        return max(math.floor((self.vagas - pessoas) / self.chegando_por_hora * 60), 0)


@dataclass(frozen=True)
class Avaliacao:
    abrigo: SituacaoAbrigo
    apto: bool
    motivo: str | None  # por que NÃO é apto, em linguagem simples
    vagas_na_chegada: int
    distancia_km: float | None = None
    minutos_a_pe: int | None = None


def avaliar(abrigo: SituacaoAbrigo, pessoas: int = 1, horas_ate_chegar: float = 0.0) -> Avaliacao:
    """Sem horas_ate_chegar (0), avalia o agora; a regra de lotar na chegada fica para quem sabe a distância."""
    vagas_chegada = abrigo.vagas_na_chegada(horas_ate_chegar)
    motivo = _motivo(abrigo, pessoas, vagas_chegada)
    return Avaliacao(abrigo, motivo is None, motivo, vagas_chegada)


def _motivo(a: SituacaoAbrigo, pessoas: int, vagas_chegada: int) -> str | None:
    if a.indisponivel:
        return a.indisponivel
    if a.vagas == 0:
        return "lotado"
    if a.em_area_de_risco and a.severidade_atual_regiao >= SEVERIDADE_PERIGOSA:
        return "fica em área de risco e o rio da região está em alerta"
    if a.em_area_de_risco and a.severidade_prevista_regiao >= SEVERIDADE_PERIGOSA:
        return "fica em área de risco e o rio da região deve entrar em alerta nas próximas 6 horas"
    if a.vagas < pessoas:
        return f"só tem {a.vagas} vaga(s) para {pessoas} pessoa(s)"
    if vagas_chegada < pessoas:
        return "deve lotar antes de você chegar"
    return None


@dataclass(frozen=True)
class Recomendacao:
    recomendados: list[Avaliacao]
    evitados: list[Avaliacao]  # os que estavam MAIS PERTO que o 1º recomendado, com o motivo


def recomendar(
    abrigos: Sequence[SituacaoAbrigo], lat: float, lon: float, pessoas: int = 1, limite: int = 3
) -> Recomendacao:
    avaliacoes = []
    for abrigo in abrigos:
        if abrigo.indisponivel:
            continue
        d = distancia_km(lat, lon, abrigo.lat, abrigo.lon)
        minutos = minutos_a_pe(d)
        base = avaliar(abrigo, pessoas, minutos / 60)
        avaliacoes.append(Avaliacao(abrigo, base.apto, base.motivo, base.vagas_na_chegada, round(d, 2), minutos))
    avaliacoes.sort(key=lambda a: (a.distancia_km, a.abrigo.abrigo_id))
    recomendados = [a for a in avaliacoes if a.apto][:limite]
    limite_distancia = recomendados[0].distancia_km if recomendados else math.inf
    evitados = [a for a in avaliacoes if not a.apto and a.distancia_km < limite_distancia]
    return Recomendacao(recomendados, evitados)
