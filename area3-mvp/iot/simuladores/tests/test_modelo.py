from simuladores.cadastro import Estacao, carregar
from simuladores.modelo import (
    PASSOS_POR_DIA,
    RIOS,
    Rio,
    Simulacao,
    calendario_misto,
    proxima_ocupacao,
)

CADASTRO = carregar()


def rodar(semente, passos, cenario="enchente"):
    sim = Simulacao(CADASTRO, semente)
    return [sim.passo(cenario) for _ in range(passos)], sim


def test_mesma_semente_gera_os_mesmos_dados():
    a, _ = rodar(42, 300)
    b, _ = rodar(42, 300)
    assert [e.nivel_m for e in a] == [e.nivel_m for e in b]
    assert [e.ocupacao for e in a] == [e.ocupacao for e in b]


def test_sementes_diferentes_geram_dados_diferentes():
    a, _ = rodar(1, 300)
    b, _ = rodar(2, 300)
    assert [e.nivel_m for e in a] != [e.nivel_m for e in b]


def _rio(estacao_id):
    e = CADASTRO.estacoes[estacao_id]
    return Rio(Estacao(e.id, e.nivel_base_m, e.cota_atencao_m, e.cota_alerta_m, e.cota_inundacao_m, False),
               RIOS[estacao_id])


def test_pico_do_rio_vem_depois_do_pico_da_chuva():
    rio = _rio("gua-cais")
    chuva = [5.0] * 36 + [0.0] * 600  # 6 horas de chuva forte e depois seca
    niveis = [rio.passo(c) for c in chuva]
    passo_do_pico = niveis.index(max(niveis))
    assert passo_do_pico > 36 + 6 * 6  # o Guaíba atinge o pico mais de 6 h depois de parar a chuva


def test_arroio_responde_mais_rapido_que_o_guaiba():
    chuva = [5.0] * 36 + [0.0] * 600
    pico = {}
    for estacao in ("gua-cais", "dil-ipiranga"):
        rio = _rio(estacao)
        niveis = [rio.passo(c) for c in chuva]
        pico[estacao] = niveis.index(max(niveis))
    assert pico["dil-ipiranga"] < pico["gua-cais"]


def test_rio_volta_ao_nivel_base_quando_para_de_chover():
    rio = _rio("dil-ipiranga")
    for _ in range(36):
        rio.passo(5.0)
    for _ in range(PASSOS_POR_DIA):
        nivel = rio.passo(0.0)
    assert abs(nivel - rio.estacao.nivel_base_m) < 0.05


def test_ocupacao_nunca_passa_da_capacidade_nem_fica_negativa():
    estados, sim = rodar(7, 6 * PASSOS_POR_DIA)
    capacidade = {a.id: a.capacidade for a in sim.abrigos}
    for estado in estados:
        for abrigo_id, ocupacao in estado.ocupacao.items():
            assert 0 <= ocupacao <= capacidade[abrigo_id]


def test_enchente_enche_os_abrigos():
    estados, _ = rodar(7, 4 * PASSOS_POR_DIA)
    assert max(sum(e.ocupacao.values()) for e in estados) > 500


def test_ocupacao_converge_para_o_alvo():
    ocupacao = 0
    for _ in range(100):
        ocupacao = proxima_ocupacao(ocupacao, 120.0)
    assert abs(ocupacao - 120) <= 1
    for _ in range(3000):
        ocupacao = proxima_ocupacao(ocupacao, 0.0)
    assert ocupacao == 0


def test_calendario_misto_tem_chuva_forte_e_enchente():
    total = 30 * PASSOS_POR_DIA
    cenarios = {calendario_misto(i, total) for i in range(total)}
    assert cenarios == {"normal", "chuva_forte", "enchente"}
