"""Física simplificada de chuva → rio → abrigos. Sem rede nem arquivo: só cálculo.

Cada passo representa 10 minutos. Com a mesma semente, a simulação gera sempre os
mesmos números (dá para testar e para reproduzir o dataset da IA).

Chuva: cadeia de Markov "seco/chovendo". O cenário muda a chance de começar e de parar
de chover e a intensidade média.

Rio: dois "reservatórios" em série (modelo hidrológico clássico). A chuva enche o
primeiro, que escoa para o segundo, que escoa para o rio. Por isso o nível sobe com
ATRASO em relação à chuva — rápido no arroio Dilúvio, lento no Guaíba. Esse atraso é o
que permite, na fase 2, uma IA prever o nível de daqui a algumas horas.

Abrigos: a ocupação tende a um alvo que cresce quando o rio da região passa da cota de
alerta. As pessoas chegam rápido (20% da diferença por passo) e vão embora devagar.
Abrigo em área de risco é evacuado quando o rio passa da cota de inundação.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import timedelta

from .cadastro import Abrigo, Cadastro, Estacao

PASSO = timedelta(minutes=10)
PASSOS_POR_DIA = 144
DT_H = PASSO.total_seconds() / 3600


@dataclass(frozen=True)
class ParametrosChuva:
    p_comecar: float  # chance de começar a chover em um passo seco
    p_parar: float  # chance de parar de chover em um passo chuvoso
    intensidade_media_mm_h: float


CENARIOS = {
    # ~6% do tempo chovendo, ~2,5 mm/h → ~110 mm/mês (média de Porto Alegre)
    "normal": ParametrosChuva(p_comecar=0.0038, p_parar=0.06, intensidade_media_mm_h=2.5),
    # ~20% do tempo chovendo, ~8 mm/h → ~38 mm/dia
    "chuva_forte": ParametrosChuva(p_comecar=0.012, p_parar=0.05, intensidade_media_mm_h=8.0),
    # ~55% do tempo chovendo, ~9 mm/h → ~120 mm/dia (vários dias seguidos)
    "enchente": ParametrosChuva(p_comecar=0.0244, p_parar=0.02, intensidade_media_mm_h=9.0),
}


@dataclass(frozen=True)
class ParametrosRio:
    k1_h: float  # tempo de resposta do 1º reservatório (horas)
    k2_h: float  # tempo de resposta do 2º reservatório (horas)
    ganho: float  # converte o volume armazenado em metros de nível
    fator_chuva: float = 1.0  # a região chove um pouco mais ou menos que a média
    expoente: float = 0.6


# Calibrado com 20 sementes: na enchente, o Guaíba passa da cota de inundação na maioria
# delas (pico típico 3–5 m; em 2024 o real chegou perto de 5,35 m) e a chuva forte leva o
# rio só até a cota de atenção.
RIOS = {
    "gua-cais": ParametrosRio(k1_h=12, k2_h=48, ganho=0.050, fator_chuva=1.0, expoente=0.8),
    "dil-ipiranga": ParametrosRio(k1_h=0.5, k2_h=1.5, ganho=0.400, fator_chuva=1.1, expoente=0.6),
    "gra-sarandi": ParametrosRio(k1_h=6, k2_h=24, ganho=0.065, fator_chuva=0.9, expoente=0.8),
}
RIO_PADRAO = ParametrosRio(k1_h=1, k2_h=3, ganho=0.15)


@dataclass
class Rio:
    estacao: Estacao
    parametros: ParametrosRio
    s1: float = 0.0
    s2: float = 0.0

    @property
    def nivel(self) -> float:
        return self.estacao.nivel_base_m + self.parametros.ganho * self.s2**self.parametros.expoente

    def passo(self, chuva_mm: float) -> float:
        p = self.parametros
        self.s1 += chuva_mm
        saida1 = self.s1 * DT_H / p.k1_h
        self.s1 -= saida1
        self.s2 += saida1
        self.s2 -= self.s2 * DT_H / p.k2_h
        return self.nivel


def alvo_de_ocupacao(abrigo: Abrigo, estacao: Estacao, nivel: float, peso: float) -> float:
    if abrigo.em_area_de_risco and nivel >= estacao.cota_inundacao_m:
        return 0.0  # o próprio abrigo alagou: evacuado
    faixa = max(estacao.cota_inundacao_m - estacao.cota_alerta_m, 0.1)
    x = (nivel - estacao.cota_alerta_m) / faixa
    return abrigo.capacidade * peso / (1 + math.exp(-4 * x))


TAXA_CHEGADA = 0.20  # por passo: as pessoas chegam rápido quando o rio sobe
TAXA_SAIDA = 0.005  # por passo: saem devagar (ficam ~1 dia depois que o rio baixa)


def proxima_ocupacao(atual: int, alvo: float) -> int:
    diferenca = round(alvo) - atual  # alvo arredondado: com alvo 0,3 o abrigo esvazia de vez
    if diferenca == 0:
        return atual
    taxa = TAXA_CHEGADA if diferenca > 0 else TAXA_SAIDA
    movimento = max(1, round(abs(diferenca) * taxa))
    return atual + movimento if diferenca > 0 else atual - movimento


@dataclass
class Estado:
    chuva_mm: dict[str, float] = field(default_factory=dict)
    nivel_m: dict[str, float] = field(default_factory=dict)
    ocupacao: dict[str, int] = field(default_factory=dict)


class Simulacao:
    def __init__(self, cadastro: Cadastro, semente: int):
        self.cadastro = cadastro
        self.rng = random.Random(semente)
        self.chovendo = False
        self.intensidade_mm_h = 0.0
        self.rios = {
            e.id: Rio(e, RIOS.get(e.id, RIO_PADRAO)) for e in cadastro.estacoes.values() if not e.demo
        }
        self.abrigos = [a for a in cadastro.abrigos.values() if not a.demo]
        # cada abrigo tem uma "procura" própria (alguns lotam, outros não)
        self.peso = {a.id: random.Random(f"{semente}-{a.id}").uniform(0.7, 1.3) for a in self.abrigos}
        self.ocupacao = {a.id: 0 for a in self.abrigos}

    def passo(self, cenario: str) -> Estado:
        p = CENARIOS[cenario]
        if self.chovendo:
            if self.rng.random() < p.p_parar:
                self.chovendo = False
        elif self.rng.random() < p.p_comecar:
            self.chovendo = True
            self.intensidade_mm_h = self.rng.gammavariate(4.0, p.intensidade_media_mm_h / 4)

        chuva_regional = self.intensidade_mm_h * self.rng.lognormvariate(0, 0.3) * DT_H if self.chovendo else 0.0

        estado = Estado()
        for estacao_id, rio in self.rios.items():
            chuva = chuva_regional * rio.parametros.fator_chuva * self.rng.lognormvariate(0, 0.15) if self.chovendo else 0.0
            estado.chuva_mm[estacao_id] = chuva
            estado.nivel_m[estacao_id] = rio.passo(chuva)

        for abrigo in self.abrigos:
            rio = self.rios[abrigo.estacao_proxima_id]
            alvo = alvo_de_ocupacao(abrigo, rio.estacao, rio.nivel, self.peso[abrigo.id])
            novo = proxima_ocupacao(self.ocupacao[abrigo.id], alvo)
            self.ocupacao[abrigo.id] = min(max(novo, 0), abrigo.capacidade)
            estado.ocupacao[abrigo.id] = self.ocupacao[abrigo.id]
        return estado


def calendario_misto(indice: int, total: int) -> str:
    """Período histórico com uma chuva forte (33–40% do período) e uma enchente (60–70%)."""
    fracao = indice / total
    if 0.33 <= fracao < 0.40:
        return "chuva_forte"
    if 0.60 <= fracao < 0.70:
        return "enchente"
    return "normal"
