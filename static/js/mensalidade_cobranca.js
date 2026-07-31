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

    // ---- Canal de envio (WhatsApp × e-mail) ----
    // A contagem "cobrado este mês" é POR CANAL: mandar por e-mail não pode fazer
    // o WhatsApp deixar de sair, então cada canal tem o seu dataset e o seu filtro.
    function canalAtual() {
        var sel = document.getElementById("cobrancaCanal");
        return (sel && sel.value) || "whatsapp";
    }

    // Canais que o envio vai tentar, conforme o seletor.
    function canaisDoEnvio() {
        var c = canalAtual();
        return c === "ambos" ? ["whatsapp", "email"] : [c];
    }

    function campoDoCanal(c) {
        return c === "email" ? "cobradoEmail" : "cobradoWhatsapp";
    }

    function temDestinoNoCanal(li, c) {
        return c === "email" ? li.dataset.temEmail === "1" : li.dataset.temNumero === "1";
    }

    // Em "ambos", basta UM canal com destino para a família entrar no lote.
    function temDestino(li) {
        return canaisDoEnvio().some(function (c) { return temDestinoNoCanal(li, c); });
    }

    // Com o filtro "só quem não recebeu", em "ambos" a família ainda entra se
    // faltar QUALQUER canal — o servidor manda só pelo que falta, sem duplicar.
    function faltaAlgumCanal(li) {
        return canaisDoEnvio().some(function (c) {
            return temDestinoNoCanal(li, c) && (li.dataset[campoDoCanal(c)] || "0") === "0";
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
            body: "so_nao_enviados=0&canal=" + encodeURIComponent(canalAtual())
                + "&usuario_id=" + encodeURIComponent(usuarioId),
        }).then(function (r) { return r.json(); });
    }

    // Recebe o `por_canal` da resposta e atualiza cada contador separadamente.
    function marcaEnviado(li, porCanal) {
        var total = 0;
        ["whatsapp", "email"].forEach(function (c) {
            var q = (porCanal && porCanal[c]) || 0;
            var campo = campoDoCanal(c);
            var n = (parseInt(li.dataset[campo], 10) || 0) + q;
            li.dataset[campo] = String(n);
            total += n;
        });
        var s = li.querySelector(".mens-cobranca-status");
        if (s) {
            var partes = [];
            if (parseInt(li.dataset.cobradoWhatsapp, 10) > 0) partes.push("💬 " + li.dataset.cobradoWhatsapp);
            if (parseInt(li.dataset.cobradoEmail, 10) > 0) partes.push("✉️ " + li.dataset.cobradoEmail);
            s.innerHTML = '<span class="mens-badge mens-badge-isento">Cobrado este mês ('
                + partes.join(" · ") + ')</span>';
        }
        return total;
    }

    // Ao trocar o canal, revalida quais linhas podem receber.
    var selCanal = document.getElementById("cobrancaCanal");
    if (selCanal) {
        var ROTULO_CANAL = {
            whatsapp: "Canal: WhatsApp 💬",
            email: "Canal: e-mail ✉️",
            ambos: "Canal: WhatsApp + e-mail 💬✉️",
        };
        selCanal.addEventListener("change", function () {
            Array.prototype.forEach.call(
                painel.querySelectorAll(".mens-cobranca-item"),
                function (li) {
                    var btn = li.querySelector(".mens-cobranca-enviar");
                    if (btn) btn.disabled = !temDestino(li);
                }
            );
            toast(ROTULO_CANAL[canalAtual()] || "Canal alterado", "success");
        });
    }

    // ---- Trocar o telefone de cobrança da família (persiste no servidor) ----
    var telUrl = painel.dataset.telefoneUrl;
    painel.addEventListener("change", function (e) {
        var sel = e.target.closest(".mens-cob-tel-sel");
        // Exige o `data-usuario`: sem ele não é um seletor de telefone de família
        // (guarda contra outro <select> herdar a classe por engano).
        if (!sel || !sel.dataset.usuario) return;
        var origem = sel.value;
        var anterior = sel.dataset.origemAtual || "";
        sel.disabled = true;
        fetch(telUrl, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrf,
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
            },
            body: "usuario_id=" + encodeURIComponent(sel.dataset.usuario)
                + "&origem=" + encodeURIComponent(origem),
        }).then(function (r) { return r.json(); }).then(function (d) {
            if (!d || !d.ok) {
                toast((d && d.erro) || "Não foi possível trocar o telefone.", "error");
                if (anterior) sel.value = anterior;  // desfaz visualmente
                return;
            }
            sel.dataset.origemAtual = origem;
            // Passou a ter número válido: habilita o envio individual e o lote.
            var li = sel.closest(".mens-cobranca-item");
            if (li) {
                li.dataset.temNumero = "1";
                var btn = li.querySelector(".mens-cobranca-enviar");
                if (btn) btn.disabled = false;
            }
            var txtOpc = sel.options[sel.selectedIndex] ? sel.options[sel.selectedIndex].text : d.numero;
            toast("Telefone de cobrança alterado ✅ (" + txtOpc + ")", "success");
        }).catch(function () {
            toast("Falha de conexão ao trocar o telefone.", "error");
            if (anterior) sel.value = anterior;
        }).finally(function () { sel.disabled = false; });
    });

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
                if (li) marcaEnviado(li, d.por_canal);
                toast(d.enviados > 1 ? "Cobrança enviada nos 2 canais!" : "Cobrança enviada!",
                      "success");
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
        var lib = document.getElementById("cobrancaSoLiberados");
        var soLiberados = lib && lib.checked;
        var usaWhatsapp = canaisDoEnvio().indexOf("whatsapp") !== -1;
        return Array.prototype.filter.call(
            painel.querySelectorAll(".mens-cobranca-item"),
            function (li) {
                if (!temDestino(li)) return false;
                if (soNao && !faltaAlgumCanal(li)) return false;
                // O filtro "só liberados" é do gate do WhatsApp (quem escreveu ao
                // clube). No e-mail o gate é outro (descadastro/bounce) e roda no
                // servidor. Em "ambos" ele não pode excluir a família, senão
                // barraria também o e-mail — o servidor resolve por canal.
                if (canalAtual() === "whatsapp" && usaWhatsapp && soLiberados
                    && li.dataset.liberado !== "1") return false;
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
            if (d.enviados) { lote.ok += d.enviados; marcaEnviado(li, d.por_canal); }
            else { lote.falhas++; }
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
