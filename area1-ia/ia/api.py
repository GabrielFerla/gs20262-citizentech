"""API da IA: previsão do nível dos rios, "onde ficar seguro" e mensagens de alerta.

    uvicorn ia.api:app --host 0.0.0.0 --port 8000     # Swagger em http://localhost:8000/docs

Lê só a camada gold (usuário ia_ro). A localização exata do cidadão não é enviada:
a recomendação usa o centro do bairro, e GET /abrigos devolve a avaliação de todos os
abrigos para o app ordenar pela distância no próprio celular.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Iterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import servicos
from .abrigos import Avaliacao, avaliar
from .config import dsn_ia, origens_cors, pasta_modelo
from .mensagens import AbrigoMensagem, Fatos, gerar
from .previsao import SITUACOES, ModeloPrevisao
from .repositorio import Repositorio, RepositorioGold
from .vigia import Vigia, rodar_em_segundo_plano

log = logging.getLogger("ia.api")
CACHE_AVALIACAO_S = 300


# ----------------------------------------------------------------------------- modelos de resposta
class Cotas(BaseModel):
    atencao_m: float
    alerta_m: float
    inundacao_m: float


class EstacaoPrevisao(BaseModel):
    estacao_id: str
    estacao: str
    corpo_hidrico: str
    medido_em_utc: datetime | None
    leitura_velha: bool = Field(description="última leitura com mais de 30 min: previsão pouco confiável")
    nivel_atual_m: float
    nivel_previsto_6h_m: float = Field(description="previsão da IA para daqui a 6 h")
    persistencia_6h_m: float = Field(description="regra simples: daqui a 6 h igual a agora")
    variacao_prevista_m: float
    tendencia: str = Field(description="subindo | estavel | descendo")
    situacao_atual: str = Field(description=" | ".join(SITUACOES))
    situacao_prevista: str
    alerta_antecipado: bool = Field(description="a previsão está pior que a situação de agora")
    cotas: Cotas
    modelo: str
    entrada: dict[str, float] = Field(description="features usadas (gold.v_ml_features_atual)")


class AbrigoAvaliado(BaseModel):
    abrigo_id: str
    abrigo: str
    lat: float
    lon: float
    capacidade: int
    ocupacao: int
    vagas: int
    vagas_previstas_na_chegada: int | None = Field(
        description="vagas quando a pessoa chegar (só na recomendação, que sabe a distância)")
    chegando_por_hora: float
    minutos_ate_lotar: int | None = Field(
        description="em quantos minutos deixa de ter vaga para o grupo, no ritmo da última hora (vazio = não está enchendo)")
    em_area_de_risco: bool
    estacao_proxima_id: str
    situacao_atual_regiao: str
    situacao_prevista_regiao: str
    apto: bool = Field(description="em GET /abrigos: apto AGORA; o app ainda confere minutos_a_pe ≤ minutos_ate_lotar")
    motivo: str | None = Field(description="por que não é recomendado (linguagem simples)")
    distancia_km: float | None = None
    minutos_a_pe: int | None = None


class AbrigoEntrada(BaseModel):
    nome: str = Field(min_length=1, max_length=120, examples=["Colégio Dom João Becker"])
    minutos_a_pe: int | None = Field(default=None, ge=0, le=600, examples=[34])
    vagas: int | None = Field(default=None, ge=0, le=10000, examples=[96])


class FatosEntrada(BaseModel):
    """Entrada do gerador de mensagens (o mesmo que a API monta a partir da previsão)."""

    # Limites de tamanho: com eles o SMS sempre cabe em 160 caracteres (teste em test_mensagens_alerta.py).
    estacao: str = Field(min_length=1, max_length=80, examples=["Guaíba - Cais Mauá"])
    corpo_hidrico: str = Field(min_length=1, max_length=24, examples=["Lago Guaíba"])
    nivel_atual_m: float = Field(ge=0, le=20, examples=[2.62])
    nivel_previsto_m: float = Field(ge=0, le=20, examples=[3.08])
    severidade_atual: int = Field(ge=0, le=3, description="0 normal, 1 atenção, 2 alerta, 3 inundação", examples=[2])
    severidade_prevista: int = Field(ge=0, le=3, examples=[3])
    cota_m: float | None = Field(default=None, examples=[3.0])
    bairro: str | None = Field(default=None, max_length=60, examples=["Navegantes"])
    abrigo: AbrigoEntrada | None = None


class MensagensSaida(BaseModel):
    intencao: str
    sms: str | None
    push_titulo: str | None
    push_corpo: str | None
    whatsapp: str | None
    defesa_civil: str
    verificacao: dict[str, list[str]] = Field(description="problemas por canal (vazio = passou nas regras)")


class Recomendacao(BaseModel):
    bairro_id: str
    bairro: str
    origem: str
    pessoas: int
    estacao_da_regiao: EstacaoPrevisao | None
    recomendados: list[AbrigoAvaliado]
    evitados: list[AbrigoAvaliado] = Field(description="abrigos mais perto que o 1º recomendado, com o motivo")
    mensagens: MensagensSaida | None


# ----------------------------------------------------------------------------- ciclo de vida
class ConexaoDoVigia:
    """Uma conexão só, reaproveitada entre as rodadas do vigia (reabre se cair)."""

    def __init__(self) -> None:
        self.conn: psycopg.Connection | None = None

    def repositorio(self) -> RepositorioGold:
        if self.conn is None or self.conn.closed:
            self.conn = psycopg.connect(dsn_ia(), autocommit=True)
        return RepositorioGold(self.conn)

    def fechar(self) -> None:
        if self.conn is not None:
            self.conn.close()
        self.conn = None


def _rodada_do_vigia(app: FastAPI) -> None:
    modelo: ModeloPrevisao = app.state.modelo
    conexao: ConexaoDoVigia = app.state.conexao_vigia
    try:
        todas = servicos.previsoes_atuais(conexao.repositorio(), modelo)
    except psycopg.Error:
        conexao.fechar()  # na próxima rodada abre outra
        raise
    previsoes = [p for p in todas if not p.leitura_velha]
    por_estacao = {p.previsao.estacao_id: p for p in previsoes}
    app.state.vigia.atualizar(
        [p.previsao for p in previsoes],
        {p.previsao.estacao_id: p.estacao.cotas for p in previsoes},
        mensagem=lambda prev: gerar(servicos.fatos(por_estacao[prev.estacao_id])).sms,
        sem_dados=[p.previsao.estacao_id for p in todas if p.leitura_velha],
    )


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app.state.modelo = ModeloPrevisao.carregar(pasta_modelo())
    app.state.vigia = Vigia()
    app.state.conexao_vigia = ConexaoDoVigia()
    app.state.cache_avaliacao = (0.0, None)
    parar = threading.Event()
    intervalo = float(os.environ.get("VIGIA_INTERVALO_S", "2"))
    if intervalo > 0:
        threading.Thread(
            target=rodar_em_segundo_plano, args=(app.state.vigia, lambda: _rodada_do_vigia(app), intervalo, parar),
            name="vigia", daemon=True,
        ).start()
        log.info("Vigia ligado: previsão a cada %.0f s", intervalo)
    yield
    parar.set()
    app.state.conexao_vigia.fechar()


app = FastAPI(
    title="CitizenTech — IA de enchentes (Porto Alegre)",
    version="2.0.0",
    description=(
        "Previsão do nível dos rios para daqui a 6 h, recomendação de abrigo seguro e mensagens de alerta "
        "em linguagem simples. Dados: camada gold do pipeline (área 2)."
    ),
    lifespan=ciclo_de_vida,
)
app.add_middleware(CORSMiddleware, allow_origins=origens_cors(), allow_methods=["GET", "POST"], allow_headers=["*"])


@app.exception_handler(psycopg.OperationalError)
def banco_indisponivel(_pedido: Request, erro: psycopg.OperationalError) -> JSONResponse:
    """Banco fora do ar (ao conectar ou no meio da consulta): 503 em qualquer rota, não 500."""
    log.warning("Banco indisponível: %s", str(erro).strip()[:200])
    return JSONResponse({"detail": "banco de dados indisponível; tente de novo em instantes"}, status_code=503)


def obter_repositorio() -> Iterator[Repositorio]:
    with psycopg.connect(dsn_ia()) as conn:
        yield RepositorioGold(conn)


def obter_modelo() -> ModeloPrevisao:
    return app.state.modelo


Repo = Annotated[Repositorio, Depends(obter_repositorio)]
Modelo = Annotated[ModeloPrevisao, Depends(obter_modelo)]


# ----------------------------------------------------------------------------- conversões
def _estacao(p: servicos.PrevisaoAtual) -> EstacaoPrevisao:
    prev, c = p.previsao, p.estacao.cotas
    return EstacaoPrevisao(
        estacao_id=prev.estacao_id, estacao=p.estacao.nome, corpo_hidrico=p.estacao.corpo_hidrico,
        medido_em_utc=p.medido_em_utc, leitura_velha=p.leitura_velha, nivel_atual_m=prev.nivel_atual_m,
        nivel_previsto_6h_m=prev.nivel_previsto_m, persistencia_6h_m=prev.persistencia_m,
        variacao_prevista_m=prev.variacao_prevista_m, tendencia=prev.tendencia, situacao_atual=prev.situacao_atual,
        situacao_prevista=prev.situacao_prevista, alerta_antecipado=prev.severidade_prevista > prev.severidade_atual,
        cotas=Cotas(atencao_m=c.atencao_m, alerta_m=c.alerta_m, inundacao_m=c.inundacao_m),
        modelo=p.modelo, entrada=p.entrada,
    )


def _abrigo(a: Avaliacao, pessoas: int, com_chegada: bool = True) -> AbrigoAvaliado:
    s = a.abrigo
    return AbrigoAvaliado(
        abrigo_id=s.abrigo_id, abrigo=s.nome, lat=s.lat, lon=s.lon, capacidade=s.capacidade, ocupacao=s.ocupacao,
        vagas=s.vagas, vagas_previstas_na_chegada=a.vagas_na_chegada if com_chegada else None,
        chegando_por_hora=s.chegando_por_hora, minutos_ate_lotar=s.minutos_ate_lotar(pessoas),
        em_area_de_risco=s.em_area_de_risco, estacao_proxima_id=s.estacao_proxima_id,
        situacao_atual_regiao=SITUACOES[s.severidade_atual_regiao],
        situacao_prevista_regiao=SITUACOES[s.severidade_prevista_regiao],
        apto=a.apto, motivo=a.motivo, distancia_km=a.distancia_km, minutos_a_pe=a.minutos_a_pe,
    )


def _avaliacao_em_cache(repo: Repositorio, modelo: ModeloPrevisao) -> dict:
    criado, valor = app.state.cache_avaliacao
    if valor is None or time.monotonic() - criado > CACHE_AVALIACAO_S:
        valor = servicos.avaliar_no_historico(repo.features_historicas(), modelo, repo.estacoes())
        app.state.cache_avaliacao = (time.monotonic(), valor)
    return valor


# ----------------------------------------------------------------------------- rotas
@app.get("/", include_in_schema=False)
def inicio() -> dict:
    return {"nome": app.title, "documentacao": "/docs", "saude": "/saude"}


@app.get("/saude", tags=["sistema"], summary="Banco acessível, modelo carregado e situação do vigia")
def saude(repo: Repo, modelo: Modelo) -> dict:
    repo.verificar()  # banco fora do ar → 503 (banco_indisponivel)
    return {
        "status": "ok",
        "banco": True,
        "modelo": {"estacoes": modelo.estacoes, "horizonte_h": modelo.horizonte_h},
        "vigia": {k: v for k, v in app.state.vigia.foto().items() if k in ("ultima_rodada_utc", "ultimo_erro")},
    }


@app.get("/modelo", tags=["previsão"], summary="Modelo escolhido por rio e erro na validação cruzada (treino)")
def modelo_info(modelo: Modelo) -> dict:
    return modelo.info


@app.get("/modelo/avaliacao", tags=["previsão"],
         summary="Teste ao vivo: IA × regra simples nos dados do pipeline (gold.v_ml_features)")
def modelo_avaliacao(repo: Repo, modelo: Modelo) -> dict:
    return _avaliacao_em_cache(repo, modelo)


@app.get("/previsao", tags=["previsão"], response_model=list[EstacaoPrevisao],
         summary="Nível atual e previsto para daqui a 6 h em cada rio")
def previsao(repo: Repo, modelo: Modelo) -> list[EstacaoPrevisao]:
    return [_estacao(p) for p in servicos.previsoes_atuais(repo, modelo)]


@app.get("/previsao/{estacao_id}", tags=["previsão"], response_model=EstacaoPrevisao, summary="Previsão de um rio")
def previsao_estacao(estacao_id: str, repo: Repo, modelo: Modelo) -> EstacaoPrevisao:
    for p in servicos.previsoes_atuais(repo, modelo):
        if p.previsao.estacao_id == estacao_id:
            return _estacao(p)
    raise HTTPException(404, f"estação '{estacao_id}' não existe ou não tem previsão (use GET /previsao)")


@app.get("/bairros", tags=["abrigos"], summary="Bairros aceitos em /abrigos/recomendacao")
def bairros(repo: Repo) -> list[dict]:
    return [{"bairro_id": b.bairro_id, "bairro": b.nome, "zona_risco": b.zona_risco} for b in repo.bairros().values()]


@app.get("/abrigos", tags=["abrigos"], response_model=list[AbrigoAvaliado],
         summary="Todos os abrigos com a avaliação da IA; o app termina no celular (distância e lotar na chegada)")
def abrigos(repo: Repo, modelo: Modelo, pessoas: Annotated[int, Query(ge=1, le=50)] = 1) -> list[AbrigoAvaliado]:
    """Sem a posição da pessoa, avalia o AGORA (vaga, risco atual e previsto). No celular, o app
    descarta os abrigos com minutos_a_pe > minutos_ate_lotar e ordena os aptos pela distância."""
    situacoes = servicos.situacoes_dos_abrigos(repo, servicos.previsoes_atuais(repo, modelo))
    return [_abrigo(avaliar(s, pessoas), pessoas, com_chegada=False) for s in situacoes]


@app.get("/abrigos/recomendacao", tags=["abrigos"], response_model=Recomendacao,
         summary="Onde ficar seguro: os 3 abrigos aptos mais perto do bairro, e por que os outros foram evitados")
def recomendacao(
    repo: Repo,
    modelo: Modelo,
    bairro: Annotated[str, Query(description="bairro_id (veja GET /bairros)", examples=["navegantes"])],
    pessoas: Annotated[int, Query(ge=1, le=50)] = 1,
    limite: Annotated[int, Query(ge=1, le=10)] = 3,
) -> Recomendacao:
    todos = repo.bairros()
    if bairro not in todos:
        raise HTTPException(404, f"bairro '{bairro}' não encontrado (use GET /bairros)")
    b = todos[bairro]
    previsoes = servicos.previsoes_atuais(repo, modelo)
    resultado = servicos.recomendar_para_bairro(servicos.situacoes_dos_abrigos(repo, previsoes), b, pessoas, limite)
    regiao = servicos.estacao_da_regiao(b, previsoes)
    mensagens = None
    if regiao is not None:
        primeiro = resultado.recomendados[0] if resultado.recomendados else None
        mensagens = MensagensSaida(**gerar(servicos.fatos(regiao, b, primeiro)).para_dict())
    return Recomendacao(
        bairro_id=b.bairro_id, bairro=b.nome, origem="centro do bairro (a posição exata não sai do celular)",
        pessoas=pessoas, estacao_da_regiao=_estacao(regiao) if regiao else None,
        recomendados=[_abrigo(a, pessoas) for a in resultado.recomendados],
        evitados=[_abrigo(a, pessoas) for a in resultado.evitados],
        mensagens=mensagens,
    )


@app.get("/alertas", tags=["alertas"],
         summary="Alertas antecipados do vigia e mensagens de cada rio fora do normal (agora ou em 6 h)")
def alertas(repo: Repo, modelo: Modelo, bairro: Annotated[str | None, Query(examples=["navegantes"])] = None) -> dict:
    previsoes = servicos.previsoes_atuais(repo, modelo)
    erros = servicos.erros_para_mensagem(_avaliacao_em_cache(repo, modelo))
    b = abrigo = regiao = None
    if bairro is not None:
        todos = repo.bairros()
        if bairro not in todos:
            raise HTTPException(404, f"bairro '{bairro}' não encontrado (use GET /bairros)")
        b = todos[bairro]
        regiao = servicos.estacao_da_regiao(b, previsoes)
        rec = servicos.recomendar_para_bairro(servicos.situacoes_dos_abrigos(repo, previsoes), b, 1)
        abrigo = rec.recomendados[0] if rec.recomendados else None
    rios = []
    for p in previsoes:
        if max(p.previsao.severidade_atual, p.previsao.severidade_prevista) == 0:
            continue
        da_regiao = regiao is not None and p.previsao.estacao_id == regiao.previsao.estacao_id
        f = servicos.fatos(p, b if da_regiao else None, abrigo if da_regiao else None, erros)
        rios.append({"previsao": _estacao(p), "mensagens": gerar(f).para_dict()})
    return {"vigia": app.state.vigia.foto(), "rios_fora_do_normal": rios}


@app.post("/mensagens/gerar", tags=["alertas"], response_model=MensagensSaida,
          summary="Demonstração: fatos (entrada) → mensagens em linguagem simples por canal (saída)")
def mensagens_gerar(entrada: FatosEntrada) -> MensagensSaida:
    dados = entrada.model_dump()
    abrigo = dados.pop("abrigo")
    fatos = Fatos(**dados, abrigo=AbrigoMensagem(**abrigo) if abrigo else None)
    return MensagensSaida(**gerar(fatos).para_dict())
