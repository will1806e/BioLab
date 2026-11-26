-- Banco novo: para atualizar instalações existentes, execute o init-db Python.
CREATE DATABASE IF NOT EXISTS biolab CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE biolab;

-- Estrutura aditiva: não remove bancos ou registros existentes.
CREATE TABLE IF NOT EXISTS usuarios (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome_usu VARCHAR(100) NOT NULL UNIQUE,
    cpf CHAR(11) NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    funcao VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS equipamentos (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome_equipamento VARCHAR(100) NOT NULL UNIQUE,
    modelo VARCHAR(100) NOT NULL DEFAULT '',
    numero_serie VARCHAR(100) NOT NULL DEFAULT '',
    observacoes VARCHAR(500) NOT NULL DEFAULT '',
    ativo BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS analitos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS lotes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(100) NOT NULL UNIQUE,
    data_validade DATE NULL,
    fabricante VARCHAR(100) NOT NULL DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS lote_analito (
    id_lote INT NOT NULL,
    id_analito INT NOT NULL,
    PRIMARY KEY (id_lote, id_analito),
    FOREIGN KEY (id_lote) REFERENCES lotes(id) ON DELETE CASCADE,
    FOREIGN KEY (id_analito) REFERENCES analitos(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- A restrição composta garante uma única série por equipamento/analito/lote.
-- Um lote nessa série corresponde a um único material/nível de controle.
CREATE TABLE IF NOT EXISTS series (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    equipamento_id BIGINT UNSIGNED NOT NULL,
    id_lote INT NOT NULL,
    id_analito INT NOT NULL,
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
    FOREIGN KEY (id_lote) REFERENCES lotes(id),
    FOREIGN KEY (id_analito) REFERENCES analitos(id),
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

-- Mantém o histórico proposto no repositório e vincula novos registros ao cálculo.
CREATE TABLE IF NOT EXISTS historico (
    id INT AUTO_INCREMENT PRIMARY KEY,
    data_hora DATETIME,
    id_equipamento BIGINT UNSIGNED,
    id_analito INT,
    id_lote INT,
    id_usuario BIGINT UNSIGNED,
    status ENUM('Normal', 'Alerta', 'Não Conformidade'),
    corrida_id BIGINT UNSIGNED NULL UNIQUE,
    FOREIGN KEY (id_equipamento) REFERENCES equipamentos(id),
    FOREIGN KEY (id_analito) REFERENCES analitos(id),
    FOREIGN KEY (id_lote) REFERENCES lotes(id),
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id),
    FOREIGN KEY (corrida_id) REFERENCES corridas(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
