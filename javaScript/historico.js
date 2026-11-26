import {api, sessionRequired, renderRuns, message, element} from './app.js';

const table = document.querySelector('main table');
const body = table.tBodies[0];
const filters = [...table.querySelectorAll('[data-filtro]')];
const dayInLab = new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit'
});

function filterValue(record, key) {
    if (key === 'equipamento') return String(record.equipamento_id ?? '—');
    return record[key] || '—';
}

function populateFilters(records, equipmentId) {
    for (const select of filters.filter(control => control.tagName === 'SELECT')) {
        const key = select.dataset.filtro;
        const options = new Map(records.map(record => [filterValue(record, key), record[key] || 'Não informado']));
        // O link em Equipamentos também pode apontar para uma máquina sem corridas.
        if (key === 'equipamento' && equipmentId && !options.has(equipmentId)) {
            options.set(equipmentId, `Equipamento ${equipmentId} (sem registros)`);
        }
        const sorted = [...options].sort((a, b) => a[1].localeCompare(b[1], 'pt-BR', {numeric: true}));
        for (const [value, label] of sorted) select.add(new Option(label, value));
        if (key === 'equipamento' && equipmentId) select.value = equipmentId;
    }
}

function appendLegacy(item) {
    const row = element('tr');
    for (const value of [item.data_hora || 'Não informada', item.equipamento, item.analito, item.lote,
        'Legado: resultado não registrado', item.responsavel, item.cargo, item.status]) {
        row.append(element('td', value || '—'));
    }
    body.append(row);
}

async function start() {
    await sessionRequired();
    const [runs, legacy] = await Promise.all([api('corridas'), api('historico-legado')]);
    const records = [
        ...runs.map(run => ({...run, dia: dayInLab.format(new Date(run.criado_em))})),
        // O legado não registra fuso. A data do filtro é a que aparece na própria linha.
        ...legacy.map(item => ({...item, dia: item.data_hora?.slice(0, 10), equipamento_id: item.id_equipamento}))
    ];
    const equipment = table.querySelector('[data-filtro="equipamento"]');
    populateFilters(records, new URLSearchParams(location.search).get('equipamento'));

    if (runs.length) renderRuns(body, runs, true);
    legacy.forEach(appendLegacy);
    const rows = [...body.rows];
    const emptyRow = element('tr');
    const emptyCell = element('td');
    emptyCell.colSpan = table.tHead.rows[0].cells.length;
    emptyRow.append(emptyCell);
    body.append(emptyRow);
    const clear = document.getElementById('limpar-filtros');

    function applyFilters() {
        const active = filters.filter(control => control.value);
        let matches = 0;
        records.forEach((record, index) => {
            const visible = active.every(control => filterValue(record, control.dataset.filtro) === control.value);
            rows[index].hidden = !visible;
            if (visible) matches++;
        });
        emptyRow.hidden = matches > 0;
        emptyCell.textContent = active.length ? 'Nenhum registro corresponde aos filtros.' : 'Nenhuma corrida registrada.';
        clear.disabled = !active.length;
    }

    function syncEquipmentLink() {
        const url = new URL(location.href);
        if (equipment.value) url.searchParams.set('equipamento', equipment.value);
        else url.searchParams.delete('equipamento');
        history.replaceState(null, '', url);
    }

    equipment.addEventListener('change', syncEquipmentLink);
    for (const control of filters) {
        control.disabled = false;
        control.addEventListener('change', applyFilters);
    }
    clear.addEventListener('click', () => {
        for (const control of filters) control.value = '';
        syncEquipmentLink();
        applyFilters();
    });
    applyFilters();
}
start().catch(error => message(error.message));
