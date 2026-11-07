import json

from apoio_ingestor import AGORA, horario
from ingestor.processamento import processar

TOPICO = "citizentech/v1/sim/gua-cais-nivel"


def nivel(valor, minutos, sensor="gua-cais-nivel"):
    return json.dumps({"v": 1, "sensor_id": sensor, "valor": valor, "unidade": "m", "medido_em": horario(minutos)})


def enviar(repo, conteudo, topico=TOPICO, canal="mqtt"):
    return processar(repo, conteudo, canal=canal, topico=topico, agora=AGORA)


def test_mensagem_valida_e_aceita_e_vai_para_silver(repo):
    r = enviar(repo, nivel(1.5, 0))
    assert r.status == "aceita"
    assert len(repo.leituras) == 1
    assert [m["status"] for m in repo.mensagens.values()] == ["aceita"]


def test_mesma_mensagem_duas_vezes_e_registrada_uma_vez(repo):
    assert enviar(repo, nivel(1.5, 0)).status == "aceita"
    assert enviar(repo, nivel(1.5, 0)).status == "repetida"
    assert len(repo.mensagens) == 1
    assert len(repo.leituras) == 1


def test_mesmo_sensor_e_horario_com_outro_valor_e_duplicada(repo):
    enviar(repo, nivel(1.5, 0))
    r = enviar(repo, nivel(1.6, 0))
    assert r.status == "duplicada"
    assert len(repo.leituras) == 1
    assert len(repo.mensagens) == 2  # fica registrada no bronze para auditoria


def test_json_quebrado_fica_no_bronze_como_rejeitado(repo):
    r = enviar(repo, '{"v": 1, "sensor_id": ')
    assert r.status == "rejeitada"
    assert r.motivo.startswith("json:")
    assert repo.leituras == {}
    assert [m["status"] for m in repo.mensagens.values()] == ["rejeitada"]


def test_sensor_publicando_em_origem_errada_e_rejeitado(repo):
    r = enviar(repo, nivel(1.5, 0), topico="citizentech/v1/wokwi/gua-cais-nivel")
    assert r.status == "rejeitada"
    assert r.motivo.startswith("origem:")


def test_mensagem_grande_demais_e_rejeitada(repo):
    r = enviar(repo, '{"lixo": "' + "x" * 5000 + '"}')
    assert r.status == "rejeitada"
    assert r.motivo.startswith("tamanho:")


def test_arquivo_nao_tem_topico_e_e_aceito(repo):
    r = processar(repo, nivel(1.5, 0), canal="arquivo", agora=AGORA)
    assert r.status == "aceita"


def test_ciclo_do_alerta_abre_escala_e_fecha_uma_vez(repo):
    acoes = [enviar(repo, nivel(v, i * 10)).alerta for i, v in enumerate([1.8, 2.1, 2.3, 2.6, 2.4, 1.95, 1.85, 1.7])]
    assert acoes == [None, "abrir", None, "escalar", None, None, "fechar", None]
    assert len(repo.alertas) == 1
    alerta = repo.alertas[0]
    assert alerta["severidade"] == 2
    assert alerta["pico_m"] == 2.6
    assert alerta["fechado_em"] is not None


def test_leitura_suspeita_nao_abre_alerta(repo):
    enviar(repo, nivel(1.5, 0))
    r = enviar(repo, nivel(4.0, 10))  # pulo de 2,5 m em 10 minutos: falha do sensor
    assert r.status == "aceita"
    assert r.qualidade == "suspeita"
    assert repo.alertas == []
