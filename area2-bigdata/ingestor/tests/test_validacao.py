from datetime import timedelta

import pytest
from apoio_ingestor import AGORA, SENSORES, horario
from ingestor.validacao import Leitura, LeituraAnterior, Rejeicao, avaliar_qualidade, validar


def mensagem(**campos):
    base = {"v": 1, "sensor_id": "gua-cais-nivel", "valor": 1.5, "unidade": "m", "medido_em": horario(0)}
    base.update(campos)
    return base


def test_leitura_valida():
    leitura = validar(mensagem(), SENSORES, AGORA, "sim", "gua-cais-nivel")
    assert leitura.valor == 1.5
    assert leitura.sensor.id == "gua-cais-nivel"


@pytest.mark.parametrize(
    ("campos", "origem", "sensor_topico", "categoria"),
    [
        ({"valor": "1.5"}, None, None, "contrato"),
        ({"sensor_id": "nao-existe"}, None, None, "sensor"),
        ({"sensor_id": "sensor-desligado", "unidade": "mm"}, None, None, "sensor"),
        ({}, "wokwi", "gua-cais-nivel", "origem"),
        ({}, "sim", "outro-sensor", "topico"),
        ({"unidade": "mm"}, None, None, "unidade"),
        ({"valor": 99.0}, None, None, "faixa"),
        ({"valor": -0.5}, None, None, "faixa"),
        ({"sensor_id": "abr-01-ocup", "unidade": "pessoas", "valor": 10.5}, None, None, "faixa"),
        ({"valor": 10**400}, None, None, "faixa"),
        ({"medido_em": "2026-11-07T15:30:00Z"}, None, None, "horario"),
        ({"medido_em": "2026-13-45T15:00:00Z"}, None, None, "horario"),
    ],
)
def test_leitura_recusada(campos, origem, sensor_topico, categoria):
    with pytest.raises(Rejeicao) as erro:
        validar(mensagem(**campos), SENSORES, AGORA, origem, sensor_topico)
    assert str(erro.value).startswith(categoria + ":")


def test_tolera_relogio_um_pouco_adiantado():
    um_minuto_depois = (AGORA + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    validar(mensagem(medido_em=um_minuto_depois), SENSORES, AGORA)


def _leitura(valor, minutos):
    return Leitura(SENSORES["gua-cais-nivel"], valor, AGORA + timedelta(minutes=minutos))


def _anterior(valor, minutos, qualidade="ok"):
    return LeituraAnterior(valor, AGORA + timedelta(minutes=minutos), qualidade)


def test_variacao_normal_e_ok():
    assert avaliar_qualidade(_leitura(1.60, 10), _anterior(1.50, 0), None) == "ok"


def test_pico_isolado_e_suspeito_e_a_volta_e_ok():
    assert avaliar_qualidade(_leitura(3.50, 10), _anterior(1.50, 0), None) == "suspeita"
    # depois do pico a leitura volta ao normal: comparada à última leitura confiável, é ok
    assert avaliar_qualidade(_leitura(1.52, 20), _anterior(3.50, 10, "suspeita"), _anterior(1.50, 0)) == "ok"


def test_mudanca_de_patamar_so_marca_a_primeira():
    # sensor reiniciado num patamar novo: a segunda leitura já segue a anterior
    assert avaliar_qualidade(_leitura(2.52, 20), _anterior(2.50, 10, "suspeita"), _anterior(1.50, 0)) == "ok"


def test_salto_depois_de_muito_tempo_sem_leitura_e_ok():
    assert avaliar_qualidade(_leitura(3.50, 90), _anterior(1.50, 0), None) == "ok"
