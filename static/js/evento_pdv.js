/* =========================================================
   PDV / Balcão: total ao vivo, alternância da forma de pagamento
   e cálculo de troco (dinheiro). Cortesia zera o total.
   JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    var form = document.getElementById("pdvForm");
    if (!form) return;
    var inputs = Array.prototype.slice.call(form.querySelectorAll(".loja-qtd"));
    var totalEl = document.getElementById("lojaTotal");
    var dinheiroBox = document.getElementById("pdvDinheiro");
    var recebidoEl = document.getElementById("valor_recebido");
    var trocoEl = document.getElementById("pdvTroco");

    function moeda(v) {
        return "R$ " + v.toLocaleString("pt-BR", {
            minimumFractionDigits: 2, maximumFractionDigits: 2,
        });
    }

    function formaSelecionada() {
        var r = form.querySelector('input[name="forma_pagamento"]:checked');
        return r ? r.value : "";
    }

    function itensTotal() {
        var t = 0;
        inputs.forEach(function (inp) {
            var q = parseInt(inp.value, 10);
            var p = parseFloat(inp.dataset.preco);
            if (!isNaN(q) && q > 0 && !isNaN(p)) t += q * p;
        });
        return t;
    }

    function atualizar() {
        var forma = formaSelecionada();
        var total = (forma === "cortesia") ? 0 : itensTotal();
        if (totalEl) {
            totalEl.textContent = moeda(total) + (forma === "cortesia" ? " (cortesia)" : "");
        }
        var ehDinheiro = forma === "dinheiro";
        if (dinheiroBox) dinheiroBox.style.display = ehDinheiro ? "" : "none";
        if (ehDinheiro && trocoEl && recebidoEl) {
            var rec = parseFloat((recebidoEl.value || "").replace(",", "."));
            if (isNaN(rec)) {
                trocoEl.textContent = moeda(0);
                trocoEl.classList.remove("troco-falta");
            } else if (rec < total) {
                trocoEl.textContent = "faltam " + moeda(total - rec);
                trocoEl.classList.add("troco-falta");
            } else {
                trocoEl.textContent = moeda(rec - total);
                trocoEl.classList.remove("troco-falta");
            }
        }
    }

    inputs.forEach(function (inp) {
        inp.addEventListener("input", atualizar);
        inp.addEventListener("change", atualizar);
    });
    form.querySelectorAll('input[name="forma_pagamento"]').forEach(function (r) {
        r.addEventListener("change", atualizar);
    });
    if (recebidoEl) recebidoEl.addEventListener("input", atualizar);
    atualizar();
})();
