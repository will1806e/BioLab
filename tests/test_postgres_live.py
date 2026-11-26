"""Fluxo real em um esquema isolado do Postgres, sem tocar em dados do produto."""
import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv('BIOLAB_TEST_POSTGRES') != '1',
    reason='Requer Neon e BIOLAB_TEST_POSTGRES=1',
)


@pytest.fixture(scope='module')
def client():
    if os.getenv('BIOLAB_TEST_POSTGRES') != '1':
        pytest.skip('Requer Neon e BIOLAB_TEST_POSTGRES=1')
    import psycopg
    from psycopg import sql
    from app import app
    from db import init_db

    schema = 'qa_' + uuid.uuid4().hex
    url = os.getenv('DATABASE_URL_UNPOOLED', os.getenv('DATABASE_URL'))
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    previous = os.environ.get('DB_SCHEMA')
    os.environ['DB_SCHEMA'] = schema
    try:
        init_db()
        app.config.update(TESTING=True)
        with app.test_client() as test_client:
            yield test_client
    finally:
        if previous is None:
            os.environ.pop('DB_SCHEMA', None)
        else:
            os.environ['DB_SCHEMA'] = previous
        with psycopg.connect(url, autocommit=True) as admin:
            admin.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def test_complete_laboratory_flow(client):
    assert client.get('/api/sessao').status_code == 401
    user = {'nome': 'Teste Neon', 'senha': 'senha1234', 'cargo': 'Biomedico', 'cpf': '52998224725'}
    assert client.post('/api/cadastro', json=user).status_code == 201
    assert client.post('/api/cadastro', json=user).status_code == 409
    assert client.post('/api/login', json={'nome': user['nome'], 'senha': 'errada'}).status_code == 401
    assert client.post('/api/login', json={'nome': user['nome'], 'senha': user['senha']}).status_code == 200
    assert client.get('/api/sessao').json['nome'] == user['nome']

    equipment = client.post('/api/equipamentos', json={
        'nome': 'Equipamento Neon', 'modelo': 'Modelo 1', 'numero_serie': 'N-1',
    })
    assert equipment.status_code == 201
    equipment_id = equipment.json['id']
    assert len(client.get('/api/equipamentos').json) == 1

    analyte = client.post('/api/analitos', json={'nome': 'Glicose'})
    assert analyte.status_code == 201
    analyte_id = analyte.json['id']
    lot = client.post('/api/lotes', json={
        'codigo': 'NEON-001', 'data_validade': '2099-12-31',
        'fabricante': 'Teste', 'analitos': [analyte_id],
    })
    assert lot.status_code == 200
    lot_id = lot.json['id']
    assert client.get('/api/lotes').json[0]['analitos'][0]['nome'] == 'Glicose'

    run = {
        'equipamento_id': equipment_id, 'analito': 'Glicose', 'lote': 'NEON-001',
        'controle': 'Nível 1', 'resultado': '104,5', 'alvo': 100, 'desvio': 2,
        'unidade': 'mg/dL', 'limite_min': 90, 'limite_max': 110,
    }
    first = client.post('/api/corridas', json=run)
    assert first.status_code == 201 and first.json['status'] == 'Alerta'
    second = client.post('/api/corridas', json=run)
    assert second.status_code == 201 and second.json['serie_id'] == first.json['serie_id']
    assert '2_2s' in second.json['regras']
    assert client.post('/api/corridas', json={**run, 'desvio': 0}).status_code == 400
    assert len(client.get('/api/corridas').json) == 2
    assert len(client.get('/api/series').json) == 1
    assert len(client.get(f"/api/series/{first.json['serie_id']}").json['corridas']) == 2
    assert client.get('/api/resumo').json['equipamentos'] == 1
    assert client.post(f'/api/lotes/{lot_id}/excluir', json={}).status_code == 409
    assert client.post(f'/api/analitos/{analyte_id}/excluir', json={}).status_code == 409
    assert client.post('/api/logout', json={}).status_code == 200
    assert client.get('/api/corridas').status_code == 401
