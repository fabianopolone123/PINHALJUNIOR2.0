/* =========================================================
   Recuperação de senha: envia os formulários por AJAX para que os
   erros apareçam como toast (padrão do sistema) SEM recarregar a
   página. Clicar de novo apenas repete a notificação.
   Resposta do servidor: {"redirect": url} → navega; ou
   {"msg": "...", "tipo": "error|info|success"} → só mostra o toast.
   Sem JS, os formulários continuam funcionando com POST normal.
   ========================================================= */
(function () {
    "use strict";

    var forms = document.querySelectorAll("form[data-ajax-recup]");
    Array.prototype.forEach.call(forms, function (form) {
        form.addEventListener("submit", function (e) {
            e.preventDefault();
            var btn = form.querySelector("button[type=submit]");
            if (btn && btn.dataset.enviando) return;
            if (btn) { btn.dataset.enviando = "1"; btn.disabled = true; }

            fetch(form.action, {
                method: "POST",
                headers: { "X-Requested-With": "XMLHttpRequest" },
                body: new FormData(form),
            })
                .then(function (r) {
                    return r.json().catch(function () { return { msg: "Resposta inválida do servidor." }; });
                })
                .then(function (d) {
                    if (d && d.redirect) { window.location = d.redirect; return; }
                    if (d && d.msg && window.mostrarToast) {
                        window.mostrarToast(d.msg, d.tipo || "error");
                    }
                })
                .catch(function () {
                    if (window.mostrarToast) window.mostrarToast("Falha de conexão.", "error");
                })
                .finally(function () {
                    if (btn) { delete btn.dataset.enviando; btn.disabled = false; }
                });
        });
    });
})();
