-- SILVER: cadastros e leituras validadas.

CREATE TABLE silver.bairro (
    id          text PRIMARY KEY,
    nome        text NOT NULL UNIQUE,
    zona_risco  text NOT NULL CHECK (zona_risco IN ('alta', 'baixa')),
    lat         numeric(8, 5) NOT NULL,
    lon         numeric(8, 5) NOT NULL
);

-- Ponto de medição de um rio/arroio, com as cotas que disparam alertas.
CREATE TABLE silver.estacao (
    id                text PRIMARY KEY,
    nome              text NOT NULL,
    corpo_hidrico     text NOT NULL,
    bairro_id         text NOT NULL REFERENCES silver.bairro (id),
    lat               numeric(8, 5) NOT NULL,
    lon               numeric(8, 5) NOT NULL,
    nivel_base_m      numeric(5, 2) NOT NULL,
    cota_atencao_m    numeric(5, 2) NOT NULL,
    cota_alerta_m     numeric(5, 2) NOT NULL,
    cota_inundacao_m  numeric(5, 2) NOT NULL,
    salto_max_m       numeric(5, 2) NOT NULL,  -- variação máxima plausível entre leituras seguidas
    demo              boolean NOT NULL DEFAULT false,
    fonte_cotas       text,
    CHECK (cota_atencao_m < cota_alerta_m AND cota_alerta_m < cota_inundacao_m)
);

CREATE TABLE silver.abrigo (
    id                   text PRIMARY KEY,
    osm_ref              text,
    nome                 text NOT NULL,
    tipo                 text NOT NULL CHECK (tipo IN ('escola', 'ginasio')),
    bairro_id            text NOT NULL REFERENCES silver.bairro (id),
    lat                  numeric(8, 5) NOT NULL,
    lon                  numeric(8, 5) NOT NULL,
    capacidade           integer NOT NULL CHECK (capacidade > 0),
    capacidade_estimada  boolean NOT NULL,
    em_area_de_risco     boolean NOT NULL,
    estacao_proxima_id   text NOT NULL REFERENCES silver.estacao (id),
    ativo                boolean NOT NULL DEFAULT true,
    demo                 boolean NOT NULL DEFAULT false
);

-- Um sensor pertence a uma estação (nível, chuva) OU a um abrigo (ocupação).
CREATE TABLE silver.sensor (
    id          text PRIMARY KEY,
    tipo        text NOT NULL CHECK (tipo IN ('nivel_rio', 'chuva', 'ocupacao_abrigo')),
    unidade     text NOT NULL,
    estacao_id  text REFERENCES silver.estacao (id),
    abrigo_id   text REFERENCES silver.abrigo (id),
    origem      text NOT NULL CHECK (origem IN ('sim', 'wokwi')),
    valor_min   numeric NOT NULL,
    valor_max   numeric NOT NULL,
    ativo       boolean NOT NULL DEFAULT true,
    CHECK ((tipo, unidade) IN (('nivel_rio', 'm'), ('chuva', 'mm'), ('ocupacao_abrigo', 'pessoas'))),
    CHECK ((estacao_id IS NULL) <> (abrigo_id IS NULL)),
    CHECK ((tipo = 'ocupacao_abrigo') = (abrigo_id IS NOT NULL)),
    CHECK (valor_min < valor_max)
);

-- Leitura validada. A chave (sensor, horário) é a segunda barreira contra duplicatas.
CREATE TABLE silver.leitura (
    sensor_id    text NOT NULL REFERENCES silver.sensor (id),
    medido_em    timestamptz NOT NULL,
    valor        numeric(10, 2) NOT NULL,
    qualidade    text NOT NULL CHECK (qualidade IN ('ok', 'suspeita')),
    canal        text NOT NULL CHECK (canal IN ('mqtt', 'arquivo')),
    mensagem_id  bigint NOT NULL REFERENCES bronze.mensagem (id),
    recebido_em  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (sensor_id, medido_em)
);

CREATE INDEX leitura_medido_em_idx ON silver.leitura (medido_em);

-- Alerta de cheia por estação: abre, escala e fecha conforme o nível.
CREATE TABLE silver.alerta (
    id                 bigserial PRIMARY KEY,
    estacao_id         text NOT NULL REFERENCES silver.estacao (id),
    severidade         smallint NOT NULL CHECK (severidade BETWEEN 1 AND 3),  -- 1 atenção, 2 alerta, 3 inundação
    aberto_em          timestamptz NOT NULL,
    fechado_em         timestamptz,
    pico_m             numeric(5, 2) NOT NULL,
    ultima_leitura_em  timestamptz NOT NULL
);

-- No máximo um alerta aberto por estação (garante que não duplica).
CREATE UNIQUE INDEX alerta_um_aberto_por_estacao ON silver.alerta (estacao_id) WHERE fechado_em IS NULL;
