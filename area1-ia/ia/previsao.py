"""Previsão do nível do rio daqui a 6 h com o modelo treinado (treino.py)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np

SITUACOES = ("normal", "atencao", "alerta", "inundacao")
LIMIAR_TENDENCIA_M = 0.05  # abaixo disso a variação prevista é "estável"


@dataclass(frozen=True)
class Cotas:
    atencao_m: float
    alerta_m: float
    inundacao_m: float

    def severidade(self, nivel: float) -> int:
        """0 normal, 1 atenção, 2 alerta, 3 inundação (mesma regra das visões gold)."""
        if nivel >= self.inundacao_m:
            return 3
        if nivel >= self.alerta_m:
            return 2
        if nivel >= self.atencao_m:
            return 1
        return 0

    def situacao(self, nivel: float) -> str:
        return SITUACOES[self.severidade(nivel)]

    def por_severidade(self, severidade: int) -> float:
        return (self.atencao_m, self.alerta_m, self.inundacao_m)[severidade - 1]


def tendencia(variacao_m: float) -> str:
    if variacao_m >= LIMIAR_TENDENCIA_M:
        return "subindo"
    if variacao_m <= -LIMIAR_TENDENCIA_M:
        return "descendo"
    return "estavel"


@dataclass(frozen=True)
class Previsao:
    estacao_id: str
    nivel_atual_m: float
    nivel_previsto_m: float
    persistencia_m: float  # regra simples: daqui a 6 h igual a agora
    tendencia: str
    situacao_atual: str
    situacao_prevista: str
    severidade_atual: int
    severidade_prevista: int

    @property
    def variacao_prevista_m(self) -> float:
        return round(self.nivel_previsto_m - self.nivel_atual_m, 2)


class ModeloPrevisao:
    """Um modelo por rio. Prevê a variação em 6 h; a previsão é o nível atual + a variação."""

    def __init__(self, modelos: dict, features: Sequence[str], horizonte_h: int, info: dict | None = None):
        self.modelos = modelos
        self.features = tuple(features)
        self.horizonte_h = horizonte_h
        self.info = info or {}

    @classmethod
    def carregar(cls, pasta: Path) -> ModeloPrevisao:
        dados = joblib.load(pasta / "modelo.joblib")
        info_arquivo = pasta / "modelo.json"
        info = json.loads(info_arquivo.read_text(encoding="utf-8")) if info_arquivo.exists() else {}
        return cls(dados["modelos"], dados["features"], dados["horizonte_h"], info)

    @property
    def estacoes(self) -> list[str]:
        return sorted(self.modelos)

    def nome_do_modelo(self, estacao_id: str) -> str:
        return self.info.get("estacoes", {}).get(estacao_id, {}).get("escolhido", type(self.modelos[estacao_id]).__name__)

    def prever_niveis(self, estacao_id: str, vetores: Sequence[Sequence[float]]) -> list[float]:
        """Nível previsto (m) para cada vetor de features, na ordem de FEATURES."""
        if not vetores:
            return []
        x = np.asarray(vetores, dtype=float)
        variacao = self.modelos[estacao_id].predict(x)
        nivel_atual = x[:, self.features.index("nivel_atual_m")]
        return [round(max(float(v), 0.0), 2) for v in nivel_atual + variacao]

    def prever(self, estacao_id: str, entrada: dict[str, float], cotas: Cotas) -> Previsao:
        """Previsão de uma estação a partir das features atuais (gold.v_ml_features_atual)."""
        vetor = [float(entrada[nome]) for nome in self.features]
        previsto = self.prever_niveis(estacao_id, [vetor])[0]
        return montar_previsao(estacao_id, entrada["nivel_atual_m"], previsto, cotas)


def montar_previsao(estacao_id: str, nivel_atual: float, previsto: float, cotas: Cotas) -> Previsao:
    nivel_atual = round(float(nivel_atual), 2)
    return Previsao(
        estacao_id=estacao_id,
        nivel_atual_m=nivel_atual,
        nivel_previsto_m=previsto,
        persistencia_m=nivel_atual,
        tendencia=tendencia(previsto - nivel_atual),
        situacao_atual=cotas.situacao(nivel_atual),
        situacao_prevista=cotas.situacao(previsto),
        severidade_atual=cotas.severidade(nivel_atual),
        severidade_prevista=cotas.severidade(previsto),
    )


def repetir_nivel_atual(estacao_id: str, nivel_atual: float, cotas: Cotas) -> Previsao:
    """Sem todas as features não há previsão do modelo: vale a regra simples (daqui a 6 h igual a agora)."""
    return montar_previsao(estacao_id, nivel_atual, round(float(nivel_atual), 2), cotas)
