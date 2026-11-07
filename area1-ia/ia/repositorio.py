"""Leitura da camada gold (usuário ia_ro). Os testes usam uma versão em memória com a mesma interface."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import psycopg
from psycopg.rows import dict_row

from .features import LinhaFeatures
from .previsao import Cotas


@dataclass(frozen=True)
class Estacao:
    estacao_id: str
    nome: str
    corpo_hidrico: str
    lat: float
    lon: float
    cotas: Cotas
    demo: bool


@dataclass(frozen=True)
class Bairro:
    bairro_id: str
    nome: str
    zona_risco: str
    lat: float
    lon: float


class Repositorio(Protocol):
    def verificar(self) -> None: ...
    def estacoes(self) -> dict[str, Estacao]: ...
    def bairros(self) -> dict[str, Bairro]: ...
    def features_atuais(self) -> list[dict]: ...
    def abrigos(self) -> list[dict]: ...
    def features_historicas(self) -> dict[str, list[LinhaFeatures]]: ...


class RepositorioGold:
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def _consultar(self, sql: str) -> list[dict]:
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql)
            return [{k: _numero(v) for k, v in linha.items()} for linha in cur.fetchall()]

    def verificar(self) -> None:
        self._consultar("SELECT 1 AS ok")

    def estacoes(self) -> dict[str, Estacao]:
        linhas = self._consultar(
            "SELECT estacao_id, estacao, corpo_hidrico, lat, lon, cota_atencao_m, cota_alerta_m, cota_inundacao_m, demo "
            "FROM gold.dim_estacao ORDER BY estacao_id"
        )
        return {
            r["estacao_id"]: Estacao(r["estacao_id"], r["estacao"], r["corpo_hidrico"], r["lat"], r["lon"],
                                     Cotas(r["cota_atencao_m"], r["cota_alerta_m"], r["cota_inundacao_m"]), r["demo"])
            for r in linhas
        }

    def bairros(self) -> dict[str, Bairro]:
        linhas = self._consultar("SELECT bairro_id, bairro, zona_risco, lat, lon FROM gold.dim_bairro ORDER BY bairro_id")
        return {r["bairro_id"]: Bairro(r["bairro_id"], r["bairro"], r["zona_risco"], r["lat"], r["lon"]) for r in linhas}

    def features_atuais(self) -> list[dict]:
        return self._consultar("SELECT * FROM gold.v_ml_features_atual ORDER BY estacao_id")

    def abrigos(self) -> list[dict]:
        return self._consultar(
            """
            SELECT s.abrigo_id, s.abrigo, s.lat, s.lon, s.capacidade, s.ocupacao, s.vagas, s.status_lotacao,
                   s.em_area_de_risco, s.estacao_proxima_id, s.severidade_regiao, s.leitura_velha, s.demo,
                   s.motivo_nao_recomendado, s.recomendavel, coalesce(t.variacao_1h, 0) AS variacao_1h,
                   coalesce(t.ativo, true) AS ativo
            FROM gold.v_abrigo_status s
            LEFT JOIN gold.v_abrigo_tendencia t ON t.abrigo_id = s.abrigo_id
            ORDER BY s.abrigo_id
            """
        )

    def features_historicas(self) -> dict[str, list[LinhaFeatures]]:
        linhas = self._consultar(
            "SELECT estacao_id, hora_utc, nivel_atual_m, variacao_1h_m, chuva_1h_mm, chuva_6h_mm, chuva_24h_mm, "
            "nivel_6h_depois_m FROM gold.v_ml_features ORDER BY estacao_id, hora_utc"
        )
        por_estacao: dict[str, list[LinhaFeatures]] = defaultdict(list)
        for r in linhas:
            por_estacao[r["estacao_id"]].append(LinhaFeatures(**r))
        return dict(por_estacao)

    # --- usados só pelo relatório (série histórica) ---
    def abrigos_cadastro(self) -> list[dict]:
        return self._consultar(
            "SELECT abrigo_id, abrigo, lat, lon, capacidade, em_area_de_risco, estacao_proxima_id "
            "FROM gold.dim_abrigo WHERE NOT demo ORDER BY abrigo_id"
        )

    def ocupacao_horaria(self) -> dict[tuple[str, datetime], int]:
        linhas = self._consultar("SELECT abrigo_id, hora_utc, ocupacao_max FROM gold.v_abrigo_horaria")
        return {(r["abrigo_id"], r["hora_utc"]): int(r["ocupacao_max"]) for r in linhas}

    def niveis_horarios(self) -> dict[tuple[str, datetime], float]:
        linhas = self._consultar(
            "SELECT estacao_id, hora_utc, nivel_max_m FROM gold.v_estacao_horaria WHERE nivel_max_m IS NOT NULL"
        )
        return {(r["estacao_id"], r["hora_utc"]): r["nivel_max_m"] for r in linhas}


def _numero(valor):
    """numeric do PostgreSQL chega como Decimal; a IA trabalha com float."""
    if valor is None or isinstance(valor, bool | int | float | str | datetime):
        return valor
    try:
        return float(valor)
    except (TypeError, ValueError):
        return valor
