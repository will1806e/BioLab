-- Esquema inicial para o banco gerenciado Neon. Não altera registros existentes.
CREATE TABLE IF NOT EXISTS usuarios (
    id BIGSERIAL PRIMARY KEY,
    nome_usu VARCHAR(100) NOT NULL UNIQUE,
    cpf CHAR(11) UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    funcao VARCHAR(40) NOT NULL
);

CREATE TABLE IF NOT EXISTS equipamentos (
    id BIGSERIAL PRIMARY KEY,
    nome_equipamento VARCHAR(100) NOT NULL UNIQUE,
    modelo VARCHAR(100) NOT NULL DEFAULT '',
    numero_serie VARCHAR(100) NOT NULL DEFAULT '',
    observacoes VARCHAR(500) NOT NULL DEFAULT '',
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS analitos (
    id BIGSERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS lotes (
    id BIGSERIAL PRIMARY KEY,
    codigo VARCHAR(100) NOT NULL UNIQUE,
    data_validade DATE,
    fabricante VARCHAR(100) NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS lote_analito (
    id_lote BIGINT NOT NULL REFERENCES lotes(id) ON DELETE CASCADE,
    id_analito BIGINT NOT NULL REFERENCES analitos(id) ON DELETE RESTRICT,
    PRIMARY KEY (id_lote, id_analito)
);

CREATE TABLE IF NOT EXISTS series (
    id BIGSERIAL PRIMARY KEY,
    equipamento_id BIGINT NOT NULL REFERENCES equipamentos(id),
    id_lote BIGINT NOT NULL REFERENCES lotes(id),
    id_analito BIGINT NOT NULL REFERENCES analitos(id),
    analito VARCHAR(100) NOT NULL,
    lote VARCHAR(100) NOT NULL,
    controle VARCHAR(100) NOT NULL,
    alvo DOUBLE PRECISION NOT NULL,
    desvio DOUBLE PRECISION NOT NULL CHECK (desvio > 0),
    unidade VARCHAR(30) NOT NULL,
    limite_min DOUBLE PRECISION,
    limite_max DOUBLE PRECISION,
    UNIQUE (equipamento_id, analito, lote),
    CHECK (limite_min IS NULL OR limite_max IS NULL OR limite_min <= limite_max)
);

CREATE TABLE IF NOT EXISTS corridas (
    id BIGSERIAL PRIMARY KEY,
    serie_id BIGINT NOT NULL REFERENCES series(id),
    usuario_id BIGINT NOT NULL REFERENCES usuarios(id),
    criado_em TIMESTAMP(6) WITHOUT TIME ZONE NOT NULL,
    resultado DOUBLE PRECISION NOT NULL,
    z DOUBLE PRECISION NOT NULL,
    status VARCHAR(20) NOT NULL,
    regras VARCHAR(100) NOT NULL,
    fora_bula BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS corrida_serie_ordem ON corridas (serie_id, id);

CREATE TABLE IF NOT EXISTS historico (
    id BIGSERIAL PRIMARY KEY,
    data_hora TIMESTAMP WITHOUT TIME ZONE,
    id_equipamento BIGINT REFERENCES equipamentos(id),
    id_analito BIGINT REFERENCES analitos(id),
    id_lote BIGINT REFERENCES lotes(id),
    id_usuario BIGINT REFERENCES usuarios(id),
    status VARCHAR(20) CHECK (status IN ('Normal', 'Alerta', 'Não Conformidade')),
    corrida_id BIGINT UNIQUE REFERENCES corridas(id)
);
