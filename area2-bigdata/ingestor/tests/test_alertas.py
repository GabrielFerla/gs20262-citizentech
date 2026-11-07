import pytest
from ingestor.alertas import Cotas, proximo_alerta, severidade_do_nivel

COTAS = Cotas(atencao=2.0, alerta=2.5, inundacao=3.0)


@pytest.mark.parametrize(("nivel", "esperado"), [(1.0, 0), (1.99, 0), (2.0, 1), (2.6, 2), (3.0, 3), (5.3, 3)])
def test_severidade_do_nivel(nivel, esperado):
    assert severidade_do_nivel(nivel, COTAS) == esperado


def test_nivel_normal_nao_abre_alerta():
    assert proximo_alerta(0, 1.5, COTAS) == ("nenhuma", 0)


def test_abre_alerta_na_severidade_do_nivel():
    assert proximo_alerta(0, 2.1, COTAS) == ("abrir", 1)
    assert proximo_alerta(0, 3.2, COTAS) == ("abrir", 3)


def test_escala_quando_passa_cota_mais_alta():
    assert proximo_alerta(1, 2.55, COTAS) == ("escalar", 2)


def test_nao_rebaixa_enquanto_o_rio_nao_baixar_de_vez():
    # rio voltou para a faixa de atenção: o alerta continua na severidade máxima
    assert proximo_alerta(3, 2.2, COTAS) == ("manter", 3)


def test_folga_evita_abre_e_fecha():
    # 1,95 m está abaixo da cota de atenção (2,00), mas dentro da folga de 0,10 m
    assert proximo_alerta(1, 1.95, COTAS) == ("manter", 1)
    assert proximo_alerta(1, 1.89, COTAS) == ("fechar", 0)
