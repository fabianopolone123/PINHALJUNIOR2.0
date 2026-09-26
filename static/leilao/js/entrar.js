/*
 * entrar.js — pequenas ajudas na porta de entrada do leilão.
 *
 * Só máscara e foco. A validação que vale é a do servidor (regra do projeto):
 * isto aqui existe para o dedo no celular errar menos, não para decidir nada.
 */
(function () {
    "use strict";

    function so(valor) { return (valor || "").replace(/\D/g, ""); }

    var tel = document.getElementById("id_whatsapp");
    if (tel) {
        tel.addEventListener("input", function () {
            var d = so(tel.value);
            // "+55 11 98765-4321" (preenchimento automático, colar) tem 13
            // dígitos: o corte em 11 gravava "(55) 11987-6543", um número que
            // não existe (revisão 26/09). Tira o DDI e o 0 de operadora antes.
            if (d.length > 11 && d.slice(0, 2) === "55") d = d.slice(2);
            if (d.length > 11 && d.charAt(0) === "0") d = d.slice(1);
            d = d.slice(0, 11);
            var saida = d;
            if (d.length > 10) saida = "(" + d.slice(0, 2) + ") " + d.slice(2, 7) + "-" + d.slice(7);
            else if (d.length > 6) saida = "(" + d.slice(0, 2) + ") " + d.slice(2, 6) + "-" + d.slice(6);
            else if (d.length > 2) saida = "(" + d.slice(0, 2) + ") " + d.slice(2);
            else if (d.length > 0) saida = "(" + d;
            tel.value = saida;
        });
    }

    // Primeiro campo em foco no computador. No celular NÃO: abrir o teclado
    // sozinho empurra a tela e esconde o formulário antes de a pessoa ler.
    var nome = document.getElementById("id_nome");
    if (nome && window.matchMedia("(min-width: 700px)").matches && !nome.value) {
        nome.focus();
    }
})();
