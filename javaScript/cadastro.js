import {api, bindForm, message} from './app.js';

// Cadastra o usuário e orienta o próximo passo sem simular autenticação.
document.getElementById('password').minLength = 8;
bindForm(document.querySelector('form'), async data => {
    const result = await api('cadastro', {nome: data.get('user'), cpf: data.get('cpf'), senha: data.get('password'), cargo: data.get('cargos')});
    document.querySelector('form').reset();
    message(result.message);
});
