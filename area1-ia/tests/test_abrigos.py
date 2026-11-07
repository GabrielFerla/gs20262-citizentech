import pytest
from ia.abrigos import SituacaoAbrigo, avaliar, distancia_km, minutos_a_pe, recomendar


def situacao(abrigo_id="a", lat=-30.0, lon=-51.2, ocupacao=0, capacidade=100, chegando=0.0, risco=False,
             sev_atual=0, sev_prevista=0, indisponivel=None) -> SituacaoAbrigo:
    return SituacaoAbrigo(abrigo_id, f"Abrigo {abrigo_id}", lat, lon, capacidade, ocupacao, chegando, risco, "gua-cais",
                          sev_atual, sev_prevista, indisponivel)


def test_haversine():
    assert distancia_km(0, 0, 1, 0) == pytest.approx(111.195, abs=0.01)  # 1 grau de latitude
    assert distancia_km(-30.0, -51.2, -30.01, -51.21) == pytest.approx(distancia_km(-30.01, -51.21, -30.0, -51.2))
    assert distancia_km(-30.0, -51.2, -30.0, -51.2) == 0


def test_tempo_a_pe_usa_fator_de_rota_e_4_km_por_hora():
    assert minutos_a_pe(2.0) == 39  # 2 km × 1,3 / 4 km/h = 0,65 h
    assert minutos_a_pe(0.0) == 1


@pytest.mark.parametrize(
    ("abrigo", "pessoas", "motivo"),
    [
        (situacao(indisponivel="sem leitura recente de ocupação"), 1, "sem leitura recente de ocupação"),
        (situacao(ocupacao=100), 1, "lotado"),
        (situacao(risco=True, sev_atual=2), 1, "fica em área de risco e o rio da região está em alerta"),
        (situacao(risco=True, sev_prevista=2), 1, "deve entrar em alerta nas próximas 6 horas"),
        (situacao(ocupacao=98), 4, "só tem 2 vaga(s) para 4 pessoa(s)"),
        (situacao(ocupacao=80, chegando=40), 4, "deve lotar antes de você chegar"),  # 0,5 h × 40/h = 20 entrando
    ],
)
def test_cada_motivo_para_nao_recomendar(abrigo, pessoas, motivo):
    resultado = avaliar(abrigo, pessoas, horas_ate_chegar=0.5)
    assert not resultado.apto
    assert motivo in resultado.motivo


def test_area_de_risco_com_rio_so_em_atencao_continua_apto():
    assert avaliar(situacao(risco=True, sev_atual=1, sev_prevista=1)).apto


def test_vagas_na_chegada_descontam_quem_esta_chegando():
    a = situacao(ocupacao=50, chegando=20)
    assert a.vagas_na_chegada(0.5) == 40
    assert situacao(ocupacao=50, chegando=-30).vagas_na_chegada(1) == 50  # gente saindo não cria vaga extra


def test_recomenda_os_aptos_mais_perto_e_explica_os_evitados():
    origem = (-30.0, -51.2)
    abrigos = [
        situacao("perto-lotado", -30.001, -51.2, ocupacao=100),
        situacao("perto-risco", -30.002, -51.2, risco=True, sev_prevista=3),
        situacao("medio", -30.01, -51.2),
        situacao("longe", -30.05, -51.2),
        situacao("mais-longe", -30.08, -51.2),
        situacao("fora", -30.0005, -51.2, indisponivel="abrigo de demonstração"),
    ]
    rec = recomendar(abrigos, *origem, pessoas=2, limite=2)
    assert [a.abrigo.abrigo_id for a in rec.recomendados] == ["medio", "longe"]
    assert [a.abrigo.abrigo_id for a in rec.evitados] == ["perto-lotado", "perto-risco"]
    assert rec.recomendados[0].minutos_a_pe < rec.recomendados[1].minutos_a_pe
    assert all(a.abrigo.abrigo_id != "fora" for a in rec.recomendados + rec.evitados)


def test_sem_abrigo_apto_devolve_lista_vazia():
    rec = recomendar([situacao(ocupacao=100)], -30.0, -51.2)
    assert rec.recomendados == []
    assert len(rec.evitados) == 1
