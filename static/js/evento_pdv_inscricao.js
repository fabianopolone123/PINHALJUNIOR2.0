/* =========================================================
   PDV — Nova inscrição: total combinado ao vivo (inscrição por
   participante, pela faixa etária/diretoria, + itens da lojinha),
   alternância da forma de pagamento e troco. Cortesia zera o total.
   JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    var form = document.getElementById("pdvInscForm");
    if (!form) return;

    var faixas = [];
    var diretoria = null;
    try { faixas = JSON.parse(document.getElementById("faixasData").textContent) || []; } catch (e) {}
    try { diretoria = JSON.parse(document.getElementById("diretoriaData").textContent); } catch (e) {}

    var totalEl = document.getElementById("pdvTotal");
    var dinheiroBox = document.getElementById("pdvDinheiro");
    var recebidoEl = document.getElementById("valor_recebido");
    var trocoEl = document.getElementById("pdvTroco");
    var participantes = document.getElementById("participantes");

    function moeda(v) {
        return "R$ " + v.toLocaleString("pt-BR", {
            minimumFractionDigits: 2, maximumFractionDigits: 2,
        });
    }
    function formaSelecionada() {
        var r = form.querySelector('input[name="forma_pagamento"]:checked');
        return r ? r.value : "";
    }
    function precoParticipante(idade, ehDiretoria) {
        if (ehDiretoria && diretoria !== null) return parseFloat(diretoria);
        if (isNaN(idade)) return 0;
        for (var i = 0; i < faixas.length; i++) {
            if (idade >= faixas[i].min && idade <= faixas[i].max) {
                return parseFloat(faixas[i].valor);
            }
        }
        return 0;
    }
    function inscricaoTotal() {
        var t = 0;
        var linhas = participantes ? participantes.querySelectorAll(".part-linha") : [];
        Array.prototype.forEach.call(linhas, function (l) {
            var nomeI = l.querySelector('input[name^="part_nome_"]');
            if (!nomeI || !nomeI.value.trim()) return;
            var idadeI = l.querySelector('input[name^="part_idade_"]');
            var dirI = l.querySelector('input[name^="part_diretoria_"]');
            var idade = idadeI ? parseInt(idadeI.value, 10) : NaN;
            var ehDir = dirI ? dirI.checked : false;
            t += precoParticipante(idade, ehDir);
        });
        return t;
    }
    function lojaTotal() {
        var t = 0;
        Array.prototype.forEach.call(form.querySelectorAll(".loja-qtd"), function (inp) {
            var q = parseInt(inp.value, 10);
            var p = parseFloat(inp.dataset.preco);
            if (!isNaN(q) && q > 0 && !isNaN(p)) t += q * p;
        });
        return t;
    }
    function atualizar() {
        var forma = formaSelecionada();
        var total = (forma === "cortesia") ? 0 : (inscricaoTotal() + lojaTotal());
        if (totalEl) totalEl.textContent = moeda(total) + (forma === "cortesia" ? " (cortesia)" : "");
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

    form.addEventListener("input", atualizar);
    form.addEventListener("change", atualizar);
    atualizar();
})();
