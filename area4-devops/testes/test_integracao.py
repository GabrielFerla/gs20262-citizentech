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
import urllib.error
import urllib.parse
import urllib.request
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


def test_it14_migracao_editada_depois_de_aplicada_para_com_erro(tmp_path):
    import shutil

    from ingestor.config import achar_pasta
    from ingestor.migrar import MigracaoAlterada, aplicar_migracoes

    copia = tmp_path / "migrations"
    shutil.copytree(achar_pasta("MIGRACOES_DIR", "area2-bigdata/db/migrations"), copia)
    gold = copia / "004_gold.sql"
    gold.write_text(gold.read_text(encoding="utf-8") + "\n-- edição depois de aplicada\n", encoding="utf-8")
    with psycopg.connect(dsn(os.environ.get("POSTGRES_USER", "migrador"), os.environ["POSTGRES_PASSWORD"])) as conn:
        with pytest.raises(MigracaoAlterada, match="004_gold.sql"):
            aplicar_migracoes(conn, copia)


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


# ----------------------------------------------------------------------------- IA (área 1)
API_URL = os.environ.get("API_URL", "http://localhost:8000")
ESTACOES_REAIS = {"gua-cais", "dil-ipiranga", "gra-sarandi"}


def api(caminho: str, corpo: dict | None = None, **params):
    """GET (ou POST com corpo JSON) na API da IA. Devolve (status, JSON)."""
    url = API_URL + caminho + ("?" + urllib.parse.urlencode(params) if params else "")
    dados = json.dumps(corpo).encode() if corpo is not None else None
    pedido = urllib.request.Request(url, data=dados, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(pedido, timeout=15) as resposta:
            return resposta.status, json.loads(resposta.read())
    except urllib.error.HTTPError as erro:
        corpo_erro = erro.read()
        try:
            return erro.code, json.loads(corpo_erro or b"{}")
        except ValueError:  # erro em texto puro (ex.: 500 do servidor): o status continua aparecendo no assert
            return erro.code, {"texto": corpo_erro.decode(errors="replace")}


def test_it15_api_da_ia_esta_saudavel():
    status, corpo = api("/saude")
    assert status == 200
    assert corpo["banco"] is True
    assert set(corpo["modelo"]["estacoes"]) == ESTACOES_REAIS


def test_it16_previsao_de_6h_para_os_tres_rios():
    status, previsoes = api("/previsao")
    assert status == 200
    assert {p["estacao_id"] for p in previsoes} == ESTACOES_REAIS
    for p in previsoes:
        assert 0 <= p["nivel_previsto_6h_m"] < 15
        assert p["persistencia_6h_m"] == p["nivel_atual_m"]
        assert p["situacao_prevista"] in ("normal", "atencao", "alerta", "inundacao")
        assert set(p["entrada"]) == {"nivel_atual_m", "variacao_1h_m", "chuva_1h_mm", "chuva_6h_mm", "chuva_24h_mm"}


def test_it17_recomendacao_so_traz_abrigos_aptos_e_explica_os_evitados(db):
    status, rec = api("/abrigos/recomendacao", bairro="navegantes", pessoas=4)
    assert status == 200
    reais = {linha[0] for linha in consultar(db, "SELECT abrigo_id FROM gold.v_abrigo_status WHERE NOT demo")}
    distancias = [a["distancia_km"] for a in rec["recomendados"]]
    assert distancias == sorted(distancias)
    for a in rec["recomendados"]:
        assert a["abrigo_id"] in reais
        assert a["apto"] and a["vagas"] >= 4 and a["vagas_previstas_na_chegada"] >= 4
        perigo = {"alerta", "inundacao"} & {a["situacao_atual_regiao"], a["situacao_prevista_regiao"]}
        assert not (a["em_area_de_risco"] and perigo)
    assert all(a["motivo"] for a in rec["evitados"])
    assert api("/abrigos/recomendacao", bairro="nao-existe")[0] == 404


def test_it18_features_do_python_iguais_as_da_visao_sql(db):
    """O modelo foi treinado com features calculadas em Python: ao vivo elas vêm do SQL. Têm de ser iguais."""
    from collections import defaultdict

    from ia.features import features_horarias

    series = defaultdict(lambda: ([], []))
    for estacao_id, tipo, medido_em, valor in consultar(
        db,
        "SELECT s.estacao_id, s.tipo, l.medido_em, l.valor::float FROM silver.leitura l "
        "JOIN silver.sensor s ON s.id = l.sensor_id JOIN silver.estacao e ON e.id = s.estacao_id AND NOT e.demo "
        "WHERE l.qualidade = 'ok' AND l.canal = 'arquivo'",
    ):
        series[estacao_id][0 if tipo == "nivel_rio" else 1].append((medido_em, valor))
    sql = {
        (r[0], r[1]): r[2:]
        for r in consultar(db, "SELECT estacao_id, hora_utc, nivel_atual_m::float, variacao_1h_m::float, chuva_1h_mm::float, "
                               "chuva_6h_mm::float, chuva_24h_mm::float, nivel_6h_depois_m::float FROM gold.v_ml_features")
    }
    python = {}
    for estacao_id, (niveis, chuvas) in series.items():
        for linha in features_horarias(estacao_id, niveis, chuvas):
            python[estacao_id, linha.hora_utc] = (linha.nivel_atual_m, linha.variacao_1h_m, linha.chuva_1h_mm,
                                                  linha.chuva_6h_mm, linha.chuva_24h_mm, linha.nivel_6h_depois_m)
    assert python.keys() == sql.keys() and len(sql) > 0
    for chave, valores in sql.items():
        for a, b in zip(python[chave], valores, strict=True):
            assert (a is None and b is None) or abs(a - b) < 1e-9, (chave, python[chave], valores)


def test_it19_usuario_da_ia_so_le_a_camada_gold():
    with psycopg.connect(dsn("ia_ro", os.environ["IA_DB_PASSWORD"]), autocommit=True) as conn:
        assert len(conn.execute("SELECT * FROM gold.v_ml_features_atual").fetchall()) == len(ESTACOES_REAIS)
        with pytest.raises(errors.InsufficientPrivilege):
            conn.execute("SELECT * FROM silver.leitura LIMIT 1")


def test_it20_mensagem_gerada_passa_nas_regras_de_linguagem_simples():
    entrada = {"estacao": "Guaíba - Cais Mauá", "corpo_hidrico": "Lago Guaíba", "nivel_atual_m": 2.62,
               "nivel_previsto_m": 3.08, "severidade_atual": 2, "severidade_prevista": 3, "bairro": "Navegantes",
               "abrigo": {"nome": "Colégio Dom João Becker", "minutos_a_pe": 34, "vagas": 96}}
    status, saida = api("/mensagens/gerar", entrada)
    assert status == 200
    assert len(saida["sms"]) <= 160 and saida["sms"].isascii() and "199" in saida["sms"]
    assert all(problemas == [] for problemas in saida["verificacao"].values())


def test_it21_features_ao_vivo_do_python_iguais_as_da_visao_sql():
    """A API prevê com gold.v_ml_features_atual (últimas leituras). O Python da mesma regra tem de dar igual; e esse
    Python é igual ao do treino quando a janela fecha uma hora cheia (test_features.py). Tudo num retrato só do banco
    (REPEATABLE READ), porque o simulador continua gravando enquanto o teste lê."""
    from ia.features import FEATURES, features_ultimas_leituras

    with psycopg.connect(dsn(os.environ.get("POSTGRES_USER", "migrador"), os.environ["POSTGRES_PASSWORD"])) as conn:
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        colunas = ", ".join(f"{nome}::float" for nome in FEATURES)
        visao = {r[0]: r[1:] for r in conn.execute(f"SELECT estacao_id, {colunas} FROM gold.v_ml_features_atual").fetchall()}
        assert set(visao) == set(ESTACOES_REAIS)

        def ultimas(estacao_id: str, tipo: str, limite: int) -> list:
            return [v for (v,) in conn.execute(
                "SELECT l.valor FROM silver.leitura l JOIN silver.sensor s ON s.id = l.sensor_id "
                "WHERE s.estacao_id = %s AND s.tipo = %s AND s.ativo AND l.qualidade = 'ok' "
                "AND l.medido_em > now() - interval '3 days' ORDER BY l.medido_em DESC LIMIT %s",
                (estacao_id, tipo, limite),
            )]

        for estacao_id, valores in visao.items():
            python = features_ultimas_leituras(ultimas(estacao_id, "nivel_rio", 12), ultimas(estacao_id, "chuva", 144))
            for nome, b in zip(FEATURES, valores, strict=True):
                a = python[nome]
                assert (a is None and b is None) or abs(a - b) < 1e-9, (estacao_id, nome, a, b)


def test_it22_abrigo_desativado_nao_e_recomendado_pela_ia(db):
    """A IA lê 'ativo' de gold.dim_abrigo (o cadastro), e não da visão de ocupação, que só tem abrigos com sensor."""
    abrigo_id = "abr-01"
    db.execute("UPDATE silver.abrigo SET ativo = false WHERE id = %s", (abrigo_id,))
    try:
        status, abrigos = api("/abrigos")
        assert status == 200
        desativado = next(a for a in abrigos if a["abrigo_id"] == abrigo_id)
        assert desativado["apto"] is False and desativado["motivo"] == "abrigo inativo"
    finally:
        db.execute("UPDATE silver.abrigo SET ativo = true WHERE id = %s", (abrigo_id,))
