/* =========================================================
   Aba "Parcelas": modal do novo lançamento (com prévia ao vivo
   das parcelas) e busca na lista de lançamentos. JS puro.

   A prévia repete a regra do back-end (`dividir_em_parcelas`):
   a sobra dos centavos vai na 1ª parcela, então as seguintes
   ficam redondas e iguais. A conta é feita em CENTAVOS porque o
   campo de valor usa a máscara pt-BR — `parseFloat` quebra com o
   separador de milhar (ver CLAUDE.md).
   ========================================================= */
(function () {
    "use strict";

    // ---- Modal (mesma mecânica do ligarModalBotao do mensalidades.js) ----
    var modal = document.getElementById("modalParcNovo");
    var btn = document.getElementById("btnParcNovo");
    if (modal && btn) {
        function fechar() { modal.hidden = true; }
        btn.addEventListener("click", function () { modal.hidden = false; });
        Array.prototype.forEach.call(modal.querySelectorAll("[data-fechar]"), function (el) {
            el.addEventListener("click", fechar);
        });
        // Fecha no fundo só com mousedown+click no fundo (não fecha ao arrastar).
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

    // ---- Prévia das parcelas ----
    var campoVis = document.getElementById("parcValorVis");
    var campoQtd = document.getElementById("parcQtd");
    var campoVenc = document.getElementById("parcVenc");
    var preview = document.getElementById("parcPreview");
    var MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
                 "agosto", "setembro", "outubro", "novembro", "dezembro"];

    function centavos(el) {
        // Campo mascarado: os dígitos SÃO os centavos.
        return parseInt((el && el.value || "").replace(/\D/g, ""), 10) || 0;
    }

    function moeda(cent) {
        var s = (cent / 100).toFixed(2).replace(".", ",");
        return s.replace(/\B(?=(\d{3})+(?!\d),)/g, ".");
    }

    function mesRotulo(valor, somar) {
        // valor = "AAAA-MM" (o mês da 1ª parcela).
        var partes = (valor || "").split("-");
        if (partes.length !== 2) return "";
        var mes = parseInt(partes[1], 10) - 1 + (somar || 0);
        var ano = parseInt(partes[0], 10) + Math.floor(mes / 12);
        mes = ((mes % 12) + 12) % 12;
        return MESES[mes] + "/" + ano;
    }

    function atualizar() {
        if (!preview) return;
        var total = centavos(campoVis);
        var qtd = parseInt(campoQtd && campoQtd.value, 10) || 0;
        if (!total || qtd < 1) { preview.hidden = true; return; }
        var base = Math.floor(total / qtd);
        if (base < 1) {
            preview.hidden = false;
            preview.textContent = "⚠️ R$ " + moeda(total) + " é pouco para dividir em "
                + qtd + " parcelas.";
            return;
        }
        var primeira = total - base * (qtd - 1);
        var venc = campoVenc ? campoVenc.value : "";
        var txt = qtd === 1
            ? "1 parcela de R$ " + moeda(total)
            : (primeira === base
                ? qtd + "x de R$ " + moeda(base)
                : qtd + "x: a 1ª de R$ " + moeda(primeira) + " e as outras de R$ " + moeda(base));
        if (venc) {
            txt += " · 1ª em " + mesRotulo(venc, 0);
            if (qtd > 1) txt += ", última em " + mesRotulo(venc, qtd - 1);
        }
        preview.hidden = false;
        preview.textContent = "📆 " + txt;
    }

    [campoVis, campoQtd, campoVenc].forEach(function (el) {
        if (!el) return;
        el.addEventListener("input", atualizar);
        el.addEventListener("change", atualizar);
    });
    atualizar();

    // ---- Busca na lista de lançamentos ----
    var painel = document.querySelector('.mens-painel[data-painel="parcelas"]');
    var busca = document.getElementById("parcBusca");
    if (painel && busca) {
        var vazio = painel.querySelector(".parc-vazio-busca");
        function normal(s) {
            return (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
        }
        busca.addEventListener("input", function () {
            var q = normal(busca.value.trim());
            var achou = 0;
            Array.prototype.forEach.call(painel.querySelectorAll(".parc-item"), function (li) {
                var ok = !q || normal(li.dataset.busca).indexOf(q) !== -1;
                li.hidden = !ok;
                if (ok) achou++;
            });
            if (vazio) vazio.hidden = achou !== 0;
        });
    }
})();
