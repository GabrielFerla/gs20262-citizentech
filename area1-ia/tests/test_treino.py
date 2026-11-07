import numpy as np
import pytest
from ia.dados_simulados import SEMENTES_TREINO, base_de_treino, serie_simulada
from ia.features import FEATURES
from ia.previsao import Cotas, ModeloPrevisao, tendencia
from ia.treino import CANDIDATOS, matriz, salvar, treinar


def test_semente_do_pipeline_fica_fora_do_treino():
    assert 42 not in SEMENTES_TREINO
    with pytest.raises(ValueError, match="pipeline"):
        serie_simulada(42, dias=1)


def test_serie_simulada_e_reproduzivel_e_tem_as_tres_estacoes():
    a, b = serie_simulada(1001, dias=2), serie_simulada(1001, dias=2)
    assert a == b
    assert {linha.estacao_id for linha in a} == {"gua-cais", "dil-ipiranga", "gra-sarandi"}
    assert len([linha for linha in a if linha.estacao_id == "gua-cais"]) == 49  # a última leitura cai à meia-noite


def test_matriz_usa_so_linhas_completas_e_o_alvo_e_a_variacao():
    linhas = serie_simulada(1001, dias=1)
    x, y, grupos = matriz([(7, linha) for linha in linhas])
    validas = [linha for linha in linhas if linha.completa() and linha.nivel_6h_depois_m is not None]
    assert x.shape == (len(validas), len(FEATURES))
    assert len(y) == len(grupos) == len(validas) and set(grupos) == {7}
    assert y[0] == pytest.approx(validas[0].nivel_6h_depois_m - validas[0].nivel_atual_m)


def test_treino_escolhe_um_candidato_por_rio_e_registra_a_validacao(modelo):
    assert modelo.estacoes == ["dil-ipiranga", "gra-sarandi", "gua-cais"]
    for info in modelo.info["estacoes"].values():
        assert info["escolhido"] in CANDIDATOS
        assert set(info["candidatos"]) == set(CANDIDATOS)
        assert info["candidatos"]["regra_simples"]["mae_m"] == info["persistencia"]["mae_m"]
        melhor = min(c["mae_m"] for c in info["candidatos"].values())
        assert info["candidatos"][info["escolhido"]]["mae_m"] == melhor


def test_salvar_e_carregar_mantem_as_previsoes(tmp_path):
    base = base_de_treino((1001, 1002), 3)
    modelos, info = treinar(base, 3, dobras=2)
    salvar(tmp_path, modelos, info)
    carregado = ModeloPrevisao.carregar(tmp_path)
    vetor = [[2.0, 0.1, 5.0, 20.0, 40.0]]
    for estacao_id, m in modelos.items():
        esperado = round(2.0 + float(m.predict(np.array(vetor))[0]), 2)
        assert carregado.prever_niveis(estacao_id, vetor) == [max(esperado, 0.0)]


def test_treino_e_deterministico():
    base = base_de_treino((1001, 1002), 3)
    m1, _ = treinar(base, 3, dobras=2)
    m2, _ = treinar(base, 3, dobras=2)
    x = np.array([[2.0, 0.1, 5.0, 20.0, 40.0], [1.0, 0.0, 0.0, 0.0, 0.0]])
    for estacao_id in m1:
        assert m1[estacao_id].predict(x).tolist() == m2[estacao_id].predict(x).tolist()


class Constante:
    def __init__(self, variacao):
        self.variacao = variacao

    def predict(self, x):
        return np.full(len(x), self.variacao)


def test_previsao_e_nivel_atual_mais_variacao_e_nunca_negativa():
    modelo = ModeloPrevisao({"a": Constante(0.6), "b": Constante(-5.0)}, FEATURES, 6)
    cotas = Cotas(2.0, 2.5, 3.0)
    p = modelo.prever("a", dict(zip(FEATURES, [2.1, 0.1, 5, 30, 60], strict=True)), cotas)
    assert (p.nivel_previsto_m, p.persistencia_m, p.variacao_prevista_m) == (2.7, 2.1, 0.6)
    assert (p.situacao_atual, p.situacao_prevista, p.tendencia) == ("atencao", "alerta", "subindo")
    assert modelo.prever_niveis("b", [[1.0, 0, 0, 0, 0]]) == [0.0]


def test_cotas_e_tendencia():
    cotas = Cotas(2.0, 2.5, 3.0)
    assert [cotas.situacao(n) for n in (1.99, 2.0, 2.5, 3.0)] == ["normal", "atencao", "alerta", "inundacao"]
    assert cotas.por_severidade(2) == 2.5
    assert [tendencia(v) for v in (0.05, 0.04, -0.05)] == ["subindo", "estavel", "descendo"]
