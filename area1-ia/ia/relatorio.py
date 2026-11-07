"""Gera o relatório da IA (evidência para o PDF) com os dados do pipeline.

    docker compose --profile ferramentas run --rm ia-relatorio
    python -m ia.relatorio --saida area1-ia/relatorio      # fora do Docker (banco em localhost:55432)

Arquivos gerados em area1-ia/relatorio/:
  RELATORIO.md         tabelas: IA × regra simples (previsão) e A × B × C (abrigos)
  metricas.json        os mesmos números, para conferir
  previsao_<rio>.png   real × IA × regra simples na maior cheia do histórico
  abrigos.png          % de pessoas mandadas para abrigo lotado ou que alagou
  demo.md              demonstração com entrada e saída num momento real do histórico
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import psycopg

from . import cenarios_abrigos, servicos
from .avaliacao import cruzamentos_da_cota
from .cenarios_abrigos import AbrigoFixo, Momento
from .config import dsn_ia, pasta_modelo
from .features import FEATURES, HORIZONTE_H, LinhaFeatures
from .mensagens import NOMES_SITUACAO, gerar
from .previsao import ModeloPrevisao
from .repositorio import Estacao, RepositorioGold

log = logging.getLogger("ia.relatorio")
BRT = timezone(timedelta(hours=-3), "BRT")  # Brasil sem horário de verão desde 2019
NOMES_MODELO = {"regra_simples": "regra simples", "regressao_linear": "regressão linear", "random_forest": "random forest"}
BAIRRO_DEMO = "navegantes"
SITUACAO = {"normal": "normal", "atencao": "atenção", "alerta": "alerta", "inundacao": "inundação"}


def _local(hora: datetime) -> str:
    return hora.astimezone(BRT).strftime("%d/%m %Hh")


def _n(valor, casas: int = 2, sufixo: str = "") -> str:
    if valor is None:
        return "—"
    return f"{valor:.{casas}f}".replace(".", ",") + sufixo


def previsoes_por_hora(historico: dict[str, list[LinhaFeatures]], modelo: ModeloPrevisao) -> dict:
    previstos = {}
    for estacao_id in modelo.estacoes:
        linhas = [linha for linha in historico.get(estacao_id, []) if linha.completa()]
        for linha, nivel in zip(linhas, modelo.prever_niveis(estacao_id, [linha.vetor() for linha in linhas]), strict=True):
            previstos[estacao_id, linha.hora_utc] = nivel
    return previstos


# ----------------------------------------------------------------------------- gráficos
def grafico_previsao(
    pasta: Path, estacao: Estacao, linhas: list[LinhaFeatures], previstos: dict, nome_modelo: str
) -> str | None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.dates import DateFormatter

    com_alvo = [linha for linha in linhas if linha.completa() and linha.nivel_6h_depois_m is not None]
    if not com_alvo:
        return None  # histórico curto demais para o gráfico
    pico = max(range(len(com_alvo)), key=lambda i: com_alvo[i].nivel_6h_depois_m)
    janela = com_alvo[max(pico - 72, 0): pico + 48]
    x = [(linha.hora_utc + timedelta(hours=HORIZONTE_H)).astimezone(BRT) for linha in janela]
    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=120)
    ax.plot(x, [linha.nivel_6h_depois_m for linha in janela], color="#1f2937", linewidth=2.2, label="nível real")
    ax.plot(x, [previstos[estacao.estacao_id, linha.hora_utc] for linha in janela], color="#2563eb", linewidth=1.8,
            label=f"IA ({NOMES_MODELO.get(nome_modelo, nome_modelo)}), prevendo 6 h antes")
    ax.plot(x, [linha.nivel_atual_m for linha in janela], color="#9ca3af", linewidth=1.5, linestyle="--",
            label="regra simples (nível de 6 h antes)")
    for cota, nome, cor in ((estacao.cotas.alerta_m, "alerta", "#f59e0b"), (estacao.cotas.inundacao_m, "inundação", "#dc2626")):
        ax.axhline(cota, color=cor, linewidth=1, linestyle=":")
        ax.annotate(f"cota de {nome}", (x[0], cota), xytext=(4, 3), textcoords="offset points", color=cor, fontsize=8)
    ax.set_title(f"{estacao.nome}: previsão do nível 6 h antes, na maior cheia dos 30 dias do pipeline")
    ax.set_ylabel("nível (m)")
    ax.xaxis.set_major_formatter(DateFormatter("%d/%m", tz=BRT))
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    arquivo = f"previsao_{estacao.estacao_id}.png"
    fig.savefig(pasta / arquivo)
    plt.close(fig)
    return arquivo


def grafico_abrigos(pasta: Path, resultado: dict) -> str:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    estrategias = resultado["estrategias"]
    nomes = [e["estrategia"] for e in estrategias.values()]
    lotado = [e["lotado_na_chegada_pct"] or 0 for e in estrategias.values()]
    alagou = [e["abrigo_alagou_pct"] or 0 for e in estrategias.values()]
    fig, ax = plt.subplots(figsize=(9, 4), dpi=120)
    posicoes = range(len(nomes))
    ax.barh([p + 0.2 for p in posicoes], lotado, height=0.4, color="#f59e0b", label="abrigo lotado na chegada")
    ax.barh([p - 0.2 for p in posicoes], alagou, height=0.4, color="#dc2626", label="abrigo alagou em até 6 h")
    for p, (a, b) in enumerate(zip(lotado, alagou, strict=True)):
        ax.annotate(f"{a:.1f}%".replace(".", ","), (a, p + 0.2), xytext=(3, -3), textcoords="offset points", fontsize=8)
        ax.annotate(f"{b:.1f}%".replace(".", ","), (b, p - 0.2), xytext=(3, -3), textcoords="offset points", fontsize=8)
    ax.set_yticks(list(posicoes), nomes)
    ax.invert_yaxis()
    ax.set_xlabel("% das pessoas")
    ax.set_title("Onde ficar seguro: para onde cada estratégia mandou as pessoas")
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(pasta / "abrigos.png")
    plt.close(fig)
    return "abrigos.png"


# ----------------------------------------------------------------------------- textos
def tabela_previsao(previsao: dict, estacoes: dict[str, Estacao]) -> list[str]:
    linhas = [
        "| Rio | Modelo usado | Erro médio (MAE) IA | MAE regra simples | Erro caiu | RMSE IA | RMSE regra simples | Erro caiu |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for estacao_id, r in previsao.items():
        if not r.get("horas"):
            continue
        linhas.append(
            f"| {estacoes[estacao_id].nome} | {NOMES_MODELO.get(r['modelo'], r['modelo'])} "
            f"| {_n(r['erro_modelo']['mae_m'], 3, ' m')} | {_n(r['erro_persistencia']['mae_m'], 3, ' m')} "
            f"| {_n(r['ganho_mae_pct'], 1, '%')} | {_n(r['erro_modelo']['rmse_m'], 3, ' m')} "
            f"| {_n(r['erro_persistencia']['rmse_m'], 3, ' m')} | {_n(r['ganho_rmse_pct'], 1, '%')} |"
        )
    return linhas


def tabela_alarmes(previsao: dict, estacoes: dict[str, Estacao]) -> list[str]:
    linhas = [
        "| Rio | Cota | Vezes que o rio passou da cota | Antecedência da IA "
        "| Antecedência da regra simples | Alarmes falsos da IA |",
        "|---|---|---|---|---|---|",
    ]
    for estacao_id, r in previsao.items():
        if not r.get("horas"):
            continue
        for nome, dados in r["alarmes"].items():
            ia, regra = dados["modelo"], dados["persistencia"]
            if ia["eventos"] == 0:
                continue
            horas = ", ".join(f"{h} h" for h in ia["antecedencias_h"])
            linhas.append(
                f"| {estacoes[estacao_id].nome} | {SITUACAO[nome]} ({_n(ia['cota_m'])} m) | {ia['eventos']} "
                f"| {horas} (média {_n(ia['antecedencia_media_h'], 1, ' h')}) "
                f"| {_n(regra['antecedencia_media_h'], 0, ' h')} | {ia['alarmes_falsos']} |"
            )
    return linhas


def tabela_validacao(info: dict, estacoes: dict[str, Estacao]) -> list[str]:
    linhas = [
        "| Rio | Regra simples | Regressão linear | Random forest | Escolhido |",
        "|---|---|---|---|---|",
    ]
    for estacao_id, r in info.get("estacoes", {}).items():
        c = r["candidatos"]
        linhas.append(
            f"| {estacoes[estacao_id].nome if estacao_id in estacoes else estacao_id} "
            f"| {_n(c['regra_simples']['mae_m'], 3, ' m')} | {_n(c['regressao_linear']['mae_m'], 3, ' m')} "
            f"| {_n(c['random_forest']['mae_m'], 3, ' m')} | **{NOMES_MODELO.get(r['escolhido'], r['escolhido'])}** |"
        )
    return linhas


def tabela_abrigos(resultado: dict) -> list[str]:
    linhas = [
        "| Estratégia | Lotado na chegada | Abrigo alagou | **Falha (um ou outro)** | Sem abrigo apto "
        "| Distância média | Tempo a pé médio |",
        "|---|---|---|---|---|---|---|",
    ]
    for e in resultado["estrategias"].values():
        linhas.append(
            f"| {e['estrategia']} | {_n(e['lotado_na_chegada_pct'], 1, '%')} | {_n(e['abrigo_alagou_pct'], 1, '%')} "
            f"| **{_n(e['falha_pct'], 1, '%')}** | {_n(e['sem_abrigo_apto_pct'], 1, '%')} "
            f"| {_n(e['distancia_media_km'], 2, ' km')} | {e['minutos_a_pe_medio'] or '—'} min |"
        )
    return linhas


def leitura_abrigos(resultado: dict) -> list[str]:
    e = resultado["estrategias"]
    if not resultado["horas_de_crise"]:
        return ["Sem horas de crise no histórico: rode com o histórico completo (30 dias) para esta métrica."]
    a, b, c = e["mais_proximo"], e["regra_fase1"], e["ia"]
    return [
        f"**Leitura:** sem o sistema, {_n(a['falha_pct'], 1, '%')} das famílias iriam para um abrigo lotado ou que alagou. "
        f"A regra da fase 1, que só olha o agora, baixa para {_n(b['falha_pct'], 1, '%')}; a IA, que olha a vaga na "
        f"chegada e o rio previsto para 6 h, para {_n(c['falha_pct'], 1, '%')}. O custo é andar em média "
        f"{(c['minutos_a_pe_medio'] or 0) - (a['minutos_a_pe_medio'] or 0)} min a mais que até o abrigo mais próximo.",
    ]


def escrever_relatorio(pasta: Path, metricas: dict, estacoes: dict[str, Estacao], graficos: list[str]) -> None:
    previsao, abrigos, info = metricas["previsao"], metricas["abrigos"], metricas["treino"]
    periodo = [r for r in previsao.values() if r.get("horas")]
    est = abrigos["estrategias"]
    texto = [
        "# Relatório da IA — previsão de cheia e \"onde ficar seguro\"",
        "",
        f"Gerado em {datetime.now(BRT):%d/%m/%Y %H:%M} (horário de Brasília) por `python -m ia.relatorio`, "
        "com os dados do pipeline (camada gold). Para gerar de novo: "
        "`docker compose --profile ferramentas run --rm ia-relatorio`.",
        "",
        "## 1. Previsão do nível do rio para daqui a 6 h",
        "",
        "**Antes (regra simples / persistência):** \"daqui a 6 h o nível é igual ao de agora\". "
        "**Depois (IA):** modelo treinado com 24 meses simulados, testado nos dados do pipeline, que ele nunca viu "
        f"({periodo[0]['horas'] if periodo else 0} horas por rio, "
        + (f"de {_local(periodo[0]['inicio_utc'])} a {_local(periodo[0]['fim_utc'])}" if periodo else "sem dados")
        + ", `gold.v_ml_features`).",
        "",
        *tabela_previsao(previsao, estacoes),
        "",
        "### Antecedência do alerta",
        "",
        "Quando o rio passou da cota, há quantas horas seguidas a previsão já avisava? "
        "A regra simples só percebe quando o rio já passou (0 h).",
        "",
        *tabela_alarmes(previsao, estacoes),
        "",
        *[f"![{g}]({g})" for g in graficos if g.startswith("previsao_")],
        "",
        "### Validação cruzada no treino (erro médio, MAE)",
        "",
        f"{info.get('validacao', '')}. A regra simples também é candidata: "
        "a IA só substitui a persistência no rio em que provou ser melhor.",
        "",
        *tabela_validacao(info, estacoes),
        "",
        "## 2. Onde ficar seguro: recomendação de abrigo",
        "",
        f"{abrigos['pontos_de_partida']} pontos de partida nos bairros de risco alto × {abrigos['horas_de_crise']} horas "
        f"de crise do histórico = {next(iter(est.values()))['casos'] if est else 0} escolhas por estratégia "
        f"(grupos de {abrigos['pessoas_por_grupo']} pessoas). Cada escolha é conferida com o que aconteceu depois.",
        "",
        *tabela_abrigos(abrigos),
        "",
        *[f"![{g}]({g})" for g in graficos if g == "abrigos.png"],
        "",
        *leitura_abrigos(abrigos),
        "",
    ]
    (pasta / "RELATORIO.md").write_text("\n".join(texto), encoding="utf-8")


def momento_da_demo(
    previsao: dict, historico: dict, previstos: dict, momentos: list[Momento]
) -> tuple[str, LinhaFeatures] | None:
    """A primeira hora em que a IA avisou a maior cheia do Guaíba (ou a de maior previsão, sem cheia)."""
    estacao_id = "gua-cais" if "gua-cais" in previsao else next(iter(previsao))
    linhas = [linha for linha in historico.get(estacao_id, []) if linha.completa()]
    horas_crise = {m.hora for m in momentos}
    for nome in ("inundacao", "alerta"):
        alarmes = previsao[estacao_id].get("alarmes", {}).get(nome, {}).get("modelo", {})
        if alarmes.get("eventos"):
            k = cruzamentos_da_cota([linha.nivel_atual_m for linha in linhas], alarmes["cota_m"])[-1]
            antecedencia = alarmes["antecedencias_h"][-1] if alarmes["antecedencias_h"] else 0
            linha = linhas[max(k - max(antecedencia, 1), 0)]
            if linha.hora_utc in horas_crise:
                return estacao_id, linha
    candidatas = [linha for linha in linhas if linha.hora_utc in horas_crise] or linhas
    if not candidatas:
        return None
    return estacao_id, max(candidatas, key=lambda linha: previstos.get((estacao_id, linha.hora_utc), 0))


def escrever_demo(pasta: Path, modelo: ModeloPrevisao, estacoes, bairros, abrigos, momentos, previsao, historico,
                  previstos) -> None:
    momento_escolhido = momento_da_demo(previsao, historico, previstos, momentos)
    if momento_escolhido is None:
        (pasta / "demo.md").write_text(
            "# Demonstração com entrada e saída\n\nO histórico do pipeline ainda não tem horas suficientes para a "
            "demonstração. Rode com o histórico completo (30 dias) e gere o relatório de novo.\n", encoding="utf-8")
        return
    estacao_id, linha = momento_escolhido
    estacao = estacoes[estacao_id]
    entrada = {nome: getattr(linha, nome) for nome in FEATURES}
    prev = modelo.prever(estacao_id, entrada, estacao.cotas)
    atual = servicos.PrevisaoAtual(prev, estacao, entrada, linha.hora_utc, False, modelo.nome_do_modelo(estacao_id))
    real = linha.nivel_6h_depois_m
    momento = next((m for m in momentos if m.hora == linha.hora_utc), None)
    bairro = bairros.get(BAIRRO_DEMO) or next(iter(bairros.values()))
    texto = [
        "# Demonstração com entrada e saída",
        "",
        f"Momento real do histórico do pipeline: **{_local(linha.hora_utc)}** (horário de Brasília), "
        f"estação **{estacao.nome}**. Gerado por `python -m ia.relatorio`.",
        "",
        "## 1. Previsão do nível em 6 h",
        "",
        "Entrada (features da hora, iguais às de `gold.v_ml_features`):",
        "",
        "```json",
        json.dumps(entrada, ensure_ascii=False, indent=2),
        "```",
        "",
        "Saída:",
        "",
        "| | Nível em 6 h | Situação prevista |",
        "|---|---|---|",
        f"| IA ({NOMES_MODELO.get(atual.modelo, atual.modelo)}) | {_n(prev.nivel_previsto_m, 2, ' m')} "
        f"| {SITUACAO[prev.situacao_prevista]} |",
        f"| Regra simples | {_n(prev.persistencia_m, 2, ' m')} | {SITUACAO[prev.situacao_atual]} |",
        f"| **O que aconteceu** | **{_n(real, 2, ' m')}** "
        f"| **{NOMES_SITUACAO[estacao.cotas.severidade(real)] if real is not None else '—'}** |",
        "",
    ]
    abrigo_ia = None
    if momento is not None:
        sits = cenarios_abrigos.situacoes(abrigos, momento)
        rec = cenarios_abrigos.recomendar(sits, bairro.lat, bairro.lon, cenarios_abrigos.PESSOAS_POR_GRUPO, limite=3)
        perto = cenarios_abrigos.escolher_mais_proximo(sits, bairro.lat, bairro.lon, 4)
        abrigo_ia = rec.recomendados[0] if rec.recomendados else None
        por_id = {a.abrigo_id: a for a in abrigos}
        km_perto = cenarios_abrigos.distancia_km(bairro.lat, bairro.lon, perto.lat, perto.lon) if perto else None

        def desfecho(abrigo_id: str) -> str:
            a = por_id[abrigo_id]
            cheio = a.capacidade - momento.ocupacao_chegada[abrigo_id] < cenarios_abrigos.PESSOAS_POR_GRUPO
            alagou = a.em_area_de_risco and momento.alaga_em_6h.get(a.estacao_proxima_id, False)
            return "alagou nas 6 h seguintes" if alagou else "estava lotado na chegada" if cheio else "seguro, com vaga"

        texto += [
            f"## 2. Onde ficar seguro (família de 4 no bairro {bairro.nome})",
            "",
            f"Entrada: `GET /abrigos/recomendacao?bairro={bairro.bairro_id}&pessoas=4` naquele momento.",
            "",
            "| Estratégia | Abrigo escolhido | Distância | O que aconteceu |",
            "|---|---|---|---|",
            f"| Mais próximo | {perto.nome} | {_n(km_perto, 1, ' km')} | {desfecho(perto.abrigo_id)} |"
            if perto else "| Mais próximo | — | — | — |",
            f"| IA | {abrigo_ia.abrigo.nome} | {_n(abrigo_ia.distancia_km, 1, ' km')} ({abrigo_ia.minutos_a_pe} min a pé) "
            f"| {desfecho(abrigo_ia.abrigo.abrigo_id)} |"
            if abrigo_ia else "| IA | nenhum abrigo apto | — | — |",
            "",
            "Abrigos mais perto que a IA evitou, e por quê:",
            "",
            *[f"- {a.abrigo.nome} ({_n(a.distancia_km, 1, ' km')}): {a.motivo}" for a in rec.evitados],
            "",
        ]
    fatos = servicos.fatos(atual, bairro, abrigo_ia, servicos.erros_para_mensagem(previsao))
    mensagens = gerar(fatos)
    texto += [
        "## 3. Mensagem de alerta em linguagem simples",
        "",
        "Entrada (fatos montados a partir da previsão e do abrigo recomendado):",
        "",
        "```json",
        json.dumps(asdict(fatos), ensure_ascii=False, indent=2),
        "```",
        "",
        "Saída:",
        "",
        "```json",
        json.dumps(mensagens.para_dict(), ensure_ascii=False, indent=2),
        "```",
        "",
        "## 4. A mesma coisa ao vivo, na API",
        "",
        "Com o ambiente no ar (`docker compose up -d --build --wait`), abra http://localhost:8000/docs ou rode:",
        "",
        "```bash",
        "curl -s localhost:8000/previsao",
        "curl -s 'localhost:8000/abrigos/recomendacao?bairro=navegantes&pessoas=4'",
        "curl -s 'localhost:8000/alertas?bairro=navegantes'",
        "curl -s -X POST localhost:8000/mensagens/gerar -H 'Content-Type: application/json' "
        "-d @area1-ia/prompts/exemplo_entrada.json",
        "```",
        "",
    ]
    (pasta / "demo.md").write_text("\n".join(texto), encoding="utf-8")


# ----------------------------------------------------------------------------- principal
def gerar_relatorio(pasta: Path, modelo: ModeloPrevisao, repo: RepositorioGold) -> dict:
    estacoes, bairros, historico = repo.estacoes(), repo.bairros(), repo.features_historicas()
    abrigos = [AbrigoFixo(r["abrigo_id"], r["abrigo"], r["lat"], r["lon"], int(r["capacidade"]), bool(r["em_area_de_risco"]),
                          r["estacao_proxima_id"]) for r in repo.abrigos_cadastro()]
    previstos = previsoes_por_hora(historico, modelo)  # uma vez só: o teste e os cenários usam as mesmas
    previsao = servicos.avaliar_no_historico(historico, modelo, estacoes, previstos)
    momentos = cenarios_abrigos.montar_momentos(
        abrigos, repo.ocupacao_horaria(), repo.niveis_horarios(), previstos,
        {e: estacoes[e].cotas for e in modelo.estacoes},
    )
    resultado_abrigos = cenarios_abrigos.avaliar(abrigos, momentos, cenarios_abrigos.pontos_de_partida(list(bairros.values())))
    metricas = {"gerado_em_utc": datetime.now(UTC), "previsao": previsao, "abrigos": resultado_abrigos, "treino": modelo.info}

    pasta.mkdir(parents=True, exist_ok=True)
    graficos = []
    for estacao_id in ("gua-cais", "gra-sarandi"):
        linhas = historico.get(estacao_id, [])
        if estacao_id in modelo.modelos:
            grafico = grafico_previsao(pasta, estacoes[estacao_id], linhas, previstos, modelo.nome_do_modelo(estacao_id))
            if grafico:
                graficos.append(grafico)
    if momentos:
        graficos.append(grafico_abrigos(pasta, resultado_abrigos))
    (pasta / "metricas.json").write_text(json.dumps(metricas, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    escrever_relatorio(pasta, metricas, estacoes, graficos)
    escrever_demo(pasta, modelo, estacoes, bairros, abrigos, momentos, previsao, historico, previstos)
    return metricas


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Gera o relatório da IA com os dados do pipeline")
    parser.add_argument("--saida", type=Path, default=Path(__file__).resolve().parents[1] / "relatorio")
    args = parser.parse_args()
    modelo = ModeloPrevisao.carregar(pasta_modelo())
    with psycopg.connect(dsn_ia()) as conn:
        metricas = gerar_relatorio(args.saida, modelo, RepositorioGold(conn))
    for chave, e in metricas["abrigos"]["estrategias"].items():
        log.info("abrigos %s: falha %s%% (lotado %s%%, alagou %s%%)", chave, e["falha_pct"], e["lotado_na_chegada_pct"],
                 e["abrigo_alagou_pct"])
    log.info("Relatório gerado em %s", args.saida)


if __name__ == "__main__":
    main()
