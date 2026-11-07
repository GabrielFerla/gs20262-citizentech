-- Ajustes da revisão de código da 007 (migração nova: a 007 já foi aplicada).
--
-- 1. v_ml_features_atual e v_abrigo_tendencia passam a olhar só os últimos 3 dias (como a
--    chuva da v_estacao_atual). O PostgreSQL acha as últimas leituras de um sensor
--    percorrendo o índice de horários de trás para frente (o comentário da 007 dizia que
--    usava a chave (sensor_id, medido_em), mas o planejador prefere o índice de horários).
--    Isso é rápido com o sensor mandando leituras, mas um sensor ativo que parou fazia a
--    busca varrer silver.leitura inteira, a cada consulta da API e a cada rodada do vigia
--    (2 s). Com o limite, o pior caso é percorrer 3 dias de leituras.
-- 2. v_abrigo_tendencia passa a dizer se o abrigo está ativo. Antes a API deduzia isso do
--    texto de motivo_nao_recomendado da v_abrigo_status, que é um texto para pessoas.

CREATE OR REPLACE VIEW gold.v_ml_features_atual AS
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
            WHERE sensor_id = sn.id AND qualidade = 'ok' AND medido_em > now() - interval '3 days'
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
            WHERE sensor_id = sc.id AND qualidade = 'ok' AND medido_em > now() - interval '3 days'
            ORDER BY medido_em DESC LIMIT 144
        ) l
    ) u
) c
WHERE NOT e.demo;

-- Colunas novas só podem entrar no fim (CREATE OR REPLACE VIEW).
CREATE OR REPLACE VIEW gold.v_abrigo_tendencia AS
SELECT a.id AS abrigo_id,
       u.ocupacao_atual,
       u.ocupacao_1h_antes,
       u.ocupacao_atual - coalesce(u.ocupacao_1h_antes, u.ocupacao_atual) AS variacao_1h,
       a.ativo
FROM silver.abrigo a
JOIN silver.sensor s ON s.abrigo_id = a.id AND s.tipo = 'ocupacao_abrigo'
CROSS JOIN LATERAL (
    SELECT (array_agg(l.valor ORDER BY l.medido_em DESC))[1]::integer AS ocupacao_atual,
           (array_agg(l.valor ORDER BY l.medido_em DESC))[7]::integer AS ocupacao_1h_antes
    FROM (
        SELECT valor, medido_em FROM silver.leitura
        WHERE sensor_id = s.id AND qualidade = 'ok' AND medido_em > now() - interval '3 days'
        ORDER BY medido_em DESC LIMIT 7
    ) l
) u;
