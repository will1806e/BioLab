// Definindo os componentes há variável
const novo_lote = document.querySelector("#novolote")
const fundo_voltar = document.querySelector(".fundo-voltar")
const section_novo_lote = document.querySelector(".novo-lote")
const icon_fechar = document.querySelectorAll(".icon-fechar")
const gerenciar_amostras = document.querySelector("#add-amostra")
const section_gerenciar_analitos = document.querySelector("#gerenciar-analitos")
const botao_deletar = document.querySelector("#botao-deletar")
const section_deletar = document.querySelector(".deletar-lote")
const botao_cancelar = document.querySelector("#botao-cancelar")
const input_analito = document.querySelector("#analito")

//Funções
function mostrarEsconder(item) {
    if(item.classList.contains("escondido")) {
        item.classList.remove("escondido")
    } else {
        item.classList.add("escondido")
    }
}

// Definindo eventos
novo_lote.addEventListener("click", () => {
    mostrarEsconder(fundo_voltar)
    mostrarEsconder(section_novo_lote)
})

icon_fechar.forEach((icon) => {
    icon.addEventListener("click", () => {
        mostrarEsconder(fundo_voltar)
        mostrarEsconder(section_novo_lote)
    })
})

gerenciar_amostras.addEventListener("click", () => {
    mostrarEsconder(section_novo_lote)
    mostrarEsconder(section_gerenciar_analitos) 
})

botao_deletar.addEventListener("click", () => {
    if(input_analito.value.trim() != ""){
        mostrarEsconder(section_deletar)
    
        section_gerenciar_analitos.setAttribute("hidden", "")
    } else {
        alert('O campo "Nome do Analito" está vazio')
    }
})

botao_cancelar.addEventListener("click", () => {
    mostrarEsconder(section_deletar)

    section_gerenciar_analitos.removeAttribute("hidden")
})