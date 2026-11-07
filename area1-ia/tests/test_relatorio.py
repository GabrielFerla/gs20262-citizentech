import json

from apoio_ia import ABRIGOS, RepoMemoria
from ia.relatorio import gerar_relatorio


class RepoRelatorio(RepoMemoria):
    """Repositório em memória com as consultas extras do relatório (série histórica)."""

    def __init__(self, historico: dict | None = None):
        super().__init__()
        self._historico = historico if historico is not None else super().features_historicas()

    def features_historicas(self):
        return self._historico

    def abrigos_cadastro(self):
        return [{k: a[k] for k in ("abrigo_id", "abrigo", "lat", "lon", "capacidade", "em_area_de_risco",
                                   "estacao_proxima_id")} for a in ABRIGOS if not a["demo"]]

    def niveis_horarios(self):
        return {(e, linha.hora_utc): linha.nivel_atual_m for e, linhas in self._historico.items() for linha in linhas}

    def ocupacao_horaria(self):
        horas = sorted({linha.hora_utc for linhas in self._historico.values() for linha in linhas})
        return {(a["abrigo_id"], h): min(i * 5, a["capacidade"]) for a in ABRIGOS for i, h in enumerate(horas)}


def test_relatorio_gera_tabelas_graficos_e_demonstracao(tmp_path, modelo):
    metricas = gerar_relatorio(tmp_path, modelo, RepoRelatorio())
    arquivos = {p.name for p in tmp_path.iterdir()}
    assert {"RELATORIO.md", "metricas.json", "demo.md", "previsao_gua-cais.png", "abrigos.png"} <= arquivos
    texto = (tmp_path / "RELATORIO.md").read_text(encoding="utf-8")
    assert "Antecedência do alerta" in texto and "Onde ficar seguro" in texto
    assert set(json.loads((tmp_path / "metricas.json").read_text(encoding="utf-8"))) >= {"previsao", "abrigos", "treino"}
    assert metricas["abrigos"]["horas_de_crise"] > 0
    assert "Entrada" in (tmp_path / "demo.md").read_text(encoding="utf-8")


def test_relatorio_com_historico_vazio_nao_quebra(tmp_path, modelo):
    gerar_relatorio(tmp_path, modelo, RepoRelatorio(historico={}))
    assert "Sem horas de crise" in (tmp_path / "RELATORIO.md").read_text(encoding="utf-8")
    assert "não tem horas suficientes" in (tmp_path / "demo.md").read_text(encoding="utf-8")
