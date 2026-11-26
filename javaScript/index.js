import {api, sessionRequired, element, message, formatNumber, formatDate, renderRuns} from './app.js';

const select = document.getElementById('filtro-grafico');
let requestVersion = 0;

// SVG local e responsivo: não depende de bibliotecas ou CDN para desenhar o gráfico.
function svgNode(tag, attributes, text) {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    return node;
}

function draw(series) {
    const host = document.getElementById('grafico'); host.replaceChildren();
    if (!series.corridas.length) { host.append(element('p', 'Esta série ainda não possui resultados.')); return; }
    const runs = series.corridas;
    const width = Math.max(850, runs.length * 35 + 180), height = 370;
    const left = 105, right = width - 110, top = 25, bottom = 290;
    // Coordenadas normalizadas evitam que valores de unidades distintas afetem a escala.
    let min = -3, max = 3;
    runs.forEach(run => { min = Math.min(min, run.z); max = Math.max(max, run.z); });
    min -= .5; max += .5;
    const y = z => bottom - ((z - min) / (max - min)) * (bottom - top);
    const x = index => runs.length === 1 ? (left + right) / 2 : left + index * (right - left) / (runs.length - 1);
    const svg = svgNode('svg', {viewBox: `0 0 ${width} ${height}`, width, height, role: 'img',
        'aria-label': `Gráfico de Levey-Jennings: ${series.equipamento}, ${series.analito}, lote ${series.lote}. Resultados na tabela abaixo.`});
    for (const limit of series.limites) {
        const color = limit.sigma === 0 ? '#0874b9' : Math.abs(limit.sigma) === 3 ? '#c84545' : '#94a9b8';
        svg.append(svgNode('line', {x1: left, x2: right, y1: y(limit.sigma), y2: y(limit.sigma), stroke: color,
            'stroke-dasharray': limit.sigma === 0 ? '0' : '5 5'}));
        svg.append(svgNode('text', {x: left - 8, y: y(limit.sigma) + 4, 'text-anchor': 'end', fill: '#183247', 'font-size': 12}, formatNumber(limit.valor)));
        svg.append(svgNode('text', {x: right + 10, y: y(limit.sigma) + 4, fill: color, 'font-size': 12},
            limit.sigma === 0 ? 'Média alvo' : `${limit.sigma > 0 ? '+' : ''}${limit.sigma} DP`));
    }
    svg.append(svgNode('polyline', {points: runs.map((run, index) => `${x(index)},${y(run.z)}`).join(' '),
        fill: 'none', stroke: '#0874b9', 'stroke-width': 2}));
    runs.forEach((run, index) => {
        const color = run.status === 'Rejeitado' ? '#c84545' : run.status === 'Alerta' ? '#cc7a16' : '#16845b';
        const point = svgNode('circle', {cx: x(index), cy: y(run.z), r: 5, fill: color, tabindex: 0});
        const description = `Corrida ${index + 1} · ${formatDate(run.criado_em)} · ${formatNumber(run.resultado)} ${series.unidade} · ${run.status} · ${run.regras.join(', ') || 'Sem violação'}${run.fora_bula ? ' · Fora da bula' : ''}`;
        point.setAttribute('aria-label', description); point.append(svgNode('title', {}, description)); svg.append(point);
        svg.append(svgNode('text', {x: x(index), y: bottom + 25, 'text-anchor': 'middle', fill: '#647b8d', 'font-size': 12}, String(index + 1)));
    });
    svg.append(svgNode('text', {x: (left + right) / 2, y: height - 15, 'text-anchor': 'middle', fill: '#647b8d', 'font-size': 13},
        `Corridas em ordem de registro · Resultado em ${series.unidade}`));
    host.append(svg);
    const stats = series.estatisticas;
    document.getElementById('grafico-resumo').textContent = `${series.controle} · Lote ${series.lote} · ${stats.n} resultados · Média observada: ${formatNumber(stats.media)} · DP amostral: ${stats.desvio_amostral === null ? 'insuficiente (n < 2)' : formatNumber(stats.desvio_amostral)}. Referências fixas: alvo ${formatNumber(series.alvo)}, DP ${formatNumber(series.desvio)} ${series.unidade}.`;
    renderRuns(document.getElementById('dados-grafico'), runs);
}

// Descarta respostas antigas caso o usuário troque rapidamente de gráfico.
async function showSelected() {
    const version = ++requestVersion;
    document.getElementById('grafico').textContent = 'Carregando gráfico…';
    document.getElementById('grafico-resumo').textContent = '';
    document.getElementById('dados-grafico').replaceChildren();
    try {
        const data = await api(`series/${select.value}`);
        if (version !== requestVersion) return;
        draw(data);
        const url = new URL(location.href); url.searchParams.set('serie', select.value);
        history.replaceState(null, '', url);
    } catch (error) {
        if (version === requestVersion) document.getElementById('grafico').textContent = error.message;
    }
}

async function start() {
    await sessionRequired();
    const [series, runs, totals] = await Promise.all([api('series'), api('corridas'), api('resumo')]);
    const metrics = [totals.equipamentos, totals.hoje.Aceito || 0, totals.hoje.Alerta || 0, totals.hoje.Rejeitado || 0];
    document.querySelectorAll('[data-metrica]').forEach((node, index) => { node.textContent = metrics[index]; });
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
    select.replaceChildren();
    series.forEach(item => select.add(new Option(`${item.equipamento} · ${item.analito} · ${item.lote}`, item.id)));
    if (!series.length) {
        select.add(new Option('Nenhum gráfico registrado', '')); select.disabled = true;
        document.getElementById('grafico').textContent = 'Registre a primeira corrida para gerar um gráfico de Levey-Jennings.';
        return;
    }
    const requested = new URLSearchParams(location.search).get('serie');
    if (series.some(item => String(item.id) === requested)) select.value = requested;
    select.addEventListener('change', showSelected);
    await showSelected();
}
document.querySelector('input[type="button"]').addEventListener('click', () => { location.href = 'registrarCorridas.html'; });
start().catch(error => message(error.message));
