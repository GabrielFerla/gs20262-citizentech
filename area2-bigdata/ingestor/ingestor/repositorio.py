"""Acesso ao PostgreSQL. Todo SQL do ingestor fica aqui; quem chama controla o commit."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import psycopg

from .alertas import Cotas
from .validacao import LeituraAnterior, Sensor


@dataclass(frozen=True)
class AlertaAberto:
    id: int
    severidade: int
    ultima_leitura_em: datetime


class Repositorio:
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn
        self._sensores: dict[str, Sensor] | None = None
        self._cotas: dict[str, Cotas] | None = None

    # ---------------- cadastros (em memória) ----------------
    def sensores(self) -> dict[str, Sensor]:
        if self._sensores is None:
            self._carregar_cadastros()
        assert self._sensores is not None
        return self._sensores

    def cotas(self, estacao_id: str) -> Cotas:
        if self._cotas is None:
            self._carregar_cadastros()
        assert self._cotas is not None
        return self._cotas[estacao_id]

    def _carregar_cadastros(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.id, s.tipo, s.unidade, s.origem, s.estacao_id, s.abrigo_id,
                       s.valor_min, s.valor_max, s.ativo, e.salto_max_m
                FROM silver.sensor s
                LEFT JOIN silver.estacao e ON e.id = s.estacao_id
                """
            )
            self._sensores = {
                r[0]: Sensor(
                    id=r[0], tipo=r[1], unidade=r[2], origem=r[3], estacao_id=r[4], abrigo_id=r[5],
                    valor_min=float(r[6]), valor_max=float(r[7]), ativo=r[8],
                    salto_max_m=float(r[9]) if r[9] is not None else None,
                )
                for r in cur.fetchall()
            }
            cur.execute("SELECT id, cota_atencao_m, cota_alerta_m, cota_inundacao_m FROM silver.estacao")
            self._cotas = {r[0]: Cotas(float(r[1]), float(r[2]), float(r[3])) for r in cur.fetchall()}

    # ---------------- bronze ----------------
    def inserir_mensagem(
        self, canal: str, topico: str | None, conteudo: str, hash_: str, status: str,
        motivo: str | None = None, carga_id: int | None = None,
    ) -> int | None:
        """Grava a mensagem bruta. Devolve None se a mesma mensagem já tinha chegado."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO bronze.mensagem (canal, topico, conteudo, hash, status, motivo, carga_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (hash) DO NOTHING
                RETURNING id
                """,
                (canal, topico, conteudo, hash_, status, motivo, carga_id),
            )
            linha = cur.fetchone()
        return linha[0] if linha else None

    def marcar_mensagem(self, mensagem_id: int, status: str, motivo: str | None = None) -> None:
        with self.conn.cursor() as cur:
            cur.execute("UPDATE bronze.mensagem SET status = %s, motivo = %s WHERE id = %s", (status, motivo, mensagem_id))

    # ---------------- silver ----------------
    def leitura_anterior(self, sensor_id: str, antes_de: datetime, so_ok: bool = False) -> LeituraAnterior | None:
        filtro = "AND qualidade = 'ok'" if so_ok else ""
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT valor, medido_em, qualidade FROM silver.leitura
                WHERE sensor_id = %s AND medido_em < %s {filtro}
                ORDER BY medido_em DESC LIMIT 1
                """,
                (sensor_id, antes_de),
            )
            r = cur.fetchone()
        return LeituraAnterior(float(r[0]), r[1], r[2]) if r else None

    def inserir_leitura(
        self, sensor_id: str, medido_em: datetime, valor: float, qualidade: str, canal: str, mensagem_id: int
    ) -> bool:
        """Devolve False se já existia leitura deste sensor neste horário."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO silver.leitura (sensor_id, medido_em, valor, qualidade, canal, mensagem_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (sensor_id, medido_em) DO NOTHING
                """,
                (sensor_id, medido_em, valor, qualidade, canal, mensagem_id),
            )
            return cur.rowcount == 1

    # ---------------- alertas ----------------
    def alerta_aberto(self, estacao_id: str) -> AlertaAberto | None:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, severidade, ultima_leitura_em FROM silver.alerta WHERE estacao_id = %s AND fechado_em IS NULL",
                (estacao_id,),
            )
            r = cur.fetchone()
        return AlertaAberto(r[0], r[1], r[2]) if r else None

    def abrir_alerta(self, estacao_id: str, severidade: int, em: datetime, nivel: float) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO silver.alerta (estacao_id, severidade, aberto_em, pico_m, ultima_leitura_em)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (estacao_id, severidade, em, nivel, em),
            )

    def atualizar_alerta(self, alerta_id: int, severidade: int, em: datetime, nivel: float) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE silver.alerta
                SET severidade = greatest(severidade, %s), pico_m = greatest(pico_m, %s), ultima_leitura_em = %s
                WHERE id = %s
                """,
                (severidade, nivel, em, alerta_id),
            )

    def fechar_alerta(self, alerta_id: int, em: datetime) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE silver.alerta SET fechado_em = %s, ultima_leitura_em = %s WHERE id = %s",
                (em, em, alerta_id),
            )

    # ---------------- cargas em lote ----------------
    def buscar_ou_criar_carga(self, arquivo: str, hash_arquivo: str) -> tuple[int, bool]:
        """Devolve (id da carga, já concluída?). Uma carga interrompida é retomada do início
        sem duplicar nada, porque cada linha repetida é barrada pelo hash da mensagem."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, concluida_em IS NOT NULL FROM bronze.carga WHERE hash_arquivo = %s", (hash_arquivo,))
            r = cur.fetchone()
            if r:
                return r[0], r[1]
            cur.execute(
                "INSERT INTO bronze.carga (arquivo, hash_arquivo) VALUES (%s, %s) RETURNING id",
                (arquivo, hash_arquivo),
            )
            return cur.fetchone()[0], False

    def concluir_carga(self, carga_id: int, contagem: dict[str, int]) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE bronze.carga
                SET concluida_em = now(), linhas = %s, aceitas = %s, rejeitadas = %s, duplicadas = %s, repetidas = %s
                WHERE id = %s
                """,
                (
                    sum(contagem.values()), contagem.get("aceita", 0), contagem.get("rejeitada", 0),
                    contagem.get("duplicada", 0), contagem.get("repetida", 0), carga_id,
                ),
            )
