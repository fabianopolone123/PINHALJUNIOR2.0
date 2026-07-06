/* =========================================================
   Financeiro geral: abas (Resumo/Extrato/Custos), filtro do
   extrato por fonte + busca, confirmação de exclusão.
   JS puro.
   ========================================================= */
(function () {
    "use strict";

    var abas = document.querySelectorAll(".fin-aba");
    var paineis = document.querySelectorAll(".fin-painel");
    function ativar(nome) {
        Array.prototype.forEach.call(abas, function (a) { a.classList.toggle("ativa", a.dataset.aba === nome); });
        Array.prototype.forEach.call(paineis, function (p) { p.hidden = p.dataset.painel !== nome; });
        try {
            var url = new URL(window.location.href);
            url.searchParams.set("aba", nome);
            window.history.replaceState({}, "", url);
        } catch (e) { /* ignora */ }
    }
    Array.prototype.forEach.call(abas, function (a) {
        a.addEventListener("click", function () { ativar(a.dataset.aba); });
    });
    // Links "ir para aba" (ex.: do resumo para custos).
    Array.prototype.forEach.call(document.querySelectorAll("[data-ir-aba]"), function (l) {
        l.addEventListener("click", function (e) { e.preventDefault(); ativar(l.dataset.irAba); });
    });

    // Extrato: filtro por fonte (chips) + busca.
    var chips = document.getElementById("finChips");
    var busca = document.getElementById("finBusca");
    var extrato = document.getElementById("finExtrato");
    var vazio = document.querySelector(".fin-extrato-vazio");
    var fonteSel = "";
    function normal(s) {
        return (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    }
    function filtrar() {
        if (!extrato) return;
        var q = normal(busca ? busca.value.trim() : "");
        var achou = 0;
        Array.prototype.forEach.call(extrato.querySelectorAll(".fin-lanc"), function (l) {
            var okFonte = !fonteSel || l.dataset.fonte === fonteSel;
            var okBusca = !q || normal(l.dataset.busca).indexOf(q) !== -1;
            var ok = okFonte && okBusca;
            l.hidden = !ok;
            if (ok) achou++;
        });
        if (vazio) vazio.hidden = achou !== 0;
    }
    if (chips) {
        chips.addEventListener("click", function (e) {
            var chip = e.target.closest(".fin-chip");
            if (!chip) return;
            fonteSel = chip.dataset.fonte || "";
            Array.prototype.forEach.call(chips.querySelectorAll(".fin-chip"), function (c) {
                c.classList.toggle("ativa", c === chip);
            });
            filtrar();
        });
    }
    if (busca) busca.addEventListener("input", filtrar);

    // Confirmação de exclusão de custo.
    document.addEventListener("submit", function (e) {
        var f = e.target;
        if (f && f.dataset && f.dataset.confirmar && !window.confirm(f.dataset.confirmar)) {
            e.preventDefault();
        }
    });
})();
