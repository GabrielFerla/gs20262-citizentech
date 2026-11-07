-- O cadastro de abrigos (gold.dim_abrigo) passa a dizer se o abrigo está ativo.
--
-- A API de IA lia "ativo" da gold.v_abrigo_tendencia, que só tem abrigos com sensor de
-- ocupação: um abrigo desativado e sem sensor aparecia como ativo. O cadastro é a fonte
-- certa. Coluna nova só pode entrar no fim (CREATE OR REPLACE VIEW); as permissões de
-- leitura (bi_ro, ia_ro) continuam valendo para a visão.

CREATE OR REPLACE VIEW gold.dim_abrigo AS
SELECT a.id AS abrigo_id, a.nome AS abrigo, a.tipo, a.bairro_id, b.nome AS bairro, a.lat, a.lon,
       a.capacidade, a.capacidade_estimada, a.em_area_de_risco, a.estacao_proxima_id, a.demo,
       a.ativo
FROM silver.abrigo a
JOIN silver.bairro b ON b.id = a.bairro_id;
