import json
import random
from datetime import UTC, datetime

from jsonschema import Draft202012Validator
from simuladores.cadastro import carregar, pasta_seeds
from simuladores.historico import gerar_linhas, gravar, nome_do_arquivo
from simuladores.mensagens import SEM_FALHAS, Falhas, GeradorDeMensagens, horario_iso
from simuladores.modelo import PASSOS_POR_DIA, Simulacao

CADASTRO = carregar()
SCHEMA = json.loads((pasta_seeds().parents[2] / "contratos" / "leitura.v1.schema.json").read_text(encoding="utf-8"))
VALIDADOR = Draft202012Validator(SCHEMA)
FIM = datetime(2026, 11, 7, 15, 0, tzinfo=UTC)


def test_horario_iso_em_utc_com_z():
    assert horario_iso(datetime(2026, 11, 7, 15, 0, 1, 250000, tzinfo=UTC)) == "2026-11-07T15:00:01.250Z"


def test_sem_falhas_todas_as_mensagens_seguem_o_contrato():
    linhas = list(gerar_linhas(CADASTRO, 1, 42, "enchente", FIM, SEM_FALHAS))
    assert len(linhas) == PASSOS_POR_DIA * len(CADASTRO.sensores_simulados())
    for linha in linhas:
        assert list(VALIDADOR.iter_errors(json.loads(linha))) == []


def test_so_sensores_simulados_sao_publicados():
    sim = Simulacao(CADASTRO, 1)
    mensagens = GeradorDeMensagens(CADASTRO, random.Random(1), SEM_FALHAS).mensagens(sim.passo("normal"), FIM)
    ids = {sensor_id for sensor_id, _ in mensagens}
    assert ids and not any(i.startswith("wok-") for i in ids)


def test_falhas_geram_mensagens_fora_do_contrato():
    falhas = Falhas(falta=0.0, pico=0.0, corrompida=0.5)
    linhas = list(gerar_linhas(CADASTRO, 1, 3, "normal", FIM, falhas))
    invalidas = 0
    for linha in linhas:
        try:
            invalidas += bool(list(VALIDADOR.iter_errors(json.loads(linha))))
        except json.JSONDecodeError:
            invalidas += 1
    assert invalidas > len(linhas) * 0.3


def test_historico_e_gravado_inteiro(tmp_path):
    destino = tmp_path / nome_do_arquivo("misto", 1, 42)
    n = gravar(destino, gerar_linhas(CADASTRO, 1, 42, "misto", FIM, SEM_FALHAS))
    assert destino.exists() and not destino.with_suffix(".tmp").exists()
    assert len(destino.read_text(encoding="utf-8").splitlines()) == n
    ultima = json.loads(destino.read_text(encoding="utf-8").splitlines()[-1])
    assert ultima["medido_em"] == "2026-11-07T15:00:00.000Z"
