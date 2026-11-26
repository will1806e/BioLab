"""Valida os dois bancos de origem com registros existentes e execução repetida."""
import os
import uuid
from pathlib import Path
import pytest
from werkzeug.security import generate_password_hash
from db import connect, init_db

pytestmark = pytest.mark.skipif(os.getenv('BIOLAB_TEST_MYSQL') != '1', reason='Requer MySQL e BIOLAB_TEST_MYSQL=1')


@pytest.mark.parametrize('source', ['previous', 'upstream'])
def test_upgrade(source, monkeypatch):
    name = 'biolab_test_' + uuid.uuid4().hex
    monkeypatch.setenv('DB_NAME', name)
    db = connect(False)
    try:
        with db.cursor() as c:
            c.execute(f'CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
            c.execute(f'USE `{name}`')
            sql = (Path(__file__).parent / 'fixtures' / f'{source}.sql').read_text(encoding='utf-8')
            for statement in sql.split(';'):
                if statement.strip() and not statement.strip().lower().startswith(('create database', 'use ', 'describe ')):
                    # A versão XAMPP anterior ao MySQL 8 usa CHANGE em vez de RENAME COLUMN.
                    statement = statement.replace('RENAME COLUMN senha TO senha_hash', 'CHANGE COLUMN senha senha_hash VARCHAR(15)')
                    c.execute(statement)
            if source == 'previous':
                c.execute('INSERT INTO usuarios (nome,senha_hash,cargo) VALUES (%s,%s,%s)', ('Antigo', generate_password_hash('senha1234'), 'Biomedico'))
                c.execute("INSERT INTO equipamentos (nome) VALUES ('Antigo')")
                c.execute("INSERT INTO series (equipamento_id,analito,lote,controle,alvo,desvio,unidade) VALUES (1,'Glicose','LEGADO','N1',100,2,'mg/dL')")
                c.execute("INSERT INTO corridas (serie_id,usuario_id,criado_em,resultado,z,status,regras) VALUES (1,1,'2026-01-01',100,0,'Aceito','[]')")
            else:
                c.execute("INSERT INTO usuarios (nome_usu,cpf,senha_hash,funcao) VALUES ('Legado','52998224725','hash-incompleto','Biomédico')")
                c.execute("INSERT INTO equipamentos (nome_equipamento) VALUES ('Legado')")
                c.execute("INSERT INTO analitos (nome) VALUES ('Glicose')")
                c.execute("INSERT INTO lotes (codigo,data_validade) VALUES ('LEGADO','2099-12-31')")
                c.execute('INSERT INTO lote_analito VALUES (1,1)')
                c.execute("INSERT INTO historico (data_hora,id_equipamento,id_analito,id_lote,id_usuario,status) VALUES ('2026-01-01',1,1,1,1,'Normal')")
        db.commit()
    finally:
        db.close()
    init_db()
    init_db()
    db = connect()
    try:
        with db.cursor() as c:
            c.execute('SELECT COUNT(*) AS n FROM historico')
            assert c.fetchone()['n'] == 1
            c.execute('SELECT * FROM usuarios')
            user = c.fetchone()
            assert user['funcao'] == 'Biomédico'
            c.execute('SHOW COLUMNS FROM usuarios LIKE %s', ('senha_hash',))
            assert c.fetchone()['Type'] == 'varchar(255)'
            if source == 'previous':
                c.execute('SELECT * FROM series')
                assert c.fetchone()['id_lote'] == 1
                c.execute('SELECT * FROM lotes')
                assert c.fetchone()['data_validade'] is None
            else:
                c.execute('SELECT * FROM historico')
                assert c.fetchone()['corrida_id'] is None
        # Comprova que novas corridas funcionam após migrar IDs INT ou BIGINT.
        from app import app
        with app.test_client() as client:
            with client.session_transaction() as session:
                session['usuario'] = {'id': 1, 'nome': 'Legado', 'cargo': 'Biomedico'}
            if source == 'previous':
                assert client.post('/api/lotes/1/editar', json={'codigo': 'LEGADO', 'data_validade': '2099-12-31', 'analitos': [1]}).status_code == 200
            limits = {} if source == 'previous' else {'limite_min': 94, 'limite_max': 106}
            response = client.post('/api/corridas', json=dict(equipamento_id=1, analito='Glicose', lote='LEGADO', controle='Nível 3', resultado=101, alvo=100, unidade='mg/dL', **limits))
            assert response.status_code == 201, response.json
            assert len(client.get('/api/historico-legado').json) == (1 if source == 'upstream' else 0)
    finally:
        db.close()
