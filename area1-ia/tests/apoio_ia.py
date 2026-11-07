"""Apoio aos testes da IA: dados fixos e um repositório em memória (a API testada sem banco)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from ia.features import LinhaFeatures
from ia.previsao import Cotas
from ia.repositorio import Bairro, Estacao

AGORA = datetime(2026, 11, 7, 15, 0, tzinfo=UTC)

ESTACOES = {
    "gua-cais": Estacao("gua-cais", "Guaíba - Cais Mauá", "Lago Guaíba", -30.0270, -51.2310, Cotas(2.0, 2.5, 3.0), False),
    "dil-ipiranga": Estacao("dil-ipiranga", "Arroio Dilúvio - Av. Ipiranga", "Arroio Dilúvio", -30.0488, -51.2196,
                            Cotas(1.8, 2.5, 3.2), False),
    "gra-sarandi": Estacao("gra-sarandi", "Rio Gravataí - Sarandi", "Rio Gravataí", -29.9790, -51.1200,
                           Cotas(3.0, 3.5, 4.0), False),
    "demo-wokwi": Estacao("demo-wokwi", "Estação de demonstração (Wokwi)", "Simulação", -30.0346, -51.2177,
                          Cotas(0.8, 1.2, 1.6), True),
}

BAIRROS = {
    "navegantes": Bairro("navegantes", "Navegantes", "alta", -29.99876, -51.20217),
    "menino-deus": Bairro("menino-deus", "Menino Deus", "alta", -30.04870, -51.22430),
    "petropolis": Bairro("petropolis", "Petrópolis", "baixa", -30.04210, -51.18745),
}


def feature_atual(estacao_id: str, nivel: float, variacao: float = 0.0, chuva_1h: float = 0.0, chuva_6h: float = 0.0,
                  chuva_24h: float = 0.0, velha: bool = False) -> dict:
    return {"estacao_id": estacao_id, "medido_em_utc": AGORA, "nivel_atual_m": nivel, "variacao_1h_m": variacao,
            "chuva_1h_mm": chuva_1h, "chuva_6h_mm": chuva_6h, "chuva_24h_mm": chuva_24h, "leituras_nivel": 12,
            "leitura_velha": velha}


def abrigo(abrigo_id: str, nome: str, lat: float, lon: float, ocupacao: int = 0, capacidade: int = 150,
           risco: bool = False, estacao: str = "gua-cais", severidade: int = 0, variacao: int = 0,
           demo: bool = False, velha: bool = False, ativo: bool = True) -> dict:
    return {"abrigo_id": abrigo_id, "abrigo": nome, "lat": lat, "lon": lon, "capacidade": capacidade, "ocupacao": ocupacao,
            "vagas": max(capacidade - ocupacao, 0), "status_lotacao": "disponivel", "em_area_de_risco": risco,
            "estacao_proxima_id": estacao, "severidade_regiao": severidade, "leitura_velha": velha, "demo": demo,
            "motivo_nao_recomendado": None, "recomendavel": True, "variacao_1h": variacao, "ativo": ativo}


ABRIGOS = [
    abrigo("abr-03", "Colégio Cândido José de Godoi", -30.00230, -51.20271, ocupacao=20, risco=True, severidade=2),
    abrigo("abr-18", "Colégio Dom João Becker", -30.01252, -51.17670, ocupacao=150),  # lotado
    abrigo("abr-10", "Escola Professora Maria Thereza da Silveira", -30.02832, -51.18409, ocupacao=10,
           estacao="dil-ipiranga"),
    abrigo("abr-11", "Colégio Leonardo da Vinci Unidade Alfa", -30.03452, -51.20279, ocupacao=140, variacao=30,
           estacao="dil-ipiranga"),  # tem vaga agora, mas deve lotar antes de a pessoa chegar
    abrigo("abr-07", "Colégio Florinda Tubino Sampaio", -30.04072, -51.18162, ocupacao=5, estacao="dil-ipiranga"),
    abrigo("abr-demo", "Abrigo de demonstração (Wokwi)", -30.0346, -51.2177, capacidade=50, estacao="demo-wokwi",
           demo=True),
]


def historico(estacao_id: str, niveis: list[float]) -> list[LinhaFeatures]:
    """Série horária de brinquedo: features simples e o alvo 6 h depois."""
    inicio = AGORA - timedelta(hours=len(niveis))
    linhas = []
    for i, nivel in enumerate(niveis):
        futuro = niveis[i + 6] if i + 6 < len(niveis) else None
        variacao = round(nivel - niveis[i - 1], 2) if i else None
        linhas.append(LinhaFeatures(estacao_id, inicio + timedelta(hours=i), nivel, variacao, 0.0, 0.0, 0.0, futuro))
    return linhas


class RepoMemoria:
    def __init__(self, features: list[dict] | None = None, abrigos: list[dict] | None = None):
        self._features = features if features is not None else [
            feature_atual("gua-cais", 2.40, 0.10, 10.0, 60.0, 120.0),
            feature_atual("dil-ipiranga", 0.45),
            feature_atual("gra-sarandi", 3.10, 0.05, 2.0, 20.0, 60.0),
        ]
        self._abrigos = abrigos if abrigos is not None else ABRIGOS
        self.verificacoes = 0

    def verificar(self) -> None:
        self.verificacoes += 1

    def estacoes(self):
        return ESTACOES

    def bairros(self):
        return BAIRROS

    def features_atuais(self):
        return self._features

    def abrigos(self):
        return self._abrigos

    def features_historicas(self):
        subida = [1.0] * 10 + [1.0 + 0.2 * i for i in range(1, 15)] + [3.8] * 10
        return {e: historico(e, subida) for e in ("gua-cais", "dil-ipiranga", "gra-sarandi")}
