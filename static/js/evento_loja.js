/* =========================================================
   Loja do evento: total ao vivo conforme as quantidades.
   JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    var form = document.getElementById("lojaForm");
    if (!form) return;
    var totalEl = document.getElementById("lojaTotal");
    var inputs = Array.prototype.slice.call(form.querySelectorAll(".loja-qtd"));

    function moeda(v) {
        return "R$ " + v.toLocaleString("pt-BR", {
            minimumFractionDigits: 2, maximumFractionDigits: 2,
        });
    }

    function recalcular() {
        var total = 0;
        inputs.forEach(function (inp) {
            var q = parseInt(inp.value, 10);
            var p = parseFloat(inp.dataset.preco);
            if (!isNaN(q) && q > 0 && !isNaN(p)) total += q * p;
        });
        if (totalEl) totalEl.textContent = moeda(total);
    }

    inputs.forEach(function (inp) {
        inp.addEventListener("input", recalcular);
        inp.addEventListener("change", recalcular);
    });
    recalcular();
})();
