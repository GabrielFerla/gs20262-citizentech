from datetime import timedelta

from apoio_ia import AGORA, BAIRROS
from ia import cenarios_abrigos as ca
from ia.cenarios_abrigos import AbrigoFixo, Momento
from ia.previsao import Cotas

# Pessoa em (-30.0, -51.2). "perto" fica em área de risco do rio X; "longe" é seguro.
PERTO = AbrigoFixo("perto", "Abrigo perto", -30.001, -51.2, 100, True, "x")
LONGE = AbrigoFixo("longe", "Abrigo longe", -30.03, -51.2, 100, False, "y")
PONTO = [(-30.0, -51.2)]


def momento(ocupacao=None, antes=None, chegada=None, sev_atual=None, sev_prevista=None, alaga=None) -> Momento:
    return Momento(
        hora=AGORA,
        ocupacao=ocupacao or {"perto": 10, "longe": 10},
        ocupacao_antes=antes or {"perto": 10, "longe": 10},
        ocupacao_chegada=chegada or {"perto": 10, "longe": 10},
        severidade_atual=sev_atual or {"x": 1, "y": 0},
        severidade_prevista=sev_prevista or {"x": 1, "y": 0},
        alaga_em_6h=alaga or {"x": False, "y": False},
    )


def falhas(resultado):
    return {k: v["falha_pct"] for k, v in resultado["estrategias"].items()}


def test_so_a_ia_evita_o_abrigo_que_vai_alagar():
    # O rio X está só em atenção agora, mas a IA prevê alerta e ele de fato alaga em 6 h.
    m = momento(sev_prevista={"x": 3, "y": 0}, alaga={"x": True, "y": False})
    r = ca.avaliar([PERTO, LONGE], [m], PONTO)
    assert falhas(r) == {"mais_proximo": 100.0, "regra_fase1": 100.0, "ia": 0.0}
    assert r["estrategias"]["ia"]["distancia_media_km"] > r["estrategias"]["mais_proximo"]["distancia_media_km"]


def test_so_a_ia_evita_o_abrigo_que_vai_lotar_antes_da_chegada():
    perto_seguro = AbrigoFixo("perto", "Abrigo perto", -30.0135, -51.2, 100, False, "x")  # 1,5 km: ~30 min a pé
    # Tem 10 vagas agora (a regra da fase 1 aceita), mas chegaram 40 pessoas na última hora.
    m = momento(ocupacao={"perto": 90, "longe": 10}, antes={"perto": 50, "longe": 10},
                chegada={"perto": 100, "longe": 12})
    r = ca.avaliar([perto_seguro, LONGE], [m], PONTO)
    assert r["estrategias"]["regra_fase1"]["lotado_na_chegada_pct"] == 100.0
    assert r["estrategias"]["ia"]["lotado_na_chegada_pct"] == 0.0


def test_regra_da_fase1_ja_evita_area_de_risco_com_alerta_agora():
    m = momento(sev_atual={"x": 2, "y": 0}, alaga={"x": True, "y": False})
    assert falhas(ca.avaliar([PERTO, LONGE], [m], PONTO))["regra_fase1"] == 0.0


def test_sem_abrigo_apto_conta_a_parte():
    m = momento(ocupacao={"perto": 100, "longe": 100})
    r = ca.avaliar([PERTO, LONGE], [m], PONTO)
    assert r["estrategias"]["ia"]["sem_abrigo_apto_pct"] == 100.0
    assert r["estrategias"]["ia"]["distancia_media_km"] is None


def test_pontos_de_partida_sao_reproduziveis_e_ficam_perto_dos_bairros_de_risco():
    pontos = ca.pontos_de_partida(list(BAIRROS.values()), n=50)
    assert pontos == ca.pontos_de_partida(list(BAIRROS.values()), n=50)
    risco = [b for b in BAIRROS.values() if b.zona_risco == "alta"]
    for lat, lon in pontos:
        assert min(ca.distancia_km(lat, lon, b.lat, b.lon) for b in risco) < 3


COTAS = {"x": Cotas(2.0, 2.5, 3.0), "y": Cotas(2.0, 2.5, 3.0)}


def test_montar_momentos_pula_horas_calmas_e_as_sem_vizinhas():
    h = [AGORA + timedelta(hours=i) for i in range(5)]
    ocupacao = {(a, x): 10 for a in ("perto", "longe") for x in h}
    nivel = {(e, x): 1.0 for e in ("x", "y") for x in h}
    nivel["x", h[2]] = 2.5  # crise só na hora 2
    previsto = dict(nivel)
    momentos = ca.montar_momentos([PERTO, LONGE], ocupacao, nivel, previsto, COTAS)
    assert [m.hora for m in momentos] == [h[2]]
    assert momentos[0].alaga_em_6h == {"x": False, "y": False}


def test_alerta_atual_segue_a_regra_da_fase1_e_nao_rebaixa_na_descida():
    h = [AGORA + timedelta(hours=i) for i in range(6)]
    niveis = [1.5, 3.2, 2.6, 2.1, 1.95, 1.85]  # sobe até inundação e desce
    nivel = {("x", x): n for x, n in zip(h, niveis, strict=True)}
    alerta = ca.alerta_da_fase1(nivel, {"x": COTAS["x"]})
    # na descida o alerta continua em inundação (3) e só fecha abaixo de 1,90 m
    assert [alerta["x", x] for x in h] == [0, 3, 3, 3, 3, 0]
