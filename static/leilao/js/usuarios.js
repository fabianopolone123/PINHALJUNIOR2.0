/*
 * usuarios.js — cadastro da equipe (tela do diretor).
 *
 * Duas coisas só, e nenhuma delas é tempo real: confirmar o que é destrutivo e
 * filtrar a lista. Tudo o que muda dado vai por `<form method="post">` normal,
 * com recarga — esta tela não está no pregão, e um POST simples é mais robusto
 * do que `fetch` no meio de um evento com internet ruim.
 */
(function () {
    "use strict";

    document.querySelectorAll("form[data-confirmar]").forEach(function (form) {
        form.addEventListener("submit", function (e) {
            if (!window.confirm(form.dataset.confirmar)) e.preventDefault();
        });
    });

    /* Busca: sem acento e sem caixa, como no caixa.js. */
    var campo = document.getElementById("buscaEquipe");
    if (!campo) return;

    function limpar(texto) {
        return (texto || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
            .toLowerCase().trim();
    }

    campo.addEventListener("input", function () {
        var termo = limpar(campo.value);
        document.querySelectorAll("#listaEquipe .pessoa-conta").forEach(function (li) {
            var alvo = limpar(li.dataset.busca);
            // Esconder com CLASSE, não com `hidden`: elemento `display:flex`
            // ignora o [hidden] do navegador (armadilha já registrada).
            li.classList.toggle("busca-oculto", termo !== "" && alvo.indexOf(termo) === -1);
        });
    });
})();
