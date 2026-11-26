import {api, sessionRequired, bindForm, message} from './app.js';

const form = document.getElementById('form-corrida');
const fields = {controle: 'controle', alvo: 'valor-alvo', desvio: 'desvio-padrao',
    unidade: 'unidade', limite_min: 'limite-min', limite_max: 'limite-max'};
let series = [], lots = [];
const normalized = value => value.trim().normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

// Parâmetros de uma série já iniciada permanecem imutáveis.
function syncReference() {
    const existing = series.find(item => String(item.equipamento_id) === form.equipamento.value &&
        normalized(item.analito) === normalized(form.analito.value) && normalized(item.lote) === normalized(form.lote.value));
    for (const [key, id] of Object.entries(fields)) {
        const input = document.getElementById(id);
        if (existing) input.value = existing[key] ?? '';
        else if (input.readOnly) input.value = '';
        input.readOnly = Boolean(existing);
    }
    message(existing ? 'Série existente: esta corrida continuará o gráfico com os parâmetros originais.' : 'Nova combinação: informe os parâmetros para criar o gráfico.');
}
// O analito depende do lote; impede selecionar combinações inexistentes.
function updateAnalytes() {
    const lot = lots.find(item => item.codigo === form.lote.value);
    const previous = form.analito.value;
    form.analito.replaceChildren(new Option('Selecione um analito', ''));
    lot?.analitos.forEach(item => form.analito.add(new Option(item.nome, item.nome)));
    if (lot?.analitos.some(item => item.nome === previous)) form.analito.value = previous;
    syncReference();
}
async function start() {
    await sessionRequired();
    const [equipment, savedSeries, savedLots] = await Promise.all([api('equipamentos'), api('series'), api('lotes')]);
    series = savedSeries; lots = savedLots;
    form.equipamento.replaceChildren(new Option('Selecione uma máquina', ''));
    equipment.filter(item => item.ativo).forEach(item => form.equipamento.add(new Option(item.nome, item.id)));
    form.lote.replaceChildren(new Option('Selecione um lote', ''));
    const today = new Intl.DateTimeFormat('en-CA', {timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit'}).format(new Date());
    lots.forEach(item => {
        const unavailable = !item.data_validade || item.data_validade < today;
        const option = new Option(`${item.codigo}${unavailable ? ' (vencido ou sem validade)' : ''}`, item.codigo);
        option.disabled = unavailable; form.lote.add(option);
    });
    form.lote.addEventListener('change', updateAnalytes);
    form.equipamento.addEventListener('change', syncReference);
    form.analito.addEventListener('change', syncReference);
    const available = equipment.some(item => item.ativo) && lots.some(item => item.data_validade >= today && item.analitos.length);
    form.querySelector('[type="submit"]').disabled = !available;
    if (!available) message('Cadastre um equipamento e um lote válido com analitos antes de continuar.');
    bindForm(form, async data => {
        const payload = {equipamento_id: data.get('equipamento'), analito: data.get('analito'), lote: data.get('lote'), resultado: data.get('resultado')};
        for (const [key, id] of Object.entries(fields)) payload[key] = data.get(id);
        const result = await api('corridas', payload);
        location.href = `index.html?serie=${result.serie_id}`;
    });
}
// O novo formulário CSV permanece explicitamente inativo até a definição do formato.
document.getElementById('formcsv').addEventListener('submit', event => event.preventDefault());
start().catch(error => message(error.message));
