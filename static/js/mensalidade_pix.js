/* =========================================================
   Mensalidades: cobrar meses em aberto via Pix. Abre um modal
   com os meses em aberto do aventureiro (checkbox), soma o
   total ao vivo e envia para gerar a cobrança. JS puro.
   ========================================================= */
(function () {
    "use strict";

    var modal = document.getElementById("modalCobrarPix");
    if (!modal) return;

    var lista = document.getElementById("cobrarLista");
    var totalEl = document.getElementById("cobrarTotal");
    var sub = document.getElementById("cobrarSub");
    var submit = document.getElementById("cobrarSubmit");

    function moeda(v) {
        return "R$ " + v.toFixed(2).replace(".", ",").replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    }

    function recalcular() {
        var total = 0;
        Array.prototype.forEach.call(
            lista.querySelectorAll("input[type=checkbox]:checked"),
            function (c) { total += parseFloat(c.dataset.valor) || 0; }
        );
        totalEl.textContent = moeda(total);
        submit.disabled = total <= 0;
    }

    function abrir(btn) {
        var card = btn.closest(".mens-av");
        if (!card) return;
        // Meses em aberto = status "aberta" e não isentos.
        var abertos = Array.prototype.filter.call(
            card.querySelectorAll(".mens-mes[data-status=aberta]"),
            function (m) { return !m.classList.contains("isenta"); }
        );
        lista.innerHTML = "";
        abertos.forEach(function (m) {
            var id = m.dataset.mens;
            var nome = m.dataset.nome || "";
            var valor = parseFloat(m.dataset.valor) || 0;
            var label = document.createElement("label");
            label.className = "mens-cobrar-item";
            label.innerHTML =
                '<input type="checkbox" name="mensalidade_ids" value="' + id +
                '" data-valor="' + valor.toFixed(2) + '" checked> ' +
                '<span class="mens-cobrar-nome">' + nome + '</span>' +
                '<span class="mens-cobrar-valor">' + moeda(valor) + '</span>';
            lista.appendChild(label);
        });
        sub.textContent = btn.dataset.av ? ("Aventureiro: " + btn.dataset.av) : "";
        recalcular();
        modal.hidden = false;
    }

    function fechar() { modal.hidden = true; }

    document.addEventListener("click", function (e) {
        var btn = e.target.closest(".mens-cobrar-btn");
        if (btn) abrir(btn);
    });
    lista.addEventListener("change", recalcular);
    Array.prototype.forEach.call(modal.querySelectorAll("[data-fechar]"), function (el) {
        el.addEventListener("click", fechar);
    });
    // Fecha só se o clique começou E terminou no fundo (não fecha ao arrastar).
    var fundoDown = false;
    modal.addEventListener("mousedown", function (e) { fundoDown = e.target === modal; });
    modal.addEventListener("click", function (e) {
        if (e.target === modal && fundoDown) fechar();
        fundoDown = false;
    });
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && !modal.hidden) fechar();
    });
})();
