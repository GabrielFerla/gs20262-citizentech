-- Usuários com o mínimo de permissão (segurança):
--   ingestor_rw: grava só em bronze e silver; lê os cadastros.
--   bi_ro:       só lê a camada gold (dashboard e exportação).
-- As senhas são definidas pelo migrar.py a partir do .env (nunca ficam no código).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ingestor_rw') THEN
        CREATE ROLE ingestor_rw LOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bi_ro') THEN
        CREATE ROLE bi_ro LOGIN;
    END IF;
END $$;

REVOKE ALL ON SCHEMA public FROM PUBLIC;

GRANT USAGE ON SCHEMA bronze, silver TO ingestor_rw;
GRANT SELECT, INSERT, UPDATE ON bronze.carga, bronze.mensagem TO ingestor_rw;
GRANT SELECT, INSERT ON silver.leitura TO ingestor_rw;
GRANT SELECT, INSERT, UPDATE ON silver.alerta TO ingestor_rw;
GRANT SELECT ON silver.bairro, silver.estacao, silver.abrigo, silver.sensor TO ingestor_rw;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA bronze, silver TO ingestor_rw;

GRANT USAGE ON SCHEMA gold TO bi_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO bi_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT ON TABLES TO bi_ro;
