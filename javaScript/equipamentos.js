import {api, sessionRequired, bindForm, element, message} from './app.js';

const overlay = document.querySelector('.fundo-voltar');
const createPanel = document.querySelector('.novo-equipamento');
const infoPanel = document.getElementById('equipamentos-info');
let opener;

// Reaproveita as janelas novas do repositório, sem substituir seu layout.
function show(panel) {
    opener = document.activeElement;
    overlay.hidden = false;
    [createPanel, infoPanel].forEach(node => {
        node.hidden = node !== panel;
        node.setAttribute('role', 'dialog'); node.setAttribute('aria-modal', 'true');
        node.setAttribute('aria-label', node.querySelector('h3').textContent);
    });
    panel.querySelector('input, .icon-fechar')?.focus();
}
function close() {
    overlay.hidden = true; createPanel.hidden = true; infoPanel.hidden = true;
    opener?.focus();
}
document.getElementById('abrir-equipamento').addEventListener('click', () => show(createPanel));
document.querySelectorAll('.icon-fechar').forEach(icon => {
    icon.tabIndex = 0; icon.setAttribute('role', 'button');
    icon.addEventListener('click', close);
    icon.addEventListener('keydown', event => { if (['Enter', ' '].includes(event.key)) close(); });
});
document.addEventListener('keydown', event => { if (event.key === 'Escape') close(); });

async function load() {
    document.querySelectorAll('main > article').forEach(node => node.remove());
    const equipment = await api('equipamentos');
    for (const item of equipment) {
        const card = element('article'), info = element('div'), actions = element('div');
        info.append(element('p', item.ativo ? 'ATIVO' : 'INATIVO'), element('h3', item.nome),
            element('p', `${item.modelo || 'Modelo não informado'} · ${item.analitos} analitos monitorados`));
        const link = element('a', 'Ver histórico'); link.href = `historico.html?equipamento=${item.id}`;
        const details = element('button', 'Informações'); details.type = 'button';
        details.addEventListener('click', () => {
            const values = [item.nome, item.modelo, item.numero_serie, item.observacoes];
            infoPanel.querySelectorAll('#infos span').forEach((node, index) => { node.textContent = values[index] || 'Não informado'; });
            show(infoPanel);
        });
        actions.append(details, document.createTextNode(' '), link); card.append(info, actions);
        document.querySelector('main').append(card);
    }
    if (!equipment.length) message('Cadastre o primeiro equipamento para registrar corridas.');
}
async function start() {
    await sessionRequired();
    bindForm(document.getElementById('novo-equipamento'), async data => {
        await api('equipamentos', {nome: data.get('nome-equipamento'), modelo: data.get('modelo'),
            numero_serie: data.get('serie'), observacoes: data.get('observacoes')});
        document.getElementById('novo-equipamento').reset(); close();
        await load(); message('Equipamento cadastrado.');
    });
    await load();
}
start().catch(error => message(error.message));
