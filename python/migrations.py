"""Adaptação idempotente dos dois esquemas publicados, sem excluir registros."""


def columns(cursor, table):
    cursor.execute('SELECT COLUMN_NAME, COLUMN_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s', (table,))
    return {row['COLUMN_NAME']: row['COLUMN_TYPE'] for row in cursor.fetchall()}


def prepare(cursor):
    """Preserva IDs/FKs existentes e adota os nomes do esquema do repositório."""
    for table, renames in [('usuarios', [('nome', 'nome_usu', 'VARCHAR(100)'), ('cargo', 'funcao', 'VARCHAR(40)')]),
                           ('equipamentos', [('nome', 'nome_equipamento', 'VARCHAR(100)')])]:
        existing = columns(cursor, table)
        for old, new, definition in renames:
            if old in existing and new not in existing:
                cursor.execute(f'ALTER TABLE `{table}` CHANGE COLUMN `{old}` `{new}` {definition} NOT NULL')
    additions = {
        'usuarios': {'cpf': 'CHAR(11) NULL'},
        'equipamentos': {'ativo': 'BOOLEAN NOT NULL DEFAULT TRUE', 'modelo': "VARCHAR(100) NOT NULL DEFAULT ''",
                         'numero_serie': "VARCHAR(100) NOT NULL DEFAULT ''", 'observacoes': "VARCHAR(500) NOT NULL DEFAULT ''"},
    }
    for table, fields in additions.items():
        existing = columns(cursor, table)
        if not existing:
            continue
        for name, definition in fields.items():
            if name not in existing:
                cursor.execute(f'ALTER TABLE `{table}` ADD COLUMN `{name}` {definition}')
    # O SQL remoto reservava somente 15 caracteres para o hash de senha.
    if columns(cursor, 'usuarios'):
        cursor.execute('ALTER TABLE usuarios MODIFY senha_hash VARCHAR(255), MODIFY nome_usu VARCHAR(100), MODIFY funcao VARCHAR(40)')
        for old, new in [('Biomedico', 'Biomédico'), ('Qualidade', 'Gestor de Qualidade'), ('Coordenador', 'Coordenador Técnico')]:
            cursor.execute('UPDATE usuarios SET funcao=%s WHERE funcao=%s', (new, old))
    if columns(cursor, 'equipamentos'):
        cursor.execute('ALTER TABLE equipamentos MODIFY nome_equipamento VARCHAR(100), MODIFY modelo VARCHAR(100), MODIFY numero_serie VARCHAR(100), MODIFY observacoes VARCHAR(500)')
    for table, name in [('analitos', 'nome'), ('lotes', 'codigo')]:
        if columns(cursor, table):
            cursor.execute(f'ALTER TABLE `{table}` MODIFY `{name}` VARCHAR(100)')
    if columns(cursor, 'lotes'):
        cursor.execute('ALTER TABLE lotes MODIFY data_validade DATE NULL, MODIFY fabricante VARCHAR(100)')


def ensure_unique(cursor, table, field, index):
    """Não escolhe arbitrariamente entre cadastros duplicados do banco antigo."""
    cursor.execute(f'SELECT `{field}` FROM `{table}` WHERE `{field}` IS NOT NULL GROUP BY `{field}` HAVING COUNT(*)>1 LIMIT 1')
    if cursor.fetchone():
        raise ValueError(f'Cadastros duplicados em {table}.{field}. Corrija-os antes de executar init-db novamente; nenhum registro foi excluído.')
    cursor.execute(f'SHOW INDEX FROM `{table}`')
    if not any(row['Column_name'] == field and row['Non_unique'] == 0 for row in cursor.fetchall()):
        cursor.execute(f'ALTER TABLE `{table}` ADD UNIQUE KEY `{index}` (`{field}`)')


def finish(cursor):
    for table, field in [('usuarios', 'nome_usu'), ('usuarios', 'cpf'), ('equipamentos', 'nome_equipamento'), ('analitos', 'nome'), ('lotes', 'codigo')]:
        ensure_unique(cursor, table, field, f'uq_{table}_{field}')
    # O esquema anterior usava nomes livres. Reconstitui o catálogo sem inventar validade.
    existing = columns(cursor, 'series')
    for name in ('id_lote', 'id_analito'):
        if name not in existing:
            cursor.execute(f'ALTER TABLE series ADD COLUMN {name} INT NULL')
    cursor.execute('SELECT id, analito, lote FROM series WHERE id_lote IS NULL OR id_analito IS NULL')
    pending = cursor.fetchall()
    for row in pending:
        cursor.execute('INSERT INTO analitos (nome) VALUES (%s) ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)', (row['analito'],))
        analyte = cursor.lastrowid
        cursor.execute('INSERT INTO lotes (codigo, data_validade) VALUES (%s,NULL) ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)', (row['lote'],))
        lot = cursor.lastrowid
        cursor.execute('SELECT id_lote FROM lote_analito WHERE id_lote=%s AND id_analito=%s', (lot, analyte))
        if not cursor.fetchone():
            cursor.execute('INSERT INTO lote_analito (id_lote,id_analito) VALUES (%s,%s)', (lot, analyte))
        cursor.execute('UPDATE series SET id_lote=%s,id_analito=%s WHERE id=%s', (lot, analyte, row['id']))
    for name, table in [('id_lote', 'lotes'), ('id_analito', 'analitos')]:
        cursor.execute('SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s AND COLUMN_NAME=%s AND REFERENCED_TABLE_NAME IS NOT NULL', ('series', name))
        if not cursor.fetchone():
            cursor.execute(f'ALTER TABLE series ADD CONSTRAINT fk_series_{name} FOREIGN KEY ({name}) REFERENCES {table}(id)')
        cursor.execute(f'ALTER TABLE series MODIFY {name} INT NOT NULL')
    if 'corrida_id' not in columns(cursor, 'historico'):
        cursor.execute('ALTER TABLE historico ADD COLUMN corrida_id BIGINT UNSIGNED NULL UNIQUE, ADD FOREIGN KEY (corrida_id) REFERENCES corridas(id)')
    # Corridas da primeira entrega também passam a aparecer no histórico relacional.
    cursor.execute("INSERT INTO historico (data_hora,id_equipamento,id_analito,id_lote,id_usuario,status,corrida_id) "
                   "SELECT c.criado_em,s.equipamento_id,s.id_analito,s.id_lote,c.usuario_id, "
                   "CASE c.status WHEN 'Aceito' THEN 'Normal' WHEN 'Rejeitado' THEN 'Não Conformidade' ELSE 'Alerta' END,c.id "
                   "FROM corridas c JOIN series s ON s.id=c.serie_id LEFT JOIN historico h ON h.corrida_id=c.id WHERE h.id IS NULL")
