import itertools

import pytest
from ia.mensagens import LIMITES, AbrigoMensagem, Fatos, gerar, verificar

ABRIGOS = [
    None,
    AbrigoMensagem("Colégio Dom João Becker", 34, 96),
    AbrigoMensagem("Escola Municipal de Educação Infantil Humaitá com Nome Bem Comprido", 118, 7),
]


def fatos(atual=0, prevista=0, abrigo=None, bairro=None, corpo="Lago Guaíba") -> Fatos:
    return Fatos("Guaíba - Cais Mauá", corpo, 2.4, 2.9, atual, prevista, 3.0, bairro, abrigo, 0.022, 0.075)


@pytest.mark.parametrize(
    ("atual", "prevista", "abrigo", "bairro"),
    list(itertools.product(range(4), range(4), ABRIGOS, [None, "Centro Histórico"])),
)
def test_todas_as_combinacoes_passam_nas_regras_de_linguagem_simples(atual, prevista, abrigo, bairro):
    m = gerar(fatos(atual, prevista, abrigo, bairro))
    assert all(problemas == [] for problemas in m.verificacao.values()), m.verificacao
    if max(atual, prevista) == 0:
        assert m.sms is None and m.whatsapp is None and m.intencao == "sem_alerta"
    else:
        assert len(m.sms) <= LIMITES["sms"] and m.sms.isascii()
        assert len(m.push_corpo) <= LIMITES["push_corpo"]
    assert len(m.defesa_civil) <= LIMITES["defesa_civil"]


def test_intencao_segue_a_situacao_mais_grave():
    assert gerar(fatos(1, 1)).intencao == "fique_atento"
    assert gerar(fatos(1, 2)).intencao == "prepare_se"
    assert gerar(fatos(2, 3)).intencao == "saia_agora"
    assert gerar(fatos(3, 2)).intencao == "nao_volte"  # baixando depois de alagar: quem saiu não volta ainda
    assert gerar(fatos(2, 1)).intencao == "fique_atento"  # no alerta ninguém precisou sair de casa


def test_rio_baixando_da_atencao_nao_fala_em_voltar_para_casa():
    m = gerar(fatos(1, 0))
    assert "voltando ao normal" in m.whatsapp
    assert "liberar a volta" not in m.whatsapp and "Nao volte" not in m.sms
    assert "liberar a volta" in gerar(fatos(3, 1)).whatsapp


def test_pior_caso_de_tamanho_aceito_pela_api_ainda_cabe_em_todos_os_canais():
    # tamanhos máximos de FatosEntrada (api.py): rio 24, estação 80, bairro 40, abrigo 80, 600 min, 10000 vagas
    abrigo = AbrigoMensagem("Escola Estadual de Ensino Fundamental Professora Maria Thereza da Silveira Norte", 600, 10000)
    for atual, prevista in itertools.product(range(4), range(4)):
        f = Fatos("E" * 80, "Rio Xxxxxxxxxxxxxxxxxxxx", 2.4, 2.9, atual, prevista, 3.0, "Bairro " + "x" * 33, abrigo)
        m = gerar(f)
        assert all(problemas == [] for problemas in m.verificacao.values()), (atual, prevista, m.verificacao)


def test_nome_proprio_com_cara_de_jargao_nao_reprova_a_mensagem():
    abrigo = AbrigoMensagem("Escola Estadual Modelo de Porto Alegre", 20, 50)
    m = gerar(Fatos("Estação Cotagem", "Rio Modelo", 2.4, 3.1, 1, 3, 3.0, "Vila Cotada", abrigo))
    assert all(problemas == [] for problemas in m.verificacao.values()), m.verificacao
    assert verificar("sms", "DEFESA CIVIL: Saia agora. A cota passou. Va para Escola... Emergencia 199", fatos(1, 3)) != []


def test_aviso_antecipado_fala_no_futuro_e_o_atual_no_presente():
    assert "deve alagar ruas" in gerar(fatos(1, 3)).whatsapp
    assert "está alagando ruas" in gerar(fatos(3, 3)).whatsapp
    assert gerar(fatos(1, 3)).defesa_civil.startswith("[ALERTA ANTECIPADO]")
    assert gerar(fatos(3, 3)).defesa_civil.startswith("[ALERTA EM CURSO]")


def test_mensagem_de_saida_traz_abrigo_e_telefone():
    m = gerar(fatos(2, 3, ABRIGOS[1], "Navegantes"))
    for texto in (m.sms, m.push_corpo, m.whatsapp):
        assert "199" in texto
    assert "Colegio Dom Joao Becker (34 min a pe)" in m.sms
    assert "Vá para Colégio Dom João Becker. Fica a 34 min a pé e tem 96 vagas." in m.whatsapp
    assert "Navegantes" in m.whatsapp


def test_nome_de_abrigo_comprido_e_encurtado_no_sms_sem_perder_o_telefone():
    m = gerar(fatos(3, 3, ABRIGOS[2]))
    assert len(m.sms) <= 160
    assert "..." in m.sms and "199" in m.sms


def test_verificacao_aponta_os_problemas():
    f = fatos(2, 3, ABRIGOS[1])
    problemas = verificar("sms", "DEFESA CIVIL: A cota do modelo foi atingida. " + "palavra " * 25 + "é", f)
    texto = " | ".join(problemas)
    for esperado in ("acento", "jargão: 'cota'", "jargão: 'modelo'", "frase longa", "não começa pela ação",
                     "199", "abrigo recomendado"):
        assert esperado in texto
    assert verificar("sms", "x" * 161, fatos())[0].startswith("tem 161 caracteres")
