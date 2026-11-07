"""Junta repositório + modelo + regras. Usado pela API, pelo vigia e pelo relatório."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from . import avaliacao
from .abrigos import Avaliacao, SituacaoAbrigo, distancia_km, recomendar
from .features import FEATURES, LinhaFeatures
from .mensagens import AbrigoMensagem, Fatos
from .previsao import ModeloPrevisao, Previsao, repetir_nivel_atual
from .repositorio import Bairro, Estacao, Repositorio


@dataclass(frozen=True)
class PrevisaoAtual:
    previsao: Previsao
    estacao: Estacao
    entrada: dict[str, float]
    medido_em_utc: datetime | None
    leitura_velha: bool
    modelo: str
    dados_incompletos: bool = False  # faltou leitura para alguma feature: a "previsão" repete o nível de agora

    @property
    def confiavel(self) -> bool:
        """Só uma previsão com leitura recente e features completas decide alguma coisa (vigia, abrigos)."""
        return not self.leitura_velha and not self.dados_incompletos


def previsoes_atuais(repo: Repositorio, modelo: ModeloPrevisao) -> list[PrevisaoAtual]:
    """Previsão de 6 h de cada rio com modelo, a partir de gold.v_ml_features_atual."""
    estacoes = repo.estacoes()
    resultado = []
    for linha in repo.features_atuais():
        estacao_id = linha["estacao_id"]
        if estacao_id not in modelo.modelos or estacao_id not in estacoes or linha["nivel_atual_m"] is None:
            continue
        cotas = estacoes[estacao_id].cotas
        entrada = {nome: float(linha[nome]) for nome in FEATURES if linha[nome] is not None}
        incompleta = len(entrada) < len(FEATURES)
        if incompleta:
            # Ex.: menos de 2 h de leituras de nível, então não há variação da última hora. O treino descartou
            # essas horas (LinhaFeatures.completa); inventar um 0 faria o modelo ver "rio parado".
            previsao = repetir_nivel_atual(estacao_id, linha["nivel_atual_m"], cotas)
        else:
            previsao = modelo.prever(estacao_id, entrada, cotas)
        resultado.append(PrevisaoAtual(
            previsao, estacoes[estacao_id], entrada, linha["medido_em_utc"], bool(linha["leitura_velha"]),
            "regra_simples" if incompleta else modelo.nome_do_modelo(estacao_id), dados_incompletos=incompleta,
        ))
    return resultado


def situacoes_dos_abrigos(repo: Repositorio, previsoes: list[PrevisaoAtual]) -> list[SituacaoAbrigo]:
    # Previsão sem leitura recente ou com feature faltando não vale: o abrigo fica só com a situação de agora.
    severidade_prevista = {p.previsao.estacao_id: p.previsao.severidade_prevista for p in previsoes if p.confiavel}
    situacoes = []
    for a in repo.abrigos():
        indisponivel = None  # mesma ordem de motivos da gold.v_abrigo_status
        if not a["ativo"]:
            indisponivel = "abrigo inativo"
        elif a["demo"]:
            indisponivel = "abrigo de demonstração"
        elif a["leitura_velha"]:
            indisponivel = "sem leitura recente de ocupação"
        situacoes.append(SituacaoAbrigo(
            abrigo_id=a["abrigo_id"], nome=a["abrigo"], lat=a["lat"], lon=a["lon"], capacidade=int(a["capacidade"]),
            ocupacao=int(a["ocupacao"]), chegando_por_hora=float(a["variacao_1h"] or 0),
            em_area_de_risco=bool(a["em_area_de_risco"]), estacao_proxima_id=a["estacao_proxima_id"],
            severidade_atual_regiao=int(a["severidade_regiao"]),
            # Sem previsão válida (estação de demonstração ou leitura velha): vale a situação atual.
            severidade_prevista_regiao=severidade_prevista.get(a["estacao_proxima_id"], int(a["severidade_regiao"])),
            indisponivel=indisponivel,
        ))
    return situacoes


def estacao_da_regiao(bairro: Bairro, previsoes: list[PrevisaoAtual]) -> PrevisaoAtual | None:
    """O rio que importa para um bairro: a estação com modelo mais perto do centro do bairro."""
    if not previsoes:
        return None
    return min(previsoes, key=lambda p: distancia_km(bairro.lat, bairro.lon, p.estacao.lat, p.estacao.lon))


def recomendar_para_bairro(abrigos: list[SituacaoAbrigo], bairro: Bairro, pessoas: int, limite: int = 3):
    return recomendar(abrigos, bairro.lat, bairro.lon, pessoas, limite)


def fatos(
    p: PrevisaoAtual,
    bairro: Bairro | None = None,
    abrigo: Avaliacao | None = None,
    erros: dict | None = None,
) -> Fatos:
    """Monta a entrada do gerador de mensagens a partir da previsão (e do abrigo recomendado)."""
    previsao, cotas = p.previsao, p.estacao.cotas
    nivel = max(previsao.severidade_atual, previsao.severidade_prevista)
    erro = (erros or {}).get(previsao.estacao_id, {})
    return Fatos(
        estacao=p.estacao.nome,
        corpo_hidrico=p.estacao.corpo_hidrico,
        nivel_atual_m=previsao.nivel_atual_m,
        nivel_previsto_m=previsao.nivel_previsto_m,
        severidade_atual=previsao.severidade_atual,
        severidade_prevista=previsao.severidade_prevista,
        cota_m=cotas.por_severidade(nivel) if nivel else None,
        bairro=bairro.nome if bairro else None,
        abrigo=AbrigoMensagem(abrigo.abrigo.nome, abrigo.minutos_a_pe, abrigo.vagas_na_chegada) if abrigo else None,
        erro_modelo_m=erro.get("modelo"),
        erro_regra_simples_m=erro.get("persistencia"),
    )


def avaliar_no_historico(
    historico: dict[str, list[LinhaFeatures]],
    modelo: ModeloPrevisao,
    estacoes: dict[str, Estacao],
    previstos: dict | None = None,
) -> dict:
    """Teste do modelo nos dados do pipeline (gold.v_ml_features), contra a persistência.

    Erro: só nas horas com o alvo conhecido. Alarmes: na série toda, para as cotas de
    alerta (todos os rios) e de inundação (Guaíba, o único que chega lá no histórico).
    `previstos` ({(estacao_id, hora_utc): nível}) evita prever de novo o que já foi previsto.
    """
    resultado = {}
    for estacao_id in modelo.estacoes:
        linhas = [linha for linha in historico.get(estacao_id, []) if linha.completa()]
        if not linhas:
            resultado[estacao_id] = {"horas": 0}
            continue
        atuais = [linha.nivel_atual_m for linha in linhas]
        if previstos is not None:
            niveis_previstos = [previstos[estacao_id, linha.hora_utc] for linha in linhas]
        else:
            niveis_previstos = modelo.prever_niveis(estacao_id, [linha.vetor() for linha in linhas])
        reais = [linha.nivel_6h_depois_m for linha in linhas]
        erro_modelo = avaliacao.erro(niveis_previstos, reais)
        erro_persistencia = avaliacao.erro(atuais, reais)
        cotas = estacoes[estacao_id].cotas
        alarmes = {}
        for nome, cota in (("alerta", cotas.alerta_m), ("inundacao", cotas.inundacao_m)):
            alarmes[nome] = {
                "modelo": avaliacao.alarmes(atuais, niveis_previstos, cota),
                "persistencia": avaliacao.alarmes(atuais, atuais, cota),
            }
        resultado[estacao_id] = {
            "horas": len(linhas),
            "inicio_utc": linhas[0].hora_utc,
            "fim_utc": linhas[-1].hora_utc,
            "modelo": modelo.nome_do_modelo(estacao_id),
            "erro_modelo": erro_modelo,
            "erro_persistencia": erro_persistencia,
            "ganho_mae_pct": avaliacao.ganho_percentual(erro_modelo["mae_m"], erro_persistencia["mae_m"]),
            "ganho_rmse_pct": avaliacao.ganho_percentual(erro_modelo["rmse_m"], erro_persistencia["rmse_m"]),
            "alarmes": alarmes,
        }
    return resultado


def erros_para_mensagem(avaliacao_historico: dict) -> dict[str, dict[str, float | None]]:
    return {
        estacao_id: {"modelo": r["erro_modelo"]["mae_m"], "persistencia": r["erro_persistencia"]["mae_m"]}
        for estacao_id, r in avaliacao_historico.items()
        if r.get("horas")
    }
