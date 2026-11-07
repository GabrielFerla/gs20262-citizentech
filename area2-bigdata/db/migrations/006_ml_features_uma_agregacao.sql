-- v_ml_features: mesma saída de antes, mas agregando silver.leitura uma vez só.
--
-- A versão da 004 fazia um self-join de v_estacao_horaria; como a visão não é
-- materializada, o GROUP BY de todas as leituras rodava duas vezes. Aqui a série
-- horária é calculada uma vez (CTE MATERIALIZED) e reaproveitada para achar o nível
-- de 6 h depois. (Exemplo de como mudar o banco: migração nova, sem editar a antiga.)
CREATE OR REPLACE VIEW gold.v_ml_features AS
WITH h AS MATERIALIZED (
    SELECT hr.*
    FROM gold.v_estacao_horaria hr
    JOIN silver.estacao e ON e.id = hr.estacao_id AND NOT e.demo
)
SELECT h.estacao_id,
       h.hora_utc,
       h.hora_local,
       h.nivel_medio_m AS nivel_atual_m,
       h.nivel_medio_m - lag(h.nivel_medio_m) OVER (PARTITION BY h.estacao_id ORDER BY h.hora_utc) AS variacao_1h_m,
       h.chuva_mm AS chuva_1h_mm,
       sum(h.chuva_mm) OVER janela_6h  AS chuva_6h_mm,
       sum(h.chuva_mm) OVER janela_24h AS chuva_24h_mm,
       futuro.nivel_medio_m AS nivel_6h_depois_m
FROM h
LEFT JOIN h AS futuro
       ON futuro.estacao_id = h.estacao_id
      AND futuro.hora_utc = h.hora_utc + interval '6 hours'
WINDOW janela_6h  AS (PARTITION BY h.estacao_id ORDER BY h.hora_utc
                      RANGE BETWEEN interval '5 hours' PRECEDING AND CURRENT ROW),
       janela_24h AS (PARTITION BY h.estacao_id ORDER BY h.hora_utc
                      RANGE BETWEEN interval '23 hours' PRECEDING AND CURRENT ROW);
