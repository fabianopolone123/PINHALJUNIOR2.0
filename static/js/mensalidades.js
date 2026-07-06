/* =========================================================
   Mensalidades: marcar pago/desfazer (fetch/JSON), busca e
   filtro "só quem deve", e confirmação de gerar cobranças.
   JS puro.
   ========================================================= */
(function () {
    "use strict";

    function csrf() {
        var m = document.cookie.match(/(?:^|;\s*)pinhaljunior2_csrftoken=([^;]+)/);
        if (m) return m[1];
        var i = document.querySelector('input[name=csrfmiddlewaretoken]');
        return i ? i.value : "";
    }

    var FORMAS = { dinheiro: "Dinheiro", pix: "Pix", cartao: "Cartão", online: "Online" };

    // URL respeitando o prefixo do app (FORCE_SCRIPT_NAME no VPS). Vem do template
    // via {% url %}; o caminho fixo é só um fallback para o uso local.
    var listaEl = document.getElementById("mensLista");
    var PAGAR_URL = (listaEl && listaEl.dataset.pagarUrl) || "/mensalidades/pagar/";

    // Abas Resumo / Aventureiros.
    var abas = document.querySelectorAll(".mens-aba");
    var paineis = document.querySelectorAll(".mens-painel");
    Array.prototype.forEach.call(abas, function (a) {
        a.addEventListener("click", function () {
            var nome = a.dataset.aba;
            Array.prototype.forEach.call(abas, function (x) { x.classList.toggle("ativa", x === a); });
            Array.prototype.forEach.call(paineis, function (p) { p.hidden = p.dataset.painel !== nome; });
            try {
                var url = new URL(window.location.href);
                url.searchParams.set("aba", nome);
                window.history.replaceState({}, "", url);
            } catch (e) { /* ignora */ }
        });
    });

    // Confirmação (gerar cobranças).
    document.addEventListener("submit", function (e) {
        var f = e.target;
        if (f && f.dataset && f.dataset.confirmar && !window.confirm(f.dataset.confirmar)) {
            e.preventDefault();
        }
    });

    // Marcar pago / desfazer.
    document.addEventListener("click", function (e) {
        var btn = e.target.closest(".mens-pagar-btn");
        if (!btn) return;
        var mes = btn.closest(".mens-mes");
        var pagar = btn.dataset.pagar === "1" ? "1" : "0";
        var forma = "dinheiro";
        if (pagar === "1") {
            var sel = mes.querySelector(".mens-forma");
            if (sel) forma = sel.value;
        }
        btn.disabled = true;
        fetch(PAGAR_URL, {
            method: "POST",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": csrf(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: "mensalidade_id=" + mes.dataset.mens + "&pagar=" + pagar + "&forma=" + forma,
        })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (!d || !d.ok) throw new Error();
                mes.dataset.status = d.status;
                if (d.status === "paga") {
                    var selo = mes.querySelector(".mens-quando-paga .mens-selo");
                    if (selo) selo.textContent = "✅ Pago · " + (FORMAS[forma] || forma);
                }
                var card = btn.closest(".mens-av");
                if (card) {
                    var p = card.querySelector("[data-resumo-pagas]");
                    var t = card.querySelector("[data-resumo-total]");
                    var a = card.querySelector("[data-resumo-aberto]");
                    if (p) p.textContent = d.pagas;
                    if (t) t.textContent = d.total;
                    if (a) a.textContent = d.aberto_fmt;
                    card.dataset.deve = d.aberto_fmt === "R$ 0,00" ? "0" : "1";
                }
                btn.disabled = false;
            })
            .catch(function () {
                if (window.mostrarToast) window.mostrarToast("Não foi possível atualizar.", "error");
                btn.disabled = false;
            });
    });

    // Modais acionados por botão (valores padrão / reajustar), com fechamento seguro.
    function ligarModalBotao(modalId, btnId) {
        var modal = document.getElementById(modalId);
        var btn = document.getElementById(btnId);
        if (!modal || !btn) return;
        function fechar() { modal.hidden = true; }
        btn.addEventListener("click", function () { modal.hidden = false; });
        Array.prototype.forEach.call(modal.querySelectorAll("[data-fechar]"), function (el) {
            el.addEventListener("click", fechar);
        });
        var fundoDown = false;
        modal.addEventListener("mousedown", function (e) { fundoDown = e.target === modal; });
        modal.addEventListener("click", function (e) {
            if (e.target === modal && fundoDown) fechar();
            fundoDown = false;
        });
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape" && !modal.hidden) fechar();
        });
    }
    ligarModalBotao("modalValores", "btnValores");
    ligarModalBotao("modalReajustar", "btnReajustar");

    // Modal de edição por mês (desconto % / isenção, com valor ao vivo).
    function moeda(v) {
        return "R$ " + v.toFixed(2).replace(".", ",").replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    }
    var modal = document.getElementById("modalEditar");
    if (modal) {
        var fId = document.getElementById("editarId");
        var fPct = document.getElementById("editarPct");
        var fIsento = document.getElementById("editarIsento");
        var fPreview = document.getElementById("editarPreview");
        var fBase = document.getElementById("editarBase");
        var sub = document.getElementById("modalEditarSub");
        var baseAtual = 0;

        function atualizarPreview() {
            var pct = parseInt(fPct.value, 10) || 0;
            if (pct < 0) pct = 0; if (pct > 100) pct = 100;
            var final = fIsento.checked ? 0 : baseAtual * (1 - pct / 100);
            fPreview.textContent = moeda(final);
        }
        function abrir(btn) {
            baseAtual = parseFloat(btn.dataset.base) || 0;
            var valor = parseFloat(btn.dataset.valor) || 0;
            var pct = baseAtual > 0 ? Math.round((1 - valor / baseAtual) * 100) : 0;
            if (pct < 0) pct = 0; if (pct > 100) pct = 100;
            fId.value = btn.dataset.mens;
            fPct.value = pct;
            fIsento.checked = btn.dataset.isento === "1";
            fPct.disabled = fIsento.checked;
            if (sub) sub.textContent = btn.dataset.label || "";
            if (fBase) fBase.textContent = "(valor cheio: " + moeda(baseAtual) + ")";
            atualizarPreview();
            modal.hidden = false;
        }
        function fechar() { modal.hidden = true; }
        document.addEventListener("click", function (e) {
            var btn = e.target.closest(".mens-editar-btn");
            if (btn) abrir(btn);
        });
        fPct.addEventListener("input", atualizarPreview);
        fIsento.addEventListener("change", function () {
            fPct.disabled = fIsento.checked;
            atualizarPreview();
        });
        document.getElementById("modalEditarFechar").addEventListener("click", fechar);
        document.getElementById("modalEditarCancelar").addEventListener("click", fechar);
        // Fecha só se o clique começou E terminou no fundo (arrastar seleção de
        // dentro para fora não fecha).
        var fundoMousedown = false;
        modal.addEventListener("mousedown", function (e) { fundoMousedown = e.target === modal; });
        modal.addEventListener("click", function (e) {
            if (e.target === modal && fundoMousedown) fechar();
            fundoMousedown = false;
        });
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape" && !modal.hidden) fechar();
        });
    }

    // Busca + "só quem deve".
    var busca = document.getElementById("mensBusca");
    var soDeve = document.getElementById("mensSoDeve");
    var lista = document.getElementById("mensLista");
    var vazio = document.querySelector(".mens-busca-vazio");
    function normal(s) {
        return (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    }
    function filtrar() {
        if (!lista) return;
        var q = normal(busca ? busca.value.trim() : "");
        var deve = soDeve && soDeve.checked;
        var achou = 0;
        Array.prototype.forEach.call(lista.querySelectorAll(".mens-av"), function (c) {
            var ok = (!q || normal(c.dataset.busca).indexOf(q) !== -1) &&
                     (!deve || c.dataset.deve === "1");
            c.hidden = !ok;
            if (ok) achou++;
        });
        if (vazio) vazio.hidden = achou !== 0;
    }
    if (busca) busca.addEventListener("input", filtrar);
    if (soDeve) soDeve.addEventListener("change", filtrar);
})();
