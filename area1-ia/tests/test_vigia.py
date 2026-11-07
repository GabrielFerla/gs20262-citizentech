import random
import threading
from datetime import timedelta

from apoio_ia import AGORA
from ia.previsao import Cotas, Previsao
from ia.vigia import Vigia, proxima_acao, rodar_em_segundo_plano
from ingestor.alertas import Cotas as CotasFase1
from ingestor.alertas import proximo_alerta

COTAS = Cotas(2.0, 2.5, 3.0)


def previsao(atual: float, previsto: float, estacao="gua-cais") -> Previsao:
    return Previsao(estacao, atual, previsto, atual, "subindo", COTAS.situacao(atual), COTAS.situacao(previsto),
                    COTAS.severidade(atual), COTAS.severidade(previsto))


def test_mesma_regra_de_alerta_da_fase1():
    rng = random.Random(7)
    severidade = severidade_fase1 = 0
    for _ in range(2000):
        nivel = round(rng.uniform(1.5, 3.5), 2)
        acao, severidade = proxima_acao(severidade, nivel, COTAS)
        acao_fase1, severidade_fase1 = proximo_alerta(severidade_fase1, nivel, CotasFase1(2.0, 2.5, 3.0))
        assert (acao, severidade) == (acao_fase1, severidade_fase1)


def test_vigia_abre_escala_mantem_e_fecha_pela_previsao():
    vigia, cotas = Vigia(), {"gua-cais": COTAS}
    sms = []

    def mensagem(p):
        sms.append(p.nivel_previsto_m)
        return f"SMS {p.nivel_previsto_m}"

    passos = [(1.5, 1.8), (1.6, 2.1), (1.9, 2.7), (2.1, 2.6), (1.8, 1.95), (1.7, 1.85)]
    acoes = []
    for i, (atual, previsto) in enumerate(passos):
        mudancas = vigia.atualizar([previsao(atual, previsto)], cotas, mensagem, AGORA + timedelta(seconds=i))
        acoes.append([(m.acao, m.severidade) for m in mudancas])
    assert acoes == [[], [("abrir", 1)], [("escalar", 2)], [], [], [("fechar", 0)]]
    assert sms == [2.1, 2.7]  # mensagem gerada só ao abrir e ao escalar
    assert vigia.abertos == {}
    assert [e.acao for e in vigia.eventos] == ["abrir", "escalar", "fechar"]


def test_alerta_e_marcado_antecipado_quando_a_previsao_esta_pior_que_agora():
    vigia = Vigia()
    vigia.atualizar([previsao(1.6, 2.6)], {"gua-cais": COTAS})
    aberto = vigia.abertos["gua-cais"]
    assert aberto.antecipado and aberto.severidade == 2
    foto = vigia.foto()
    assert foto["abertos"][0]["estacao_id"] == "gua-cais"
    assert foto["eventos"][0]["acao"] == "abrir"


def test_rodada_com_erro_nao_derruba_o_vigia():
    vigia, parar, rodadas = Vigia(), threading.Event(), []

    def rodada():
        rodadas.append(1)
        if len(rodadas) == 1:
            raise RuntimeError("banco fora do ar")
        parar.set()

    rodar_em_segundo_plano(vigia, rodada, 0.01, parar)
    assert len(rodadas) == 2
    assert vigia.ultimo_erro is None


def test_estacao_sem_dados_recentes_encerra_o_alerta_da_previsao():
    vigia = Vigia()
    vigia.atualizar([previsao(1.6, 2.6)], {"gua-cais": COTAS})
    mudancas = vigia.atualizar([], {}, sem_dados=["gua-cais", "gra-sarandi"])
    assert [(m.estacao_id, m.acao) for m in mudancas] == [("gua-cais", "sem_dados")]  # gra-sarandi não tinha alerta
    assert vigia.abertos == {}
    assert vigia.foto()["eventos"][0]["nivel_atual_m"] is None  # sem NaN: o JSON da API aceita
