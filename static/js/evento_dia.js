/* =========================================================
   Console "Dia do evento" (Fase 5.4):
   - busca em tempo real (responsável, participante ou código);
   - marcar check-in por participante e entrega por unidade, via endpoints JSON,
     atualizando a tela e o resumo sem recarregar.
   JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    // ---- Busca em tempo real ----
    function normalizar(t) {
        return (t || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
            .toLowerCase().replace(/\s+/g, " ").trim();
    }
    var input = document.getElementById("buscaDia");
    if (input) {
        var itens = Array.prototype.slice.call(document.querySelectorAll(".dia-busca"));
        itens.forEach(function (el) { el.dataset.busca = normalizar(el.textContent); });
        var vazio = document.getElementById("diaVazio");
        var aplicar = function () {
            var termo = normalizar(input.value);
            var visiveis = 0;
            itens.forEach(function (el) {
                var ok = !termo || el.dataset.busca.indexOf(termo) !== -1;
                el.classList.toggle("busca-oculto", !ok);
                if (ok) visiveis++;
            });
            if (vazio) vazio.hidden = visiveis !== 0;
        };
        input.addEventListener("input", aplicar);
        input.addEventListener("keydown", function (e) {
            if (e.key === "Escape") { input.value = ""; aplicar(); }
        });
    }

    // ---- Ações (check-in / entrega) ----
    var dados = document.getElementById("diaDados");
    if (!dados) return;
    var CSRF = dados.dataset.csrf;
    var URL_CHECKIN = dados.dataset.checkinUrl;
    var URL_ENTREGA = dados.dataset.entregaUrl;

    function toast(msg, tipo) {
        if (window.mostrarToast) window.mostrarToast(msg, tipo || "info");
    }

    function post(url, params) {
        return fetch(url, {
            method: "POST",
            headers: {
                "X-CSRFToken": CSRF,
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: new URLSearchParams(params).toString(),
        }).then(function (r) { return r.json().catch(function () { return {ok: false}; }); });
    }

    function atualizarResumo(r) {
        if (!r) return;
        var set = function (id, v) {
            var el = document.getElementById(id);
            if (el) el.textContent = v;
        };
        set("resPresentes", r.presentes);
        set("resFaltam", r.faltam_part);
        set("resEntregues", r.entregues);
        set("resPendentes", r.pendentes_itens);
    }

    // Aplica o visual de um selo (ok/parcial/pendente) + texto.
    function pintarSelo(el, classe, texto) {
        el.classList.remove("selo-ok", "selo-parcial", "selo-pendente");
        el.classList.add(classe);
        var txt = el.querySelector(".checkin-txt, .entrega-txt");
        if (txt) txt.textContent = texto;
    }

    document.addEventListener("click", function (e) {
        var checkBtn = e.target.closest(".checkin-btn");
        if (checkBtn) { marcarCheckin(checkBtn); return; }
        var entregaBox = e.target.closest(".entrega");
        if (!entregaBox) return;
        var qtd = parseInt(entregaBox.dataset.qtd, 10) || 0;
        var atual = parseInt(entregaBox.dataset.entregue, 10) || 0;
        if (e.target.closest(".entrega-selo")) {
            marcarEntrega(entregaBox, atual >= qtd ? 0 : qtd);
        } else if (e.target.closest(".entrega-menos")) {
            marcarEntrega(entregaBox, Math.max(0, atual - 1));
        } else if (e.target.closest(".entrega-mais")) {
            marcarEntrega(entregaBox, Math.min(qtd, atual + 1));
        }
    });

    function marcarCheckin(btn) {
        if (btn.dataset.enviando) return;
        var novo = btn.getAttribute("aria-pressed") !== "true";
        btn.dataset.enviando = "1";
        btn.disabled = true;
        post(URL_CHECKIN, { participante: btn.dataset.part, presente: novo ? "1" : "0" })
            .then(function (d) {
                if (!d.ok) { toast(d.erro || "Não foi possível marcar.", "error"); return; }
                btn.setAttribute("aria-pressed", d.presente ? "true" : "false");
                pintarSelo(btn, d.presente ? "selo-ok" : "selo-pendente",
                    d.presente ? "✅ Chegou" : "Marcar chegada");
                atualizarResumo(d.resumo);
            })
            .catch(function () { toast("Falha de conexão.", "error"); })
            .finally(function () { delete btn.dataset.enviando; btn.disabled = false; });
    }

    function marcarEntrega(box, alvo) {
        if (box.dataset.enviando) return;
        var qtd = parseInt(box.dataset.qtd, 10) || 0;
        box.dataset.enviando = "1";
        post(URL_ENTREGA, { item: box.dataset.item, quantidade: alvo })
            .then(function (d) {
                if (!d.ok) { toast(d.erro || "Não foi possível registrar.", "error"); return; }
                box.dataset.entregue = d.quantidade_entregue;
                var num = box.querySelector(".entrega-num");
                if (num) num.textContent = d.quantidade_entregue + "/" + qtd;
                var selo = box.querySelector(".entrega-selo");
                if (selo) {
                    if (d.status === "entregue") pintarSelo(selo, "selo-ok", "✅ Entregue");
                    else if (d.status === "parcial") pintarSelo(selo, "selo-parcial", "Parcial");
                    else pintarSelo(selo, "selo-pendente", "Não entregue");
                }
                atualizarResumo(d.resumo);
            })
            .catch(function () { toast("Falha de conexão.", "error"); })
            .finally(function () { delete box.dataset.enviando; });
    }
})();
