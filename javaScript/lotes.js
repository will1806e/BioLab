import {api, sessionRequired, bindForm, element, message} from './app.js';

const overlay = document.querySelector('.fundo-voltar');
const lotPanel = document.querySelector('.novo-lote');
const analytePanel = document.getElementById('gerenciar-analitos');
const deletePanel = document.querySelector('.deletar-lote');
const lotForm = document.getElementById('form-lote');
const analyteForm = document.getElementById('form-analito');
let lots = [], analytes = [], editing = null, pendingDelete = null, returnPanel = null, opener = null;

// Controla explicitamente qual janela está aberta, substituindo as alternâncias
// antigas que podiam deixar o fundo visível sem conteúdo ou fechar a janela errada.
function show(panel) {
    overlay.classList.remove('escondido');
    [lotPanel, analytePanel, deletePanel].forEach(node => {
        node.classList.toggle('escondido', node !== panel);
        node.setAttribute('role', 'dialog'); node.setAttribute('aria-modal', 'true');
        node.setAttribute('aria-label', node.querySelector('h3')?.textContent || 'Confirmar exclusão');
    });
    panel.querySelector('input, button, .icon-fechar')?.focus();
}
function close() {
    overlay.classList.add('escondido');
    [lotPanel, analytePanel, deletePanel].forEach(node => node.classList.add('escondido'));
    pendingDelete = null; opener?.focus();
}
function fillCheckboxes(selected = []) {
    const host = document.querySelector('.check-amostras'); host.replaceChildren();
    analytes.forEach(item => {
        const row = element('div'), input = element('input'), label = element('label', item.nome, 'check-label');
        input.type = 'checkbox'; input.name = 'analitos'; input.value = item.id; input.id = `analito-${item.id}`;
        input.checked = selected.includes(item.id); label.htmlFor = input.id;
        row.append(input, label); host.append(row);
    });
    if (!analytes.length) host.append(element('p', 'Cadastre os analitos em Gerenciar amostras.'));
    const list = document.getElementById('analitos-opcoes'); list.replaceChildren();
    analytes.forEach(item => list.append(new Option(item.nome, item.nome)));
}
function editLot(lot = null) {
    opener = document.activeElement; editing = lot?.id ?? null; lotForm.reset();
    lotPanel.querySelector('h3').textContent = lot ? 'Editar Lote' : 'Adicionar Lotes';
    lotForm.querySelector('[type=submit]').value = lot ? 'Editar' : 'Adicionar';
    lotForm.lote.value = lot?.codigo || ''; lotForm.validade.value = lot?.data_validade || '';
    lotForm.fabricante.value = lot?.fabricante || '';
    fillCheckboxes(lot?.analitos.map(item => item.id) || []); show(lotPanel);
}
function confirmDelete(kind, item, back) {
    returnPanel = back;
    pendingDelete = {kind, id: item.id};
    deletePanel.querySelector('p').textContent = `Excluir ${kind === 'lotes' ? 'o lote' : 'o analito'} “${item.codigo || item.nome}”? A exclusão será bloqueada se houver vínculos protegidos.`;
    show(deletePanel);
}
function action(label, image, handler) {
    const button = element('button'); button.type = 'button'; button.setAttribute('aria-label', label); button.title = label;
    const icon = element('img'); icon.src = `../img/${image}.png`; icon.alt = ''; icon.width = 18; icon.height = 18;
    button.append(icon); button.addEventListener('click', handler); return button;
}
async function load() {
    [lots, analytes] = await Promise.all([api('lotes'), api('analitos')]);
    const body = document.querySelector('tbody'); body.replaceChildren();
    for (const lot of lots) {
        const row = element('tr');
        row.append(element('td', lot.codigo), element('td', lot.data_validade ? lot.data_validade.split('-').reverse().join('/') : 'Validade pendente'), element('td', lot.fabricante || '—'));
        const actions = element('td');
        actions.append(action(`Editar ${lot.codigo}`, 'edit', () => editLot(lot)), document.createTextNode(' '),
            action(`Excluir ${lot.codigo}`, 'delete', () => { opener = document.activeElement; confirmDelete('lotes', lot, null); }));
        row.append(actions); body.append(row);
    }
    if (!lots.length) {
        const row = element('tr'), cell = element('td', 'Nenhum lote cadastrado.'); cell.colSpan = 4; row.append(cell); body.append(row);
    }
}
async function start() {
    await sessionRequired(); await load();
    document.getElementById('novolote').addEventListener('click', () => editLot());
    document.getElementById('add-amostra').addEventListener('click', () => show(analytePanel));
    document.querySelectorAll('.icon-fechar').forEach(icon => {
        icon.tabIndex = 0; icon.setAttribute('role', 'button');
        const back = () => { if (icon.closest('section') === analytePanel) show(lotPanel); else close(); };
        icon.addEventListener('click', back);
        icon.addEventListener('keydown', event => { if (['Enter', ' '].includes(event.key)) back(); });
    });
    document.addEventListener('keydown', event => { if (event.key === 'Escape') close(); });
    bindForm(lotForm, async values => {
        await api(editing === null ? 'lotes' : `lotes/${editing}/editar`, {
            codigo: values.get('lote'), data_validade: values.get('validade'), fabricante: values.get('fabricante'),
            analitos: values.getAll('analitos').map(Number)
        });
        close(); await load(); message('Lote salvo.');
    });
    bindForm(analyteForm, async values => {
        const selected = [...lotForm.querySelectorAll('[name="analitos"]:checked')].map(input => Number(input.value));
        const added = await api('analitos', {nome: values.get('analito')});
        await load(); fillCheckboxes([...selected, added.id]); analyteForm.reset(); message('Analito cadastrado.');
    });
    document.getElementById('botao-deletar').addEventListener('click', () => {
        const name = analyteForm.analito.value.trim().toLocaleLowerCase('pt-BR');
        const item = analytes.find(item => item.nome.toLocaleLowerCase('pt-BR') === name);
        if (!item) { message('Selecione um analito cadastrado pelo nome.'); return; }
        confirmDelete('analitos', item, analytePanel);
    });
    document.getElementById('botao-cancelar').addEventListener('click', () => { pendingDelete = null; if (returnPanel) show(returnPanel); else close(); });
    document.getElementById('confirmar-exclusao').addEventListener('click', async event => {
        if (!pendingDelete) return;
        event.currentTarget.disabled = true;
        try {
            const result = await api(`${pendingDelete.kind}/${pendingDelete.id}/excluir`, {});
            const selected = [...lotForm.querySelectorAll('[name="analitos"]:checked')].map(input => Number(input.value));
            await load(); fillCheckboxes(selected); pendingDelete = null;
            if (returnPanel) show(returnPanel); else close();
            message(result.message);
        } catch (error) { message(error.message); }
        finally { document.getElementById('confirmar-exclusao').disabled = false; }
    });
}
start().catch(error => message(error.message));
