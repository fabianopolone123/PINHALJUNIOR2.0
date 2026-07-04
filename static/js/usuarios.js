/* =========================================================
   Tela "Usuários" — pesquisa inteligente em tempo real.
   Filtra os cards de responsáveis e o resumo de aventureiros
   (nome, papel, aventureiro, idade, vínculos), ignorando
   maiúsculas/minúsculas e acentos. JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    var input = document.getElementById("pesquisaUsuarios");
    if (!input) return;

    function normalizar(texto) {
        return (texto || "")
            .normalize("NFD")
            .replace(/[̀-ͯ]/g, "") // remove acentos (diacríticos)
            .toLowerCase()
            .replace(/\s+/g, " ")
            .trim();
    }

    // Pré-calcula o texto pesquisável de cada card (uma vez).
    var itens = Array.prototype.slice.call(document.querySelectorAll(".busca-item"));
    itens.forEach(function (el) {
        el.dataset.busca = normalizar(el.textContent);
    });

    var listaResp = document.getElementById("listaResponsaveis");
    var listaAv = document.getElementById("listaAventureiros");
    var semResp = document.getElementById("semRespResultado");
    var semAv = document.getElementById("semAvResultado");

    function filtrarSecao(container, mensagem) {
        if (!container) return;
        var cards = container.querySelectorAll(".busca-item");
        var visiveis = 0;
        cards.forEach(function (el) {
            var ok = !termo || el.dataset.busca.indexOf(termo) !== -1;
            el.hidden = !ok;
            if (ok) visiveis++;
        });
        if (mensagem) mensagem.hidden = visiveis !== 0;
    }

    var termo = "";
    function aplicar() {
        termo = normalizar(input.value);
        filtrarSecao(listaResp, semResp);
        filtrarSecao(listaAv, semAv);
    }

    input.addEventListener("input", aplicar);
    // Esc limpa a pesquisa.
    input.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            input.value = "";
            aplicar();
        }
    });
})();

/* =========================================================
   Modal de dados completos: ao clicar num card (.clicavel),
   abre uma janela suspensa com TODOS os dados da pessoa.
   O conteúdo vem do #detalhesFonte (renderizado no servidor);
   fecha no X, ao clicar fora e com Esc. JS puro.
   ========================================================= */
(function () {
    "use strict";

    var modal = document.getElementById("modalDados");
    var corpo = document.getElementById("modalCorpo");
    var titulo = document.getElementById("modalTitulo");
    var fechar = document.getElementById("modalFechar");
    var fonte = document.getElementById("detalhesFonte");
    if (!modal || !corpo || !titulo || !fechar || !fonte) return;

    function abrir(id) {
        var origem = document.getElementById("detalhe-" + id);
        if (!origem) return;
        corpo.innerHTML = origem.innerHTML;
        titulo.textContent = origem.getAttribute("data-titulo") || "Dados";
        // No modal, todas as seções aparecem já expandidas.
        Array.prototype.forEach.call(
            corpo.querySelectorAll("details"),
            function (d) { d.open = true; }
        );
        corpo.scrollTop = 0;
        modal.hidden = false;
        document.body.classList.add("modal-aberto");
        fechar.focus();
    }

    function fecharModal() {
        modal.hidden = true;
        corpo.innerHTML = "";
        document.body.classList.remove("modal-aberto");
    }

    // Abre ao clicar num card marcado como clicável.
    document.addEventListener("click", function (e) {
        var alvo = e.target;
        var card = alvo && alvo.closest ? alvo.closest(".clicavel[data-modal]") : null;
        if (card) {
            abrir(card.getAttribute("data-modal"));
        }
    });

    fechar.addEventListener("click", fecharModal);
    // Clique no fundo (fora da caixa) fecha.
    modal.addEventListener("click", function (e) {
        if (e.target === modal) fecharModal();
    });
    // Esc fecha o modal.
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && !modal.hidden) fecharModal();
    });
})();
