-- GOLD: visões prontas para decisão.
--
-- Dois tipos de visão:
--   * série histórica (v_*_horaria, v_ml_features): só leituras consolidadas da carga em lote
--     (canal 'arquivo'), com qualidade ok. É a base do dashboard e do treino da IA.
--   * situação atual (v_*_atual, v_abrigo_status, v_alertas, v_kpis): todas as leituras,
--     inclusive as do tempo real (MQTT). É a base do app e dos alertas.

------------------------------------------------------------------------------
-- Dimensões (tabelas de apoio para filtros no Power BI)
------------------------------------------------------------------------------
CREATE VIEW gold.dim_bairro AS
SELECT id AS bairro_id, nome AS bairro, zona_risco, lat, lon
FROM silver.bairro;

CREATE VIEW gold.dim_estacao AS
SELECT e.id AS estacao_id, e.nome AS estacao, e.corpo_hidrico, e.bairro_id, b.nome AS bairro,
       e.lat, e.lon, e.nivel_base_m, e.cota_atencao_m, e.cota_alerta_m, e.cota_inundacao_m, e.demo
FROM silver.estacao e
JOIN silver.bairro b ON b.id = e.bairro_id;

CREATE VIEW gold.dim_abrigo AS
SELECT a.id AS abrigo_id, a.nome AS abrigo, a.tipo, a.bairro_id, b.nome AS bairro, a.lat, a.lon,
       a.capacidade, a.capacidade_estimada, a.em_area_de_risco, a.estacao_proxima_id, a.demo
FROM silver.abrigo a
JOIN silver.bairro b ON b.id = a.bairro_id;

------------------------------------------------------------------------------
-- Série histórica
------------------------------------------------------------------------------
CREATE VIEW gold.v_estacao_horaria AS
WITH por_hora AS (
    SELECT s.estacao_id,
           date_trunc('hour', l.medido_em) AS hora_utc,
           max(l.valor) FILTER (WHERE s.tipo = 'nivel_rio') AS nivel_max_m,
           avg(l.valor) FILTER (WHERE s.tipo = 'nivel_rio') AS nivel_medio_m,
           sum(l.valor) FILTER (WHERE s.tipo = 'chuva')     AS chuva_mm
    FROM silver.leitura l
    JOIN silver.sensor s ON s.id = l.sensor_id
    WHERE s.estacao_id IS NOT NULL
      AND l.qualidade = 'ok'
      AND l.canal = 'arquivo'
    GROUP BY s.estacao_id, date_trunc('hour', l.medido_em)
)
SELECT h.estacao_id,
       e.bairro_id,
       h.hora_utc,
       (h.hora_utc AT TIME ZONE 'America/Sao_Paulo') AS hora_local,
       round(h.nivel_max_m, 2)              AS nivel_max_m,
       round(h.nivel_medio_m, 2)            AS nivel_medio_m,
       round(coalesce(h.chuva_mm, 0), 1)    AS chuva_mm,
       CASE
           WHEN h.nivel_max_m >= e.cota_inundacao_m THEN 'inundacao'
           WHEN h.nivel_max_m >= e.cota_alerta_m    THEN 'alerta'
           WHEN h.nivel_max_m >= e.cota_atencao_m   THEN 'atencao'
           ELSE 'normal'
       END AS situacao
FROM por_hora h
JOIN silver.estacao e ON e.id = h.estacao_id;

CREATE VIEW gold.v_abrigo_horaria AS
SELECT s.abrigo_id,
       a.bairro_id,
       date_trunc('hour', l.medido_em) AS hora_utc,
       (date_trunc('hour', l.medido_em) AT TIME ZONE 'America/Sao_Paulo') AS hora_local,
       round(avg(l.valor))::integer AS ocupacao_media,
       max(l.valor)::integer        AS ocupacao_max,
       a.capacidade,
       round(100.0 * max(l.valor) / a.capacidade, 1) AS pct_lotacao_max
FROM silver.leitura l
JOIN silver.sensor s ON s.id = l.sensor_id
JOIN silver.abrigo a ON a.id = s.abrigo_id
WHERE s.tipo = 'ocupacao_abrigo'
  AND l.qualidade = 'ok'
  AND l.canal = 'arquivo'
GROUP BY s.abrigo_id, a.bairro_id, a.capacidade, date_trunc('hour', l.medido_em);

-- Base de treino da IA (fase 2): prever o nível daqui a 6 horas.
CREATE VIEW gold.v_ml_features AS
SELECT h.estacao_id,
       h.hora_utc,
       h.hora_local,
       h.nivel_medio_m AS nivel_atual_m,
       h.nivel_medio_m - lag(h.nivel_medio_m) OVER (PARTITION BY h.estacao_id ORDER BY h.hora_utc) AS variacao_1h_m,
       h.chuva_mm AS chuva_1h_mm,
       sum(h.chuva_mm) OVER janela_6h  AS chuva_6h_mm,
       sum(h.chuva_mm) OVER janela_24h AS chuva_24h_mm,
       futuro.nivel_medio_m AS nivel_6h_depois_m
FROM gold.v_estacao_horaria h
JOIN silver.estacao e ON e.id = h.estacao_id AND NOT e.demo
LEFT JOIN gold.v_estacao_horaria futuro
       ON futuro.estacao_id = h.estacao_id
      AND futuro.hora_utc = h.hora_utc + interval '6 hours'
WINDOW janela_6h  AS (PARTITION BY h.estacao_id ORDER BY h.hora_utc
                      RANGE BETWEEN interval '5 hours' PRECEDING AND CURRENT ROW),
       janela_24h AS (PARTITION BY h.estacao_id ORDER BY h.hora_utc
                      RANGE BETWEEN interval '23 hours' PRECEDING AND CURRENT ROW);

------------------------------------------------------------------------------
-- Situação atual
------------------------------------------------------------------------------
-- Chuva das últimas 6 e 144 leituras (= 1 h e 24 h de medições de 10 min).
-- Contar leituras em vez de relógio funciona igual no histórico e na simulação acelerada.
CREATE VIEW gold.v_estacao_atual AS
WITH nivel AS (
    SELECT DISTINCT ON (s.estacao_id) s.estacao_id, l.valor AS nivel_m, l.medido_em
    FROM silver.leitura l
    JOIN silver.sensor s ON s.id = l.sensor_id
    WHERE s.tipo = 'nivel_rio' AND l.qualidade = 'ok'
    ORDER BY s.estacao_id, l.medido_em DESC
),
chuva_recente AS (
    SELECT s.estacao_id, l.valor,
           row_number() OVER (PARTITION BY s.estacao_id ORDER BY l.medido_em DESC) AS ordem
    FROM silver.leitura l
    JOIN silver.sensor s ON s.id = l.sensor_id
    WHERE s.tipo = 'chuva' AND l.qualidade = 'ok'
      AND l.medido_em > now() - interval '3 days'
),
chuva AS (
    SELECT estacao_id,
           sum(valor) FILTER (WHERE ordem <= 6) AS chuva_1h_mm,
           sum(valor) AS chuva_24h_mm
    FROM chuva_recente
    WHERE ordem <= 144
    GROUP BY estacao_id
)
SELECT e.id AS estacao_id,
       e.nome AS estacao,
       e.bairro_id,
       n.nivel_m,
       n.medido_em AS medido_em_utc,
       (n.medido_em AT TIME ZONE 'America/Sao_Paulo') AS medido_em_local,
       round(coalesce(c.chuva_1h_mm, 0), 1)  AS chuva_1h_mm,
       round(coalesce(c.chuva_24h_mm, 0), 1) AS chuva_24h_mm,
       e.cota_atencao_m, e.cota_alerta_m, e.cota_inundacao_m,
       CASE
           WHEN n.nivel_m IS NULL               THEN 'sem_dados'
           WHEN n.nivel_m >= e.cota_inundacao_m THEN 'inundacao'
           WHEN n.nivel_m >= e.cota_alerta_m    THEN 'alerta'
           WHEN n.nivel_m >= e.cota_atencao_m   THEN 'atencao'
           ELSE 'normal'
       END AS situacao,
       coalesce(al.severidade, 0) AS alerta_severidade,
       al.aberto_em AS alerta_aberto_em_utc,
       (n.medido_em IS NULL OR n.medido_em < now() - interval '30 minutes') AS leitura_velha,
       e.demo
FROM silver.estacao e
LEFT JOIN nivel n ON n.estacao_id = e.id
LEFT JOIN chuva c ON c.estacao_id = e.id
LEFT JOIN silver.alerta al ON al.estacao_id = e.id AND al.fechado_em IS NULL;

-- "Onde ficar seguro": situação de cada abrigo e se ele pode ser recomendado agora.
CREATE VIEW gold.v_abrigo_status AS
WITH ultima AS (
    SELECT DISTINCT ON (s.abrigo_id) s.abrigo_id, l.valor::integer AS ocupacao, l.medido_em
    FROM silver.leitura l
    JOIN silver.sensor s ON s.id = l.sensor_id
    WHERE s.tipo = 'ocupacao_abrigo' AND l.qualidade = 'ok'
    ORDER BY s.abrigo_id, l.medido_em DESC
),
base AS (
    SELECT a.*,
           coalesce(u.ocupacao, 0) AS ocupacao,
           u.medido_em,
           (u.medido_em IS NULL OR u.medido_em < now() - interval '30 minutes') AS leitura_velha,
           coalesce(al.severidade, 0) AS severidade_regiao
    FROM silver.abrigo a
    LEFT JOIN ultima u ON u.abrigo_id = a.id
    LEFT JOIN silver.alerta al ON al.estacao_id = a.estacao_proxima_id AND al.fechado_em IS NULL
)
SELECT b.id AS abrigo_id,
       b.nome AS abrigo,
       b.tipo,
       b.bairro_id,
       br.nome AS bairro,
       b.lat, b.lon,
       b.capacidade,
       b.ocupacao,
       greatest(b.capacidade - b.ocupacao, 0) AS vagas,
       round(100.0 * b.ocupacao / b.capacidade, 1) AS pct_lotacao,
       CASE
           WHEN b.ocupacao >= b.capacidade       THEN 'lotado'
           WHEN b.ocupacao >= 0.8 * b.capacidade THEN 'quase_cheio'
           ELSE 'disponivel'
       END AS status_lotacao,
       b.medido_em AS ultima_leitura_utc,
       b.leitura_velha,
       b.em_area_de_risco,
       b.estacao_proxima_id,
       b.severidade_regiao,
       CASE
           WHEN NOT b.ativo                                    THEN 'abrigo inativo'
           WHEN b.demo                                         THEN 'abrigo de demonstração'
           WHEN b.leitura_velha                                THEN 'sem leitura recente'
           WHEN b.ocupacao >= b.capacidade                     THEN 'lotado'
           WHEN b.em_area_de_risco AND b.severidade_regiao >= 2 THEN 'área de risco com rio em alerta'
       END AS motivo_nao_recomendado,
       (b.ativo AND NOT b.demo AND NOT b.leitura_velha AND b.ocupacao < b.capacidade
        AND NOT (b.em_area_de_risco AND b.severidade_regiao >= 2)) AS recomendavel,
       b.demo
FROM base b
JOIN silver.bairro br ON br.id = b.bairro_id;

CREATE VIEW gold.v_alertas AS
SELECT al.id AS alerta_id,
       al.estacao_id,
       e.nome AS estacao,
       e.bairro_id,
       al.severidade,
       CASE al.severidade WHEN 1 THEN 'atencao' WHEN 2 THEN 'alerta' ELSE 'inundacao' END AS severidade_nome,
       al.aberto_em AS aberto_em_utc,
       (al.aberto_em AT TIME ZONE 'America/Sao_Paulo') AS aberto_em_local,
       al.fechado_em AS fechado_em_utc,
       (al.fechado_em AT TIME ZONE 'America/Sao_Paulo') AS fechado_em_local,
       al.fechado_em IS NULL AS em_aberto,
       round(extract(epoch FROM coalesce(al.fechado_em, al.ultima_leitura_em) - al.aberto_em) / 3600.0, 1) AS duracao_h,
       al.pico_m,
       e.demo
FROM silver.alerta al
JOIN silver.estacao e ON e.id = al.estacao_id;

-- Qualidade da ingestão: quanto foi aceito, rejeitado e duplicado, e por quê.
CREATE VIEW gold.v_qualidade AS
SELECT (m.recebido_em AT TIME ZONE 'America/Sao_Paulo')::date AS dia_local,
       m.canal,
       m.status,
       coalesce(split_part(m.motivo, ':', 1), '') AS motivo,
       count(*) AS mensagens
FROM bronze.mensagem m
GROUP BY 1, 2, 3, 4;

-- Números-resumo (uma linha) para cartões do dashboard e do app.
CREATE VIEW gold.v_kpis AS
SELECT
    (SELECT count(*) FROM gold.v_abrigo_status WHERE recomendavel)                        AS abrigos_recomendaveis,
    (SELECT coalesce(sum(vagas), 0) FROM gold.v_abrigo_status WHERE recomendavel)         AS vagas_disponiveis,
    (SELECT coalesce(sum(ocupacao), 0) FROM gold.v_abrigo_status WHERE NOT demo)          AS pessoas_abrigadas,
    (SELECT count(*) FROM silver.alerta WHERE fechado_em IS NULL)                          AS alertas_abertos,
    (SELECT coalesce(max(severidade), 0) FROM silver.alerta WHERE fechado_em IS NULL)      AS maior_severidade,
    (SELECT count(*) FROM silver.leitura WHERE recebido_em > now() - interval '24 hours')  AS leituras_recebidas_24h,
    (SELECT count(*) FROM bronze.mensagem
      WHERE status = 'rejeitada' AND recebido_em > now() - interval '24 hours')            AS rejeitadas_24h,
    now() AS calculado_em_utc;
