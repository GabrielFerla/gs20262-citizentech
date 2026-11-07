from __future__ import annotations

import pytest
from ia.dados_simulados import base_de_treino
from ia.previsao import ModeloPrevisao
from ia.treino import salvar, treinar


@pytest.fixture(scope="session")
def pasta_modelo(tmp_path_factory):
    """Modelo pequeno de verdade (2 séries de 4 dias), treinado uma vez para todos os testes."""
    pasta = tmp_path_factory.mktemp("modelo")
    modelos, info = treinar(base_de_treino((1001, 1002), 4), 4, dobras=2)
    salvar(pasta, modelos, info)
    return pasta


@pytest.fixture(scope="session")
def modelo(pasta_modelo) -> ModeloPrevisao:
    return ModeloPrevisao.carregar(pasta_modelo)
