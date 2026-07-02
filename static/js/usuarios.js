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
