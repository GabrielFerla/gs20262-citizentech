"""Testes de integração: rodam contra o docker compose de verdade (broker, banco, ingestor).

    docker compose --profile ferramentas run --rm testes

Usam os sensores de demonstração do Wokwi (estação demo-wokwi, abrigo abr-demo), publicando
com o usuário da ponte, para não interferir na simulação que está rodando.
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import UTC, datetime

import paho.mqtt.client as mqtt
import psycopg
import pytest
from paho.mqtt.enums import CallbackAPIVersion
from psycopg import errors

pytestmark = pytest.mark.integration

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "11883"))
SENHA = {
    "ingestor": os.environ.get("MQTT_INGESTOR_PASSWORD", ""),
    "simulador": os.environ.get("MQTT_SIMULADOR_PASSWORD", ""),
    "ponte": os.environ.get("MQTT_PONTE_PASSWORD", ""),
}
TOPICO_WOKWI = "citizentech/v1/wokwi/{}"


def dsn(usuario: str, senha: str) -> str:
    return psycopg.conninfo.make_conninfo(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "55432"),
        dbname=os.environ.get("POSTGRES_DB", "citizentech"),
        user=usuario,
        password=senha,
    )


@pytest.fixture(scope="module")
def db():
    with psycopg.connect(
        dsn(os.environ.get("POSTGRES_USER", "migrador"), os.environ["POSTGRES_PASSWORD"]), autocommit=True
    ) as conn:
        yield conn


def consultar(db, sql: str, *params):
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def esperar(db, sql: str, *params, condicao=lambda linhas: bool(linhas), tempo_s: float = 15):
    limite = time.monotonic() + tempo_s
    while True:
        linhas = consultar(db, sql, *params)
        if condicao(linhas) or time.monotonic() > limite:
            return linhas
        time.sleep(0.3)


def agora_iso() -> str:
    time.sleep(0.002)  # garante horários diferentes entre mensagens seguidas
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


_seq = int(time.time())


def leitura(sensor_id: str, valor: float, unidade: str = "m") -> str:
    global _seq
    _seq += 1
    return json.dumps({"v": 1, "sensor_id": sensor_id, "valor": valor, "unidade": unidade,
                       "medido_em": agora_iso(), "seq": _seq})


def publicar(usuario: str, topico: str, *conteudos: str) -> None:
    cliente = mqtt.Client(CallbackAPIVersion.VERSION2, client_id=f"teste-{usuario}-{time.time_ns()}")
    cliente.username_pw_set(usuario, SENHA[usuario])
    cliente.connect(MQTT_HOST, MQTT_PORT)
    cliente.loop_start()
    for conteudo in conteudos:
        cliente.publish(topico, conteudo, qos=1).wait_for_publish(timeout=5)
    cliente.disconnect()
    cliente.loop_stop()


def na_silver(db, conteudo: str) -> int:
    m = json.loads(conteudo)
    linhas = esperar(db, "SELECT count(*) FROM silver.leitura WHERE sensor_id = %s AND medido_em = %s",
                     m["sensor_id"], m["medido_em"], condicao=lambda r: r[0][0] > 0)
    return linhas[0][0]


# ----------------------------------------------------------------------------- ingestão
def test_it01_mensagem_publicada_chega_na_silver(db):
    conteudo = leitura("wok-nivel", 0.31)
    publicar("ponte", TOPICO_WOKWI.format("wok-nivel"), conteudo)
    assert na_silver(db, conteudo) == 1


def test_it02_mesma_mensagem_duas_vezes_vira_uma_linha(db):
    repetida, sentinela = leitura("wok-nivel", 0.32), leitura("wok-nivel", 0.33)
    publicar("ponte", TOPICO_WOKWI.format("wok-nivel"), repetida, repetida, sentinela)
    na_silver(db, sentinela)  # a sentinela chegou, então a repetida também já foi processada
    assert consultar(db, "SELECT count(*) FROM bronze.mensagem WHERE conteudo = %s", repetida)[0][0] == 1
    assert na_silver(db, repetida) == 1


def test_it03_mensagem_invalida_fica_rejeitada_no_bronze(db):
    invalida = leitura("wok-nivel", 31, unidade="cm")
    publicar("ponte", TOPICO_WOKWI.format("wok-nivel"), invalida)
    linhas = esperar(db, "SELECT status, motivo FROM bronze.mensagem WHERE conteudo = %s", invalida)
    assert linhas and linhas[0][0] == "rejeitada"
    assert linhas[0][1].startswith("contrato:")
    medido_em = json.loads(invalida)["medido_em"]
    assert consultar(db, "SELECT count(*) FROM silver.leitura WHERE medido_em = %s", medido_em)[0][0] == 0


def test_it04_sensor_publicando_com_origem_errada_e_rejeitado(db):
    # o simulador pode publicar em sim/, mas o sensor wok-nivel só é aceito vindo do Wokwi
    conteudo = leitura("wok-nivel", 0.34)
    publicar("simulador", "citizentech/v1/sim/wok-nivel", conteudo)
    linhas = esperar(db, "SELECT status, motivo FROM bronze.mensagem WHERE conteudo = %s", conteudo)
    assert linhas and linhas[0][0] == "rejeitada" and linhas[0][1].startswith("origem:")


# ----------------------------------------------------------------------------- segurança
def test_it05_conexao_anonima_e_recusada():
    resultado: dict = {}
    conectou = threading.Event()

    def ao_conectar(_c, _u, _f, reason_code, _p):
        resultado["rc"] = reason_code
        conectou.set()

    cliente = mqtt.Client(CallbackAPIVersion.VERSION2, client_id=f"anonimo-{time.time_ns()}")
    cliente.on_connect = ao_conectar
    cliente.connect(MQTT_HOST, MQTT_PORT)
    cliente.loop_start()
    conectou.wait(5)
    cliente.loop_stop()
    assert resultado["rc"].is_failure


def test_it06_acl_impede_simulador_de_publicar_como_wokwi(db):
    conteudo = leitura("wok-nivel", 0.35)
    publicar("simulador", TOPICO_WOKWI.format("wok-nivel"), conteudo)
    time.sleep(3)
    assert consultar(db, "SELECT count(*) FROM bronze.mensagem WHERE conteudo = %s", conteudo)[0][0] == 0


def test_it07_usuario_do_dashboard_so_le_a_camada_gold():
    with psycopg.connect(dsn("bi_ro", os.environ["BI_DB_PASSWORD"]), autocommit=True) as conn:
        conn.execute("SELECT * FROM gold.v_kpis").fetchall()
        with pytest.raises(errors.InsufficientPrivilege):
            conn.execute("SELECT * FROM silver.leitura LIMIT 1")


def test_it08_ingestor_nao_consegue_apagar_dados():
    with psycopg.connect(dsn("ingestor_rw", os.environ["INGESTOR_DB_PASSWORD"]), autocommit=True) as conn:
        with pytest.raises(errors.InsufficientPrivilege):
            conn.execute("DELETE FROM silver.leitura WHERE sensor_id = 'wok-nivel'")


# ----------------------------------------------------------------------------- regras de negócio
def test_it09_alerta_abre_escala_e_fecha_uma_vez(db):
    # cotas da estação demo: atenção 0,80 | alerta 1,20 | inundação 1,60
    inicio = agora_iso()
    sequencia = [leitura("wok-nivel", v) for v in (0.30, 1.00, 1.30, 0.75, 0.50)]
    publicar("ponte", TOPICO_WOKWI.format("wok-nivel"), *sequencia)
    na_silver(db, sequencia[-1])
    alertas = esperar(
        db,
        "SELECT severidade, pico_m::float, fechado_em IS NOT NULL FROM silver.alerta "
        "WHERE estacao_id = 'demo-wokwi' AND aberto_em >= %s ORDER BY aberto_em",
        inicio,
        condicao=lambda r: bool(r) and r[-1][2],
    )
    assert alertas == [(2, pytest.approx(1.30), True)]


def test_it10_vagas_do_abrigo_sao_calculadas(db):
    conteudo = leitura("wok-ocup", 45, unidade="pessoas")
    publicar("ponte", TOPICO_WOKWI.format("wok-ocup"), conteudo)
    na_silver(db, conteudo)
    linha = consultar(db, "SELECT ocupacao, vagas, status_lotacao, recomendavel FROM gold.v_abrigo_status "
                          "WHERE abrigo_id = 'abr-demo'")[0]
    assert linha == (45, 5, "quase_cheio", False)  # abrigo de demonstração nunca é recomendado


# ----------------------------------------------------------------------------- dados e operação
def test_it11_migracoes_rodam_de_novo_sem_mudar_nada():
    from ingestor.config import achar_pasta
    from ingestor.migrar import aplicar_migracoes

    with psycopg.connect(dsn(os.environ.get("POSTGRES_USER", "migrador"), os.environ["POSTGRES_PASSWORD"])) as conn:
        assert aplicar_migracoes(conn, achar_pasta("MIGRACOES_DIR", "area2-bigdata/db/migrations")) == []


def test_it12_historico_foi_carregado_e_gera_base_de_treino(db):
    cargas = consultar(db, "SELECT count(*) FROM bronze.carga WHERE concluida_em IS NOT NULL")[0][0]
    assert cargas >= 1
    exemplos = consultar(db, "SELECT count(*) FROM gold.v_ml_features WHERE nivel_6h_depois_m IS NOT NULL")[0][0]
    assert exemplos > 0


def test_it13_simulador_esta_publicando_em_tempo_real(db):
    linhas = esperar(
        db,
        "SELECT count(*) FROM silver.leitura WHERE canal = 'mqtt' AND sensor_id LIKE 'gua-%%' "
        "AND recebido_em > now() - interval '1 minute'",
        condicao=lambda r: r[0][0] > 0,
    )
    assert linhas[0][0] > 0
