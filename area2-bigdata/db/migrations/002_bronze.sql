-- BRONZE: registro bruto de tudo o que chegou (auditoria e reprocessamento).

-- Cada arquivo da carga histórica (zona de chegada do data lake) vira uma carga.
CREATE TABLE bronze.carga (
    id            bigserial PRIMARY KEY,
    arquivo       text        NOT NULL,
    hash_arquivo  char(64)    NOT NULL UNIQUE,   -- o mesmo arquivo não é carregado duas vezes
    iniciada_em   timestamptz NOT NULL DEFAULT now(),
    concluida_em  timestamptz,
    linhas        integer,
    aceitas       integer,
    rejeitadas    integer,
    duplicadas    integer,
    repetidas     integer
);

-- Cada mensagem recebida (MQTT ou linha de arquivo), inclusive as inválidas.
CREATE TABLE bronze.mensagem (
    id           bigserial PRIMARY KEY,
    recebido_em  timestamptz NOT NULL DEFAULT now(),
    canal        text        NOT NULL CHECK (canal IN ('mqtt', 'arquivo')),
    topico       text,
    conteudo     text        NOT NULL,
    hash         char(64)    NOT NULL UNIQUE,    -- barra a mesma mensagem entregue duas vezes (QoS 1)
    status       text        NOT NULL CHECK (status IN ('aceita', 'rejeitada', 'duplicada')),
    motivo       text,
    carga_id     bigint REFERENCES bronze.carga (id)
);

CREATE INDEX mensagem_recebido_em_idx ON bronze.mensagem (recebido_em);
CREATE INDEX mensagem_status_idx ON bronze.mensagem (status);
