// Utilitários compartilhados. Cada HTML importa seu próprio módulo de página.
export async function api(path, data) {
    const response = await fetch(`/api/${path}`, {
        credentials: 'same-origin',
        ...(data === undefined ? {} : {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)
        })
    });
    const mediaType = (response.headers.get('Content-Type') || '').split(';')[0].trim().toLowerCase();
    if (mediaType !== 'application/json' && !mediaType.endsWith('+json')) {
        throw new Error(`A API não retornou JSON (HTTP ${response.status}). Verifique se o servidor da aplicação está em execução.`);
    }
    const payload = await response.json();
    if (!response.ok) {
        if (response.status === 401 && !['login', 'sessao'].includes(path)) location.href = 'login.html';
        throw new Error(payload.error || 'Não foi possível concluir a operação.');
    }
    return payload;
}

// textContent impede que nomes cadastrados sejam interpretados como HTML.
export function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
}

export function message(text) {
    const parent = document.querySelector('[role="dialog"]:not([hidden]):not(.escondido)') || document.querySelector('main');
    let node = document.getElementById('mensagem');
    if (!node) {
        node = element('p'); node.id = 'mensagem'; node.setAttribute('role', 'status');
        parent.append(node);
    }
    if (node.parentElement !== parent) parent.append(node);
    node.textContent = text;
}

export async function sessionRequired() {
    try {
        const user = await api('sessao');
        const header = document.querySelector('body > header > div:nth-child(2)');
        if (header) {
            const exit = header.querySelector('img');
            const button = element('button', 'Sair', 'sair-conta'); button.type = 'button';
            button.addEventListener('click', async () => {
                try { await api('logout', {}); location.href = 'login.html'; }
                catch (error) { message(error.message); }
            });
            header.replaceChildren(document.createTextNode(`${user.cargo} | ${user.nome} `), button);
            if (exit) { button.replaceChildren(exit); button.setAttribute('aria-label', 'Sair da conta'); }
        }
        return user;
    } catch (error) {
        message(error.message);
        if (error.message.includes('Entre na sua conta')) location.href = 'login.html';
        throw error;
    }
}

export const formatNumber = value => new Intl.NumberFormat('pt-BR', {maximumFractionDigits: 6}).format(value);
export const formatDate = value => new Date(value).toLocaleString('pt-BR', {timeZone: 'America/Sao_Paulo'});

export function statusBadge(run) {
    const css = run.status === 'Aceito' ? 'success' : run.status === 'Rejeitado' ? 'danger' : 'alert';
    const badge = element('span', run.status, `status status--${css}`);
    badge.title = run.regras.join(', ') || 'Nenhuma regra violada';
    return badge;
}

export function renderRuns(target, runs, history = false) {
    target.replaceChildren();
    for (const run of runs) {
        const row = element('tr');
        const values = [formatDate(run.criado_em), run.equipamento, history ? run.analito : `${run.analito} · ${run.lote}`];
        if (history) values.push(run.lote);
        values.push(`${formatNumber(run.resultado)} ${run.unidade}`);
        if (history) values.push(run.responsavel, run.cargo);
        values.forEach(value => row.append(element('td', value)));
        const status = element('td'); status.append(statusBadge(run));
        row.append(status); target.append(row);
    }
    if (!runs.length) {
        const row = element('tr'), cell = element('td', 'Nenhuma corrida registrada.');
        cell.colSpan = history ? 8 : 5; row.append(cell); target.append(row);
    }
}

// Centraliza o bloqueio de envio e os erros, evitando duplo clique durante a gravação.
export function bindForm(form, handler) {
    let busy = false;
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (busy) return;
        busy = true;
        const button = form.querySelector('[type="submit"]'); button.disabled = true;
        message('Processando…');
        try { await handler(new FormData(form)); }
        catch (error) { message(error.message); }
        finally { busy = false; button.disabled = false; }
    });
}
