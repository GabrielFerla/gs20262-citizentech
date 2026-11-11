-- A situação atual dos rios e dos abrigos passa a achar a última leitura de cada sensor pela
-- chave (sensor_id, medido_em), em vez de varrer silver.leitura inteira.
--
-- Na 004, gold.v_estacao_atual e gold.v_abrigo_status usavam DISTINCT ON sobre todas as
-- leituras: o PostgreSQL lia e ordenava a tabela inteira a cada consulta. Com o simulador
-- ligado (cerca de 1,7 milhão de leituras por dia), "Onde ficar seguro" levava 1,5 s com
-- 3 milhões de leituras e ficava mais lento a cada dia (o app desiste depois de 8 s).
--
-- Agora, para cada sensor, a busca desce a chave primária a partir da leitura mais nova e para
-- na primeira com qualidade 'ok' (a chuva pega as 144 mais novas, de até 3 dias, como antes).
-- Duas coisas parecem estranhas e são de propósito, para o PostgreSQL usar a chave primária:
-- o sensor é filtrado como faixa ("l.sensor_id >= s.id AND l.sensor_id <= s.id", o mesmo que
-- "= s.id") e a ordem é "l.sensor_id DESC, l.medido_em DESC", a ordem da chave. Com "= s.id" o
-- planejador descarta o sensor_id da ordem e prefere o índice de horários, que é rápido enquanto
-- o sensor manda leituras mas varre a tabela inteira para um sensor parado (o do Wokwi com o
-- ESP32 desligado, ou um banco recém-criado sem nenhuma leitura dele).
--
-- O resultado é o mesmo da 004 (sem limite de dias no nível e na ocupação: um sensor parado
-- continua mostrando a última leitura que mandou). As colunas e a ordem são as mesmas
-- (CREATE OR REPLACE VIEW exige isso); as permissões de leitura continuam valendo.

CREATE OR REPLACE VIEW gold.v_estacao_atual AS
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
LEFT JOIN LATERAL (
    -- a leitura 'ok' mais nova entre os sensores de nível da estação
    SELECT ul.valor AS nivel_m, ul.medido_em
    FROM silver.sensor s
    CROSS JOIN LATERAL (
        SELECT l.valor, l.medido_em
        FROM silver.leitura l
        WHERE l.sensor_id >= s.id AND l.sensor_id <= s.id AND l.qualidade = 'ok'
        ORDER BY l.sensor_id DESC, l.medido_em DESC
        LIMIT 1
    ) ul
    WHERE s.estacao_id = e.id AND s.tipo = 'nivel_rio'
    ORDER BY ul.medido_em DESC
    LIMIT 1
) n ON true
LEFT JOIN LATERAL (
    -- Chuva das últimas 6 e 144 leituras (= 1 h e 24 h de medições de 10 min), de até 3 dias.
    -- Contar leituras em vez de relógio funciona igual no histórico e na simulação acelerada.
    SELECT sum(r.valor) FILTER (WHERE r.ordem <= 6) AS chuva_1h_mm,
           sum(r.valor) AS chuva_24h_mm
    FROM (
        SELECT ul.valor, row_number() OVER (ORDER BY ul.medido_em DESC) AS ordem
        FROM silver.sensor s
        CROSS JOIN LATERAL (
            SELECT l.valor, l.medido_em
            FROM silver.leitura l
            WHERE l.sensor_id >= s.id AND l.sensor_id <= s.id AND l.qualidade = 'ok'
              AND l.medido_em > now() - interval '3 days'
            ORDER BY l.sensor_id DESC, l.medido_em DESC
            LIMIT 144
        ) ul
        WHERE s.estacao_id = e.id AND s.tipo = 'chuva'
    ) r
    WHERE r.ordem <= 144
) c ON true
LEFT JOIN silver.alerta al ON al.estacao_id = e.id AND al.fechado_em IS NULL;

CREATE OR REPLACE VIEW gold.v_abrigo_status AS
WITH base AS (
    SELECT a.*,
           coalesce(u.ocupacao, 0) AS ocupacao,
           u.medido_em,
           (u.medido_em IS NULL OR u.medido_em < now() - interval '30 minutes') AS leitura_velha,
           coalesce(al.severidade, 0) AS severidade_regiao
    FROM silver.abrigo a
    LEFT JOIN LATERAL (
        -- a leitura 'ok' mais nova entre os sensores de ocupação do abrigo
        SELECT ul.valor::integer AS ocupacao, ul.medido_em
        FROM silver.sensor s
        CROSS JOIN LATERAL (
            SELECT l.valor, l.medido_em
            FROM silver.leitura l
            WHERE l.sensor_id >= s.id AND l.sensor_id <= s.id AND l.qualidade = 'ok'
            ORDER BY l.sensor_id DESC, l.medido_em DESC
            LIMIT 1
        ) ul
        WHERE s.abrigo_id = a.id AND s.tipo = 'ocupacao_abrigo'
        ORDER BY ul.medido_em DESC
        LIMIT 1
    ) u ON true
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
