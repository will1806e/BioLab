"""Servidor local BioLab: páginas, sessão e API de controle de qualidade."""
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

import pymysql
from flask import Flask, jsonify, request, session, send_from_directory, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException

from db import get_db, close_db, init_db
from quality import number, evaluate, summary
from catalog import catalog, valid_cpf

ROOT = Path(__file__).resolve().parents[1]
app = Flask(__name__, static_folder=None)
app.config.update(SECRET_KEY=os.getenv('SECRET_KEY') or secrets.token_hex(32),
                  SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict',
                  MAX_CONTENT_LENGTH=32 * 1024)
app.teardown_appcontext(close_db)
app.register_blueprint(catalog)


def text(data, key, maximum=100):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise ValueError(f'{key}: informe um texto de até {maximum} caracteres.')
    return value.strip()


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError('Envie um objeto JSON válido.')
    return data


def query(sql, args=()):
    with get_db().cursor() as cursor:
        cursor.execute(sql, args)
        return cursor.fetchall()


def authenticated(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        if 'usuario' not in session:
            return jsonify(error='Entre na sua conta para continuar.'), 401
        return handler(*args, **kwargs)
    return wrapped


@app.before_request
def same_origin():
    """As mutações exigem JSON e origem local, evitando formulários externos."""
    if request.path.startswith('/api/') and request.method == 'POST':
        if request.headers.get('Origin') not in (None, request.host_url.rstrip('/')):
            return jsonify(error='Origem não permitida.'), 403
        if not request.is_json:
            return jsonify(error='Utilize JSON.'), 415


@app.errorhandler(ValueError)
def invalid(error):
    return jsonify(error=str(error)), 400


@app.errorhandler(pymysql.MySQLError)
def database_error(error):
    app.logger.exception('Falha MySQL')
    return jsonify(error='Não foi possível acessar o MySQL. Confira a conexão e execute init-db.'), 503


@app.errorhandler(HTTPException)
def http_error(error):
    return jsonify(error=error.description), error.code


@app.cli.command('init-db')
def initialize():
    """Executar: python -m flask --app python/app.py init-db."""
    init_db()
    print('Banco BioLab inicializado.')


@app.get('/')
def home():
    return redirect('/html/index.html')


@app.get('/<folder>/<path:filename>')
def files(folder, filename):
    if folder not in {'html', 'css', 'javaScript', 'img'}:
        return jsonify(error='Arquivo não encontrado.'), 404
    return send_from_directory(ROOT / folder, filename)


@app.post('/api/cadastro')
def register():
    data = body()
    name, password, role = text(data, 'nome'), text(data, 'senha', 200), text(data, 'cargo', 40)
    if len(password) < 8:
        raise ValueError('Use uma senha com pelo menos 8 caracteres.')
    roles = {'Biomedico': 'Biomédico', 'Qualidade': 'Gestor de Qualidade', 'Coordenador': 'Coordenador Técnico'}
    if role not in roles:
        raise ValueError('Função inválida.')
    cpf = valid_cpf(data.get('cpf'))
    role = roles[role]
    try:
        with get_db().cursor() as cursor:
            cursor.execute('INSERT INTO usuarios (nome_usu, senha_hash, funcao, cpf) VALUES (%s,%s,%s,%s)',
                           (name, generate_password_hash(password), role, cpf))
        get_db().commit()
    except pymysql.IntegrityError:
        get_db().rollback()
        return jsonify(error='Nome de usuário ou CPF já cadastrado.'), 409
    return jsonify(message='Cadastro realizado. Entre com sua conta.'), 201


@app.post('/api/login')
def login():
    data = body()
    users = query('SELECT id, nome_usu AS nome, senha_hash, funcao AS cargo FROM usuarios WHERE nome_usu=%s', (text(data, 'nome'),))
    password = text(data, 'senha', 200)
    if not users or not check_password_hash(users[0]['senha_hash'] or '', password):
        return jsonify(error='Usuário ou senha inválidos.'), 401
    user = users[0]
    session.clear()
    session['usuario'] = {k: user[k] for k in ('id', 'nome', 'cargo')}
    return jsonify(session['usuario'])


@app.get('/api/sessao')
@authenticated
def current_user():
    return jsonify(session['usuario'])


@app.post('/api/logout')
def logout():
    session.clear()
    return jsonify(message='Sessão encerrada.')


@app.get('/api/equipamentos')
@authenticated
def equipment_list():
    return jsonify(query('SELECT e.*, e.nome_equipamento AS nome, COUNT(DISTINCT s.analito) AS analitos FROM equipamentos e '
                         'LEFT JOIN series s ON s.equipamento_id=e.id GROUP BY e.id ORDER BY e.nome_equipamento'))


@app.post('/api/equipamentos')
@authenticated
def equipment_create():
    data = body()
    name = text(data, 'nome')
    model = text(data, 'modelo')
    serial = text(data, 'numero_serie')
    notes = data.get('observacoes', '')
    if not isinstance(notes, str) or len(notes) > 500:
        raise ValueError('Observações: máximo de 500 caracteres.')
    try:
        with get_db().cursor() as cursor:
            cursor.execute('INSERT INTO equipamentos (nome_equipamento, modelo, numero_serie, observacoes) VALUES (%s,%s,%s,%s)', (name, model, serial, notes))
            identifier = cursor.lastrowid
        get_db().commit()
    except pymysql.IntegrityError:
        get_db().rollback()
        return jsonify(error='Equipamento já cadastrado.'), 409
    return jsonify(id=identifier, nome=name), 201


SERIES_SQL = 'SELECT s.*, e.nome_equipamento AS equipamento FROM series s JOIN equipamentos e ON e.id=s.equipamento_id '
RUNS_SQL = ('SELECT c.*, s.equipamento_id, e.nome_equipamento AS equipamento, s.analito, s.lote, s.controle, '
            's.unidade, u.nome_usu AS responsavel, u.funcao AS cargo FROM corridas c JOIN series s ON s.id=c.serie_id '
            'JOIN equipamentos e ON e.id=s.equipamento_id JOIN usuarios u ON u.id=c.usuario_id ')


def serialize_run(row):
    row['regras'] = json.loads(row['regras'])
    # Instantes são guardados em UTC e enviados com fuso explícito ao navegador.
    row['criado_em'] = row['criado_em'].replace(tzinfo=timezone.utc).isoformat()
    return row


@app.get('/api/series')
@authenticated
def series_list():
    return jsonify(query(SERIES_SQL + 'ORDER BY e.nome_equipamento, s.analito, s.lote'))


@app.get('/api/series/<int:identifier>')
@authenticated
def series_detail(identifier):
    rows = query(SERIES_SQL + 'WHERE s.id=%s', (identifier,))
    if not rows:
        return jsonify(error='Gráfico não encontrado.'), 404
    series = rows[0]
    runs = [serialize_run(r) for r in query(RUNS_SQL + 'WHERE s.id=%s ORDER BY c.id', (identifier,))]
    series['corridas'] = runs
    series['estatisticas'] = summary([r['resultado'] for r in runs])
    series['limites'] = [{'sigma': i, 'valor': series['alvo'] + i * series['desvio']} for i in range(-3, 4)]
    return jsonify(series)


@app.get('/api/corridas')
@authenticated
def runs_list():
    return jsonify([serialize_run(r) for r in query(RUNS_SQL + 'ORDER BY c.id DESC')])


@app.get('/api/historico-legado')
@authenticated
def legacy_history():
    """Registros antigos sem medição são exibidos sem inventar resultado ou regras."""
    result = query('SELECT h.*, e.nome_equipamento AS equipamento, a.nome AS analito, l.codigo AS lote, '
                   'u.nome_usu AS responsavel, u.funcao AS cargo FROM historico h '
                   'LEFT JOIN equipamentos e ON e.id=h.id_equipamento LEFT JOIN analitos a ON a.id=h.id_analito '
                   'LEFT JOIN lotes l ON l.id=h.id_lote LEFT JOIN usuarios u ON u.id=h.id_usuario '
                   'WHERE h.corrida_id IS NULL ORDER BY h.data_hora DESC, h.id DESC')
    for row in result:
        # O SQL legado não especificava fuso: não atribuímos UTC a esses instantes.
        row['data_hora'] = row['data_hora'].isoformat(sep=' ') if row['data_hora'] else None
    return jsonify(result)


@app.get('/api/resumo')
@authenticated
def dashboard_summary():
    # O laboratório usa America/Sao_Paulo (UTC-3); armazenamento continua em UTC.
    now = datetime.now(timezone(timedelta(hours=-3)))
    start = now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).replace(tzinfo=None)
    counts = query('SELECT status, COUNT(*) AS total FROM corridas WHERE criado_em >= %s GROUP BY status', (start,))
    return jsonify(equipamentos=query('SELECT COUNT(*) AS n FROM equipamentos WHERE ativo=TRUE')[0]['n'],
                   hoje={r['status']: r['total'] for r in counts})


@app.post('/api/corridas')
@authenticated
def run_create():
    data = body()
    equipment = data.get('equipamento_id')
    if isinstance(equipment, bool) or not str(equipment).isdigit() or int(equipment) <= 0:
        raise ValueError('Selecione um equipamento válido.')
    equipment = int(equipment)
    names = {key: text(data, key, 30 if key == 'unidade' else 100) for key in ('analito', 'lote', 'controle', 'unidade')}
    numeric = {key: number(data.get(key), key) for key in ('resultado', 'alvo', 'desvio')}
    if numeric['desvio'] <= 0:
        raise ValueError('Desvio padrão deve ser maior que zero.')
    for key in ('limite_min', 'limite_max'):
        numeric[key] = None if data.get(key) in (None, '') else number(data[key], key)
    low, high = numeric['limite_min'], numeric['limite_max']
    if low is not None and high is not None and low > high:
        raise ValueError('Limite mínimo não pode superar o máximo.')
    db = get_db()
    try:
        with db.cursor() as cursor:
            # Serializa registros por equipamento, inclusive a criação concorrente da série.
            cursor.execute('SELECT id FROM equipamentos WHERE id=%s AND ativo=TRUE FOR UPDATE', (equipment,))
            if not cursor.fetchone():
                raise ValueError('Equipamento não encontrado ou inativo.')
            # Bloqueia lote e analito durante a gravação para coordenar edições/exclusões.
            cursor.execute('SELECT * FROM lotes WHERE codigo=%s FOR UPDATE', (names['lote'],))
            lot = cursor.fetchone()
            if not lot:
                raise ValueError('Cadastre o lote antes de registrar a corrida.')
            today = datetime.now(timezone(timedelta(hours=-3))).date()
            if lot['data_validade'] is None or lot['data_validade'] < today:
                raise ValueError('Lote vencido ou sem validade. Atualize o cadastro em Lotes.')
            cursor.execute('SELECT a.* FROM analitos a JOIN lote_analito la ON la.id_analito=a.id '
                           'WHERE la.id_lote=%s AND a.nome=%s FOR UPDATE', (lot['id'], names['analito']))
            analyte = cursor.fetchone()
            if not analyte:
                raise ValueError('O analito não pertence ao lote selecionado.')
            names['lote'], names['analito'] = lot['codigo'], analyte['nome']
            cursor.execute('SELECT * FROM series WHERE equipamento_id=%s AND analito=%s AND lote=%s FOR UPDATE',
                           (equipment, names['analito'], names['lote']))
            series = cursor.fetchone()
            if series:
                for key in ('controle', 'unidade', 'alvo', 'desvio', 'limite_min', 'limite_max'):
                    supplied = names[key] if key in names else numeric[key]
                    if series[key] != supplied:
                        raise ValueError('Esta série já existe. Mantenha seu material, unidade e parâmetros originais; use outro lote para uma nova referência.')
                identifier = series['id']
            else:
                cursor.execute('INSERT INTO series (equipamento_id, analito, lote, controle, unidade, alvo, desvio, limite_min, limite_max, id_lote, id_analito) '
                               'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                               (equipment, names['analito'], names['lote'], names['controle'], names['unidade'],
                                numeric['alvo'], numeric['desvio'], low, high, lot['id'], analyte['id']))
                identifier = cursor.lastrowid
            cursor.execute('SELECT resultado FROM corridas WHERE serie_id=%s ORDER BY id DESC LIMIT 9', (identifier,))
            previous = [r['resultado'] for r in reversed(cursor.fetchall())]
            result = evaluate(previous, numeric['resultado'], numeric['alvo'], numeric['desvio'])
            outside = (low is not None and numeric['resultado'] < low) or (high is not None and numeric['resultado'] > high)
            cursor.execute('INSERT INTO corridas (serie_id, usuario_id, criado_em, resultado, z, status, regras, fora_bula) '
                           'VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                           (identifier, session['usuario']['id'], datetime.now(timezone.utc).replace(tzinfo=None),
                            numeric['resultado'], result['z'], result['status'], json.dumps(result['regras']), outside))
            run_id = cursor.lastrowid
            cursor.execute('INSERT INTO historico (data_hora,id_equipamento,id_analito,id_lote,id_usuario,status,corrida_id) '
                           'SELECT criado_em,%s,%s,%s,usuario_id,%s,id FROM corridas WHERE id=%s',
                           (equipment, analyte['id'], lot['id'], {'Aceito': 'Normal', 'Alerta': 'Alerta', 'Rejeitado': 'Não Conformidade'}[result['status']], run_id))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return jsonify(id=run_id, serie_id=identifier, fora_bula=outside, **result), 201


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.getenv('PORT', '5000')), debug=False)
