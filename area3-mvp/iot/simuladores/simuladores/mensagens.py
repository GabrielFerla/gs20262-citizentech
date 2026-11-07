"""Transforma o estado da simulação em mensagens no formato do contrato (contratos/leitura.v1.schema.json).

Também simula defeitos reais de sensor, para a camada silver ter o que tratar:
leitura que não chega, pico absurdo no nível e mensagem corrompida.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

from .cadastro import Cadastro
from .modelo import Estado


@dataclass(frozen=True)
class Falhas:
    falta: float = 0.005  # leitura que não chega
    pico: float = 0.001  # salto absurdo de nível (falha do sensor)
    corrompida: float = 0.001  # mensagem fora do contrato


FALHAS_PADRAO = Falhas()
SEM_FALHAS = Falhas(0, 0, 0)


def horario_iso(quando: datetime) -> str:
    """UTC com milissegundos, terminado em Z (ex.: 2026-11-07T15:00:00.000Z)."""
    return quando.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def corromper(mensagem: dict, rng: random.Random) -> str:
    defeito = rng.choice(["unidade", "texto", "sem_horario", "json_quebrado", "negativo"])
    m = dict(mensagem)
    if defeito == "unidade":
        m["unidade"] = "cm"
    elif defeito == "texto":
        m["valor"] = str(m["valor"])
    elif defeito == "sem_horario":
        del m["medido_em"]
    elif defeito == "negativo":
        m["valor"] = -abs(m["valor"]) - 5
    else:
        return json.dumps(m)[:-7]
    return json.dumps(m, separators=(",", ":"))


class GeradorDeMensagens:
    def __init__(self, cadastro: Cadastro, rng: random.Random, falhas: Falhas = FALHAS_PADRAO):
        self.sensores = cadastro.sensores_simulados()
        self.rng = rng
        self.falhas = falhas
        self.seq: dict[str, int] = defaultdict(int)

    def mensagens(self, estado: Estado, quando: datetime) -> list[tuple[str, str]]:
        """Lista de (sensor_id, conteúdo JSON) para um passo da simulação."""
        saida = []
        for sensor in self.sensores:
            if sensor.tipo == "nivel_rio":
                valor = estado.nivel_m[sensor.estacao_id] + self.rng.gauss(0, 0.01)
                if self.rng.random() < self.falhas.pico:
                    valor += self.rng.uniform(1.0, 3.0)
                valor = round(max(valor, 0.0), 2)
            elif sensor.tipo == "chuva":
                valor = round(estado.chuva_mm[sensor.estacao_id], 1)
            else:
                valor = estado.ocupacao[sensor.abrigo_id]

            if self.rng.random() < self.falhas.falta:
                continue
            self.seq[sensor.id] += 1
            mensagem = {
                "v": 1,
                "sensor_id": sensor.id,
                "valor": valor,
                "unidade": sensor.unidade,
                "medido_em": horario_iso(quando),
                "seq": self.seq[sensor.id],
            }
            if self.rng.random() < self.falhas.corrompida:
                saida.append((sensor.id, corromper(mensagem, self.rng)))
            else:
                saida.append((sensor.id, json.dumps(mensagem, separators=(",", ":"))))
        return saida
