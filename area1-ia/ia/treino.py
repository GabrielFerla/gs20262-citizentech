"""Treina a previsão do nível do rio para daqui a 6 h (um modelo por rio).

    python -m ia.treino --saida area1-ia/modelo

O modelo aprende quanto o rio vai SUBIR ou DESCER em 6 h (o alvo é a variação), a
partir do nível atual, da variação na última hora e da chuva de 1, 6 e 24 h.
Previsão = nível atual + variação prevista. A regra simples (persistência) equivale a
prever variação zero; é com ela que o modelo é comparado.

Para cada rio são testados três candidatos com validação cruzada por semente
(GroupKFold): uma série simulada nunca aparece no treino e na validação ao mesmo tempo,
então não há vazamento. Fica o de menor erro médio (MAE). A própria regra simples é um
dos candidatos: a IA só substitui a persistência no rio em que provou ser melhor.

Roda no "docker build" da imagem da IA: o modelo nasce dentro da imagem.
"""

from __future__ import annotations

import argparse
import json
import logging
import platform
import time
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.base import RegressorMixin
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GroupKFold

from . import avaliacao
from .dados_simulados import DIAS_POR_SEMENTE, SEMENTES_TREINO, base_de_treino
from .features import FEATURES, HORIZONTE_H, LinhaFeatures

log = logging.getLogger("ia.treino")

ARQUIVO_MODELO = "modelo.joblib"
ARQUIVO_INFO = "modelo.json"

# Árvores rasas o suficiente para o arquivo ficar pequeno (poucos MB) e o treino rápido.
CANDIDATOS: dict[str, Callable[[], RegressorMixin]] = {
    # Prevê variação zero = "daqui a 6 h igual a agora". Em empate, fica a mais simples.
    "regra_simples": lambda: DummyRegressor(strategy="constant", constant=0.0),
    "regressao_linear": LinearRegression,
    "random_forest": lambda: RandomForestRegressor(
        n_estimators=60, max_depth=10, min_samples_leaf=5, n_jobs=-1, random_state=42
    ),
}


def matriz(itens: list[tuple[int, LinhaFeatures]]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """X (features), y (variação do nível em 6 h) e o grupo (semente) de cada linha.

    Filtra uma vez só (linhas completas e com alvo), então X, y e grupos ficam sempre alinhados.
    """
    validos = [(s, linha) for s, linha in itens if linha.completa() and linha.nivel_6h_depois_m is not None]
    x = np.array([linha.vetor() for _, linha in validos], dtype=float)
    y = np.array([linha.nivel_6h_depois_m - linha.nivel_atual_m for _, linha in validos], dtype=float)
    return x, y, np.array([s for s, _ in validos])


def validacao_cruzada(x: np.ndarray, y: np.ndarray, grupos: np.ndarray, fabrica, dobras: int) -> dict:
    """Erro de cada dobra junta numa coisa só (previsões fora da amostra de todas as linhas)."""
    previsto = np.zeros_like(y)
    for treino, validacao in GroupKFold(n_splits=dobras).split(x, y, grupos):
        modelo = fabrica().fit(x[treino], y[treino])
        previsto[validacao] = modelo.predict(x[validacao])
    erros = (previsto - y).tolist()
    return {"mae_m": round(avaliacao.mae(erros), 4), "rmse_m": round(avaliacao.rmse(erros), 4)}


def treinar(base: list[tuple[int, LinhaFeatures]], dias_por_semente: int, dobras: int = 4) -> tuple[dict, dict]:
    """Devolve ({estacao_id: modelo}, relatório da validação)."""
    por_estacao: dict[str, list[tuple[int, LinhaFeatures]]] = defaultdict(list)
    for semente, linha in base:
        por_estacao[linha.estacao_id].append((semente, linha))

    modelos, estacoes = {}, {}
    for estacao_id, itens in sorted(por_estacao.items()):
        x, y, grupos = matriz(itens)
        persistencia = {"mae_m": round(avaliacao.mae(y.tolist()), 4), "rmse_m": round(avaliacao.rmse(y.tolist()), 4)}
        candidatos = {nome: validacao_cruzada(x, y, grupos, fabrica, dobras) for nome, fabrica in CANDIDATOS.items()}
        escolhido = min(candidatos, key=lambda nome: candidatos[nome]["mae_m"])
        modelo = CANDIDATOS[escolhido]().fit(x, y)
        if "n_jobs" in modelo.get_params():
            modelo.set_params(n_jobs=1)  # treina em paralelo; prevê numa thread só (mais rápido para 1 linha e sem variação)
        modelos[estacao_id] = modelo
        estacoes[estacao_id] = {
            "escolhido": escolhido,
            "exemplos": len(y),
            "persistencia": persistencia,
            "candidatos": candidatos,
            "ganho_mae_pct": avaliacao.ganho_percentual(candidatos[escolhido]["mae_m"], persistencia["mae_m"]),
        }
        log.info("%s: %s (MAE %.3f m; persistência %.3f m)", estacao_id, escolhido,
                 candidatos[escolhido]["mae_m"], persistencia["mae_m"])

    info = {
        "horizonte_h": HORIZONTE_H,
        "features": list(FEATURES),
        "alvo": "variação do nível em 6 h (previsão = nível atual + variação)",
        "treino": {
            "origem": "simulador da fase 1, calendário misto (uma chuva forte e uma enchente por série)",
            "sementes": sorted({s for s, _ in base}),
            "dias_por_semente": dias_por_semente,
        },
        "validacao": f"GroupKFold({dobras}) por semente: a mesma série nunca fica no treino e na validação",
        "estacoes": estacoes,
        "versoes": {"python": platform.python_version(), "scikit-learn": sklearn.__version__},
    }
    return modelos, info


def salvar(pasta: Path, modelos: dict, info: dict) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    joblib.dump({"features": list(FEATURES), "horizonte_h": HORIZONTE_H, "modelos": modelos}, pasta / ARQUIVO_MODELO,
                compress=3)
    (pasta / ARQUIVO_INFO).write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Treina a previsão do nível dos rios para daqui a 6 h")
    parser.add_argument("--saida", type=Path, default=Path(__file__).resolve().parents[1] / "modelo")
    parser.add_argument("--sementes", type=int, default=len(SEMENTES_TREINO), help="quantas séries simuladas usar")
    parser.add_argument("--dias", type=int, default=DIAS_POR_SEMENTE, help="dias de cada série")
    args = parser.parse_args()

    inicio = time.monotonic()
    sementes = SEMENTES_TREINO[: args.sementes]
    base = base_de_treino(sementes, args.dias)
    log.info("Base de treino: %s linhas horárias de %s séries de %s dias", len(base), len(sementes), args.dias)
    modelos, info = treinar(base, args.dias)
    salvar(args.saida, modelos, info)
    log.info("Modelo salvo em %s (%.0fs)", args.saida, time.monotonic() - inicio)


if __name__ == "__main__":
    main()
