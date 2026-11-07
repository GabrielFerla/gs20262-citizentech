"""Lê os cadastros (estações, abrigos, sensores) dos mesmos CSVs que o banco usa."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Estacao:
    id: str
    nivel_base_m: float
    cota_atencao_m: float
    cota_alerta_m: float
    cota_inundacao_m: float
    demo: bool


@dataclass(frozen=True)
class Abrigo:
    id: str
    capacidade: int
    em_area_de_risco: bool
    estacao_proxima_id: str
    demo: bool


@dataclass(frozen=True)
class SensorCadastro:
    id: str
    tipo: str
    unidade: str
    estacao_id: str | None
    abrigo_id: str | None
    origem: str


@dataclass(frozen=True)
class Cadastro:
    estacoes: dict[str, Estacao]
    abrigos: dict[str, Abrigo]
    sensores: list[SensorCadastro]

    def sensores_simulados(self) -> list[SensorCadastro]:
        return [s for s in self.sensores if s.origem == "sim"]


def pasta_seeds() -> Path:
    if os.environ.get("SEEDS_DIR"):
        return Path(os.environ["SEEDS_DIR"])
    for pai in Path(__file__).resolve().parents:
        candidato = pai / "area2-bigdata" / "db" / "seeds"
        if candidato.is_dir():
            return candidato
    raise FileNotFoundError("Pasta de seeds não encontrada; defina SEEDS_DIR")


def _ler(pasta: Path, nome: str) -> list[dict[str, str]]:
    with (pasta / nome).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def carregar(pasta: Path | None = None) -> Cadastro:
    pasta = pasta or pasta_seeds()
    estacoes = {
        r["id"]: Estacao(
            r["id"], float(r["nivel_base_m"]), float(r["cota_atencao_m"]), float(r["cota_alerta_m"]),
            float(r["cota_inundacao_m"]), r["demo"] == "true",
        )
        for r in _ler(pasta, "estacoes.csv")
    }
    abrigos = {
        r["id"]: Abrigo(r["id"], int(r["capacidade"]), r["em_area_de_risco"] == "true", r["estacao_proxima_id"],
                        r["demo"] == "true")
        for r in _ler(pasta, "abrigos.csv")
    }
    sensores = [
        SensorCadastro(r["id"], r["tipo"], r["unidade"], r["estacao_id"] or None, r["abrigo_id"] or None, r["origem"])
        for r in _ler(pasta, "sensores.csv")
    ]
    return Cadastro(estacoes, abrigos, sensores)
