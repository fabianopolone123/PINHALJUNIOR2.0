/* =========================================================
   Módulo WhatsApp (W-API): pré-visualização do telefone no formato
   de envio, botão mostrar/ocultar token e envio de teste via AJAX
   com o toast padrão do sistema. JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    // ---- Normalização do telefone (espelha normalizar_telefone no back-end) ----
    function normalizarTelefone(bruto) {
        var d = (bruto || "").replace(/\D/g, "");
        if (!d) return "";
        if (d.indexOf("00") === 0) d = d.slice(2);
        if (d.indexOf("55") === 0 && (d.length === 12 || d.length === 13)) return d;
        if (d.length === 10 || d.length === 11) return "55" + d;
        return d;
    }

    // Deixa o número legível na prévia: +55 (47) 99224-9708.
    function formatarBonito(num) {
        if (num.indexOf("55") === 0 && num.length >= 12) {
            var ddd = num.slice(2, 4);
            var resto = num.slice(4);
            var meio = resto.length > 8 ? resto.slice(0, 5) : resto.slice(0, 4);
            var fim = resto.length > 8 ? resto.slice(5) : resto.slice(4);
            return "+55 (" + ddd + ") " + meio + "-" + fim;
        }
        return num;
    }

    var tel = document.getElementById("wa_telefone");
    var preview = document.getElementById("waPreview");
    if (tel && preview) {
        var atualizarPreview = function () {
            var norm = normalizarTelefone(tel.value);
            if (norm && norm.length >= 12) {
                preview.textContent = "Será enviado para: " + formatarBonito(norm);
                preview.hidden = false;
                preview.classList.remove("wa-preview-erro");
            } else if (tel.value.trim()) {
                preview.textContent = "Número incompleto — confira o DDD.";
                preview.hidden = false;
                preview.classList.add("wa-preview-erro");
            } else {
                preview.hidden = true;
            }
        };
        tel.addEventListener("input", atualizarPreview);
    }

    // ---- Abas (Configurações / Grupos) ----
    var abas = document.querySelectorAll(".wa-aba");
    var paineis = document.querySelectorAll(".wa-painel");
    Array.prototype.forEach.call(abas, function (b) {
        b.addEventListener("click", function () {
            var alvo = b.dataset.aba;
            Array.prototype.forEach.call(abas, function (x) { x.classList.toggle("ativa", x === b); });
            Array.prototype.forEach.call(paineis, function (p) { p.hidden = p.dataset.painel !== alvo; });
        });
    });

    // ---- Grupos: sincronizar da W-API ----
    var painelGrupos = document.querySelector('.wa-painel[data-painel="grupos"]');
    var btnSync = document.getElementById("waGruposSync");
    if (painelGrupos && btnSync) {
        var lista = document.getElementById("waGruposLista");
        var vazio = document.getElementById("waGruposVazio");
        var escapar = function (s) {
            var d = document.createElement("div"); d.textContent = s == null ? "" : String(s); return d.innerHTML;
        };
        var render = function (grupos) {
            lista.innerHTML = "";
            grupos.forEach(function (g) {
                var li = document.createElement("li");
                li.className = "wa-grupo-item";
                li.innerHTML = '<div class="wa-grupo-info">'
                    + '<span class="wa-grupo-nome">' + (escapar(g.nome) || "(sem nome)") + '</span>'
                    + '<span class="wa-grupo-id">' + escapar(g.group_id) + '</span></div>'
                    + '<span class="wa-grupo-tam">' + (g.tamanho || 0) + ' 👤</span>';
                lista.appendChild(li);
            });
            if (vazio) vazio.hidden = grupos.length > 0;
        };
        btnSync.addEventListener("click", function () {
            if (btnSync.dataset.carregando) return;
            btnSync.dataset.carregando = "1"; btnSync.disabled = true;
            var txt = btnSync.textContent; btnSync.textContent = "Buscando…";
            fetch(painelGrupos.dataset.syncUrl, {
                method: "POST",
                headers: {
                    "X-CSRFToken": painelGrupos.dataset.csrf,
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            }).then(function (r) { return r.json().catch(function () { return { ok: false, erro: "Resposta inválida." }; }); })
                .then(function (d) {
                    if (d.ok) {
                        render(d.grupos || []);
                        if (window.mostrarToast) window.mostrarToast((d.total || 0) + " grupo(s) carregado(s). ✅", "success");
                    } else if (window.mostrarToast) {
                        window.mostrarToast(d.erro || "Não foi possível buscar os grupos.", "error");
                    }
                })
                .catch(function () { if (window.mostrarToast) window.mostrarToast("Falha de conexão.", "error"); })
                .finally(function () {
                    delete btnSync.dataset.carregando; btnSync.disabled = false; btnSync.textContent = txt;
                });
        });
    }

    // ---- Mostrar/ocultar token ----
    var verToken = document.getElementById("verToken");
    var token = document.getElementById("token");
    if (verToken && token) {
        verToken.addEventListener("click", function () {
            var mostrar = token.type === "password";
            token.type = mostrar ? "text" : "password";
            verToken.textContent = mostrar ? "Ocultar" : "Mostrar";
            verToken.setAttribute("aria-pressed", mostrar ? "true" : "false");
        });
    }

    // ---- Envio de teste (AJAX + toast) ----
    var form = document.getElementById("waEnviarForm");
    if (form) {
        var btn = document.getElementById("waEnviarBtn");
        var URL = form.dataset.url, CSRF = form.dataset.csrf;
        form.addEventListener("submit", function (e) {
            e.preventDefault();
            if (btn.dataset.enviando) return;
            var mensagem = document.getElementById("wa_mensagem").value.trim();
            var telefone = tel ? tel.value.trim() : "";
            if (!telefone) {
                if (window.mostrarToast) window.mostrarToast("Digite o número do WhatsApp.", "error");
                return;
            }
            if (!mensagem) {
                if (window.mostrarToast) window.mostrarToast("Digite a mensagem.", "error");
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
                body: new URLSearchParams({ telefone: telefone, mensagem: mensagem }).toString(),
            })
                .then(function (r) { return r.json().catch(function () { return { ok: false, erro: "Resposta inválida do servidor." }; }); })
                .then(function (d) {
                    if (d.ok) {
                        if (window.mostrarToast) window.mostrarToast("Mensagem enviada! ✅", "success");
                        document.getElementById("wa_mensagem").value = "";
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
    }
})();
