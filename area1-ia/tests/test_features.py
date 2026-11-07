from datetime import UTC, datetime, timedelta, timezone

import pytest
from ia.features import FEATURES, features_horarias, features_ultimas_leituras

H0 = datetime(2026, 11, 1, 0, 0, tzinfo=UTC)


def minutos(m: int) -> datetime:
    return H0 + timedelta(minutes=m)


def serie_constante(horas: int, nivel: float = 1.0) -> list:
    return [(minutos(10 * i), nivel) for i in range(horas * 6)]


def test_nivel_da_hora_e_a_media_arredondada_meio_para_cima_como_no_postgres():
    # média 1,005: round() do Python daria 1,0 (float/arredondamento bancário); o PostgreSQL dá 1,01
    linhas = features_horarias("x", [(minutos(0), 1.00), (minutos(10), 1.01)], [])
    assert linhas[0].nivel_atual_m == 1.01


def test_chuva_da_hora_e_as_janelas_de_6_e_24_horas():
    chuvas = [(minutos(60 * h + 10), 1.0) for h in range(30)]  # 1 mm por hora, por 30 horas
    linhas = features_horarias("x", serie_constante(30), chuvas)
    assert linhas[0].chuva_1h_mm == 1.0
    assert linhas[0].chuva_6h_mm == 1.0  # só a hora atual existe ainda
    assert linhas[10].chuva_6h_mm == 6.0
    assert linhas[10].chuva_24h_mm == 11.0
    assert linhas[29].chuva_24h_mm == 24.0


def test_chuva_soma_as_leituras_da_hora_e_arredonda_para_uma_casa():
    chuvas = [(minutos(0), 0.25), (minutos(10), 0.1)]
    assert features_horarias("x", serie_constante(1), chuvas)[0].chuva_1h_mm == 0.4  # 0,35 → 0,4


def test_variacao_usa_a_hora_anterior_e_a_primeira_fica_vazia():
    niveis = [(minutos(0), 1.0), (minutos(60), 1.3), (minutos(120), 1.2)]
    linhas = features_horarias("x", niveis, [])
    assert [linha.variacao_1h_m for linha in linhas] == [None, 0.3, -0.1]
    assert not linhas[0].completa() and linhas[1].completa()


def test_alvo_e_o_nivel_6_horas_depois_e_fica_vazio_no_fim():
    niveis = [(minutos(60 * h), 1.0 + h / 10) for h in range(10)]
    linhas = features_horarias("x", niveis, [])
    assert linhas[0].nivel_6h_depois_m == 1.6
    assert linhas[3].nivel_6h_depois_m == 1.9
    assert linhas[4].nivel_6h_depois_m is None


def test_hora_so_com_chuva_nao_tem_nivel_e_a_seguinte_fica_sem_variacao():
    niveis = [(minutos(0), 1.0), (minutos(120), 1.2)]
    chuvas = [(minutos(60), 2.0)]
    linhas = features_horarias("x", niveis, chuvas)
    assert [linha.nivel_atual_m for linha in linhas] == [1.0, None, 1.2]
    assert linhas[2].variacao_1h_m is None  # como o lag() do SQL: a linha anterior não tem nível


def test_horario_com_outro_fuso_e_agrupado_pela_hora_utc():
    brt = timezone(timedelta(hours=-3))
    linhas = features_horarias("x", [(datetime(2026, 11, 1, 21, 50, tzinfo=brt), 1.0)], [])
    assert linhas[0].hora_utc == datetime(2026, 11, 2, 0, 0, tzinfo=UTC)


def test_vetor_segue_a_ordem_das_features():
    linha = features_horarias("x", serie_constante(2, 1.5), [(minutos(70), 3.0)])[1]
    assert linha.vetor() == [getattr(linha, nome) for nome in FEATURES] == [1.5, 0.0, 3.0, 3.0, 3.0]


def test_horario_sem_fuso_e_recusado():
    with pytest.raises(ValueError, match="sem fuso"):
        features_horarias("x", [(datetime(2026, 11, 1, 12, 0), 1.0)], [])


def test_features_ao_vivo_iguais_as_do_treino_quando_a_janela_fecha_a_hora():
    # 30 h de leituras de 10 em 10 min, com nível e chuva variando (chuva com 1 casa, como a do simulador).
    # A última leitura é às hh:50: as 6 últimas formam a hora cheia, e as features ao vivo
    # (gold.v_ml_features_atual) têm de ser iguais às do treino para essa hora.
    passos = 30 * 6
    niveis = [(minutos(10 * i), round(1.0 + 0.013 * i + (0.07 if i % 7 == 0 else 0.0), 2)) for i in range(passos)]
    chuvas = [(minutos(10 * i), round((i * 37 % 11) / 10, 1)) for i in range(passos)]
    ultima_hora = features_horarias("x", niveis, chuvas)[-1]
    ao_vivo = features_ultimas_leituras([v for _, v in reversed(niveis)], [v for _, v in reversed(chuvas)])
    assert ao_vivo == {nome: getattr(ultima_hora, nome) for nome in FEATURES}


def test_features_ao_vivo_sem_duas_horas_de_nivel_nao_tem_variacao():
    ao_vivo = features_ultimas_leituras([1.2, 1.2, 1.1], [0.5])
    assert ao_vivo["nivel_atual_m"] == 1.17 and ao_vivo["variacao_1h_m"] is None
    assert ao_vivo["chuva_24h_mm"] == 0.5
