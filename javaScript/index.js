import {drawLeveyJennings} from './leveyJennings.js';
import {api, sessionRequired, element, message, renderRuns} from './app.js';

const equipmentFilter = document.getElementById('filtro-equipamento');
const lotFilter = document.getElementById('filtro-lote');
const analyteFilter = document.getElementById('filtro-analito');
let requestVersion = 0;

let chart;
let displayedSeries;
const levelSelect = document.getElementById('nivel-visual');
const visualControls = document.getElementById('grafico-visual');

function draw(series) {
    const host = document.getElementById('grafico');
    const runs = series.corridas;
    if (!runs.length) {
        host.textContent = 'Esta série ainda não possui resultados.';
        return;
    }
    const canvas = element('canvas');
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', `Levey-Jennings de ${series.analito}, equipamento ${series.equipamento}, lote ${series.lote}.`);
    host.replaceChildren(canvas);
    chart = drawLeveyJennings(canvas, series);
    displayedSeries = series;
    levelSelect.value = String(series.nivel_visual);
    visualControls.hidden = false;
}

// Descarta respostas antigas caso o usuário troque rapidamente de gráfico.
async function showSelected(id) {
    const version = ++requestVersion;
    chart?.destroy();
    chart = undefined;
    displayedSeries = null;
    visualControls.hidden = true;
    document.getElementById('grafico').textContent = 'Carregando gráfico…';
    try {
        const data = await api(`series/${id}`);
        if (version !== requestVersion) return;
        draw(data);
        const url = new URL(location.href); url.searchParams.set('serie', id);
        history.replaceState(null, '', url);
    } catch (error) {
        if (version === requestVersion) document.getElementById('grafico').textContent = error.message;
    }
}

// Alterar a visualização não registra corrida nem reclassifica resultados de Westgard.
levelSelect.addEventListener('change', async () => {
    const series = displayedSeries;
    if (!series) return;
    const controls = [equipmentFilter, lotFilter, analyteFilter, levelSelect];
    controls.forEach(control => { control.disabled = true; });
    try {
        const result = await api(`series/${series.id}/nivel`, {nivel_visual: Number(levelSelect.value)});
        series.nivel_visual = result.nivel_visual;
        chart.destroy();
        draw(series);
    } catch (error) {
        levelSelect.value = String(series.nivel_visual);
        message(error.message);
    } finally {
        controls.forEach(control => { control.disabled = false; });
    }
});

async function loadMetrics() {
    const totals = await api('resumo');
    const metrics = [totals.equipamentos, totals.hoje.Aceito || 0, totals.hoje.Alerta || 0, totals.hoje.Rejeitado || 0];
    document.querySelectorAll('[data-metrica]').forEach((node, index) => { node.textContent = metrics[index]; });
}

async function loadRecentRuns() {
    const runs = await api('corridas');
    renderRuns(document.querySelector('main > section:nth-child(4) tbody'), runs.slice(0, 10));
    const alerts = document.querySelector('main > section:nth-child(3) ul'); alerts.replaceChildren();
    const irregular = runs.filter(run => run.status !== 'Aceito' || run.fora_bula).slice(0, 5);
    for (const run of irregular) {
        const item = element('li'), dot = element('div'), content = element('div');
        if (run.status === 'Rejeitado') item.classList.add('alerta-rejeitado');
        const link = element('a', `${run.equipamento} · ${run.analito} · ${run.lote}`);
        link.href = `index.html?serie=${run.serie_id}`;
        content.append(link, element('p', `${run.status} · ${run.regras.join(', ')}${run.fora_bula ? ' · Fora da bula' : ''}`));
        item.append(dot, content); alerts.append(item);
    }
    if (!irregular.length) alerts.append(element('li', 'Nenhum alerta registrado.'));
}

function fillFilter(select, rows, key, label, preferred) {
    const options = new Map(rows.map(row => [String(row[key]), row[label]]));
    select.replaceChildren(...Array.from(options, ([id, name]) => new Option(name, id)));
    if (options.has(String(preferred))) select.value = String(preferred);
    select.disabled = !options.size;
}

async function loadSeries() {
    const series = await api('series');
    if (!series.length) {
        document.getElementById('grafico').textContent = 'Registre a primeira corrida para gerar um gráfico de Levey-Jennings.';
        return;
    }
    const requested = new URLSearchParams(location.search).get('serie');
    const initial = series.find(row => String(row.id) === requested) || series[0];
    fillFilter(equipmentFilter, series, 'equipamento_id', 'equipamento', initial.equipamento_id);

    // Só oferece lotes e analitos que têm gráfico no equipamento selecionado.
    function selectSeries(lotId, analyteId) {
        const equipment = series.filter(row => String(row.equipamento_id) === equipmentFilter.value);
        fillFilter(lotFilter, equipment, 'id_lote', 'lote', lotId);
        const lots = equipment.filter(row => String(row.id_lote) === lotFilter.value);
        fillFilter(analyteFilter, lots, 'id_analito', 'analito', analyteId);
        const selected = lots.find(row => String(row.id_analito) === analyteFilter.value);
        return showSelected(selected.id);
    }
    for (const filter of [equipmentFilter, lotFilter, analyteFilter]) {
        filter.addEventListener('change', () => selectSeries(lotFilter.value, analyteFilter.value));
    }
    await selectSeries(initial.id_lote, initial.id_analito);
}
document.querySelector('input[type="button"]').addEventListener('click', () => { location.href = 'registrarCorridas.html'; });
// Falhas nos indicadores ou no histórico não bloqueiam uma série disponível.
async function start() {
    await sessionRequired();
    await Promise.all([
        loadSeries(),
        loadMetrics().catch(error => message(error.message)),
        loadRecentRuns().catch(error => message(error.message))
    ]);
}
start().catch(error => {
    for (const filter of [equipmentFilter, lotFilter, analyteFilter]) filter.disabled = true;
    document.getElementById('grafico').textContent = error.message;
});
