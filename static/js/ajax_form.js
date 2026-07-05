/* =========================================================
   Envio de formulário por AJAX com toast (padrão do sistema).
   Usado no login e nas telas de recuperação de senha: o erro aparece
   como toast SEM recarregar a página (clicar de novo só repete a
   notificação). Aplica-se a todo <form data-ajax-toast>.
   Resposta do servidor (quando X-Requested-With: XMLHttpRequest):
     {"redirect": url}           → navega para url
     {"msg": "...", "tipo": ...} → só mostra o toast (sem recarregar)
   Sem JS, os formulários continuam funcionando com POST normal.
   ========================================================= */
(function () {
    "use strict";

    var forms = document.querySelectorAll("form[data-ajax-toast]");
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
