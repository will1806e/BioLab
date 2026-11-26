import {api, sessionRequired, element, formatDate, message} from './app.js';

// Lista ocorrências calculadas, incluindo limites de bula em separado de Westgard.
async function start() {
    await sessionRequired();
    const runs = (await api('corridas')).filter(run => run.status !== 'Aceito' || run.fora_bula);
    const section = document.querySelector('main > section'); section.replaceChildren();
    for (const run of runs) {
        const item = element('div');
        item.append(element('h3', `${run.equipamento} · ${run.analito} · ${run.lote}`),
            element('p', `${formatDate(run.criado_em)} — ${run.status} — ${run.regras.join(', ') || 'Sem violação Westgard'}${run.fora_bula ? ' · Fora da bula' : ''}`));
        const link = element('a', 'Ver gráfico'); link.href = `index.html?serie=${run.serie_id}`;
        item.append(link); section.append(item);
    }
}
start().catch(error => message(error.message));
