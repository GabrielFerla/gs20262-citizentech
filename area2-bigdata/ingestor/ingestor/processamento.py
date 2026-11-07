"""Caminho de uma mensagem: bronze → validação → silver → alerta.

A mesma função atende o tempo real (MQTT) e a carga em lote (arquivo NDJSON),
então as duas entradas passam exatamente pelas mesmas regras.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from .alertas import Cotas, proximo_alerta
from .contrato import interpretar_topico
from .validacao import Leitura, LeituraAnterior, Rejeicao, Sensor, avaliar_qualidade, validar

TAMANHO_MAXIMO = 4096  # bytes; mensagens maiores são recusadas (proteção contra abuso)


class RepositorioLeituras(Protocol):
    """O que o processamento precisa do banco (o teste usa uma versão em memória)."""

    def sensores(self) -> dict[str, Sensor]: ...
    def cotas(self, estacao_id: str) -> Cotas: ...
    def inserir_mensagem(self, canal, topico, conteudo, hash_, status, motivo=None, carga_id=None) -> int | None: ...
    def marcar_mensagem(self, mensagem_id: int, status: str, motivo: str | None = None) -> None: ...
    def leitura_anterior(self, sensor_id: str, antes_de: datetime, so_ok: bool = False) -> LeituraAnterior | None: ...
    def inserir_leitura(self, sensor_id, medido_em, valor, qualidade, canal, mensagem_id) -> bool: ...
    def alerta_aberto(self, estacao_id: str): ...
    def abrir_alerta(self, estacao_id: str, severidade: int, em: datetime, nivel: float) -> None: ...
    def atualizar_alerta(self, alerta_id: int, severidade: int, em: datetime, nivel: float) -> None: ...
    def fechar_alerta(self, alerta_id: int, em: datetime) -> None: ...


@dataclass(frozen=True)
class Resultado:
    status: str  # aceita | rejeitada | duplicada | repetida
    motivo: str | None = None
    qualidade: str | None = None
    alerta: str | None = None  # abrir | escalar | fechar quando houve mudança


def calcular_hash(canal: str, topico: str | None, conteudo: str) -> str:
    return hashlib.sha256(f"{canal}\n{topico or ''}\n{conteudo}".encode()).hexdigest()


def _interpretar(conteudo: str, topico: str | None, repo: RepositorioLeituras, agora: datetime) -> Leitura:
    origem = sensor_topico = None
    if topico is not None:
        partes = interpretar_topico(topico)
        if partes is None:
            raise Rejeicao(f"topico: '{topico}' fora do padrão citizentech/v1/{{origem}}/{{sensor_id}}")
        origem, sensor_topico = partes
    if len(conteudo.encode()) > TAMANHO_MAXIMO:
        raise Rejeicao(f"tamanho: mensagem maior que {TAMANHO_MAXIMO} bytes")
    try:
        payload = json.loads(conteudo)
    except json.JSONDecodeError as erro:
        raise Rejeicao(f"json: conteúdo não é JSON válido ({erro.msg})") from None
    return validar(payload, repo.sensores(), agora, origem, sensor_topico)


def processar(
    repo: RepositorioLeituras,
    conteudo: str,
    canal: str,
    topico: str | None = None,
    agora: datetime | None = None,
    carga_id: int | None = None,
) -> Resultado:
    agora = agora or datetime.now(UTC)
    hash_ = calcular_hash(canal, topico, conteudo)
    bruto = conteudo[:TAMANHO_MAXIMO]

    try:
        leitura = _interpretar(conteudo, topico, repo, agora)
    except Rejeicao as rejeicao:
        motivo = str(rejeicao)[:500]
        if repo.inserir_mensagem(canal, topico, bruto, hash_, "rejeitada", motivo, carga_id) is None:
            return Resultado("repetida")
        return Resultado("rejeitada", motivo)

    mensagem_id = repo.inserir_mensagem(canal, topico, bruto, hash_, "aceita", None, carga_id)
    if mensagem_id is None:
        return Resultado("repetida")  # a mesma mensagem exata já tinha chegado (reentrega do QoS 1)

    sensor = leitura.sensor
    qualidade = "ok"
    if sensor.tipo == "nivel_rio":
        anterior = repo.leitura_anterior(sensor.id, leitura.medido_em)
        ultima_ok = None
        if anterior is not None and anterior.qualidade != "ok":
            ultima_ok = repo.leitura_anterior(sensor.id, leitura.medido_em, so_ok=True)
        qualidade = avaliar_qualidade(leitura, anterior, ultima_ok)

    if not repo.inserir_leitura(sensor.id, leitura.medido_em, leitura.valor, qualidade, canal, mensagem_id):
        motivo = "duplicada: já existe leitura deste sensor neste horário"
        repo.marcar_mensagem(mensagem_id, "duplicada", motivo)
        return Resultado("duplicada", motivo)

    alerta = None
    if sensor.tipo == "nivel_rio" and qualidade == "ok" and sensor.estacao_id:
        alerta = atualizar_alerta(repo, sensor.estacao_id, leitura.valor, leitura.medido_em)
    return Resultado("aceita", qualidade=qualidade, alerta=alerta)


def atualizar_alerta(repo: RepositorioLeituras, estacao_id: str, nivel: float, medido_em: datetime) -> str | None:
    aberto = repo.alerta_aberto(estacao_id)
    if aberto is not None and medido_em <= aberto.ultima_leitura_em:
        return None  # leitura atrasada: não mexe no alerta
    atual = aberto.severidade if aberto else 0
    acao, nova = proximo_alerta(atual, nivel, repo.cotas(estacao_id))
    if acao == "abrir":
        repo.abrir_alerta(estacao_id, nova, medido_em, nivel)
    elif acao in ("escalar", "manter"):
        repo.atualizar_alerta(aberto.id, nova, medido_em, nivel)
    elif acao == "fechar":
        repo.fechar_alerta(aberto.id, medido_em)
    return acao if acao in ("abrir", "escalar", "fechar") else None
