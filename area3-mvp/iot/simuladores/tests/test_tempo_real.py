from itertools import islice

from simuladores.cadastro import carregar
from simuladores.modelo import PASSOS_POR_DIA, Simulacao, calendario_misto
from simuladores.tempo_real import PASSOS_DO_CICLO, comeca_ciclo_novo, passos, proximo_envio


def aquecida(dias: int = 30) -> tuple[Simulacao, object]:
    """Como o simulador sobe no Compose: semente 42 e 30 dias de aquecimento."""
    cadastro = carregar()
    simulacao = Simulacao(cadastro, 42)
    total = dias * PASSOS_POR_DIA
    for i in range(total):
        simulacao.passo(calendario_misto(i, total))
    return simulacao, cadastro


def test_ciclo_novo_comeca_depois_de_cada_volta_completa():
    assert not comeca_ciclo_novo(1, "ciclo")
    assert not comeca_ciclo_novo(PASSOS_DO_CICLO, "ciclo")
    assert comeca_ciclo_novo(PASSOS_DO_CICLO + 1, "ciclo")
    assert comeca_ciclo_novo(2 * PASSOS_DO_CICLO + 1, "ciclo")
    assert not comeca_ciclo_novo(PASSOS_DO_CICLO + 1, "enchente")  # cenário fixo não recomeça


def test_cada_volta_da_cheia_recomeca_do_normal_e_e_igual_a_primeira():
    simulacao, cadastro = aquecida()
    guaiba = cadastro.estacoes["gua-cais"]
    estados = [estado for _, estado in islice(passos(simulacao, "ciclo"), 2 * PASSOS_DO_CICLO + 1)]
    primeira, segunda, terceira = estados[0], estados[PASSOS_DO_CICLO], estados[2 * PASSOS_DO_CICLO]
    assert max(e.nivel_m["gua-cais"] for e in estados[:PASSOS_DO_CICLO]) >= guaiba.cota_alerta_m  # a cheia acontece
    # A volta seguinte começa com o rio abaixo da cota de atenção menos a folga de 0,10 m: o alerta fecha.
    assert segunda.nivel_m["gua-cais"] < guaiba.cota_atencao_m - 0.10
    assert segunda == primeira and terceira == primeira  # mesmo estado, como um restart


def test_mantem_o_ritmo_normal():
    assert proximo_envio(anterior=100.0, agora=100.2, intervalo=1.0) == 101.0


def test_pequeno_atraso_e_compensado():
    # um passo que demorou um pouco: o próximo sai logo, sem perder o ritmo
    assert proximo_envio(anterior=100.0, agora=101.5, intervalo=1.0) == 101.0


def test_depois_de_uma_pausa_longa_nao_dispara_rajada():
    # 10 minutos parado (notebook dormindo): retoma de agora, não de 600 passos atrás
    assert proximo_envio(anterior=100.0, agora=700.0, intervalo=1.0) == 700.0
