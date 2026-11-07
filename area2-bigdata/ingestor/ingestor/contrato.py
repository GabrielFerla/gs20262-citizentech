"""Validação estrutural da mensagem contra o contrato JSON Schema (fonte única da verdade)."""

from __future__ import annotations

import functools
import json
import re

from jsonschema import Draft202012Validator

from .config import achar_pasta

# citizentech/v1/{origem}/{sensor_id}
TOPICO = re.compile(r"^citizentech/v1/(sim|wokwi)/([a-z0-9]+(?:-[a-z0-9]+)*)$")
TOPICO_ASSINATURA = "citizentech/v1/+/+"


@functools.cache
def validador() -> Draft202012Validator:
    arquivo = achar_pasta("CONTRATOS_DIR", "contratos") / "leitura.v1.schema.json"
    schema = json.loads(arquivo.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def erros_do_contrato(payload: object) -> list[str]:
    """Lista de erros legíveis; vazia quando a mensagem segue o contrato."""
    erros = []
    for erro in validador().iter_errors(payload):
        campo = "/".join(str(p) for p in erro.path) or "(mensagem)"
        erros.append(f"{campo}: {erro.message}")
    return sorted(erros)


def interpretar_topico(topico: str) -> tuple[str, str] | None:
    """Devolve (origem, sensor_id) ou None se o tópico não segue o padrão."""
    m = TOPICO.match(topico)
    return (m.group(1), m.group(2)) if m else None
