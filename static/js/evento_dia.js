/* =========================================================
   Console "Dia do evento" (Fase 5.4):
   - busca em tempo real por responsável, participante ou código.
   As ações de check-in/entrega chegam na 5.4b.
   JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    function normalizar(t) {
        return (t || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
            .toLowerCase().replace(/\s+/g, " ").trim();
    }

    var input = document.getElementById("buscaDia");
    if (!input) return;
    var itens = Array.prototype.slice.call(document.querySelectorAll(".dia-busca"));
    itens.forEach(function (el) { el.dataset.busca = normalizar(el.textContent); });
    var vazio = document.getElementById("diaVazio");

    function aplicar() {
        var termo = normalizar(input.value);
        var visiveis = 0;
        itens.forEach(function (el) {
            var ok = !termo || el.dataset.busca.indexOf(termo) !== -1;
            el.classList.toggle("busca-oculto", !ok);
            if (ok) visiveis++;
        });
        if (vazio) vazio.hidden = visiveis !== 0;
    }
    input.addEventListener("input", aplicar);
    input.addEventListener("keydown", function (e) {
        if (e.key === "Escape") { input.value = ""; aplicar(); }
    });
})();
