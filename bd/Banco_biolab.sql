CREATE DATABASE biolab;
use biolab;

CREATE TABLE usuarios(
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome_usu VARCHAR(30),
    cpf CHAR(11),
    senha VARCHAR(15),
    funcao ENUM('Biomédico', 'Gestor de Qualidade', 'Coordenador Técnico')
);

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

