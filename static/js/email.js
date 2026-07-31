/* =========================================================
   E-mail (SMTP): botão mostrar/ocultar senha e envio de teste
   via AJAX, com o resultado em toast. JS puro, sem bibliotecas.
   Espelha o padrão de ia.js / whatsapp.js.
   ========================================================= */
(function () {
    "use strict";

    // ---- Mostrar/ocultar senha ----
    var verSenha = document.getElementById("verSenha");
    var senha = document.getElementById("senha");
    if (verSenha && senha) {
        verSenha.addEventListener("click", function () {
            var mostrar = senha.type === "password";
            senha.type = mostrar ? "text" : "password";
            verSenha.textContent = mostrar ? "Ocultar" : "Mostrar";
            verSenha.setAttribute("aria-pressed", mostrar ? "true" : "false");
        });
    }

    // ---- Envio de teste (AJAX + toast) ----
    var form = document.getElementById("emailTestarForm");
    if (!form) return;
    var btn = document.getElementById("emailTestarBtn");
    var URL = form.dataset.url, CSRF = form.dataset.csrf;

    // Atualiza os números do card "Envios" sem recarregar a página.
    function atualizarContador(c) {
        if (!c) return;
        var mapa = { emEnviados: c.enviados, emFalhas: c.falhas };
        Object.keys(mapa).forEach(function (id) {
            var el = document.getElementById(id);
            if (el && mapa[id] != null) el.textContent = mapa[id];
        });
    }

    form.addEventListener("submit", function (e) {
        e.preventDefault();
        if (btn.dataset.enviando) return;
        var destino = document.getElementById("destino").value.trim();
        if (!destino) {
            if (window.mostrarToast) window.mostrarToast("Informe o e-mail de destino.", "error");
            return;
        }
        btn.dataset.enviando = "1"; btn.disabled = true;
        var textoOriginal = btn.innerHTML;
        btn.innerHTML = "Enviando…";
        fetch(URL, {
            method: "POST",
            headers: {
                "X-CSRFToken": CSRF, "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: new URLSearchParams({ destino: destino }).toString(),
        })
            .then(function (r) { return r.json().catch(function () { return { ok: false, erro: "Resposta inválida do servidor." }; }); })
            .then(function (d) {
                if (window.mostrarToast) {
                    window.mostrarToast(
                        d.ok ? "E-mail enviado para " + d.destino + " ✅"
                             : (d.erro || "Não foi possível enviar."),
                        d.ok ? "success" : "error"
                    );
                }
                atualizarContador(d.contador);
            })
            .catch(function () {
                if (window.mostrarToast) window.mostrarToast("Falha de conexão.", "error");
            })
            .finally(function () {
                delete btn.dataset.enviando; btn.disabled = false;
                btn.innerHTML = textoOriginal;
            });
    });
})();
