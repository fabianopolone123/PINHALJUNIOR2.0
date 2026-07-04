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

    // Botões que trocam de aba (ex.: "Gerenciar custos →" no Financeiro).
    Array.prototype.slice.call(document.querySelectorAll("[data-aba-ir]"))
        .forEach(function (b) {
            b.addEventListener("click", function () {
                var nome = b.dataset.abaIr;
                if (abas.some(function (a) { return a.dataset.aba === nome; })) {
                    ativar(nome);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                }
            });
        });

    // ---- Modais (adicionar custo, adicionar faixa etária) ----
    // Cada modal fecha só quando o clique começou E terminou no fundo (não fecha
    // ao arrastar uma seleção de texto de dentro para fora).
    function configurarModal(cfg) {
        var modal = document.getElementById(cfg.modal);
        if (!modal) return;
        var abrirBtn = document.getElementById(cfg.abrir);
        var fechar = document.getElementById(cfg.fechar);
        var cancelar = document.getElementById(cfg.cancelar);

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
    }

    configurarModal({
        modal: "modalCusto", abrir: "btnAddCusto",
        fechar: "modalCustoFechar", cancelar: "modalCustoCancelar",
    });
    configurarModal({
        modal: "modalFaixa", abrir: "btnAddFaixa",
        fechar: "modalFaixaFechar", cancelar: "modalFaixaCancelar",
    });
    configurarModal({
        modal: "modalCampo", abrir: "btnAddCampo",
        fechar: "modalCampoFechar", cancelar: "modalCampoCancelar",
    });

    // ---- Campo do formulário: "Opções" só aparece p/ escolha única/múltipla ----
    var tipoSel = document.getElementById("id_campo-tipo");
    var opcoesWrap = document.getElementById("campoOpcoesWrap");
    function alternarOpcoes() {
        if (!tipoSel || !opcoesWrap) return;
        var v = tipoSel.value;
        opcoesWrap.hidden = !(v === "escolha_unica" || v === "escolha_multipla");
    }
    if (tipoSel) {
        tipoSel.addEventListener("change", alternarOpcoes);
        alternarOpcoes();
    }

    // ---- Busca em tempo real (cobertura do clube e lista de inscrições) ----
    function normalizar(t) {
        return (t || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
            .toLowerCase().replace(/\s+/g, " ").trim();
    }
    function ligarBusca(inputId, itemSelector, vazioId) {
        var input = document.getElementById(inputId);
        if (!input) return;
        var itens = Array.prototype.slice.call(document.querySelectorAll(itemSelector));
        itens.forEach(function (el) { el.dataset.busca = normalizar(el.textContent); });
        var vazio = vazioId ? document.getElementById(vazioId) : null;
        function aplicar() {
            var termo = normalizar(input.value);
            var visiveis = 0;
            itens.forEach(function (el) {
                var ok = !termo || el.dataset.busca.indexOf(termo) !== -1;
                el.hidden = !ok;
                if (ok) visiveis++;
            });
            if (vazio) vazio.hidden = visiveis !== 0;
        }
        input.addEventListener("input", aplicar);
        input.addEventListener("keydown", function (e) {
            if (e.key === "Escape") { input.value = ""; aplicar(); }
        });
    }
    ligarBusca("buscaCobertura", ".cob-item", "cobVazio");
    ligarBusca("buscaInscricoes", ".inscricao-busca", "inscricoesVazio");
})();
