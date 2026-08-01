/* =========================================================
   Aniversariantes: envio manual de UMA pessoa, via AJAX.
   O disparo em lote é do cron; aqui é o botão avulso.
   JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    var painel = document.getElementById("anivPainel");
    if (!painel) return;
    var URL = painel.dataset.url, CSRF = painel.dataset.csrf;

    function toast(msg, tipo) {
        if (typeof window.mostrarToast === "function") window.mostrarToast(msg, tipo);
    }

    // Repinta os selos "já enviado" e o rótulo do botão conforme a resposta.
    function atualizarLinha(btn, d) {
        var acoes = btn.parentElement;
        if (!acoes) return;
        acoes.querySelectorAll(".aniv-selo").forEach(function (s) { s.remove(); });
        [["enviado_whatsapp", "💬", "WhatsApp"], ["enviado_email", "✉️", "e-mail"]]
            .forEach(function (par) {
                if (!d[par[0]]) return;
                var s = document.createElement("span");
                s.className = "aniv-selo aniv-selo-ok";
                s.title = "Enviado por " + par[2] + " este ano";
                s.textContent = par[1] + " ✓";
                acoes.insertBefore(s, btn);
            });
        if (d.enviado_whatsapp && d.enviado_email) {
            btn.dataset.reenvio = "1";
            btn.textContent = "↻ Reenviar";
        }
    }

    document.addEventListener("click", function (e) {
        var btn = e.target.closest(".aniv-enviar");
        if (!btn || btn.disabled) return;

        var nome = btn.dataset.nome || "esta pessoa";
        var reenvio = btn.dataset.reenvio === "1";
        if (reenvio && !window.confirm(
            "A mensagem de aniversário de " + nome + " já foi enviada este ano.\n\n"
            + "Enviar de novo?")) return;

        var original = btn.textContent;
        btn.disabled = true;
        btn.textContent = "Enviando…";

        fetch(URL, {
            method: "POST",
            headers: {
                "X-CSRFToken": CSRF, "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: new URLSearchParams({
                chave: btn.dataset.chave, forcar: reenvio ? "1" : "0",
            }).toString(),
        })
            .then(function (r) {
                return r.json().catch(function () {
                    return { ok: false, erro: "Resposta inválida do servidor." };
                });
            })
            .then(function (d) {
                if (!d.ok) { toast(d.erro || "Não foi possível enviar.", "error"); return; }
                atualizarLinha(btn, d);
                if (d.enviados && d.enviados.length) {
                    toast("Parabéns enviados para " + d.nome + " ✅ ("
                          + d.enviados.length + " canal/canais)", "success");
                }
                // Os problemas são informativos: "já enviado" ou barrado por gate.
                if (d.problemas && d.problemas.length) {
                    toast(d.problemas.join(" · "), d.enviados.length ? "success" : "error");
                }
            })
            .catch(function () { toast("Falha de conexão.", "error"); })
            .finally(function () {
                btn.disabled = false;
                if (btn.textContent === "Enviando…") btn.textContent = original;
            });
    });
})();
