"""Apoio aos testes: repositório em memória (testa o processamento sem banco de dados)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from ingestor.alertas import Cotas
from ingestor.repositorio import AlertaAberto
from ingestor.validacao import LeituraAnterior, Sensor

AGORA = datetime(2026, 11, 7, 15, 0, tzinfo=UTC)

SENSORES = {
    "gua-cais-nivel": Sensor("gua-cais-nivel", "nivel_rio", "m", "sim", "gua-cais", None, 0, 15, True, 0.30),
    "gua-cais-chuva": Sensor("gua-cais-chuva", "chuva", "mm", "sim", "gua-cais", None, 0, 60, True, 0.30),
    "abr-01-ocup": Sensor("abr-01-ocup", "ocupacao_abrigo", "pessoas", "sim", None, "abr-01", 0, 300, True),
    "wok-nivel": Sensor("wok-nivel", "nivel_rio", "m", "wokwi", "demo-wokwi", None, 0, 15, True, 2.0),
    "sensor-desligado": Sensor("sensor-desligado", "chuva", "mm", "sim", "gua-cais", None, 0, 60, False),
}
COTAS = {"gua-cais": Cotas(2.0, 2.5, 3.0), "demo-wokwi": Cotas(0.8, 1.2, 1.6)}


class RepoMemoria:
    def __init__(self) -> None:
        self.mensagens: dict[str, dict] = {}
        self.por_id: dict[int, dict] = {}
        self.leituras: dict[tuple[str, datetime], dict] = {}
        self.alertas: list[dict] = []

    def sensores(self):
        return SENSORES

    def cotas(self, estacao_id):
        return COTAS[estacao_id]

    def inserir_mensagem(self, canal, topico, conteudo, hash_, status, motivo=None, carga_id=None):
        if hash_ in self.mensagens:
            return None
        mensagem = {"id": len(self.por_id) + 1, "canal": canal, "topico": topico, "status": status, "motivo": motivo}
        self.mensagens[hash_] = mensagem
        self.por_id[mensagem["id"]] = mensagem
        return mensagem["id"]

    def marcar_mensagem(self, mensagem_id, status, motivo=None):
        self.por_id[mensagem_id].update(status=status, motivo=motivo)

    def leitura_anterior(self, sensor_id, antes_de, so_ok=False):
        candidatas = [
            (t, leitura) for (s, t), leitura in self.leituras.items()
            if s == sensor_id and t < antes_de and (not so_ok or leitura["qualidade"] == "ok")
        ]
        if not candidatas:
            return None
        t, leitura = max(candidatas, key=lambda par: par[0])
        return LeituraAnterior(leitura["valor"], t, leitura["qualidade"])

    def inserir_leitura(self, sensor_id, medido_em, valor, qualidade, canal, mensagem_id):
        if (sensor_id, medido_em) in self.leituras:
            return False
        self.leituras[(sensor_id, medido_em)] = {"valor": valor, "qualidade": qualidade, "canal": canal}
        return True

    def alerta_aberto(self, estacao_id):
        for a in self.alertas:
            if a["estacao_id"] == estacao_id and a["fechado_em"] is None:
                return AlertaAberto(a["id"], a["severidade"], a["ultima_leitura_em"])
        return None

    def abrir_alerta(self, estacao_id, severidade, em, nivel):
        self.alertas.append({
            "id": len(self.alertas) + 1, "estacao_id": estacao_id, "severidade": severidade,
            "aberto_em": em, "fechado_em": None, "pico_m": nivel, "ultima_leitura_em": em,
        })

    def atualizar_alerta(self, alerta_id, severidade, em, nivel):
        a = self.alertas[alerta_id - 1]
        a.update(severidade=max(a["severidade"], severidade), pico_m=max(a["pico_m"], nivel), ultima_leitura_em=em)

    def fechar_alerta(self, alerta_id, em):
        self.alertas[alerta_id - 1].update(fechado_em=em, ultima_leitura_em=em)


def horario(minutos: int) -> str:
    """Horário ISO em UTC, 'minutos' depois de AGORA - 3 h (sempre no passado)."""
    t = AGORA - timedelta(hours=3) + timedelta(minutes=minutos)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")
