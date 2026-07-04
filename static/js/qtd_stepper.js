/* =========================================================
   Botões +/- de quantidade (lojinha). Ao clicar, ajusta o
   input .loja-qtd (respeitando min/max) e dispara "input"
   para o total ao vivo recalcular. Delegação no documento.
   ========================================================= */
(function () {
    "use strict";

    document.addEventListener("click", function (e) {
        var btn = e.target.closest(".qtd-btn");
        if (!btn) return;
        var stepper = btn.closest(".qtd-stepper");
        var input = stepper ? stepper.querySelector(".loja-qtd") : null;
        if (!input) return;

        var valor = parseInt(input.value, 10);
        if (isNaN(valor)) valor = 0;
        var min = input.min !== "" ? parseInt(input.min, 10) : 0;
        var maxAttr = input.getAttribute("max");
        var max = (maxAttr !== null && maxAttr !== "") ? parseInt(maxAttr, 10) : null;

        valor += btn.classList.contains("qtd-mais") ? 1 : -1;
        if (valor < min) valor = min;
        if (max !== null && valor > max) valor = max;

        input.value = valor;
        input.dispatchEvent(new Event("input", { bubbles: true }));
    });
})();
