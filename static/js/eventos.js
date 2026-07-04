/* =========================================================
   Tela "Eventos" — modal de escolha do tipo de evento.
   Abre ao clicar em "Criar evento"; fecha no X, ao clicar
   fora e com Esc. JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    var modal = document.getElementById("modalTipoEvento");
    if (!modal) return;
    var fechar = document.getElementById("modalTipoFechar");
    var gatilhos = [
        document.getElementById("btnCriarEvento"),
        document.getElementById("btnCriarEventoVazio"),
    ];

    function abrir() {
        modal.hidden = false;
        document.body.classList.add("modal-aberto");
        if (fechar) fechar.focus();
    }

    function fecharModal() {
        modal.hidden = true;
        document.body.classList.remove("modal-aberto");
    }

    gatilhos.forEach(function (b) {
        if (b) b.addEventListener("click", abrir);
    });
    if (fechar) fechar.addEventListener("click", fecharModal);
    // Fecha só se o clique começou E terminou no fundo (não fecha ao arrastar
    // uma seleção de texto de dentro para fora).
    var fundoMousedown = false;
    modal.addEventListener("mousedown", function (e) {
        fundoMousedown = e.target === modal;
    });
    modal.addEventListener("click", function (e) {
        if (e.target === modal && fundoMousedown) fecharModal();
    });
    // Esc fecha o modal.
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && !modal.hidden) fecharModal();
    });
})();

/* =========================================================
   Modal de visualização do evento: ao clicar no CARD (não nos
   botões), abre uma janela suspensa com todos os dados do evento.
   ========================================================= */
(function () {
    "use strict";

    var modal = document.getElementById("modalEvento");
    var corpo = document.getElementById("modalEventoCorpo");
    var titulo = document.getElementById("modalEventoTitulo");
    var fechar = document.getElementById("modalEventoFechar");
    var fonte = document.getElementById("eventosFonte");
    if (!modal || !corpo || !titulo || !fechar || !fonte) return;

    function abrir(id) {
        var origem = document.getElementById("evento-detalhe-" + id);
        if (!origem) return;
        corpo.innerHTML = origem.innerHTML;
        titulo.textContent = origem.getAttribute("data-titulo") || "Evento";
        modal.hidden = false;
        document.body.classList.add("modal-aberto");
        fechar.focus();
    }
    function fecharModal() {
        modal.hidden = true;
        corpo.innerHTML = "";
        document.body.classList.remove("modal-aberto");
    }

    // Clique no card abre o modal — mas cliques em links/botões (Abrir painel,
    // Duplicar) seguem seu comportamento normal.
    document.addEventListener("click", function (e) {
        var alvo = e.target;
        if (!alvo || !alvo.closest) return;
        if (alvo.closest("a, button")) return;
        var card = alvo.closest(".evento-clicavel[data-evento]");
        if (card) abrir(card.getAttribute("data-evento"));
    });

    fechar.addEventListener("click", fecharModal);
    var fundoMousedown = false;
    modal.addEventListener("mousedown", function (e) {
        fundoMousedown = e.target === modal;
    });
    modal.addEventListener("click", function (e) {
        if (e.target === modal && fundoMousedown) fecharModal();
    });
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && !modal.hidden) fecharModal();
    });
})();
