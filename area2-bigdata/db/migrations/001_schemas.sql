-- Camadas do "data lake" dentro do PostgreSQL (arquitetura medalhão):
--   bronze: tudo o que chegou, do jeito que chegou (inclusive mensagens inválidas)
--   silver: dado validado e tratado + cadastros (bairros, estações, abrigos, sensores)
--   gold:   visões prontas para decisão (dashboard, app e IA)
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- Todos os horários são gravados em UTC; o horário de Brasília aparece só no gold.
DO $$
BEGIN
    EXECUTE format('ALTER DATABASE %I SET timezone TO %L', current_database(), 'UTC');
END $$;
