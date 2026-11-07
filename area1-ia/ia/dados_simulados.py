"""Histórico de treino: meses simulados com o MESMO simulador da fase 1, outras sementes.

Por que não treinar só com o banco? Os 30 dias do pipeline têm 1 ou 2 cheias por rio.
Treinar e medir nesses mesmos poucos eventos daria uma nota enganosa. Então:
- treino: 24 meses simulados (sementes 1001 a 1024), cada um com uma chuva forte e uma enchente;
- teste:  os 30 dias do pipeline (semente 42, gold.v_ml_features), que o modelo nunca vê.

As leituras passam pelo mesmo gerador de mensagens da fase 1 (ruído do sensor,
arredondamento e 0,5% de leituras que não chegam) e viram features com a mesma regra
da visão SQL (features.py).
"""

from __future__ import annotations

import json
import random
from dataclasses import replace
from datetime import UTC, datetime

from simuladores.cadastro import Cadastro, carregar
from simuladores.mensagens import Falhas, GeradorDeMensagens
from simuladores.modelo import PASSO, PASSOS_POR_DIA, Simulacao, calendario_misto

from .features import LinhaFeatures, features_horarias

SEMENTES_TREINO = tuple(range(1001, 1025))
SEMENTE_PIPELINE = 42  # a do histórico do banco: fica de fora do treino
DIAS_POR_SEMENTE = 30
# Picos e mensagens corrompidas são barrados pelo pipeline antes do gold; aqui só falta leitura.
FALHAS_TREINO = Falhas(falta=0.005, pico=0.0, corrompida=0.0)
INICIO = datetime(2025, 1, 1, tzinfo=UTC)


def so_estacoes(cadastro: Cadastro) -> Cadastro:
    """Mesmo cadastro, mas o gerador só cria mensagens dos sensores de nível e chuva (4x mais rápido)."""
    return replace(cadastro, sensores=[s for s in cadastro.sensores if s.estacao_id is not None])


def serie_simulada(semente: int, dias: int = DIAS_POR_SEMENTE, cadastro: Cadastro | None = None) -> list[LinhaFeatures]:
    """Features horárias de uma série simulada (calendário misto, como o histórico da fase 1)."""
    if semente == SEMENTE_PIPELINE:
        raise ValueError("a semente 42 é a do pipeline (conjunto de teste); use outra para treinar")
    cadastro = so_estacoes(cadastro or carregar())
    simulacao = Simulacao(cadastro, semente)
    gerador = GeradorDeMensagens(cadastro, random.Random(semente + 1), FALHAS_TREINO)
    sensores = {s.id: s for s in gerador.sensores}
    niveis: dict[str, list] = {e: [] for e in simulacao.rios}
    chuvas: dict[str, list] = {e: [] for e in simulacao.rios}

    total = dias * PASSOS_POR_DIA
    for i in range(total):
        estado = simulacao.passo(calendario_misto(i, total))
        quando = INICIO + (i + 1) * PASSO
        for sensor_id, conteudo in gerador.mensagens(estado, quando):
            sensor = sensores[sensor_id]
            if sensor.estacao_id not in simulacao.rios:
                continue  # estação de demonstração (Wokwi): não entra no treino
            destino = niveis if sensor.tipo == "nivel_rio" else chuvas
            destino[sensor.estacao_id].append((quando, float(json.loads(conteudo)["valor"])))

    linhas: list[LinhaFeatures] = []
    for estacao_id in simulacao.rios:
        linhas += features_horarias(estacao_id, niveis[estacao_id], chuvas[estacao_id])
    return linhas


def base_de_treino(
    sementes: tuple[int, ...] = SEMENTES_TREINO, dias: int = DIAS_POR_SEMENTE
) -> list[tuple[int, LinhaFeatures]]:
    """(semente, linha) de todas as séries; a semente serve de grupo na validação cruzada."""
    cadastro = carregar()
    return [(semente, linha) for semente in sementes for linha in serie_simulada(semente, dias, cadastro)]
