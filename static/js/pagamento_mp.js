/* =========================================================
   Pagamento Pix (Mercado Pago): faz polling do status e, no
   modo teste, o botão "Simular pagamento aprovado". Também
   um "Copiar" genérico (usado na tela de config do webhook).
   JS puro, sem dependências.
   ========================================================= */
(function () {
    "use strict";

    // --- Copiar genérico (qualquer [data-target], menos o do Pix, que já é
    //     tratado por evento_pagamento.js) ---
    var copias = document.querySelectorAll("button[data-target]");
    Array.prototype.forEach.call(copias, function (btn) {
        if (btn.id === "btnCopiarPix") return;
        var input = document.getElementById(btn.dataset.target);
        if (!input) return;
        btn.addEventListener("click", function () {
            var texto = input.value;
            function ok() {
                if (typeof window.mostrarToast === "function") {
                    window.mostrarToast("Copiado!", "success");
                }
                var t = btn.textContent;
                btn.textContent = "Copiado!";
                setTimeout(function () { btn.textContent = t; }, 2000);
            }
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(texto).then(ok, function () {
                    input.select(); document.execCommand("copy"); ok();
                });
            } else {
                input.removeAttribute("readonly");
                input.select();
                try { document.execCommand("copy"); } catch (e) { /* ignora */ }
                input.setAttribute("readonly", "readonly");
                ok();
            }
        });
    });

    // --- Polling do status + botão de simular (só na tela de pagamento) ---
    var box = document.getElementById("pixMP");
    if (!box) return;

    var statusUrl = box.dataset.statusUrl;
    var simularUrl = box.dataset.simularUrl;
    var csrf = box.dataset.csrf;
    if (!statusUrl) return;

    var indo = false;

    function irPara(url) {
        if (url) { window.location.href = url; }
    }

    function checar() {
        if (indo) return;
        fetch(statusUrl, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (r) { return r.json(); })
            .then(function (j) {
                if (j.status === "aprovado" && j.redirect) {
                    indo = true;
                    irPara(j.redirect);
                }
            })
            .catch(function () { /* silencioso; tenta de novo no próximo tick */ });
    }

    var timer = setInterval(checar, 4000);
    checar();

    var btnSim = document.getElementById("btnSimularPix");
    if (btnSim && simularUrl) {
        btnSim.addEventListener("click", function () {
            btnSim.disabled = true;
            btnSim.textContent = "Confirmando…";
            fetch(simularUrl, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrf,
                    "X-Requested-With": "XMLHttpRequest",
                },
            })
                .then(function (r) { return r.json(); })
                .then(function (j) {
                    if (j.ok && j.redirect) {
                        clearInterval(timer);
                        indo = true;
                        irPara(j.redirect);
                    } else {
                        btnSim.disabled = false;
                        btnSim.textContent = "✅ Simular pagamento aprovado (teste)";
                        if (typeof window.mostrarToast === "function") {
                            window.mostrarToast(j.erro || "Não foi possível simular.", "error");
                        }
                    }
                })
                .catch(function () {
                    btnSim.disabled = false;
                    btnSim.textContent = "✅ Simular pagamento aprovado (teste)";
                });
        });
    }
})();
