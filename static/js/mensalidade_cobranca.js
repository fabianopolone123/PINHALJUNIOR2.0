/* =========================================================
   Aba "Cobranças": envia cobrança por WhatsApp (uma família ou
   todas), com filtro "só quem não recebeu este mês". JS puro.
   ========================================================= */
(function () {
    "use strict";

    var painel = document.querySelector('.mens-painel[data-painel="cobrancas"]');
    if (!painel) return;

    var url = painel.dataset.enviarUrl;
    var csrf = painel.dataset.csrf;

    function enviar(usuarioId, soNao) {
        var corpo = "so_nao_enviados=" + (soNao ? "1" : "0");
        if (usuarioId) corpo += "&usuario_id=" + encodeURIComponent(usuarioId);
        return fetch(url, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrf,
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
            },
            body: corpo,
        }).then(function (r) { return r.json(); });
    }

    function toast(msg, tipo) {
        if (typeof window.mostrarToast === "function") window.mostrarToast(msg, tipo);
    }

    function resultado(d) {
        if (!d || !d.ok) { toast((d && d.erro) || "Não foi possível enviar.", "error"); return false; }
        var txt = "Enviadas: " + d.enviados;
        if (d.falhas && d.falhas.length) txt += " · " + d.falhas.length + " falha(s)";
        toast(txt, d.enviados ? "success" : "error");
        return true;
    }

    document.addEventListener("click", function (e) {
        var um = e.target.closest(".mens-cobranca-enviar");
        if (um) {
            um.disabled = true;
            var t = um.textContent;
            um.textContent = "Enviando…";
            enviar(um.dataset.usuario, false).then(function (d) {
                if (resultado(d)) { setTimeout(function () { location.reload(); }, 900); }
                else { um.disabled = false; um.textContent = t; }
            }).catch(function () { um.disabled = false; um.textContent = t; });
            return;
        }
        var todos = e.target.closest("#cobrancaEnviarTodos");
        if (todos) {
            var so = document.getElementById("cobrancaSoNaoEnviados");
            var soNao = so && so.checked;
            if (!window.confirm("Enviar a cobrança por WhatsApp"
                + (soNao ? " para quem ainda não recebeu este mês" : " para TODAS as famílias em aberto") + "?")) return;
            todos.disabled = true;
            todos.textContent = "Enviando…";
            enviar(null, soNao).then(function (d) {
                if (resultado(d)) { setTimeout(function () { location.reload(); }, 1200); }
                else { todos.disabled = false; todos.textContent = "📤 Enviar a todos"; }
            }).catch(function () { todos.disabled = false; todos.textContent = "📤 Enviar a todos"; });
        }
    });
})();
