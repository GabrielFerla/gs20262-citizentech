import json

import pytest
from ingestor.config import achar_pasta
from ingestor.contrato import erros_do_contrato, interpretar_topico

EXEMPLOS = achar_pasta("CONTRATOS_DIR", "contratos") / "exemplos"


@pytest.mark.parametrize("arquivo", sorted((EXEMPLOS / "validos").glob("*.json")), ids=lambda p: p.stem)
def test_exemplo_valido_segue_o_contrato(arquivo):
    assert erros_do_contrato(json.loads(arquivo.read_text(encoding="utf-8"))) == []


@pytest.mark.parametrize("arquivo", sorted((EXEMPLOS / "invalidos").glob("*.json")), ids=lambda p: p.stem)
def test_exemplo_invalido_e_recusado(arquivo):
    assert erros_do_contrato(json.loads(arquivo.read_text(encoding="utf-8"))) != []


def test_existem_exemplos_dos_dois_tipos():
    assert len(list((EXEMPLOS / "validos").glob("*.json"))) >= 3
    assert len(list((EXEMPLOS / "invalidos").glob("*.json"))) >= 5


@pytest.mark.parametrize(
    ("topico", "esperado"),
    [
        ("citizentech/v1/sim/gua-cais-nivel", ("sim", "gua-cais-nivel")),
        ("citizentech/v1/wokwi/wok-ocup", ("wokwi", "wok-ocup")),
        ("citizentech/v1/outro/gua-cais-nivel", None),
        ("citizentech/v2/sim/gua-cais-nivel", None),
        ("citizentech/v1/sim/GUA CAIS", None),
        ("citizentech/v1/sim/a/b", None),
    ],
)
def test_interpretar_topico(topico, esperado):
    assert interpretar_topico(topico) == esperado
