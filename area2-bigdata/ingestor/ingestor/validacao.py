"""Validação de negócio: além do formato, a leitura precisa fazer sentido para o sensor."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

from .contrato import erros_do_contrato

TOLERANCIA_FUTURO = timedelta(minutes=2)  # relógios de dispositivos podem estar um pouco adiantados
JANELA_SALTO = timedelta(minutes=30)


class Rejeicao(Exception):
    """Mensagem recusada. O texto segue o padrão 'categoria: detalhe' (vira coluna no dashboard)."""


@dataclass(frozen=True)
class Sensor:
    id: str
    tipo: str
    unidade: str
    origem: str
    estacao_id: str | None
    abrigo_id: str | None
    valor_min: float
    valor_max: float
    ativo: bool
    salto_max_m: float | None = None


@dataclass(frozen=True)
class Leitura:
    sensor: Sensor
    valor: float
    medido_em: datetime


@dataclass(frozen=True)
class LeituraAnterior:
    valor: float
    medido_em: datetime
    qualidade: str


def validar(
    payload: object,
    sensores: Mapping[str, Sensor],
    agora: datetime,
    origem_topico: str | None = None,
    sensor_topico: str | None = None,
) -> Leitura:
    erros = erros_do_contrato(payload)
    if erros:
        raise Rejeicao("contrato: " + "; ".join(erros))
    assert isinstance(payload, dict)

    sensor_id = payload["sensor_id"]
    if sensor_topico is not None and sensor_id != sensor_topico:
        raise Rejeicao(f"topico: sensor do tópico ({sensor_topico}) difere da mensagem ({sensor_id})")

    sensor = sensores.get(sensor_id)
    if sensor is None:
        raise Rejeicao(f"sensor: {sensor_id} não está cadastrado")
    if not sensor.ativo:
        raise Rejeicao(f"sensor: {sensor_id} está inativo")
    if origem_topico is not None and origem_topico != sensor.origem:
        raise Rejeicao(f"origem: {sensor_id} só pode publicar em '{sensor.origem}', veio de '{origem_topico}'")
    if payload["unidade"] != sensor.unidade:
        raise Rejeicao(f"unidade: esperado '{sensor.unidade}', veio '{payload['unidade']}'")

    valor = float(payload["valor"])
    if not math.isfinite(valor):
        raise Rejeicao("faixa: valor não é um número finito")
    if not sensor.valor_min <= valor <= sensor.valor_max:
        raise Rejeicao(f"faixa: {valor} fora de [{sensor.valor_min}, {sensor.valor_max}]")
    if sensor.tipo == "ocupacao_abrigo" and not valor.is_integer():
        raise Rejeicao("faixa: ocupação precisa ser um número inteiro de pessoas")

    try:
        medido_em = datetime.fromisoformat(payload["medido_em"])
    except ValueError as erro:
        raise Rejeicao(f"horario: data inválida ({erro})") from None
    if medido_em > agora + TOLERANCIA_FUTURO:
        raise Rejeicao(f"horario: medição no futuro ({payload['medido_em']})")

    return Leitura(sensor=sensor, valor=valor, medido_em=medido_em)


def _variacao(a: float, b: float) -> float:
    # arredonda em cm: 2,10 - 1,80 em ponto flutuante dá 0,30000000000000004
    return round(abs(a - b), 2)


def avaliar_qualidade(leitura: Leitura, anterior: LeituraAnterior | None, ultima_ok: LeituraAnterior | None) -> str:
    """Marca como 'suspeita' um salto de nível impossível entre leituras seguidas.

    Regra: é suspeita se pulou mais que salto_max em relação à leitura anterior E
    (a anterior era confiável OU também pulou em relação à última leitura confiável).
    Assim um pico isolado é marcado, mas uma mudança real de patamar (ex.: sensor
    reiniciado) só marca a primeira leitura.
    """
    salto = leitura.sensor.salto_max_m
    if leitura.sensor.tipo != "nivel_rio" or salto is None or anterior is None:
        return "ok"
    if leitura.medido_em - anterior.medido_em > JANELA_SALTO:
        return "ok"
    if _variacao(leitura.valor, anterior.valor) <= salto:
        return "ok"
    if anterior.qualidade == "ok":
        return "suspeita"
    if ultima_ok is not None and _variacao(leitura.valor, ultima_ok.valor) <= salto:
        return "ok"
    return "suspeita"
