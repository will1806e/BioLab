import {api, sessionRequired, renderRuns, message, element} from './app.js';

// O link em Equipamentos limita a consulta à máquina selecionada.
async function start() {
    await sessionRequired();
    const equipment = new URLSearchParams(location.search).get('equipamento');
    const [runs, legacy] = await Promise.all([api('corridas'), api('historico-legado')]);
    const selected = equipment ? runs.filter(run => String(run.equipamento_id) === equipment) : runs;
    renderRuns(document.querySelector('tbody'), selected, true);
    const old = equipment ? legacy.filter(row => String(row.id_equipamento) === equipment) : legacy;
    if (old.length && !selected.length) document.querySelector('tbody').replaceChildren();
    // O legado não contém resultados numéricos: preserva seus dados sem gerar pontos fictícios.
    old.forEach(item => {
        const row = element('tr');
        [item.data_hora || 'Não informada', item.equipamento || '—', item.analito || '—', item.lote || '—',
            'Legado: resultado não registrado', item.responsavel || '—', item.cargo || '—', item.status || '—']
            .forEach(value => row.append(element('td', value)));
        document.querySelector('tbody').append(row);
    });
    if (equipment) message('Histórico filtrado por equipamento. Abra Histórico no menu para ver todos.');
}
start().catch(error => message(error.message));
