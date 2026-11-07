import psycopg
import pytest
from apoio_ia import RepoMemoria, abrigo, feature_atual
from fastapi.testclient import TestClient
from ia import api
from ia.servicos import previsoes_atuais, situacoes_dos_abrigos


@pytest.fixture
def cliente(pasta_modelo, monkeypatch):
    monkeypatch.setenv("MODELO_DIR", str(pasta_modelo))
    monkeypatch.setenv("VIGIA_INTERVALO_S", "0")  # sem thread de vigia nos testes
    repo = RepoMemoria()
    api.app.dependency_overrides[api.obter_repositorio] = lambda: repo
    with TestClient(api.app) as c:
        c.repo = repo
        yield c
    api.app.dependency_overrides.clear()


def test_saude(cliente):
    r = cliente.get("/saude")
    assert r.status_code == 200
    assert r.json()["banco"] is True
    assert r.json()["modelo"]["estacoes"] == ["dil-ipiranga", "gra-sarandi", "gua-cais"]


def test_previsao_de_cada_rio_com_a_entrada_usada(cliente):
    dados = cliente.get("/previsao").json()
    assert [d["estacao_id"] for d in dados] == ["gua-cais", "dil-ipiranga", "gra-sarandi"]
    gua = dados[0]
    assert gua["nivel_atual_m"] == 2.4 and gua["persistencia_6h_m"] == 2.4
    assert gua["entrada"]["chuva_6h_mm"] == 60.0
    assert gua["situacao_atual"] == "atencao"
    assert gua["alerta_antecipado"] == (gua["situacao_prevista"] not in ("normal", "atencao"))
    assert gua["cotas"] == {"atencao_m": 2.0, "alerta_m": 2.5, "inundacao_m": 3.0}


def test_previsao_de_estacao_inexistente_da_404(cliente):
    assert cliente.get("/previsao/demo-wokwi").status_code == 404
    assert cliente.get("/previsao/gua-cais").json()["estacao_id"] == "gua-cais"


def test_estacao_sem_leitura_de_nivel_fica_fora(modelo):
    repo = RepoMemoria(features=[feature_atual("gua-cais", None), feature_atual("gra-sarandi", 3.0)])
    assert [p.previsao.estacao_id for p in previsoes_atuais(repo, modelo)] == ["gra-sarandi"]


def test_abrigos_traz_avaliacao_de_todos_com_o_motivo(cliente):
    dados = {a["abrigo_id"]: a for a in cliente.get("/abrigos", params={"pessoas": 4}).json()}
    assert dados["abr-18"]["motivo"] == "lotado"
    assert "área de risco" in dados["abr-03"]["motivo"]
    assert dados["abr-demo"]["motivo"] == "abrigo de demonstração"
    assert dados["abr-10"]["apto"] and dados["abr-10"]["distancia_km"] is None  # sem posição: o app calcula
    assert dados["abr-10"]["minutos_ate_lotar"] is None  # não está enchendo


def test_abrigos_sem_posicao_entrega_os_minutos_ate_lotar_para_o_app_decidir(cliente):
    # abr-11: 10 vagas, 30 pessoas/h chegando. Apto AGORA; para 4 pessoas lota em (10 - 4) / 30 h = 12 min.
    abr11 = next(a for a in cliente.get("/abrigos", params={"pessoas": 4}).json() if a["abrigo_id"] == "abr-11")
    assert abr11["apto"] and abr11["minutos_ate_lotar"] == 12
    assert abr11["vagas_previstas_na_chegada"] is None  # sem a distância não dá para saber
    # já na recomendação (distância conhecida) a regra de lotar na chegada é aplicada pela API
    rec = cliente.get("/abrigos/recomendacao", params={"bairro": "navegantes", "pessoas": 4}).json()
    assert "abr-11" not in [a["abrigo_id"] for a in rec["recomendados"]]


def test_recomendacao_por_bairro(cliente):
    r = cliente.get("/abrigos/recomendacao", params={"bairro": "navegantes", "pessoas": 4})
    assert r.status_code == 200
    d = r.json()
    assert d["bairro"] == "Navegantes" and "não sai do celular" in d["origem"]
    ids = [a["abrigo_id"] for a in d["recomendados"]]
    assert ids == ["abr-10", "abr-07"]
    distancias = [a["distancia_km"] for a in d["recomendados"]]
    assert distancias == sorted(distancias)
    assert {a["abrigo_id"] for a in d["evitados"]} == {"abr-03", "abr-18"}
    assert d["estacao_da_regiao"]["estacao_id"] == "gua-cais"
    assert d["mensagens"]["verificacao"]["sms"] == []


def test_recomendacao_valida_a_entrada(cliente):
    assert cliente.get("/abrigos/recomendacao", params={"bairro": "atlantida"}).status_code == 404
    assert cliente.get("/abrigos/recomendacao", params={"bairro": "navegantes", "pessoas": 0}).status_code == 422
    assert cliente.get("/abrigos/recomendacao").status_code == 422


def test_alertas_traz_mensagens_dos_rios_fora_do_normal(cliente):
    d = cliente.get("/alertas", params={"bairro": "navegantes"}).json()
    rios = {r["previsao"]["estacao_id"]: r for r in d["rios_fora_do_normal"]}
    assert "gua-cais" in rios and "dil-ipiranga" not in rios
    assert "vigia" in d
    assert rios["gua-cais"]["mensagens"]["defesa_civil"].startswith("[")


def test_gerar_mensagens_entrada_e_saida(cliente):
    entrada = {"estacao": "Guaíba - Cais Mauá", "corpo_hidrico": "Lago Guaíba", "nivel_atual_m": 2.62,
               "nivel_previsto_m": 3.08, "severidade_atual": 2, "severidade_prevista": 3, "bairro": "Navegantes",
               "abrigo": {"nome": "Colégio Dom João Becker", "minutos_a_pe": 34, "vagas": 96}}
    d = cliente.post("/mensagens/gerar", json=entrada).json()
    assert d["intencao"] == "saia_agora"
    assert len(d["sms"]) <= 160 and "199" in d["sms"]
    assert all(v == [] for v in d["verificacao"].values())
    assert cliente.post("/mensagens/gerar", json={**entrada, "severidade_prevista": 5}).status_code == 422


def test_avaliacao_ao_vivo_compara_com_a_regra_simples(cliente):
    d = cliente.get("/modelo/avaliacao").json()
    gua = d["gua-cais"]
    assert gua["horas"] > 0
    assert gua["erro_persistencia"]["mae_m"] > 0
    assert gua["alarmes"]["alerta"]["persistencia"]["antecedencia_media_h"] == 0


def test_cors_libera_o_app_da_fase_3(cliente):
    r = cliente.get("/saude", headers={"Origin": "http://localhost:5173"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
    r = cliente.get("/saude", headers={"Origin": "http://site-qualquer.com"})
    assert "access-control-allow-origin" not in r.headers


def test_abrigo_com_leitura_velha_fica_indisponivel(pasta_modelo, monkeypatch):
    monkeypatch.setenv("MODELO_DIR", str(pasta_modelo))
    monkeypatch.setenv("VIGIA_INTERVALO_S", "0")
    repo = RepoMemoria(abrigos=[abrigo("abr-x", "Velho", -30.0, -51.2, velha=True)])
    api.app.dependency_overrides[api.obter_repositorio] = lambda: repo
    try:
        with TestClient(api.app) as c:
            assert c.get("/abrigos").json()[0]["motivo"] == "sem leitura recente de ocupação"
    finally:
        api.app.dependency_overrides.clear()


def test_banco_fora_do_ar_responde_503(pasta_modelo, monkeypatch):
    monkeypatch.setenv("MODELO_DIR", str(pasta_modelo))
    monkeypatch.setenv("VIGIA_INTERVALO_S", "0")
    monkeypatch.setenv("POSTGRES_HOST", "127.0.0.1")
    monkeypatch.setenv("POSTGRES_PORT", "1")  # ninguém escuta: conexão recusada na hora
    monkeypatch.setenv("IA_DB_PASSWORD", "x")
    with TestClient(api.app) as c:
        for rota in ("/saude", "/previsao"):
            r = c.get(rota)
            assert r.status_code == 503 and "indisponível" in r.json()["detail"]


class RepoQueCai(RepoMemoria):
    def abrigos(self):
        raise psycopg.OperationalError("server closed the connection unexpectedly")


def test_banco_que_cai_no_meio_da_requisicao_responde_503(pasta_modelo, monkeypatch):
    monkeypatch.setenv("MODELO_DIR", str(pasta_modelo))
    monkeypatch.setenv("VIGIA_INTERVALO_S", "0")
    api.app.dependency_overrides[api.obter_repositorio] = lambda: RepoQueCai()
    try:
        with TestClient(api.app) as c:
            assert c.get("/abrigos").status_code == 503
    finally:
        api.app.dependency_overrides.clear()


def test_abrigo_inativo_vem_da_coluna_ativo_e_tem_prioridade(modelo):
    repo = RepoMemoria(abrigos=[abrigo("abr-x", "Fechado", -30.0, -51.2, ativo=False, velha=True)])
    situacao = situacoes_dos_abrigos(repo, previsoes_atuais(repo, modelo))[0]
    assert situacao.indisponivel == "abrigo inativo"  # mesma ordem de motivos da gold.v_abrigo_status


def test_previsao_com_leitura_velha_nao_vale_para_os_abrigos(modelo):
    # Guaíba com previsão de cheia, mas a leitura é velha: o abrigo fica só com a situação de agora.
    features = [feature_atual("gua-cais", 2.9, 0.3, 30.0, 150.0, 300.0, velha=True)]
    risco = abrigo("abr-r", "Risco", -30.0, -51.2, risco=True, severidade=1)
    repo = RepoMemoria(features=features, abrigos=[risco])
    previsoes = previsoes_atuais(repo, modelo)
    assert previsoes[0].leitura_velha and previsoes[0].previsao.severidade_prevista >= 2
    assert situacoes_dos_abrigos(repo, previsoes)[0].severidade_prevista_regiao == 1
