-- Estrutura aditiva: não remove bancos ou registros existentes.
CREATE TABLE IF NOT EXISTS usuarios (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    cargo VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS equipamentos (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    ativo BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- A restrição composta garante uma única série por equipamento/analito/lote.
-- Um lote nessa série corresponde a um único material/nível de controle.
CREATE TABLE IF NOT EXISTS series (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    equipamento_id BIGINT UNSIGNED NOT NULL,
    analito VARCHAR(100) NOT NULL,
    lote VARCHAR(100) NOT NULL,
    controle VARCHAR(100) NOT NULL,
    alvo DOUBLE NOT NULL,
    desvio DOUBLE NOT NULL,
    unidade VARCHAR(30) NOT NULL,
    limite_min DOUBLE NULL,
    limite_max DOUBLE NULL,
    UNIQUE KEY serie_identidade (equipamento_id, analito, lote),
    FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id),
    CHECK (desvio > 0),
    CHECK (limite_min IS NULL OR limite_max IS NULL OR limite_min <= limite_max)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS corridas (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    serie_id BIGINT UNSIGNED NOT NULL,
    usuario_id BIGINT UNSIGNED NOT NULL,
    criado_em DATETIME(6) NOT NULL,
    resultado DOUBLE NOT NULL,
    z DOUBLE NOT NULL,
    status VARCHAR(20) NOT NULL,
    regras VARCHAR(100) NOT NULL,
    fora_bula BOOLEAN NOT NULL DEFAULT FALSE,
    INDEX corrida_serie_ordem (serie_id, id),
    FOREIGN KEY (serie_id) REFERENCES series(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
