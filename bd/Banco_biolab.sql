CREATE DATABASE biolab;
use biolab;

CREATE TABLE usuarios(
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome_usu VARCHAR(30),
    cpf CHAR(11),
    senha VARCHAR(15),
    funcao ENUM('Biomédico', 'Gestor de Qualidade', 'Coordenador Técnico')
);

ALTER TABLE usuarios RENAME COLUMN senha TO senha_hash;
ALTER TABLE usuarios MODIFY COLUMN cpf CHAR(11) NOT NULL;
ALTER TABLE usuarios MODIFY COLUMN funcao ENUM('Biomédico', 'Gestor de Qualidade', 'Coordenador Técnico') NOT NULL;

DESCRIBE usuarios;

CREATE TABLE analitos(
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(30)
);

CREATE TABLE lotes(
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(30) NOT NULL,
    data_validade DATE NOT NULL,
    fabricante VARCHAR(30)
);

CREATE TABLE lote_analito(
    id_lote INT NOT NULL,
    id_analito INT NOT NULL,
    FOREIGN KEY (id_lote) REFERENCES lotes (id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (id_analito) REFERENCES analitos (id) ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE equipamentos(
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome_equipamento VARCHAR(30),
    modelo VARCHAR(30),
    numero_serie VARCHAR(30),
    observacoes VARCHAR(100)
);

CREATE TABLE historico(
    id INT AUTO_INCREMENT PRIMARY KEY,
    data_hora DATETIME,
    id_equipamento INT,
    id_analito INT,
    id_lote INT,
    id_usuario INT,
    status ENUM('Normal', 'Alerta', 'Não Conformidade'),
    FOREIGN KEY (id_equipamento) REFERENCES equipamentos (id) ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (id_analito) REFERENCES analitos (id) ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (id_lote) REFERENCES lotes (id) ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (id_usuario) REFERENCES usuarios (id) ON DELETE SET NULL ON UPDATE CASCADE
);















