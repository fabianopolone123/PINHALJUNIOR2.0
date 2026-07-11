/* =========================================================
   Aba "Cobranças": busca por nome, envio individual e envio em
   LOTE (um a um, com 10s entre cada, barra de progresso e
   cancelamento). O aviso de WhatsApp não configurado vem como
   toast na resposta do servidor. JS puro.
   ========================================================= */
(function () {
    "use strict";

    var painel = document.querySelector('.mens-painel[data-painel="cobrancas"]');
    if (!painel) return;

    var url = painel.dataset.enviarUrl;
    var csrf = painel.dataset.csrf;
    var DELAY_MS = 10000;

    function toast(msg, tipo) {
        if (typeof window.mostrarToast === "function") window.mostrarToast(msg, tipo);
    }

    // ---- Alavanca: mensagem padrão × IA (persiste ao trocar) ----
    var modoIA = document.getElementById("cobrancaModoIA");
    var modoSub = document.getElementById("cobrancaModoSub");
    var iaAviso = document.getElementById("cobrancaIaAviso");
    var iaConfigurada = painel.dataset.iaConfigurada === "1";
    if (modoIA) {
        modoIA.addEventListener("change", function () {
            var ligado = modoIA.checked;
            if (modoSub) {
                modoSub.textContent = ligado
                    ? "🤖 A IA redige uma mensagem personalizada para cada família."
                    : "📝 Usa a mensagem de cobrança padrão.";
            }
            if (iaAviso && !iaConfigurada) iaAviso.hidden = !ligado;
            fetch(painel.dataset.modoUrl, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrf,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: "via_ia=" + (ligado ? "1" : "0"),
            }).then(function (r) { return r.json(); }).then(function (d) {
                if (!d || !d.ok) { toast("Não foi possível salvar o modo.", "error"); return; }
                toast(ligado ? "Cobrança pela IA ativada. 🤖" : "Cobrança pela mensagem padrão.", "success");
            }).catch(function () { toast("Falha ao salvar o modo.", "error"); });
        });
    }

    function enviar(usuarioId) {
        return fetch(url, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrf,
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
            },
            body: "so_nao_enviados=0&usuario_id=" + encodeURIComponent(usuarioId),
        }).then(function (r) { return r.json(); });
    }

    function marcaEnviado(li) {
        var n = (parseInt(li.dataset.cobrado, 10) || 0) + 1;
        li.dataset.cobrado = String(n);
        var s = li.querySelector(".mens-cobranca-status");
        if (s) {
            s.innerHTML = '<span class="mens-badge mens-badge-isento">📤 Cobrado este mês (' + n + ')</span>';
        }
    }

    // ---- Busca ao vivo ----
    function normal(s) {
        return (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    }
    var busca = document.getElementById("cobrancaBusca");
    var vazio = painel.querySelector(".mens-cobranca-vazio-busca");
    if (busca) {
        busca.addEventListener("input", function () {
            var q = normal(busca.value.trim());
            var achou = 0;
            Array.prototype.forEach.call(painel.querySelectorAll(".mens-cobranca-item"), function (li) {
                var ok = !q || normal(li.dataset.busca).indexOf(q) !== -1;
                li.hidden = !ok;
                if (ok) achou++;
            });
            if (vazio) vazio.hidden = achou !== 0;
        });
    }

    // ---- Envio individual ----
    document.addEventListener("click", function (e) {
        var um = e.target.closest(".mens-cobranca-enviar");
        if (!um) return;
        um.disabled = true;
        var t = um.textContent;
        um.textContent = "Enviando…";
        enviar(um.dataset.usuario).then(function (d) {
            if (!d || !d.ok) { toast((d && d.erro) || "Não foi possível enviar.", "error"); }
            else if (d.enviados) {
                var li = um.closest(".mens-cobranca-item");
                if (li) marcaEnviado(li);
                toast("Cobrança enviada!", "success");
            } else {
                toast((d.falhas && d.falhas[0]) || "Não enviado.", "error");
            }
            um.disabled = false;
            um.textContent = t;
        }).catch(function () {
            toast("Falha de conexão ao enviar.", "error");
            um.disabled = false;
            um.textContent = t;
        });
    });

    // ---- Envio em LOTE (10s entre cada, barra + cancelar) ----
    var btnTodos = document.getElementById("cobrancaEnviarTodos");
    var prog = document.getElementById("cobrancaProgresso");
    var fill = document.getElementById("cobrancaProgFill");
    var txt = document.getElementById("cobrancaProgTxt");
    var btnCancelar = document.getElementById("cobrancaCancelar");

    // Estado do lote (compartilhado entre "enviar a todos" e "cancelar").
    var lote = { ativo: false, cancelado: false, timer: null, i: 0, ok: 0, falhas: 0, alvos: [] };

    function alvosLote() {
        var so = document.getElementById("cobrancaSoNaoEnviados");
        var soNao = so && so.checked;
        return Array.prototype.filter.call(
            painel.querySelectorAll(".mens-cobranca-item"),
            function (li) {
                if (li.dataset.temNumero !== "1") return false;
                if (soNao && li.dataset.cobrado !== "0") return false;
                return true;
            }
        );
    }

    function barra() {
        if (fill) fill.style.width = Math.round(lote.i / (lote.alvos.length || 1) * 100) + "%";
    }

    function fim(cancel) {
        if (lote.timer) { clearTimeout(lote.timer); lote.timer = null; }
        lote.ativo = false;
        if (prog) prog.hidden = true;
        if (btnTodos) btnTodos.disabled = false;
        toast(
            (cancel ? "Cancelado. " : "Concluído. ") + "Enviadas: " + lote.ok
            + (lote.falhas ? " · " + lote.falhas + " falha(s)" : ""),
            lote.ok ? "success" : "error"
        );
    }

    function proximo() {
        if (lote.cancelado || lote.i >= lote.alvos.length) { fim(lote.cancelado); return; }
        var li = lote.alvos[lote.i];
        if (txt) txt.textContent = "Enviando " + (lote.i + 1) + " de " + lote.alvos.length + "…";
        enviar(li.dataset.usuario).then(function (d) {
            if (!d || !d.ok) {  // WhatsApp não configurado → aborta o lote inteiro
                toast((d && d.erro) || "Falha ao enviar.", "error");
                lote.cancelado = true;
                fim(true);
                return;
            }
            if (d.enviados) { lote.ok++; marcaEnviado(li); } else { lote.falhas++; }
            lote.i++;
            barra();
            if (lote.cancelado || lote.i >= lote.alvos.length) { fim(lote.cancelado); return; }
            if (txt) txt.textContent = "Enviado " + lote.i + " de " + lote.alvos.length
                + " · aguardando 10s… (pode cancelar)";
            lote.timer = setTimeout(proximo, DELAY_MS);
        }).catch(function () {
            lote.falhas++; lote.i++; barra();
            if (lote.cancelado || lote.i >= lote.alvos.length) { fim(lote.cancelado); return; }
            lote.timer = setTimeout(proximo, DELAY_MS);
        });
    }

    if (btnTodos) {
        btnTodos.addEventListener("click", function () {
            if (lote.ativo) return;
            var alvos = alvosLote();
            if (!alvos.length) { toast("Ninguém para enviar com esse filtro.", "error"); return; }
            if (!window.confirm(
                "Enviar cobrança para " + alvos.length + " família(s)?\n"
                + "Há um intervalo de 10 segundos entre cada envio — você pode cancelar a qualquer momento."
            )) return;
            lote = { ativo: true, cancelado: false, timer: null, i: 0, ok: 0, falhas: 0, alvos: alvos };
            btnTodos.disabled = true;
            if (prog) prog.hidden = false;
            barra();
            proximo();
        });
    }

    if (btnCancelar) {
        btnCancelar.addEventListener("click", function () {
            if (!lote.ativo) return;
            lote.cancelado = true;
            // Se está no intervalo de 10s (timer pendente), encerra agora. Se há um
            // envio em andamento, o retorno dele já vai encerrar (vê o cancelado).
            if (lote.timer) { clearTimeout(lote.timer); lote.timer = null; fim(true); }
        });
    }
})();
