/* =========================================================
   Painel do evento complexo:
   - troca de abas (Resumo, Inscrições, Lojinha, Custos, Financeiro);
   - modal de "Adicionar custo".
   JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    var abas = Array.prototype.slice.call(document.querySelectorAll(".painel-aba"));
    var secoes = Array.prototype.slice.call(document.querySelectorAll(".painel-secao"));

    function ativar(nome) {
        abas.forEach(function (a) {
            a.classList.toggle("ativa", a.dataset.aba === nome);
        });
        secoes.forEach(function (s) {
            s.hidden = s.dataset.secao !== nome;
        });
    }

    abas.forEach(function (a) {
        a.addEventListener("click", function () { ativar(a.dataset.aba); });
    });

    // Ativa a aba indicada pela hash da URL (ex.: .../#custos) ao carregar.
    var hashAba = (location.hash || "").replace("#", "");
    if (hashAba && abas.some(function (a) { return a.dataset.aba === hashAba; })) {
        ativar(hashAba);
    }

    // ---- Modal: adicionar custo ----
    var modal = document.getElementById("modalCusto");
    if (!modal) return;
    var abrirBtn = document.getElementById("btnAddCusto");
    var fechar = document.getElementById("modalCustoFechar");
    var cancelar = document.getElementById("modalCustoCancelar");

    function abrir() {
        modal.hidden = false;
        document.body.classList.add("modal-aberto");
    }
    function fecharModal() {
        modal.hidden = true;
        document.body.classList.remove("modal-aberto");
    }

    if (abrirBtn) abrirBtn.addEventListener("click", abrir);
    if (fechar) fechar.addEventListener("click", fecharModal);
    if (cancelar) cancelar.addEventListener("click", fecharModal);
    modal.addEventListener("click", function (e) {
        if (e.target === modal) fecharModal();
    });
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && !modal.hidden) fecharModal();
    });
})();
