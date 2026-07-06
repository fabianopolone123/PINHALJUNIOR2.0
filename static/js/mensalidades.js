/* =========================================================
   Mensalidades: marcar pago/desfazer (fetch/JSON), busca e
   filtro "só quem deve", e confirmação de gerar cobranças.
   JS puro.
   ========================================================= */
(function () {
    "use strict";

    function csrf() {
        var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        if (m) return m[1];
        var i = document.querySelector('input[name=csrfmiddlewaretoken]');
        return i ? i.value : "";
    }

    var FORMAS = { dinheiro: "Dinheiro", pix: "Pix", cartao: "Cartão", online: "Online" };

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
        fetch("/mensalidades/pagar/", {
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
