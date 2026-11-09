"""Gera __fixtures__/paridade-geo.json: a resposta da IA (area1-ia/ia/abrigos.py) para o teste de paridade do app.

O app calcula "abrigos perto de mim" no próprio celular (a posição não vai ao servidor). Para garantir
que a conta é a mesma da IA, este script roda a função recomendar() do Python em alguns pontos de
Porto Alegre e grava o resultado. O teste __tests__/paridade-geo.test.ts confere o TypeScript contra ele.

    .venv/bin/python area3-mvp/app/scripts/paridade_geo.py      # na raiz do repositório
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP.parents[1] / "area1-ia"))

from ia.abrigos import SituacaoAbrigo, avaliar, recomendar  # noqa: E402

SITUACOES = ("normal", "atencao", "alerta", "inundacao")  # ia/previsao.py (sem importar o scikit-learn)
INDISPONIVEIS = {"abrigo inativo", "abrigo de demonstração", "sem leitura recente de ocupação"}

# Pontos de partida: centro de três bairros (area2-bigdata/db/seeds/bairros.csv) e o tamanho do grupo.
CASOS = [
    ("Navegantes, 4 pessoas", -29.99363, -51.20077, 4),
    ("Centro Histórico, 1 pessoa", -30.03250, -51.23033, 1),
    ("Cristal, 6 pessoas", -30.08700, -51.24400, 6),
]


def situacoes_da_fixture() -> list[SituacaoAbrigo]:
    """Os abrigos como estavam na resposta real de GET /abrigos guardada em __fixtures__/abrigos-4.json."""
    abrigos = json.loads((APP / "__fixtures__" / "abrigos-4.json").read_text(encoding="utf-8"))
    situacoes = [
        SituacaoAbrigo(
            abrigo_id=a["abrigo_id"], nome=a["abrigo"], lat=a["lat"], lon=a["lon"], capacidade=a["capacidade"],
            ocupacao=a["ocupacao"], chegando_por_hora=a["chegando_por_hora"], em_area_de_risco=a["em_area_de_risco"],
            estacao_proxima_id=a["estacao_proxima_id"],
            severidade_atual_regiao=SITUACOES.index(a["situacao_atual_regiao"]),
            severidade_prevista_regiao=SITUACOES.index(a["situacao_prevista_regiao"]),
            indisponivel=a["motivo"] if a["motivo"] in INDISPONIVEIS else None,
        )
        for a in abrigos
    ]
    # Dois abrigos inventados, enchendo depressa (10 vagas, 30 pessoas/h: para 4 pessoas, lota em 12 min):
    # - a 1 km de Navegantes (20 min a pé): lota antes de a pessoa chegar → evitado;
    # - a 300 m do Centro Histórico (5 min a pé): dá tempo → recomendado.
    base = next(s for s in situacoes if s.abrigo_id == "abr-10")
    situacoes.append(replace(base, abrigo_id="teste-lota-antes", nome="Teste: lota antes de chegar",
                             lat=-29.98463, lon=-51.20077, ocupacao=140, chegando_por_hora=30.0))
    situacoes.append(replace(base, abrigo_id="teste-da-tempo", nome="Teste: enche, mas dá tempo",
                             lat=-30.03000, lon=-51.23033, ocupacao=140, chegando_por_hora=30.0))
    return situacoes


def como_get_abrigos(situacoes: list[SituacaoAbrigo], pessoas: int) -> list[dict]:
    """O que GET /abrigos?pessoas= devolveria (ia/api.py: avaliação de AGORA, sem distância)."""
    saida = []
    for s in situacoes:
        a = avaliar(s, pessoas)
        saida.append({
            "abrigo_id": s.abrigo_id, "abrigo": s.nome, "lat": s.lat, "lon": s.lon, "capacidade": s.capacidade,
            "ocupacao": s.ocupacao, "vagas": s.vagas, "vagas_previstas_na_chegada": None,
            "chegando_por_hora": s.chegando_por_hora, "minutos_ate_lotar": s.minutos_ate_lotar(pessoas),
            "em_area_de_risco": s.em_area_de_risco, "estacao_proxima_id": s.estacao_proxima_id,
            "situacao_atual_regiao": SITUACOES[s.severidade_atual_regiao],
            "situacao_prevista_regiao": SITUACOES[s.severidade_prevista_regiao],
            "apto": a.apto, "motivo": a.motivo, "distancia_km": None, "minutos_a_pe": None,
        })
    return saida


def main() -> None:
    situacoes = situacoes_da_fixture()
    casos = []
    for nome, lat, lon, pessoas in CASOS:
        r = recomendar(situacoes, lat, lon, pessoas)
        casos.append({
            "nome": nome,
            "posicao": {"lat": lat, "lon": lon},
            "pessoas": pessoas,
            "abrigos": como_get_abrigos(situacoes, pessoas),
            "recomendados": [
                {"abrigo_id": a.abrigo.abrigo_id, "distancia_km": a.distancia_km, "minutos_a_pe": a.minutos_a_pe,
                 "vagas_na_chegada": a.vagas_na_chegada}
                for a in r.recomendados
            ],
            "evitados": [
                {"abrigo_id": a.abrigo.abrigo_id, "distancia_km": a.distancia_km, "minutos_a_pe": a.minutos_a_pe,
                 "motivo": a.motivo}
                for a in r.evitados
            ],
        })
    destino = APP / "__fixtures__" / "paridade-geo.json"
    destino.write_text(json.dumps({"gerado_por": "scripts/paridade_geo.py", "casos": casos},
                                  ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for c in casos:
        print(f"{c['nome']}: recomendados {[a['abrigo_id'] for a in c['recomendados']]}, "
              f"evitados {[(a['abrigo_id'], a['motivo']) for a in c['evitados']]}")


if __name__ == "__main__":
    main()
