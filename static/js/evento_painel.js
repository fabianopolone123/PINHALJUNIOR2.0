/* =========================================================
   Painel do evento complexo:
   - troca de abas (Resumo, Inscrições, Lojinha, Custos, Financeiro);
   - modal de "Adicionar custo".
   JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    // Só as abas com data-aba trocam de seção; as ".painel-aba-acao" são links
    // (abrem páginas próprias, ex.: balcão/operadores) e não entram aqui.
    var abas = Array.prototype.slice.call(document.querySelectorAll(".painel-aba[data-aba]"));
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

    // Sub-abas (abas DENTRO de uma seção; ex.: Inscrições → Lista/Config/Faixas/Formulário).
    // Cada barra é independente e só mexe nas sub-seções da sua própria .painel-secao.
    Array.prototype.slice.call(document.querySelectorAll(".sub-abas")).forEach(function (barra) {
        var escopo = barra.closest(".painel-secao") || document;
        var subAbas = Array.prototype.slice.call(barra.querySelectorAll(".sub-aba"));
        var subSecoes = Array.prototype.slice.call(escopo.querySelectorAll(".sub-secao"));
        barra.addEventListener("click", function (e) {
            var btn = e.target.closest(".sub-aba");
            if (!btn) return;
            var nome = btn.dataset.sub;
            subAbas.forEach(function (a) { a.classList.toggle("ativa", a === btn); });
            subSecoes.forEach(function (s) { s.hidden = s.dataset.subsecao !== nome; });
        });
    });

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
                // Classe (não o atributo hidden): itens com display:flex ignorariam
                // o [hidden], então a lista não sumia. .busca-oculto usa !important.
                el.classList.toggle("busca-oculto", !ok);
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
    ligarBusca("buscaPedidos", ".pedido-busca", "pedidosVazio");

    // Cards de KPI clicáveis (Resumo): abrem uma lista simples abaixo (uma por vez).
    var kpiCards = Array.prototype.slice.call(document.querySelectorAll(".kpi-clicavel"));
    var kpiPainel = document.getElementById("kpiListas");
    if (kpiCards.length && kpiPainel) {
        var kpiListas = Array.prototype.slice.call(kpiPainel.querySelectorAll(".kpi-lista"));
        function abrirKpi(card) {
            var jaAtivo = card.classList.contains("ativo");
            kpiCards.forEach(function (c) {
                c.classList.remove("ativo");
                c.setAttribute("aria-expanded", "false");
            });
            kpiListas.forEach(function (l) { l.hidden = true; });
            if (!jaAtivo) {
                card.classList.add("ativo");
                card.setAttribute("aria-expanded", "true");
                var el = kpiPainel.querySelector(
                    '.kpi-lista[data-lista-alvo="' + card.dataset.lista + '"]'
                );
                if (el) el.hidden = false;
            }
        }
        kpiCards.forEach(function (card) {
            card.addEventListener("click", function () { abrirKpi(card); });
            card.addEventListener("keydown", function (e) {
                if (e.key === "Enter" || e.key === " ") { e.preventDefault(); abrirKpi(card); }
            });
        });
    }

    // ---- Stepper de quantidade ao gerar cupons (1 a 5) ----
    // Ao tentar passar do máximo, mostra o toast padrão do sistema.
    var stepper = document.querySelector(".cupom-qtd-stepper");
    if (stepper) {
        var qtdInput = stepper.querySelector(".cupom-qtd-input");
        var minQ = parseInt(stepper.dataset.min, 10) || 1;
        var maxQ = parseInt(stepper.dataset.max, 10) || 5;
        stepper.addEventListener("click", function (e) {
            var btn = e.target.closest(".cupom-qtd-btn");
            if (!btn || !qtdInput) return;
            var atual = parseInt(qtdInput.value, 10);
            if (isNaN(atual)) atual = minQ;
            var passo = parseInt(btn.dataset.passo, 10) || 0;
            var novo = atual + passo;
            if (novo > maxQ) {
                novo = maxQ;
                if (window.mostrarToast) {
                    window.mostrarToast("No máximo 5 cupons gerados por vez.", "info");
                }
            }
            if (novo < minQ) novo = minQ;
            qtdInput.value = novo;
        });
    }
})();
