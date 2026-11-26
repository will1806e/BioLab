import pytest
from catalog import valid_cpf
from test_api import client, payload
from db import get_db


def test_cpf():
    assert valid_cpf('529.982.247-25') == '52998224725'
    for value in ['11111111111', '52998224724', '', None, 'abc52998224725']:
        with pytest.raises(ValueError):
            valid_cpf(value)


def test_catalog_integrity(client):
    analytes = client.get('/api/analitos').json
    a = next(row['id'] for row in analytes if row['nome'] == 'Glicose')
    b = next(row['id'] for row in analytes if row['nome'] == 'Ureia')
    lot = next(row for row in client.get('/api/lotes').json if row['codigo'] == 'L01')
    data = dict(codigo='L01', data_validade='2099-12-31', analitos=[a, b])
    assert client.post('/api/lotes', json=data).status_code == 409
    assert client.post('/api/lotes', json={**data, 'codigo': 'bad', 'analitos': [999999]}).status_code == 400
    assert client.post('/api/lotes', json={**data, 'codigo': 'bad', 'data_validade': 'no'}).status_code == 400
    assert client.post(f'/api/analitos/{a}/excluir', json={}).status_code == 409
    equipment = client.post('/api/equipamentos', json={'nome': 'M', 'modelo': 'X', 'numero_serie': '123'}).json['id']
    assert client.post('/api/corridas', json=payload(equipment)).status_code == 201
    assert client.post(f"/api/lotes/{lot['id']}/excluir", json={}).status_code == 409
    assert client.post(f"/api/lotes/{lot['id']}/editar", json={**data, 'codigo': 'RENOMEADO'}).status_code == 409
    assert client.post(f"/api/lotes/{lot['id']}/editar", json={**data, 'analitos': [b]}).status_code == 409
    assert client.post(f"/api/lotes/{lot['id']}/editar", json={**data, 'fabricante': 'Atualizado'}).status_code == 200
    assert client.post('/api/corridas', json={**payload(equipment), 'analito': 'Inexistente'}).status_code == 400
    assert client.post(f"/api/lotes/{lot['id']}/editar", json={**data, 'data_validade': '2000-01-01'}).status_code == 200
    assert client.post('/api/corridas', json=payload(equipment)).status_code == 400
    # Um lote sem corridas pode ser excluído, sem excluir seu analito.
    unused = client.post('/api/analitos', json={'nome': 'Livre'}).json['id']
    spare = client.post('/api/lotes', json={**data, 'codigo': 'Livre', 'analitos': [unused]}).json['id']
    assert client.post(f'/api/lotes/{spare}/excluir', json={}).status_code == 200
    assert client.post(f'/api/analitos/{unused}/excluir', json={}).status_code == 200
    with get_db().cursor() as cursor:
        cursor.execute('SELECT COUNT(*) AS n FROM historico WHERE corrida_id IS NOT NULL')
        assert cursor.fetchone()['n'] == 1
