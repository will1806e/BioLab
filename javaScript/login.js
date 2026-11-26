import {api, bindForm} from './app.js';

// Autentica no servidor; a senha nunca fica no armazenamento do navegador.
bindForm(document.querySelector('form'), async data => {
    await api('login', {nome: data.get('user'), senha: data.get('password')});
    location.href = 'index.html';
});
