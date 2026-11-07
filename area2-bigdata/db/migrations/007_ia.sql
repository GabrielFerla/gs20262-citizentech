-- Fase 2 (Área 1 — IA): entradas da previsão ao vivo e usuário da API.
--
-- A previsão ao vivo usa as mesmas features de gold.v_ml_features, mas a partir das
-- últimas leituras de cada sensor. Conta leituras em vez de relógio (6 = 1 h, 36 = 6 h,
-- 144 = 24 h), como a v_estacao_atual: assim funciona igual no histórico e na simulação
-- acelerada. Cada subconsulta usa ORDER BY medido_em DESC LIMIT n sobre a chave
-- (sensor_id, medido_em), então continua rápida mesmo com horas de tempo real gravadas.

CREATE VIEW gold.v_ml_features_atual AS
SELECT e.id AS estacao_id,
       n.medido_em AS medido_em_utc,
       round(n.nivel_1h, 2) AS nivel_atual_m,
       round(n.nivel_1h, 2) - round(n.nivel_1h_antes, 2) AS variacao_1h_m,
       round(coalesce(c.chuva_1h, 0), 1) AS chuva_1h_mm,
       round(coalesce(c.chuva_6h, 0), 1) AS chuva_6h_mm,
       round(coalesce(c.chuva_24h, 0), 1) AS chuva_24h_mm,
       n.leituras AS leituras_nivel,
       (n.medido_em IS NULL OR n.medido_em < now() - interval '30 minutes') AS leitura_velha
FROM silver.estacao e
JOIN silver.sensor sn ON sn.estacao_id = e.id AND sn.tipo = 'nivel_rio' AND sn.ativo
JOIN silver.sensor sc ON sc.estacao_id = e.id AND sc.tipo = 'chuva' AND sc.ativo
CROSS JOIN LATERAL (
    SELECT max(u.medido_em) AS medido_em,
           avg(u.valor) FILTER (WHERE u.ordem <= 6) AS nivel_1h,
           avg(u.valor) FILTER (WHERE u.ordem > 6)  AS nivel_1h_antes,
           count(*) AS leituras
    FROM (
        SELECT l.valor, l.medido_em, row_number() OVER (ORDER BY l.medido_em DESC) AS ordem
        FROM (
            SELECT valor, medido_em FROM silver.leitura
            WHERE sensor_id = sn.id AND qualidade = 'ok'
            ORDER BY medido_em DESC LIMIT 12
        ) l
    ) u
) n
CROSS JOIN LATERAL (
    SELECT sum(u.valor) FILTER (WHERE u.ordem <= 6)  AS chuva_1h,
           sum(u.valor) FILTER (WHERE u.ordem <= 36) AS chuva_6h,
           sum(u.valor) AS chuva_24h
    FROM (
        SELECT l.valor, row_number() OVER (ORDER BY l.medido_em DESC) AS ordem
        FROM (
            SELECT valor, medido_em FROM silver.leitura
            WHERE sensor_id = sc.id AND qualidade = 'ok'
            ORDER BY medido_em DESC LIMIT 144
        ) l
    ) u
) c
WHERE NOT e.demo;

-- Tendência da ocupação: a leitura atual e a de 1 h antes (6 leituras atrás).
-- A IA usa isso para estimar quantas vagas ainda vão existir quando a pessoa chegar.
CREATE VIEW gold.v_abrigo_tendencia AS
SELECT a.id AS abrigo_id,
       u.ocupacao_atual,
       u.ocupacao_1h_antes,
       u.ocupacao_atual - coalesce(u.ocupacao_1h_antes, u.ocupacao_atual) AS variacao_1h
FROM silver.abrigo a
JOIN silver.sensor s ON s.abrigo_id = a.id AND s.tipo = 'ocupacao_abrigo'
CROSS JOIN LATERAL (
    SELECT (array_agg(l.valor ORDER BY l.medido_em DESC))[1]::integer AS ocupacao_atual,
           (array_agg(l.valor ORDER BY l.medido_em DESC))[7]::integer AS ocupacao_1h_antes
    FROM (
        SELECT valor, medido_em FROM silver.leitura
        WHERE sensor_id = s.id AND qualidade = 'ok'
        ORDER BY medido_em DESC LIMIT 7
    ) l
) u;

-- Usuário da API de IA: só lê a camada gold (menor privilégio, como o bi_ro).
-- A senha é definida pelo migrar.py a partir do .env (IA_DB_PASSWORD).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ia_ro') THEN
        CREATE ROLE ia_ro LOGIN;
    END IF;
END $$;

GRANT USAGE ON SCHEMA gold TO ia_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO ia_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT ON TABLES TO ia_ro;
