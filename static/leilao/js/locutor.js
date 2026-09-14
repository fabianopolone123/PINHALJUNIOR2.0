/*
 * locutor.js — a mesa de comando.
 *
 * Escuta o MESMO stream SSE do participante (o pregão é um só) e acrescenta as
 * ações da mesa. Todo botão manda `acao` para um POST único — assim existe um
 * lugar só no servidor decidindo o que cada comando faz.
 *
 * O histórico completo de lances vem por `fetch` (`locutor/dados/`), não pelo
 * stream: ele é grande e só interessa a quem está na mesa; mandá-lo no
 * broadcast pesaria na conexão de 50 celulares que não vão usá-lo.
 */
(function () {
    "use strict";

    function $(id) { return document.getElementById(id); }

    var dados = $("dadosMesa");
    if (!dados || !$("mesaCronoTexto")) return;   // lotes.html usa outro script

    var CSRF = dados.dataset.csrf;
    var URL_ACAO = dados.dataset.acaoUrl;
    var URL_DADOS = dados.dataset.dadosUrl;
    var URL_STREAM = dados.dataset.streamUrl;

    var estado = JSON.parse(($("estadoInicial") || {}).textContent || "{}");
    var offset = 0;
    var ultimoSegundo = null;

    function agora() { return Date.now() + offset; }

    function calibrar(e) {
        if (e && e.servidor_em) {
            var t = Date.parse(e.servidor_em);
            if (!isNaN(t)) offset = t - Date.now();
        }
    }

    function moeda(v) {
        var n = parseFloat(v || 0);
        if (isNaN(n)) n = 0;
        return "R$ " + n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function mmss(s) {
        s = Math.max(0, Math.floor(s));
        return Math.floor(s / 60) + ":" + (s % 60 < 10 ? "0" : "") + (s % 60);
    }

    function hora(iso) {
        var d = new Date(iso);
        if (isNaN(d.getTime())) return "";
        return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    }

    function toast(msg, tipo) {
        if (window.mostrarToast) window.mostrarToast(msg, tipo || "info");
    }

    function acao(corpo) {
        return fetch(URL_ACAO, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": CSRF,
                "X-Requested-With": "XMLHttpRequest"
            },
            body: JSON.stringify(corpo)
        }).then(function (r) { return r.json().catch(function () { return {}; }); })
          .then(function (d) {
              if (d.msg) toast(d.msg, d.ok ? "success" : "error");
              return d;
          })
          .catch(function () { toast("Sem conexão com o servidor.", "error"); });
    }

    /* ---------------------------------------------------------------
       Desenho
       --------------------------------------------------------------- */
    function render(novo) {
        if (novo) { estado = novo; calibrar(novo); }
        var lote = estado && estado.ativo ? estado.lote : null;

        if ($("online") && estado && typeof estado.online === "number") {
            $("online").textContent = estado.online;
        }

        var foto = $("mesaFoto");
        if (lote) {
            $("mesaEtiqueta").textContent =
                (numeroAtual ? "Item nº " + numeroAtual + " · " : "") +
                "Em pregão" + (lote.voltas ? " · voltou " + lote.voltas + "x" : "");
            $("mesaNome").textContent = lote.nome;
            $("mesaDesc").textContent = lote.descricao || "";
            $("mesaValor").textContent = moeda(lote.tem_lance ? lote.valor_atual : lote.lance_inicial);
            $("mesaLider").textContent = lote.lider ? lote.lider.nome : "ninguém ainda";
            $("mesaProximo").textContent = moeda(lote.proximo_valor);
            if (lote.foto) { foto.src = lote.foto; foto.hidden = false; } else { foto.hidden = true; }
        } else {
            $("mesaEtiqueta").textContent = "Nenhum item em pregão";
            $("mesaNome").textContent = "—";
            $("mesaDesc").textContent = "";
            $("mesaValor").textContent = moeda(0);
            $("mesaLider").textContent = "—";
            $("mesaProximo").textContent = moeda(0);
            foto.hidden = true;
        }

        desenharFila();
        desenharChatMesa();
        tick();
    }

    var filaCache = [];
    // Número do item em pregão. Vem do fetch da mesa, NÃO do broadcast — no
    // broadcast ele contaria ao público quantos itens existem.
    var numeroAtual = null;

    function desenharFila(fila, restam) {
        var ul = $("fila");
        if (!ul) return;
        if (fila) filaCache = fila;
        fila = filaCache;
        ul.innerHTML = "";
        $("contaFila").textContent = restam ? "(" + restam + ")" : "";
        if (!fila.length) {
            var li = document.createElement("li");
            li.className = "vazio";
            li.textContent = "A fila está vazia.";
            ul.appendChild(li);
            return;
        }
        fila.forEach(function (l, i) {
            var li = document.createElement("li");
            var nome = document.createElement("span");
            nome.className = "nome";
            // O número do ITEM (a etiqueta colada na caixa), não a posição na
            // fila: é por ele que se acha o objeto na prateleira, e a posição
            // muda toda vez que a noite é reorganizada.
            nome.textContent = "nº " + l.numero + " — " + l.nome;
            li.appendChild(nome);

            var b = document.createElement("button");
            b.type = "button";
            b.className = "btn-mini destaque";
            b.textContent = "▶ Abrir";
            b.addEventListener("click", function () { acao({ acao: "abrir", lote: l.id }); });
            li.appendChild(b);
            ul.appendChild(li);
        });
    }

    function desenharHistorico(lista) {
        var ul = $("historico");
        if (!ul) return;
        ul.innerHTML = "";
        if (!lista || !lista.length) {
            var li = document.createElement("li");
            li.className = "vazio";
            li.textContent = "Nenhum lance ainda.";
            ul.appendChild(li);
            return;
        }
        lista.forEach(function (l) {
            var li = document.createElement("li");
            if (l.cancelado) li.className = "cancelado";
            var quem = document.createElement("span");
            quem.className = "quem";
            quem.textContent = l.quem;
            var quanto = document.createElement("span");
            quanto.className = "quanto";
            quanto.textContent = moeda(l.valor);
            var quando = document.createElement("span");
            quando.className = "quando";
            quando.textContent = hora(l.em);
            li.appendChild(quem);
            li.appendChild(quanto);
            li.appendChild(quando);
            ul.appendChild(li);
        });
    }

    var chatCache = [];

    function desenharChatMesa(mensagens) {
        var ul = $("chatMesa");
        if (!ul) return;
        if (mensagens) chatCache = mensagens;

        var c = estado && estado.chat;
        var alvo = $("chatEstadoMesa");
        if (alvo) {
            alvo.textContent = c && c.aberto
                ? "aberto · fecha em " + mmss((Date.parse(c.ate) - agora()) / 1000)
                : "fechado para os participantes";
        }
        ul.innerHTML = "";
        if (!chatCache.length) {
            var vazio = document.createElement("li");
            vazio.className = "vazio";
            vazio.textContent = "Nenhuma mensagem ainda.";
            ul.appendChild(vazio);
        } else {
            chatCache.forEach(function (m) { ul.appendChild(linhaChat(m)); });
        }
        ul.scrollTop = ul.scrollHeight;
    }

    function linhaChat(m) {
        var li = document.createElement("li");
        if (!m.autor_id) li.className = "locutor";
        var b = document.createElement("span");
        b.className = "autor";
        b.textContent = m.autor + ": ";
        li.appendChild(b);
        li.appendChild(document.createTextNode(m.texto));
        return li;
    }

    /* ---------------------------------------------------------------
       Cronômetro
       --------------------------------------------------------------- */
    /* Conta para CIMA: há quanto tempo a sala está calada.
       Sem fechamento automático não existe prazo — o que decide o martelo é o
       silêncio, e é isso que este número mostra. Passando de 15s ele chama
       atenção; de 30s, grita. */
    function tick() {
        var lote = estado && estado.ativo ? estado.lote : null;
        var caixa = $("mesaCrono");
        var txt = $("mesaCronoTexto");
        if (!caixa || !txt) return;

        if (!lote) {
            txt.textContent = "--";
            $("mesaCronoRotulo").textContent = "sem item em pregão";
            caixa.className = "mesa-crono";
            return;
        }

        // Não é contagem regressiva: é o contrário. Conta para CIMA desde o
        // último lance, porque o que ajuda a decidir o martelo é há quanto
        // tempo a sala está calada.
        var parado = lote.parado_desde
            ? Math.max(0, (agora() - Date.parse(lote.parado_desde)) / 1000)
            : 0;
        caixa.className = "mesa-crono" + (parado >= 30 ? " final" : parado >= 15 ? " apertado" : "");
        $("mesaCronoRotulo").textContent = parado >= 30 ? "sala calada — martelo?" : "sem lance há";
        txt.textContent = mmss(parado);
    }
    setInterval(tick, 250);
    setInterval(desenharChatMesa, 5000);

    /* ---------------------------------------------------------------
       Stream
       --------------------------------------------------------------- */
    var recargaAgendada = null;

    /* O histórico completo vem por `fetch`, e numa disputa quente chega um lance
       por segundo. Sem o agrupamento abaixo, a mesa dispararia uma consulta por
       lance — justo quando o servidor está mais ocupado atendendo o pregão. */
    function recarregarDados() {
        if (recargaAgendada) return;
        recargaAgendada = setTimeout(function () {
            recargaAgendada = null;
            fetch(URL_DADOS, { headers: { "X-Requested-With": "XMLHttpRequest" } })
                .then(function (r) { return r.json(); })
                .then(function (d) {
                    if (!d.ok) return;
                    // O número ANTES do render: é ele que a etiqueta do item em
                    // pregão desenha, e pintar duas vezes só pisca na tela.
                    numeroAtual = d.numero_atual;
                    render(d.estado);
                    desenharHistorico(d.historico);
                    // A fila e o histórico do chat NÃO vêm no broadcast: o
                    // público não pode saber quantos itens faltam, e o fio da
                    // conversa da noite é só da mesa.
                    desenharFila(d.fila, d.restam_na_fila);
                    desenharChatMesa(d.chat);
                })
                .catch(function () { /* a próxima volta resolve */ });
        }, 700);
    }

    var fonte = new EventSource(URL_STREAM);

    fonte.addEventListener("estado", function (e) { render(JSON.parse(e.data)); recarregarDados(); });
    fonte.addEventListener("lote_aberto", function (e) { render(JSON.parse(e.data)); recarregarDados(); });
    fonte.addEventListener("lance", function (e) {
        var d = JSON.parse(e.data);
        if (estado && estado.ativo) { estado.lote = d.lote; render(estado); }
        recarregarDados();
    });
    fonte.addEventListener("lote_vendido", function (e) {
        var d = JSON.parse(e.data);
        render(d.estado);
        desenharHistorico([]);
        if (d.vendido) toast("Vendido para " + d.vencedor + " — " + moeda(d.valor), "success");
        else toast("Item sem lance: voltou para a fila.", "info");
    });
    fonte.addEventListener("chat", function (e) {
        // Teto: a mesa fica aberta a noite inteira e não pode acumular memória.
        chatCache = chatCache.concat([JSON.parse(e.data)]).slice(-120);
        desenharChatMesa();
    });
    fonte.addEventListener("chat_estado", function (e) {
        var d = JSON.parse(e.data);
        if (!estado.chat) estado.chat = {};
        estado.chat.aberto = d.aberto;
        estado.chat.ate = d.ate;
        // O histórico da MESA não zera no intervalo — só o dos participantes.
        desenharChatMesa();
    });
    fonte.addEventListener("online", function (e) {
        var d = JSON.parse(e.data);
        if (estado) estado.online = d.online;
        if ($("online")) $("online").textContent = d.online;
    });
    fonte.addEventListener("arremate_expirado", function (e) {
        var d = JSON.parse(e.data);
        render(d.estado);
        toast("Prazo vencido: " + d.lote + " voltou para a fila.", "error");
    });
    fonte.addEventListener("pagamento", function () {
        toast("Pagamento confirmado.", "success");
    });

    /* ---------------------------------------------------------------
       Botões
       --------------------------------------------------------------- */
    document.addEventListener("click", function (e) {
        var alvo = e.target.closest("[data-acao]");
        if (!alvo) return;
        var qual = alvo.dataset.acao;

        if (qual === "chat-fechar") { acao({ acao: "chat", fechar: true }); return; }
        if (qual === "microfone") return;   // tratado abaixo

        var corpo = { acao: qual };
        if (alvo.dataset.lote) corpo.lote = alvo.dataset.lote;
        if (alvo.dataset.arremate) corpo.arremate = alvo.dataset.arremate;
        if (alvo.dataset.participante) corpo.participante = alvo.dataset.participante;
        if (alvo.dataset.direcao) corpo.direcao = alvo.dataset.direcao;

        // Bater o martelo mexe em dinheiro: confirma.
        if (qual === "fechar" && !window.confirm("Bater o martelo e fechar este item?")) return;

        // Abrir outro item com um pregão ACONTECENDO joga o atual de volta para a
        // fila e a disputa se perde. É um acidente fácil de cometer falando ao
        // mesmo tempo — e caro, porque há gente disputando naquele instante.
        if (qual === "abrir") {
            var atual = estado && estado.ativo ? estado.lote : null;
            if (atual && atual.tem_lance) {
                var aviso = "O item “" + atual.nome + "” está em disputa por " +
                    moeda(atual.valor_atual) + " (" + (atual.lider ? atual.lider.nome : "—") + ").\n\n" +
                    "Abrir outro joga este de volta para a fila e a disputa se perde.\n" +
                    "Para vender, use o botão VENDIDO.\n\nAbrir outro mesmo assim?";
                if (!window.confirm(aviso)) return;
            }
        }

        acao(corpo).then(function (d) {
            if (!d) return;
            if (qual === "pago" || qual === "bloquear") { window.location.reload(); return; }
            recarregarDados();
        });
    });

    var avisoForm = $("avisoForm");
    if (avisoForm) {
        avisoForm.addEventListener("submit", function (e) {
            e.preventDefault();
            var campo = $("avisoTexto");
            var texto = campo.value.trim();
            if (!texto) return;
            campo.value = "";
            acao({ acao: "aviso", texto: texto });
        });
    }

    /* ---------------------------------------------------------------
       Abas
       --------------------------------------------------------------- */
    document.querySelectorAll(".mesa-aba").forEach(function (b) {
        b.addEventListener("click", function () {
            document.querySelectorAll(".mesa-aba").forEach(function (x) { x.classList.remove("ativa"); });
            b.classList.add("ativa");
            document.querySelectorAll(".mesa-secao").forEach(function (s) {
                s.hidden = s.dataset.secao !== b.dataset.aba;
                s.classList.toggle("ativa", !s.hidden);
            });
        });
    });

    /* ---------------------------------------------------------------
       Busca de pessoas (padrão do usuarios.js: sem acento, sem caixa)
       --------------------------------------------------------------- */
    var busca = $("buscaPessoas");
    if (busca) {
        busca.addEventListener("input", function () {
            var termo = busca.value.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
            document.querySelectorAll("#listaPessoas .pessoa").forEach(function (li) {
                var alvo = (li.dataset.busca || "").normalize("NFD")
                    .replace(/[̀-ͯ]/g, "").toLowerCase();
                li.classList.toggle("busca-oculto", termo !== "" && alvo.indexOf(termo) === -1);
            });
        });
    }

    /* ---------------------------------------------------------------
       Microfone (WHIP)
       --------------------------------------------------------------- */
    var btnMic = $("btnMicrofone");
    if (btnMic && window.AudioFalar) {
        btnMic.addEventListener("click", function () {
            if (window.AudioFalar.ativo()) {
                window.AudioFalar.parar();
                btnMic.textContent = "🎤 Transmitir";
                btnMic.classList.remove("ligado");
                $("microEstado").textContent = "Desligado. Ninguém está ouvindo você pelo sistema.";
                $("microBarra").style.width = "0%";
                return;
            }
            btnMic.disabled = true;
            $("microEstado").textContent = "Pedindo acesso ao microfone…";
            window.AudioFalar.iniciar(
                btnMic.dataset.whip,
                function (nivel) {
                    $("microBarra").style.width = Math.min(100, nivel * 140) + "%";
                },
                btnMic.dataset.whipUsuario,
                btnMic.dataset.whipSenha
            ).then(function (ok) {
                btnMic.disabled = false;
                if (ok) {
                    btnMic.textContent = "⏹ Parar transmissão";
                    btnMic.classList.add("ligado");
                    $("microEstado").textContent = "🔴 No ar — todos que ligaram o som estão ouvindo você.";
                    toast("Transmissão de voz ligada.", "success");
                } else {
                    $("microEstado").textContent = "Não consegui transmitir. Confira o microfone e o servidor de áudio.";
                    toast("Falha ao ligar o microfone.", "error");
                }
            });
        });
    }

    /* A mesa é a tela que MENOS pode apagar: quem está conduzindo passa minutos
       falando sem tocar no aparelho. O Chrome concede o bloqueio sem gesto
       quando a aba está à frente; o primeiro clique em qualquer lugar cobre os
       navegadores que exigem gesto. */
    if (window.TelaAcesa) {
        window.TelaAcesa.ligar();
        document.addEventListener("click", function reforcar() {
            window.TelaAcesa.ligar();
            document.removeEventListener("click", reforcar);
        });
    }

    render(estado);
    recarregarDados();
})();
