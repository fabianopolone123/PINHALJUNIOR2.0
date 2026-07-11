/* =========================================================
   Configurações IA (API do GPT): botão mostrar/ocultar chave e
   envio de teste via AJAX, exibindo a resposta da IA na tela.
   JS puro, sem bibliotecas. Espelha o padrão de whatsapp.js.
   ========================================================= */
(function () {
    "use strict";

    // ---- Mostrar/ocultar chave ----
    var verChave = document.getElementById("verChave");
    var chave = document.getElementById("api_key");
    if (verChave && chave) {
        verChave.addEventListener("click", function () {
            var mostrar = chave.type === "password";
            chave.type = mostrar ? "text" : "password";
            verChave.textContent = mostrar ? "Ocultar" : "Mostrar";
            verChave.setAttribute("aria-pressed", mostrar ? "true" : "false");
        });
    }

    // ---- Envio de teste (AJAX + resposta na tela + toast) ----
    var form = document.getElementById("iaTestarForm");
    if (!form) return;
    var btn = document.getElementById("iaTestarBtn");
    var URL = form.dataset.url, CSRF = form.dataset.csrf;
    var caixa = document.getElementById("iaResposta");
    var caixaTexto = document.getElementById("iaRespostaTexto");
    var caixaModelo = document.getElementById("iaRespostaModelo");

    form.addEventListener("submit", function (e) {
        e.preventDefault();
        if (btn.dataset.enviando) return;
        var prompt = document.getElementById("ia_prompt").value.trim();
        if (!prompt) {
            if (window.mostrarToast) window.mostrarToast("Digite o texto do teste.", "error");
            return;
        }
        btn.dataset.enviando = "1"; btn.disabled = true;
        var textoOriginal = btn.innerHTML;
        btn.innerHTML = "Enviando…";
        if (caixa) caixa.hidden = true;
        fetch(URL, {
            method: "POST",
            headers: {
                "X-CSRFToken": CSRF, "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: new URLSearchParams({ prompt: prompt }).toString(),
        })
            .then(function (r) { return r.json().catch(function () { return { ok: false, erro: "Resposta inválida do servidor." }; }); })
            .then(function (d) {
                if (d.ok) {
                    if (window.mostrarToast) window.mostrarToast("A IA respondeu! ✅", "success");
                    if (caixa && caixaTexto) {
                        caixaTexto.textContent = d.resposta || "(resposta vazia)";
                        if (caixaModelo) caixaModelo.textContent = d.modelo ? "(" + d.modelo + ")" : "";
                        caixa.hidden = false;
                    }
                } else {
                    if (window.mostrarToast) window.mostrarToast(d.erro || "Não foi possível enviar.", "error");
                }
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
