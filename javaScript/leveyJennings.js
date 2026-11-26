// O bundle oficial fica no projeto para usar o mesmo Chart.js localmente e na Vercel.
import './vendor/chartjs/chart.umd.js';
import {formatDate, formatNumber} from './app.js';

// O limiar inclui a fronteira. O status Westgard gravado continua no tooltip.
function visualAlert(run, series) {
    const distance = series.nivel_visual * series.desvio;
    return run.resultado <= series.alvo - distance || run.resultado >= series.alvo + distance;
}

export function drawLeveyJennings(canvas, series) {
    const runs = series.corridas;
    const right = runs.length + 1;
    // Mantém o alvo no centro mesmo quando uma corrida ultrapassa ±3 DP.
    let radius = 3 * series.desvio;
    for (const run of runs) radius = Math.max(radius, Math.abs(run.resultado - series.alvo));
    for (const limit of [series.limite_min, series.limite_max]) {
        if (limit != null) radius = Math.max(radius, Math.abs(limit - series.alvo));
    }
    radius *= 1.05;
    // Cada referência tem duas extremidades para atravessar inclusive uma série de um ponto.
    function guide(label, value, color, dash) {
        return {label, data: [{x: 0, y: value}, {x: right, y: value}],
            borderColor: color, borderDash: dash, borderWidth: 1.5, pointRadius: 0,
            pointHoverRadius: 0, pointHitRadius: 0, order: 1};
    }
    const guides = series.limites.map(({sigma, valor}) => guide(
        sigma === 0 ? 'Alvo' : `${sigma > 0 ? '+' : ''}${sigma} DP`, valor,
        ['#265c85', '#648291', '#b37619', '#b73f47'][Math.abs(sigma)], sigma === 0 ? [] : [5, 4]));
    for (const [field, label] of [['limite_min', 'Bula mín.'], ['limite_max', 'Bula máx.']]) {
        if (series[field] != null) guides.push(guide(label, series[field], '#775193', [2, 3]));
    }
    return new globalThis.Chart(canvas, {
        type: 'line',
        data: {datasets: [{
            label: 'Resultado',
            data: runs.map((run, i) => ({x: i + 1, y: run.resultado})),
            borderColor: '#0874b9', borderWidth: 2, pointRadius: 4, pointHoverRadius: 6,
            pointBackgroundColor: runs.map(run => visualAlert(run, series) ? '#bc7013' : '#16845b')
        }, ...guides]},
        options: {
            responsive: true, maintainAspectRatio: false, animation: false, locale: 'pt-BR',
            scales: {
                x: {type: 'linear', min: 0, max: right, title: {display: true, text: 'Corrida'},
                    ticks: {precision: 0, maxTicksLimit: 12, callback: value => value > 0 && value < right ? value : ''}},
                y: {min: series.alvo - radius, max: series.alvo + radius, title: {display: true, text: `Resultado (${series.unidade})`}}
            },
            plugins: {
                legend: {display: false},
                tooltip: {filter: item => item.datasetIndex === 0, callbacks: {
                    title: ([item]) => item ? `Corrida ${item.parsed.x} · ${formatDate(runs[item.dataIndex].criado_em)}` : '',
                    label: item => {
                        const run = runs[item.dataIndex];
                        return [`${formatNumber(run.resultado)} ${series.unidade} · ${visualAlert(run, series) ? 'Alerta visual' : 'Dentro do limiar'}`,
                            `Westgard: ${run.status}`, ...run.regras, ...(run.fora_bula ? ['Fora da bula'] : [])];
                    }
                }}
            }
        }
    });
}
