from simuladores.tempo_real import proximo_envio


def test_mantem_o_ritmo_normal():
    assert proximo_envio(anterior=100.0, agora=100.2, intervalo=1.0) == 101.0


def test_pequeno_atraso_e_compensado():
    # um passo que demorou um pouco: o próximo sai logo, sem perder o ritmo
    assert proximo_envio(anterior=100.0, agora=101.5, intervalo=1.0) == 101.0


def test_depois_de_uma_pausa_longa_nao_dispara_rajada():
    # 10 minutos parado (notebook dormindo): retoma de agora, não de 600 passos atrás
    assert proximo_envio(anterior=100.0, agora=700.0, intervalo=1.0) == 700.0
