/*
 * preparacao.js — a tela é a LISTA dos leilões; criar é uma janela suspensa.
 *
 * O formulário vivia aberto no fim da página, ocupando meia tela com campos que
 * se usam uma vez por evento e empurrando para baixo a lista, que é o que se vem
 * ver aqui.
 */
(function () {
    "use strict";

    var overlay = document.getElementById("modalNovoLeilao");
    var botao = document.getElementById("btnNovoLeilao");
    if (!overlay || !botao || !window.ModalLeilao) return;

    var modal = window.ModalLeilao.ligar(overlay);
    botao.addEventListener("click", modal.abrir);

    // O POST com erro volta com o modal JÁ aberto (o servidor manda
    // `abrir_modal`), com o que a pessoa digitou dentro. Fechá-lo aqui faria
    // ela redigitar tudo sem nem ver o que estava errado.
})();
