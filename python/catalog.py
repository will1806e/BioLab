"""Cadastro de lotes/analitos e validação de CPF, integrado ao esquema novo."""
import re
from datetime import date
from flask import Blueprint, jsonify, request, session
from db import get_db, insert_id, table_exists, IntegrityError

catalog = Blueprint('catalog', __name__, url_prefix='/api')


def valid_cpf(value):
    """Normaliza a pontuação e verifica os dois dígitos, sem consultar terceiros."""
    if not isinstance(value, str) or re.search(r'[^0-9.\-\s]', value):
        raise ValueError('Informe um CPF válido.')
    cpf = re.sub(r'\D', '', value)
    if len(cpf) != 11 or len(set(cpf)) == 1:
        raise ValueError('Informe um CPF válido.')
    for size in (9, 10):
        digit = (sum(int(cpf[i]) * (size + 1 - i) for i in range(size)) * 10) % 11 % 10
        if digit != int(cpf[size]):
            raise ValueError('Informe um CPF válido.')
    return cpf


@catalog.before_request
def require_session():
    if 'usuario' not in session:
        return jsonify(error='Entre na sua conta para continuar.'), 401


def data():
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise ValueError('Envie um objeto JSON válido.')
    return value


def field(values, name, required=True):
    value = values.get(name, '')
    if not isinstance(value, str) or len(value.strip()) > 100 or (required and not value.strip()):
        raise ValueError(f'{name}: informe até 100 caracteres.')
    return value.strip()


def rows(sql, args=()):
    with get_db().cursor() as cursor:
        cursor.execute(sql, args)
        return cursor.fetchall()


def conflict(message):
    get_db().rollback()
    return jsonify(error=message), 409


@catalog.get('/analitos')
def analytes():
    return jsonify(rows('SELECT * FROM analitos ORDER BY nome'))


@catalog.post('/analitos')
def create_analyte():
    name = field(data(), 'nome')
    try:
        with get_db().cursor() as cursor:
            identifier = insert_id(cursor, 'INSERT INTO analitos (nome) VALUES (%s)', (name,))
        get_db().commit()
    except IntegrityError:
        return conflict('Analito já cadastrado.')
    return jsonify(id=identifier, nome=name), 201


@catalog.post('/analitos/<int:identifier>/excluir')
def delete_analyte(identifier):
    try:
        with get_db().cursor() as cursor:
            cursor.execute('SELECT id FROM analitos WHERE id=%s FOR UPDATE', (identifier,))
            if not cursor.fetchone():
                return jsonify(error='Analito não encontrado.'), 404
            cursor.execute('SELECT id_lote FROM lote_analito WHERE id_analito=%s LIMIT 1', (identifier,))
            if cursor.fetchone():
                return conflict('Não é possível excluir um analito associado a um lote.')
            cursor.execute('SELECT id FROM historico WHERE id_analito=%s LIMIT 1', (identifier,))
            if cursor.fetchone():
                return conflict('Analito vinculado ao histórico; exclusão bloqueada.')
            cursor.execute('DELETE FROM analitos WHERE id=%s', (identifier,))
        get_db().commit()
    except IntegrityError:
        return conflict('Analito vinculado ao histórico; exclusão bloqueada.')
    return jsonify(message='Analito excluído.')


@catalog.get('/lotes')
def lots():
    result = rows('SELECT * FROM lotes ORDER BY codigo')
    associations = rows('SELECT la.id_lote, a.id, a.nome FROM lote_analito la JOIN analitos a ON a.id=la.id_analito ORDER BY a.nome')
    for lot in result:
        lot['data_validade'] = lot['data_validade'].isoformat() if lot['data_validade'] else None
        lot['analitos'] = [{'id': a['id'], 'nome': a['nome']} for a in associations if a['id_lote'] == lot['id']]
    return jsonify(result)


@catalog.post('/lotes')
@catalog.post('/lotes/<int:identifier>/editar')
def save_lot(identifier=None):
    values = data()
    code, manufacturer = field(values, 'codigo'), field(values, 'fabricante', False)
    try:
        expiry = date.fromisoformat(values.get('data_validade', ''))
    except (ValueError, TypeError):
        raise ValueError('Informe uma data de validade válida.') from None
    ids = values.get('analitos')
    if not isinstance(ids, list) or not ids or any(type(i) is not int or i <= 0 for i in ids):
        raise ValueError('Selecione ao menos um analito válido.')
    ids = sorted(set(ids))
    db = get_db()
    try:
        with db.cursor() as cursor:
            if identifier is not None:
                cursor.execute('SELECT * FROM lotes WHERE id=%s FOR UPDATE', (identifier,))
                old = cursor.fetchone()
                if not old:
                    return jsonify(error='Lote não encontrado.'), 404
                cursor.execute('SELECT id_analito FROM series WHERE id_lote=%s', (identifier,))
                used = {row['id_analito'] for row in cursor.fetchall()}
                # Historico legado pode não possuir resultados suficientes para uma série.
                if table_exists(cursor, 'historico'):
                    cursor.execute('SELECT id_analito FROM historico WHERE id_lote=%s', (identifier,))
                    used.update(row['id_analito'] for row in cursor.fetchall())
                if used and (code != old['codigo'] or not used.issubset(set(ids))):
                    return conflict('Lote utilizado: preserve o código e os analitos vinculados ao histórico.')
            placeholders = ','.join(['%s'] * len(ids))
            cursor.execute(f'SELECT id FROM analitos WHERE id IN ({placeholders}) ORDER BY id FOR UPDATE', ids)
            if len(cursor.fetchall()) != len(ids):
                raise ValueError('Um dos analitos selecionados não existe mais.')
            if identifier is None:
                identifier = insert_id(cursor, 'INSERT INTO lotes (codigo,data_validade,fabricante) VALUES (%s,%s,%s)', (code, expiry, manufacturer))
            else:
                cursor.execute('UPDATE lotes SET codigo=%s,data_validade=%s,fabricante=%s WHERE id=%s', (code, expiry, manufacturer, identifier))
                cursor.execute('DELETE FROM lote_analito WHERE id_lote=%s', (identifier,))
            cursor.executemany('INSERT INTO lote_analito (id_lote,id_analito) VALUES (%s,%s)', [(identifier, i) for i in ids])
        db.commit()
    except IntegrityError:
        return conflict('Código de lote já cadastrado ou vínculo inválido.')
    except Exception:
        db.rollback()
        raise
    return jsonify(id=identifier, message='Lote salvo.'), 200


@catalog.post('/lotes/<int:identifier>/excluir')
def delete_lot(identifier):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute('SELECT id FROM lotes WHERE id=%s FOR UPDATE', (identifier,))
            if not cursor.fetchone():
                return jsonify(error='Lote não encontrado.'), 404
            cursor.execute('SELECT id FROM series WHERE id_lote=%s LIMIT 1', (identifier,))
            if cursor.fetchone():
                return conflict('Lote utilizado em corridas; exclusão bloqueada para preservar os gráficos.')
            if table_exists(cursor, 'historico'):
                cursor.execute('SELECT id FROM historico WHERE id_lote=%s LIMIT 1', (identifier,))
                if cursor.fetchone():
                    return conflict('Lote utilizado no histórico legado; exclusão bloqueada.')
            cursor.execute('DELETE FROM lote_analito WHERE id_lote=%s', (identifier,))
            cursor.execute('DELETE FROM lotes WHERE id=%s', (identifier,))
        db.commit()
    except IntegrityError:
        return conflict('Lote possui vínculos; exclusão bloqueada.')
    return jsonify(message='Lote excluído.')
