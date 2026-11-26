"""Conexão MySQL por requisição e inicialização explícita do esquema."""
import os
from pathlib import Path
import pymysql
from flask import g
from migrations import prepare, finish, columns


def connect(database=True):
    return pymysql.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'), port=int(os.getenv('DB_PORT', '3306')),
        user=os.getenv('DB_USER', 'root'), password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'biolab') if database else None,
        charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor,
        autocommit=False, connect_timeout=5)


def get_db():
    if 'db' not in g:
        g.db = connect()
    return g.db


def close_db(_error=None):
    connection = g.pop('db', None)
    if connection:
        connection.close()


def init_db():
    """Cria somente o banco configurado e tabelas ausentes, sem dados fictícios."""
    name = os.getenv('DB_NAME', 'biolab')
    if not name.isascii() or not name.replace('_', '').isalnum():
        raise ValueError('DB_NAME deve conter apenas letras, números e sublinhado.')
    connection = connect(False)
    try:
        with connection.cursor() as cursor:
            cursor.execute(f'CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
            cursor.execute(f'USE `{name}`')
            prepare(cursor)
            sql = (Path(__file__).resolve().parents[1] / 'database/schema.sql').read_text(encoding='utf-8')
            for statement in sql.split(';'):
                if statement.strip():
                    # IDs do SQL remoto são INT; a primeira entrega usava BIGINT.
                    # FKs precisam acompanhar exatamente o tipo já instalado.
                    for table, field in [('equipamentos', 'equipamento_id'), ('usuarios', 'usuario_id'),
                                         ('equipamentos', 'id_equipamento'), ('usuarios', 'id_usuario')]:
                        types = columns(cursor, table)
                        if types:
                            statement = statement.replace(f'{field} BIGINT UNSIGNED', f'{field} {types["id"]}')
                    cursor.execute(statement)
            finish(cursor)
        connection.commit()
    finally:
        connection.close()
