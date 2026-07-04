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
    // Clique no fundo (fora da caixa) fecha.
    modal.addEventListener("click", function (e) {
        if (e.target === modal) fecharModal();
    });
    // Esc fecha o modal.
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && !modal.hidden) fecharModal();
    });
})();
