"""Integração opt-in: cria um banco biolab_test_* exclusivo, sem apagar dados."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

pytestmark = pytest.mark.skipif(os.getenv('BIOLAB_TEST_MYSQL') != '1', reason='Requer MySQL e BIOLAB_TEST_MYSQL=1')


@pytest.fixture
def client(monkeypatch):
    if os.getenv('BIOLAB_TEST_MYSQL') != '1':
        pytest.skip('Requer MySQL e BIOLAB_TEST_MYSQL=1')
    from app import app
    from db import init_db
    monkeypatch.setenv('DB_NAME', 'biolab_test_' + uuid.uuid4().hex)
    app.config.update(TESTING=True)
    init_db()
    with app.test_client() as client:
        assert client.post('/api/cadastro', json={'nome': 'Teste', 'senha': 'senha1234', 'cargo': 'Biomedico', 'cpf': '52998224725'}).status_code == 201
        assert client.post('/api/login', json={'nome': 'Teste', 'senha': 'senha1234'}).status_code == 200
        a = client.post('/api/analitos', json={'nome': 'Glicose', 'modelo': 'M', 'numero_serie': 'S'}).json['id']
        b = client.post('/api/analitos', json={'nome': 'Ureia', 'modelo': 'M', 'numero_serie': 'S'}).json['id']
        for code in ['L01', 'L02']:
            assert client.post('/api/lotes', json={'codigo': code, 'data_validade': '2099-12-31', 'analitos': [a, b]}).status_code == 200
        yield client


def payload(equipment):
    return dict(equipamento_id=equipment, analito='Glicose', lote='L01', controle='Nível 1',
                resultado='104,5', alvo=100, desvio=2, unidade='mg/dL', limite_min=90, limite_max=110)


def test_series_and_validation(client):
    first = client.post('/api/equipamentos', json={'nome': 'Máquina A', 'modelo': 'M', 'numero_serie': 'S'}).json['id']
    second = client.post('/api/equipamentos', json={'nome': 'Máquina B', 'modelo': 'M', 'numero_serie': 'S'}).json['id']
    data = payload(first)
    one = client.post('/api/corridas', json=data)
    assert one.status_code == 201 and one.json['status'] == 'Alerta'
    two = client.post('/api/corridas', json=data)
    assert two.json['serie_id'] == one.json['serie_id']
    assert '2_2s' in two.json['regras']
    for change in [{'equipamento_id': second}, {'analito': 'Ureia'}, {'lote': 'L02'}]:
        response = client.post('/api/corridas', json={**data, **change})
        assert response.status_code == 201
        assert response.json['serie_id'] != one.json['serie_id']
        assert response.json['regras'] == ['1_2s']
    for change in [{'desvio': 0}, {'resultado': 'NaN'}, {'alvo': 101}, {'controle': 'Nível 2'},
                   {'limite_min': 120}, {'equipamento_id': 99999}, {'resultado': ''}]:
        assert client.post('/api/corridas', json={**data, **change}).status_code == 400
    assert len(client.get('/api/series').json) == 4
    detail = client.get(f"/api/series/{one.json['serie_id']}").json
    assert len(detail['corridas']) == 2
    assert len(detail['limites']) == 7
    assert detail['estatisticas']['media'] == 104.5
    assert len(client.get('/api/corridas').json) == 5
    assert client.get('/api/resumo').json['hoje']['Rejeitado'] == 1
    assert client.post('/api/logout', json={}).status_code == 200
    assert client.get('/api/corridas').status_code == 401


def test_auth_and_bula(client):
    assert client.post('/api/cadastro', json={'nome': 'Teste', 'senha': 'senha1234', 'cargo': 'Biomedico', 'cpf': '52998224725'}).status_code == 409
    assert client.post('/api/login', json={'nome': 'Teste', 'senha': 'errada'}).status_code == 401
    assert client.post('/api/equipamentos', json={'nome': 'A', 'modelo': 'M', 'numero_serie': 'S'}, headers={'Origin': 'https://other.test'}).status_code == 403
    equipment = client.post('/api/equipamentos', json={'nome': 'A', 'modelo': 'M', 'numero_serie': 'S'}).json['id']
    result = client.post('/api/corridas', json={**payload(equipment), 'resultado': 100, 'limite_max': 99}).json
    assert result['status'] == 'Aceito' and result['fora_bula']


def test_concurrent_creation(client):
    from app import app
    equipment = client.post('/api/equipamentos', json={'nome': 'Concorrente', 'modelo': 'M', 'numero_serie': 'S'}).json['id']
    def send(_):
        with app.test_client() as other:
            other.post('/api/login', json={'nome': 'Teste', 'senha': 'senha1234'})
            response = other.post('/api/corridas', json=payload(equipment))
            assert response.status_code == 201
            return response.json
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(send, range(3)))
    assert len({r['serie_id'] for r in results}) == 1
    assert sorted(r['status'] for r in results) == ['Alerta', 'Rejeitado', 'Rejeitado']
