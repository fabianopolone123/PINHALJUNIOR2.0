/* =========================================================
   Lojinha: total ao vivo conforme as quantidades.
   Funciona na página da loja e na seção de lojinha da inscrição
   (basta ter campos .loja-qtd e um #lojaTotal na página).
   JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    var inputs = Array.prototype.slice.call(document.querySelectorAll(".loja-qtd"));
    var totalEl = document.getElementById("lojaTotal");
    if (!inputs.length || !totalEl) return;

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
        totalEl.textContent = moeda(total);
    }

    inputs.forEach(function (inp) {
        inp.addEventListener("input", recalcular);
        inp.addEventListener("change", recalcular);
    });
    recalcular();
})();
