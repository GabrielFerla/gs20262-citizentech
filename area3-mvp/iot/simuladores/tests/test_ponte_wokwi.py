import json
from datetime import UTC, datetime, timedelta

import pytest
from simuladores.ponte_wokwi import Recusa, Verificador, assinar, texto_assinado

CHAVE = b"chave-de-teste"
AGORA = datetime(2026, 11, 7, 15, 0, tzinfo=UTC)


def mensagem(sensor="wok-nivel", valor=1.25, seq=100, quando=AGORA, chave=CHAVE, **extra) -> bytes:
    medido_em = quando.strftime("%Y-%m-%dT%H:%M:%SZ")
    m = {"v": 1, "sensor_id": sensor, "valor": valor, "unidade": "m", "medido_em": medido_em, "seq": seq}
    m["assinatura"] = assinar(chave, texto_assinado(sensor, seq, medido_em, valor))
    m.update(extra)
    return json.dumps(m).encode()


def test_mensagem_assinada_e_repassada_sem_a_assinatura():
    saida = json.loads(Verificador(CHAVE).verificar("wok-nivel", mensagem(), AGORA, 0.0))
    assert "assinatura" not in saida
    assert saida["valor"] == 1.25


@pytest.mark.parametrize(
    ("sensor_topico", "conteudo", "trecho"),
    [
        ("gua-cais-nivel", mensagem(sensor="gua-cais-nivel"), "não permitido"),
        ("wok-nivel", mensagem(chave=b"chave-errada"), "assinatura"),
        ("wok-nivel", mensagem(quando=AGORA - timedelta(minutes=10)), "janela"),
        ("wok-nivel", mensagem(sensor="wok-chuva"), "difere"),
        ("wok-nivel", b"{nao e json", "JSON"),
        ("wok-nivel", mensagem(valor=1.25, assinatura="00" * 32), "assinatura"),
    ],
)
def test_mensagens_recusadas(sensor_topico, conteudo, trecho):
    with pytest.raises(Recusa, match=trecho):
        Verificador(CHAVE).verificar(sensor_topico, conteudo, AGORA, 0.0)


def test_valor_alterado_no_caminho_invalida_a_assinatura():
    original = json.loads(mensagem(valor=1.25))
    original["valor"] = 3.0  # alguém mudou o nível no broker público
    with pytest.raises(Recusa, match="assinatura"):
        Verificador(CHAVE).verificar("wok-nivel", json.dumps(original).encode(), AGORA, 0.0)


def test_reenvio_da_mesma_mensagem_e_recusado():
    v = Verificador(CHAVE)
    v.verificar("wok-nivel", mensagem(seq=100), AGORA, 0.0)
    with pytest.raises(Recusa, match="seq"):
        v.verificar("wok-nivel", mensagem(seq=100), AGORA, 5.0)


def test_mais_de_uma_mensagem_por_segundo_e_recusada():
    v = Verificador(CHAVE)
    v.verificar("wok-nivel", mensagem(seq=100), AGORA, 10.0)
    with pytest.raises(Recusa, match="por segundo"):
        v.verificar("wok-nivel", mensagem(seq=101), AGORA, 10.5)
    v.verificar("wok-nivel", mensagem(seq=102), AGORA, 11.5)


def test_sem_chave_aceita_mensagem_sem_assinatura():
    sem_assinatura = json.loads(mensagem())
    del sem_assinatura["assinatura"]
    Verificador(None).verificar("wok-nivel", json.dumps(sem_assinatura).encode(), AGORA, 0.0)


def test_valor_gigante_e_recusado_sem_derrubar_a_ponte():
    medido_em = AGORA.strftime("%Y-%m-%dT%H:%M:%SZ")
    gigante = '{"v":1,"sensor_id":"wok-nivel","valor":1' + "0" * 400 + ',"unidade":"m","medido_em":"' + medido_em + '","seq":1}'
    with pytest.raises(Recusa, match="grande demais"):
        Verificador(CHAVE).verificar("wok-nivel", gigante.encode(), AGORA, 0.0)


def test_mensagem_medida_antes_de_a_ponte_reiniciar_e_recusada():
    capturada = mensagem(seq=100, quando=AGORA - timedelta(seconds=30))
    reiniciada = Verificador(CHAVE, aceitar_a_partir_de=AGORA)
    with pytest.raises(Recusa, match="início da ponte"):
        reiniciada.verificar("wok-nivel", capturada, AGORA, 0.0)
    reiniciada.verificar("wok-nivel", mensagem(seq=101, quando=AGORA), AGORA, 0.0)
