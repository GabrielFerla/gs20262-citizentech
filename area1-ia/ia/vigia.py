"""Automação: o "vigia" emite sozinho o ALERTA ANTECIPADO quando a previsão cruza uma cota.

Roda numa thread da API (a cada VIGIA_INTERVALO_S segundos):
1. lê as features atuais do gold e calcula a previsão de 6 h de cada rio;
2. aplica ao NÍVEL PREVISTO a mesma regra de alerta da fase 1 (abre na cota de atenção,
   escala, nunca rebaixa enquanto aberto e só fecha 0,10 m abaixo da cota de atenção);
3. quando abre ou escala, gera a mensagem em linguagem simples e registra no log
   ("[vigia] ..."). O estado fica em memória e aparece em GET /alertas.
4. estação sem leitura recente não tem previsão confiável: o alerta dela é encerrado
   ("sem_dados") em vez de ficar aberto para sempre.

Assim a Defesa Civil é avisada quando o rio AINDA VAI chegar à cota, e não só quando
ele já chegou (que é quando o silver.alerta da fase 1 abre).
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from .previsao import SITUACOES, Cotas, Previsao

log = logging.getLogger("ia.vigia")

FOLGA_M = 0.10  # igual à fase 1 (area2-bigdata/ingestor/ingestor/alertas.py)


def proxima_acao(severidade_aberta: int, nivel: float, cotas: Cotas, folga: float = FOLGA_M) -> tuple[str, int]:
    """Mesma regra de ingestor.alertas.proximo_alerta, aplicada ao nível previsto."""
    alvo = cotas.severidade(nivel)
    if severidade_aberta == 0:
        return ("abrir", alvo) if alvo > 0 else ("nenhuma", 0)
    if alvo > severidade_aberta:
        return "escalar", alvo
    if nivel < cotas.atencao_m - folga:
        return "fechar", 0
    return "manter", severidade_aberta


@dataclass
class AlertaAntecipado:
    estacao_id: str
    severidade: int
    aberto_em: datetime
    atualizado_em: datetime
    nivel_previsto_m: float
    pico_previsto_m: float
    antecipado: bool  # a previsão estava pior que o nível de agora quando abriu/escalou
    mensagem_sms: str | None = None


@dataclass
class Evento:
    quando: datetime
    estacao_id: str
    acao: str
    severidade: int
    nivel_atual_m: float | None  # None quando encerrado por falta de dados
    nivel_previsto_m: float


@dataclass
class Vigia:
    abertos: dict[str, AlertaAntecipado] = field(default_factory=dict)
    eventos: deque[Evento] = field(default_factory=lambda: deque(maxlen=100))
    ultima_rodada: datetime | None = None
    ultimo_erro: str | None = None
    _trava: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def atualizar(
        self,
        previsoes: list[Previsao],
        cotas: dict[str, Cotas],
        mensagem: Callable[[Previsao], str | None] = lambda _: None,
        agora: datetime | None = None,
        sem_dados: Iterable[str] = (),
    ) -> list[Evento]:
        """Aplica a regra a cada previsão. Devolve só as mudanças (abrir, escalar, fechar, sem_dados)."""
        agora = agora or datetime.now(UTC)
        mudancas = []
        with self._trava:
            for estacao_id in sem_dados:
                aberto = self.abertos.pop(estacao_id, None)
                if aberto is not None:
                    evento = Evento(agora, estacao_id, "sem_dados", 0, None, aberto.nivel_previsto_m)
                    self.eventos.append(evento)
                    mudancas.append(evento)
                    log.warning("[vigia] alerta pela previsão em %s encerrado: sem leitura recente", estacao_id)
            for p in previsoes:
                aberto = self.abertos.get(p.estacao_id)
                acao, severidade = proxima_acao(aberto.severidade if aberto else 0, p.nivel_previsto_m, cotas[p.estacao_id])
                if acao == "abrir":
                    self.abertos[p.estacao_id] = AlertaAntecipado(
                        p.estacao_id, severidade, agora, agora, p.nivel_previsto_m, p.nivel_previsto_m,
                        antecipado=p.severidade_prevista > p.severidade_atual, mensagem_sms=mensagem(p),
                    )
                elif acao in ("escalar", "manter"):
                    aberto.atualizado_em = agora
                    aberto.nivel_previsto_m = p.nivel_previsto_m
                    aberto.pico_previsto_m = max(aberto.pico_previsto_m, p.nivel_previsto_m)
                    if acao == "escalar":
                        aberto.severidade = severidade
                        aberto.antecipado = p.severidade_prevista > p.severidade_atual
                        aberto.mensagem_sms = mensagem(p)
                elif acao == "fechar":
                    del self.abertos[p.estacao_id]
                if acao in ("abrir", "escalar", "fechar"):
                    evento = Evento(agora, p.estacao_id, acao, severidade, p.nivel_atual_m, p.nivel_previsto_m)
                    self.eventos.append(evento)
                    mudancas.append(evento)
                    aberto = self.abertos.get(p.estacao_id)
                    tipo = "ANTECIPADO (a previsão está pior que agora)" if aberto and aberto.antecipado else ""
                    log.info("[vigia] %s alerta pela previsão em %s: %s %s| agora %.2f m (%s), em 6 h %.2f m (%s)%s",
                             acao, p.estacao_id, SITUACOES[severidade], tipo and tipo + " ", p.nivel_atual_m,
                             p.situacao_atual, p.nivel_previsto_m, p.situacao_prevista,
                             f" | SMS: {aberto.mensagem_sms}" if aberto and aberto.mensagem_sms else "")
            self.ultima_rodada = agora
        return mudancas

    def foto(self) -> dict:
        """Cópia do estado para a API (sem segurar a trava durante a resposta)."""
        with self._trava:
            return {
                "ultima_rodada_utc": self.ultima_rodada,
                "ultimo_erro": self.ultimo_erro,
                "abertos": [vars(a).copy() for a in self.abertos.values()],
                "eventos": [vars(e).copy() for e in reversed(self.eventos)],
            }


def rodar_em_segundo_plano(vigia: Vigia, rodada: Callable[[], None], intervalo_s: float, parar: threading.Event) -> None:
    """Laço da thread: uma rodada a cada intervalo; um erro não derruba o vigia."""
    while not parar.is_set():
        try:
            rodada()
            vigia.ultimo_erro = None
        except Exception as erro:  # banco fora do ar, por exemplo: tenta de novo na próxima rodada
            vigia.ultimo_erro = str(erro)[:300]
            log.warning("[vigia] rodada falhou: %s", erro)
        parar.wait(intervalo_s)
