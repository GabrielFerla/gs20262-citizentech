import pytest
from ia import avaliacao


def test_mae_e_rmse():
    assert avaliacao.mae([1, -1, 2]) == pytest.approx(4 / 3)
    assert avaliacao.rmse([3, -4]) == pytest.approx((12.5) ** 0.5)
    assert avaliacao.mae([]) is None


def test_erro_ignora_horas_sem_valor_real():
    resultado = avaliacao.erro([1.0, 2.0, 3.0], [1.5, None, 3.0])
    assert resultado == {"mae_m": 0.25, "rmse_m": pytest.approx(0.354, abs=1e-3), "exemplos": 2}


def test_ganho_percentual():
    assert avaliacao.ganho_percentual(0.02, 0.08) == 75.0
    assert avaliacao.ganho_percentual(0.1, 0.08) == -25.0
    assert avaliacao.ganho_percentual(None, 0.08) is None


def test_antecedencia_conta_as_horas_seguidas_em_que_a_previsao_ja_avisava():
    atuais = [1, 1, 1, 1, 1, 1, 3, 3]
    previstos = [1, 1, 3, 3, 3, 3, 3, 3]  # previsão passa da cota desde a hora 2
    r = avaliacao.alarmes(atuais, previstos, cota=2)
    assert r["eventos"] == 1
    assert r["antecedencias_h"] == [4]
    assert r["antecipados"] == 1
    assert r["alarmes_falsos"] == 0


def test_regra_simples_tem_antecedencia_zero_por_definicao():
    atuais = [1, 1.5, 1.9, 2.2, 2.5, 1.0]
    r = avaliacao.alarmes(atuais, atuais, cota=2)
    assert r["antecedencias_h"] == [0]
    assert r["antecipados"] == 0
    assert r["alarmes_falsos"] == 0


def test_alarme_falso_quando_o_rio_nao_chega_na_cota():
    atuais = [1.0] * 20
    previstos = [1.0] * 5 + [2.5, 2.5] + [1.0] * 13
    r = avaliacao.alarmes(atuais, previstos, cota=2)
    assert r["eventos"] == 0
    assert r["alarmes_falsos"] == 1


def test_aviso_seguido_de_cheia_dentro_do_horizonte_nao_e_falso():
    atuais = [1.0] * 8 + [2.5] * 4
    previstos = [1.0, 1.0, 2.5, 2.5, 1.0, 1.0, 1.0, 1.0, 2.5, 2.5, 2.5, 2.5]  # avisou e desligou antes da cheia
    assert avaliacao.alarmes(atuais, previstos, cota=2)["alarmes_falsos"] == 0


def test_rio_oscilando_na_cota_conta_um_evento_so():
    atuais = [1.5, 2.05, 1.98, 2.03, 1.97, 2.04, 1.0]  # nunca desce 0,10 m abaixo da cota
    assert avaliacao.alarmes(atuais, atuais, cota=2)["eventos"] == 1
    assert avaliacao.cruzamentos_da_cota([1.5, 2.1, 1.85, 2.1], cota=2) == [1, 3]  # desceu além da folga: 2 eventos


def test_antecedencia_nao_passa_do_horizonte_da_previsao():
    # avisou 30 h antes, mas a previsão é de 6 h: os avisos mais antigos erraram cedo
    atuais = [1.0] * 30 + [3.0]
    previstos = [3.0] * 31
    assert avaliacao.alarmes(atuais, previstos, cota=2)["antecedencias_h"] == [6]
    assert avaliacao.alarmes(atuais, previstos, cota=2, horizonte_h=3)["antecedencias_h"] == [3]


def test_series_de_tamanhos_diferentes_dao_erro():
    with pytest.raises(ValueError):
        avaliacao.alarmes([1, 2], [1], cota=2)
