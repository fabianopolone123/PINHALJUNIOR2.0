/* =========================================================
   Módulo WhatsApp (W-API): pré-visualização do telefone no formato
   de envio, botão mostrar/ocultar token e envio de teste via AJAX
   com o toast padrão do sistema. JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    // ---- Copiar (qualquer botão com data-target apontando um input) ----
    document.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-target]");
        if (!btn) return;
        var inp = document.getElementById(btn.dataset.target);
        if (!inp) return;
        inp.select();
        if (navigator.clipboard) navigator.clipboard.writeText(inp.value);
        else document.execCommand("copy");
        if (window.mostrarToast) window.mostrarToast("Copiado!", "success");
    });

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

    // ---- Webhook: configurar + copiar URL + últimas 5 mensagens (poll) ----
    var painelWebhook = document.querySelector('.wa-painel[data-painel="webhook"]');
    if (painelWebhook) {
        var csrfWh = painelWebhook.dataset.csrf;
        var esc = function (s) {
            var d = document.createElement("div"); d.textContent = s == null ? "" : String(s); return d.innerHTML;
        };
        // Configurar webhook na W-API
        var btnCfg = document.getElementById("waWebhookConfig");
        if (btnCfg) {
            btnCfg.addEventListener("click", function () {
                if (btnCfg.dataset.ok) return;
                btnCfg.dataset.ok = "1"; btnCfg.disabled = true;
                var t = btnCfg.textContent; btnCfg.textContent = "Configurando…";
                fetch(painelWebhook.dataset.configUrl, {
                    method: "POST",
                    headers: { "X-CSRFToken": csrfWh, "X-Requested-With": "XMLHttpRequest",
                        "Content-Type": "application/x-www-form-urlencoded" },
                }).then(function (r) { return r.json(); }).then(function (d) {
                    if (window.mostrarToast) window.mostrarToast(
                        d.ok ? "Webhook configurado na W-API! ✅" : (d.erro || "Não foi possível configurar."),
                        d.ok ? "success" : "error");
                }).catch(function () {
                    if (window.mostrarToast) window.mostrarToast("Falha de conexão.", "error");
                }).finally(function () {
                    delete btnCfg.dataset.ok; btnCfg.disabled = false; btnCfg.textContent = t;
                });
            });
        }
        // Últimas mensagens recebidas
        var listaEv = document.getElementById("waEventosLista");
        var vazioEv = document.getElementById("waEventosVazio");
        var carregarEventos = function () {
            fetch(painelWebhook.dataset.eventosUrl, { headers: { "X-Requested-With": "XMLHttpRequest" } })
                .then(function (r) { return r.json(); })
                .then(function (d) {
                    if (!d || !d.ok) return;
                    listaEv.innerHTML = "";
                    (d.eventos || []).forEach(function (e) {
                        var li = document.createElement("li");
                        li.className = "wa-evento-item";
                        var tags = (e.is_group ? '<span class="wa-evento-tag">grupo</span>' : "")
                            + (e.from_me ? '<span class="wa-evento-tag">enviada por mim</span>' : "");
                        li.innerHTML = '<div class="wa-evento-topo">'
                            + '<span class="wa-evento-de">' + esc(e.contact_name) + ' · ' + esc(e.phone) + '</span>'
                            + '<span class="wa-evento-hora">' + esc(e.recebido_em) + '</span></div>'
                            + '<div class="wa-evento-txt">' + esc(e.message_text) + '</div>'
                            + '<div class="wa-evento-meta">' + esc(e.event_type) + ' ' + tags + '</div>';
                        listaEv.appendChild(li);
                    });
                    if (vazioEv) vazioEv.hidden = (d.eventos || []).length > 0;
                }).catch(function () {});
        };
        var btnRefresh = document.getElementById("waEventosRefresh");
        if (btnRefresh) btnRefresh.addEventListener("click", carregarEventos);
        // Poll a cada 5s só enquanto a aba Webhook está visível.
        setInterval(function () {
            if (!painelWebhook.hidden) carregarEventos();
        }, 5000);
        if (!painelWebhook.hidden) carregarEventos();
        // Carrega ao entrar na aba.
        var abaWh = document.querySelector('.wa-aba[data-aba="webhook"]');
        if (abaWh) abaWh.addEventListener("click", carregarEventos);
    }

    // ---- Reengajar inativos (um a um, 10s entre cada, barra + cancelar) ----
    var painelLib = document.querySelector('.wa-painel[data-painel="liberacao"]');
    var btnReeng = document.getElementById("waReengajarBtn");
    if (painelLib && btnReeng) {
        var RE_DELAY = 10000;
        var reFill = document.getElementById("waReengajarFill");
        var reTxt = document.getElementById("waReengajarTxt");
        var reProg = document.getElementById("waReengajarProg");
        var reN = document.getElementById("waReengajarN");
        var reCancel = document.getElementById("waReengajarCancelar");
        var reAlvos = [];
        try { reAlvos = JSON.parse((document.getElementById("reengajarAlvos") || {}).textContent || "[]"); } catch (e) { reAlvos = []; }
        var reToast = function (m, t) { if (window.mostrarToast) window.mostrarToast(m, t); };
        var reLote = { on: false, cancel: false, timer: null, i: 0, ok: 0, fail: 0 };

        var reBarra = function () { if (reFill) reFill.style.width = Math.round(reLote.i / (reAlvos.length || 1) * 100) + "%"; };
        var reFim = function (c) {
            if (reLote.timer) { clearTimeout(reLote.timer); reLote.timer = null; }
            reLote.on = false; if (reProg) reProg.hidden = true; btnReeng.disabled = false;
            if (reN) reN.textContent = Math.max(0, reAlvos.length - reLote.ok);
            reToast((c ? "Cancelado. " : "Concluído. ") + "Reengajados: " + reLote.ok
                + (reLote.fail ? " · " + reLote.fail + " falha(s)" : ""), reLote.ok ? "success" : "error");
        };
        var reEnviar = function (uid) {
            return fetch(painelLib.dataset.reengajarUrl, {
                method: "POST",
                headers: { "X-CSRFToken": painelLib.dataset.csrf, "Content-Type": "application/x-www-form-urlencoded", "X-Requested-With": "XMLHttpRequest" },
                body: "usuario_id=" + encodeURIComponent(uid),
            }).then(function (r) { return r.json(); });
        };
        var reProximo = function () {
            if (reLote.cancel || reLote.i >= reAlvos.length) { reFim(reLote.cancel); return; }
            var a = reAlvos[reLote.i];
            if (reTxt) reTxt.textContent = "Enviando " + (reLote.i + 1) + " de " + reAlvos.length + "…";
            reEnviar(a.usuario_id).then(function (d) {
                if (d && d.ok) reLote.ok++; else reLote.fail++;
                reLote.i++; reBarra();
                if (reLote.cancel || reLote.i >= reAlvos.length) { reFim(reLote.cancel); return; }
                if (reTxt) reTxt.textContent = "Enviado " + reLote.i + " de " + reAlvos.length + " · aguardando 10s… (pode cancelar)";
                reLote.timer = setTimeout(reProximo, RE_DELAY);
            }).catch(function () {
                reLote.fail++; reLote.i++; reBarra();
                if (reLote.cancel || reLote.i >= reAlvos.length) { reFim(reLote.cancel); return; }
                reLote.timer = setTimeout(reProximo, RE_DELAY);
            });
        };
        btnReeng.addEventListener("click", function () {
            if (reLote.on) return;
            if (!reAlvos.length) { reToast("Nenhum inativo para reengajar agora.", "error"); return; }
            if (!window.confirm("Enviar reengajamento para " + reAlvos.length + " contato(s)?\nHá um intervalo de 10s entre cada envio — você pode cancelar.")) return;
            reLote = { on: true, cancel: false, timer: null, i: 0, ok: 0, fail: 0 };
            btnReeng.disabled = true; if (reProg) reProg.hidden = false; reBarra(); reProximo();
        });
        if (reCancel) reCancel.addEventListener("click", function () {
            if (!reLote.on) return; reLote.cancel = true;
            if (reLote.timer) { clearTimeout(reLote.timer); reLote.timer = null; reFim(true); }
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
