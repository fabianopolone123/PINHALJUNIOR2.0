/* =========================================================
   Inscrição (online e PDV/balcão): total ao vivo + cupom por participante.

   - Calcula o preço de cada participante pela faixa etária / diretoria
     (mesmos dados do servidor, em faixasData/diretoriaData).
   - Cada participante tem um campo de cupom (.part-cupom): ao digitar/sair do
     campo, valida no servidor (endpoint JSON, sem gravar nada), mostra o toast
     padrão e abate o desconto (em R$) daquele participante do total.
   - No PDV, ainda controla a forma de pagamento (cortesia zera) e o troco.
   O uso único do cupom é aplicado de fato no servidor ao confirmar.
   JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    var lista = document.getElementById("participantes");
    if (!lista) return;
    var form = lista.closest("form") || document;
    var cupomUrl = lista.dataset.cupomUrl || "";

    var faixas = [];
    var diretoria = null;
    try { faixas = JSON.parse(document.getElementById("faixasData").textContent) || []; } catch (e) {}
    try { diretoria = JSON.parse(document.getElementById("diretoriaData").textContent); } catch (e) {}

    var totalEl = document.querySelector("[data-insc-total]");
    var descEl = document.querySelector("[data-insc-descontos]");
    // PDV (opcionais — só existem no balcão).
    var dinheiroBox = document.getElementById("pdvDinheiro");
    var recebidoEl = document.getElementById("valor_recebido");
    var trocoEl = document.getElementById("pdvTroco");
    var temFormas = !!form.querySelector('input[name="forma_pagamento"]');

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
    function linhas() {
        return Array.prototype.slice.call(lista.querySelectorAll(".part-linha"));
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

    function recalcular() {
        var cortesia = formaSelecionada() === "cortesia";
        var totalInsc = 0, totalDesc = 0;
        linhas().forEach(function (l) {
            var nomeI = l.querySelector('input[name^="part_nome_"]');
            if (!nomeI || !nomeI.value.trim()) return;
            var idadeI = l.querySelector('input[name^="part_idade_"]');
            var dirI = l.querySelector('input[name^="part_diretoria_"]');
            var idade = idadeI ? parseInt(idadeI.value, 10) : NaN;
            var ehDir = dirI ? dirI.checked : false;
            var preco = precoParticipante(idade, ehDir);
            var desc = parseFloat(l.dataset.desconto || "0");
            if (isNaN(desc) || cortesia) desc = 0;
            if (desc > preco) desc = preco;
            totalInsc += preco;
            totalDesc += desc;
        });
        var grand = cortesia ? 0 : (totalInsc - totalDesc + lojaTotal());

        if (totalEl) {
            totalEl.textContent = moeda(grand) + (cortesia ? " (cortesia)" : "");
        }
        if (descEl) {
            if (!cortesia && totalDesc > 0) {
                descEl.hidden = false;
                descEl.textContent = "Cupons: −" + moeda(totalDesc);
            } else {
                descEl.hidden = true;
                descEl.textContent = "";
            }
        }
        // Troco (PDV, dinheiro).
        if (temFormas) {
            var ehDinheiro = formaSelecionada() === "dinheiro";
            if (dinheiroBox) dinheiroBox.style.display = ehDinheiro ? "" : "none";
            if (ehDinheiro && trocoEl && recebidoEl) {
                // Campo com máscara de moeda ("1.234,56"): lê os dígitos como centavos.
                var dig = (recebidoEl.value || "").replace(/\D/g, "");
                var rec = dig ? parseInt(dig, 10) / 100 : NaN;
                if (isNaN(rec)) {
                    trocoEl.textContent = moeda(0);
                    trocoEl.classList.remove("troco-falta");
                } else if (rec < grand) {
                    trocoEl.textContent = "faltam " + moeda(grand - rec);
                    trocoEl.classList.add("troco-falta");
                } else {
                    trocoEl.textContent = moeda(rec - grand);
                    trocoEl.classList.remove("troco-falta");
                }
            }
        }
    }

    // ---- Validação do cupom de um participante (contra o servidor) ----
    function limparCupom(cupomI, fb, l) {
        l.dataset.desconto = "";
        cupomI.classList.remove("cupom-ok", "cupom-erro");
        if (fb) { fb.textContent = ""; fb.className = "part-cupom-feedback"; }
    }
    function validarLinha(l, comToast) {
        var cupomI = l.querySelector(".part-cupom");
        if (!cupomI || !cupomUrl) return;
        var fb = l.querySelector(".part-cupom-feedback");
        var codigo = (cupomI.value || "").trim();
        if (!codigo) { limparCupom(cupomI, fb, l); recalcular(); return; }

        var idadeI = l.querySelector('input[name^="part_idade_"]');
        var dirI = l.querySelector('input[name^="part_diretoria_"]');
        var idade = idadeI ? idadeI.value : "";
        var ehDir = dirI ? dirI.checked : false;
        var url = cupomUrl + "?codigo=" + encodeURIComponent(codigo) +
            "&idade=" + encodeURIComponent(idade) + "&diretoria=" + (ehDir ? 1 : 0);

        fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" }, credentials: "same-origin" })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (d.valido) {
                    l.dataset.desconto = d.desconto || "0";
                    cupomI.classList.remove("cupom-erro");
                    cupomI.classList.add("cupom-ok");
                    if (fb) { fb.className = "part-cupom-feedback cupom-fb-ok"; fb.textContent = "✓ " + d.mensagem; }
                } else {
                    l.dataset.desconto = "";
                    cupomI.classList.remove("cupom-ok");
                    cupomI.classList.add("cupom-erro");
                    if (fb) { fb.className = "part-cupom-feedback cupom-fb-erro"; fb.textContent = d.mensagem; }
                }
                if (comToast && window.mostrarToast) {
                    window.mostrarToast(d.mensagem, d.valido ? "sucesso" : "erro");
                }
                recalcular();
            })
            .catch(function () { /* sem rede: o servidor revalida ao confirmar */ });
    }

    // Digitação: valida sem toast (feedback inline). Ao sair do campo / Enter:
    // valida com toast. Mudar idade/diretoria revalida o cupom daquela linha.
    var timers = new WeakMap();
    lista.addEventListener("input", function (e) {
        var alvo = e.target;
        if (alvo.classList && alvo.classList.contains("part-cupom")) {
            var l = alvo.closest(".part-linha");
            var t = timers.get(alvo);
            if (t) clearTimeout(t);
            timers.set(alvo, setTimeout(function () { validarLinha(l, false); }, 600));
        }
        recalcular();
    });
    lista.addEventListener("change", function (e) {
        var alvo = e.target;
        var l = alvo.closest(".part-linha");
        if (!l) { recalcular(); return; }
        if (alvo.classList && alvo.classList.contains("part-cupom")) {
            var t = timers.get(alvo);
            if (t) { clearTimeout(t); timers.delete(alvo); }
            validarLinha(l, true);
        } else if (alvo.matches('input[name^="part_idade_"], input[name^="part_diretoria_"]')) {
            var cupomI = l.querySelector(".part-cupom");
            if (cupomI && cupomI.value.trim()) validarLinha(l, true);
            else recalcular();
        } else {
            recalcular();
        }
    });

    // Recalcula com mudanças fora da lista (forma de pagamento, valor recebido, lojinha).
    form.addEventListener("input", recalcular);
    form.addEventListener("change", recalcular);

    recalcular();
})();
