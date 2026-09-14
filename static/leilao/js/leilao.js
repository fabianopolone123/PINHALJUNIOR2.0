/*
 * leilao.js — a tela do participante.
 *
 * Recebe os eventos do pregão por SSE (`EventSource`) e redesenha. Decisões que
 * explicam o arquivo inteiro:
 *
 * 1. **O relógio é do servidor.** Cada estado traz `servidor_em`; daí sai um
 *    `offset` que é somado ao relógio do aparelho. Celular com a hora errada
 *    (tem muitos) vê o mesmo cronômetro que todo mundo.
 * 2. **O toque responde na hora** (otimista): o botão pinta o novo valor antes
 *    da resposta do servidor, e o evento que volta corrige. A verdade continua
 *    sendo a do servidor — a tela só não fica parada esperando a rede.
 * 3. **Reconexão não tem lógica de replay.** O `EventSource` reconecta sozinho
 *    e o servidor manda o estado INTEIRO; quem volta está sempre correto.
 */
(function () {
    "use strict";

    function $(id) { return document.getElementById(id); }

    var dados = $("dadosLeilao");
    if (!dados) return;

    var URLS = JSON.parse($("urlsLeilao").textContent);
    var CSRF = dados.dataset.csrf;
    var EU = parseInt(dados.dataset.eu, 10) || null;
    var EU_CHAVE = dados.dataset.euChave || "";
    var AUDIO_URL = dados.dataset.audio || "";

    var estado = JSON.parse($("estadoInicial").textContent || "{}");
    var offset = 0;            // relógio do servidor − relógio daqui
    var fonte = null;          // EventSource
    var loteId = null;
    var valorMostrado = null;
    var liderMostrado = "-";
    // "Já liderei este item alguma vez" — é o que distingue *perder a liderança*
    // de *nunca ter dado lance*. Sem isso, quem só está assistindo veria a tela
    // vermelha de "te superaram".
    var euJaLiderei = false;
    var ultimoSegundo = null;
    var somLigado = false;
    var gavetaAberta = false;
    var arremateAberto = null;
    var codigoPix = "";

    /* ---------------------------------------------------------------
       Utilidades
       --------------------------------------------------------------- */
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
        return "R$ " + n.toLocaleString("pt-BR", {
            minimumFractionDigits: 2, maximumFractionDigits: 2
        });
    }

    function mmss(s) {
        s = Math.max(0, Math.floor(s));
        var m = Math.floor(s / 60);
        var r = s % 60;
        return m + ":" + (r < 10 ? "0" : "") + r;
    }

    function toast(msg, tipo) {
        if (window.mostrarToast) window.mostrarToast(msg, tipo || "info");
    }

    function vibrar(padrao) {
        if (navigator.vibrate) { try { navigator.vibrate(padrao); } catch (e) { /* nada */ } }
    }

    function post(url, corpo) {
        return fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": CSRF,
                "X-Requested-With": "XMLHttpRequest"
            },
            body: JSON.stringify(corpo || {})
        }).then(function (r) { return r.json().catch(function () { return {}; }); });
    }

    /* ---------------------------------------------------------------
       Efeitos
       --------------------------------------------------------------- */
    function flash() {
        var d = document.createElement("div");
        d.className = "flash";
        document.body.appendChild(d);
        setTimeout(function () { d.remove(); }, 450);
    }

    function onda(botao, evento) {
        var r = botao.getBoundingClientRect();
        var tam = Math.max(r.width, r.height);
        var x = (evento && evento.clientX ? evento.clientX : r.left + r.width / 2) - r.left;
        var y = (evento && evento.clientY ? evento.clientY : r.top + r.height / 2) - r.top;
        var d = document.createElement("span");
        d.className = "onda";
        d.style.width = d.style.height = tam + "px";
        d.style.left = (x - tam / 2) + "px";
        d.style.top = (y - tam / 2) + "px";
        botao.appendChild(d);
        setTimeout(function () { d.remove(); }, 600);
    }

    /* ---------------------------------------------------------------
       Desenho
       --------------------------------------------------------------- */
    function render(novo) {
        if (novo) { estado = novo; calibrar(novo); }

        var temLeilao = estado && estado.ativo;
        var lote = temLeilao ? estado.lote : null;

        $("palcoVazio").hidden = !!temLeilao;
        $("palcoPregao").hidden = !lote;
        $("palcoIntervalo").hidden = !(temLeilao && !lote);

        var selo = $("seloVivo");
        if (selo) selo.classList.toggle("parado", !lote);

        if (estado && typeof estado.online === "number") {
            $("online").textContent = estado.online;
        }

        if (temLeilao && !lote) {
            var restam = estado.restam_na_fila || 0;
            $("intervaloTexto").textContent = restam
                ? "Preparando o próximo item… faltam " + restam + " na fila."
                : "O locutor está organizando o próximo item.";
        }

        if (lote) desenharLote(lote);
        desenharChat();
        desenharBarra();
        precarregarProxima();
        tick();
    }

    var precarregadas = {};

    /* Baixa a foto do PRÓXIMO item enquanto o atual ainda está em disputa.
       Quando o locutor abrir, a imagem já está no cache do navegador e a tela
       muda no mesmo instante — em vez de piscar um quadro vazio justo no
       segundo em que todo mundo está olhando. */
    function precarregarProxima() {
        var fila = (estado && estado.fila) || [];
        if (!fila.length) return;
        var url = fila[0].foto || fila[0].foto_mini;
        if (!url || precarregadas[url]) return;
        precarregadas[url] = true;
        var img = new Image();
        img.src = url;
    }

    function desenharLote(lote) {
        var trocouLote = loteId !== lote.id;
        loteId = lote.id;

        if (trocouLote) {
            $("loteNome").textContent = lote.nome || "—";
            $("loteDesc").textContent = lote.descricao || "";
            var img = $("loteImg");
            var vazio = $("loteSemFoto");
            if (lote.foto) {
                img.src = lote.foto;
                img.alt = lote.nome || "";
                img.hidden = false;
                vazio.hidden = true;
            } else {
                img.hidden = true;
                img.removeAttribute("src");
                vazio.hidden = false;
            }
            $("loteVolta").hidden = !(lote.voltas > 0);
            valorMostrado = null;
            liderMostrado = "-";
            euJaLiderei = false;
            ultimoSegundo = null;
            desenharUltimos(estado.ultimos_lances || []);
        }

        // "Sou eu que estou ganhando?" — pelo id OU pela chave da pessoa. A
        // segunda cobre quem abriu o leilão em dois aparelhos: são registros
        // diferentes, mesma pessoa. Sem ela, o botão ficaria ativo no segundo
        // aparelho e a pessoa cobriria o próprio lance.
        var euGanhando = !!(lote.lider && (
            (EU && lote.lider.id === EU) ||
            (EU_CHAVE && lote.lider.chave === EU_CHAVE)
        ));
        if (euGanhando) euJaLiderei = true;

        // --- Quem está ganhando ---
        var rotulo = $("liderRotulo");
        var nome = $("liderNome");
        var valor = $("liderValor");

        if (!lote.tem_lance) {
            rotulo.textContent = "Lance inicial";
            nome.textContent = "Ninguém ainda";
        } else {
            rotulo.textContent = euGanhando ? "🟢 VOCÊ ESTÁ GANHANDO" : "Está ganhando";
            nome.textContent = lote.lider ? lote.lider.nome : "—";
        }

        if (nome.textContent !== liderMostrado) {
            liderMostrado = nome.textContent;
            if (!trocouLote) {
                nome.classList.remove("trocou");
                void nome.offsetWidth;   // reinicia a animação
                nome.classList.add("trocou");
            }
        }

        var valorAtual = lote.tem_lance ? lote.valor_atual : lote.lance_inicial;
        var texto = moeda(valorAtual);
        if (valor.textContent !== texto) {
            valor.textContent = texto;
            if (!trocouLote && valorMostrado !== null) {
                valor.classList.remove("subiu");
                void valor.offsetWidth;
                valor.classList.add("subiu");
            }
            valorMostrado = valorAtual;
        }

        // O estado "te superaram" PERMANECE até a pessoa cobrir o lance — não é
        // um piscar. É a informação mais importante da tela para quem está
        // disputando, e ela pode estar olhando para o celular só de vez em quando.
        var superado = !euGanhando && lote.tem_lance && euJaLiderei;

        var pregao = document.querySelector(".pregao");
        pregao.classList.toggle("eu-ganhando", euGanhando && lote.tem_lance);
        pregao.classList.toggle("superado", superado);
        if (superado) rotulo.textContent = "🔴 TE SUPERARAM";

        // --- Botão ---
        var btn = $("btnLance");
        $("btnLanceValor").textContent = moeda(lote.proximo_valor);
        $("dicaIncremento").textContent = moeda(lote.incremento);
        btn.classList.toggle("ganhando", euGanhando);
        btn.disabled = euGanhando || lote.pausado;
        btn.querySelector(".btn-lance-rotulo").textContent =
            euGanhando ? "VOCÊ ESTÁ GANHANDO"
            : lote.pausado ? "PAUSADO"
            : superado ? "COBRIR O LANCE"
            : "DAR LANCE";
        $("acaoDica").hidden = euGanhando;
    }

    function liderEra(quem) {
        var lote = estado && estado.ativo ? estado.lote : null;
        if (!lote || !lote.lider) return false;
        if (quem && lote.lider.id === quem) return true;
        return !!(EU_CHAVE && lote.lider.chave === EU_CHAVE);
    }

    function desenharUltimos(lances) {
        var lista = $("ultimosLista");
        var caixa = $("ultimos");
        if (!lances || !lances.length) { caixa.hidden = true; lista.innerHTML = ""; return; }
        caixa.hidden = false;
        lista.innerHTML = "";
        lances.forEach(function (l) { lista.appendChild(linhaLance(l)); });
    }

    function linhaLance(l) {
        var li = document.createElement("li");
        if (EU && l.quem_id === EU) li.className = "meu";
        var quem = document.createElement("span");
        quem.className = "quem";
        quem.textContent = (EU && l.quem_id === EU) ? "Você" : l.quem;
        var quanto = document.createElement("span");
        quanto.className = "quanto";
        quanto.textContent = moeda(l.valor);
        li.appendChild(quem);
        li.appendChild(quanto);
        return li;
    }

    function empurrarLance(l) {
        var lista = $("ultimosLista");
        $("ultimos").hidden = false;
        var li = linhaLance(l);
        li.classList.add("novo");
        lista.insertBefore(li, lista.firstChild);
        while (lista.children.length > 6) lista.removeChild(lista.lastChild);
    }

    function desenharBarra() {
        var info = $("barraInfo");
        if (!estado || !estado.ativo) { info.textContent = ""; return; }
        var partes = [];
        if (estado.restam_na_fila) partes.push(estado.restam_na_fila + " na fila");
        if (estado.vendidos) partes.push(estado.vendidos + " vendidos");
        info.textContent = partes.join(" · ");
    }

    /* ---------------------------------------------------------------
       Cronômetro (200ms — suficiente para parecer contínuo)
       --------------------------------------------------------------- */
    function tick() {
        var lote = estado && estado.ativo ? estado.lote : null;
        var crono = $("cronometro");
        var txt = $("cronoTexto");
        var anel = $("cronoAnel");
        if (!lote || !crono) return;

        var restante;
        if (lote.pausado) {
            restante = lote.segundos || 0;
            crono.classList.add("pausado");
            txt.textContent = "pausa";
        } else {
            crono.classList.remove("pausado");
            restante = lote.fecha_em
                ? Math.max(0, (Date.parse(lote.fecha_em) - agora()) / 1000)
                : 0;
            txt.textContent = mmss(restante);
        }

        var total = parseFloat(lote.total_segundos || 60) || 60;
        var pct = Math.max(0, Math.min(100, (restante / total) * 100));
        if (anel) anel.setAttribute("stroke-dasharray", pct.toFixed(1) + " 100");

        crono.classList.toggle("apertado", !lote.pausado && restante <= 20 && restante > 10);
        crono.classList.toggle("final", !lote.pausado && restante <= 10);

        // Tique dos 10 segundos finais — uma vez por segundo, não por quadro.
        var s = Math.ceil(restante);
        if (!lote.pausado && s !== ultimoSegundo) {
            if (s <= 10 && s > 0 && ultimoSegundo !== null && window.SomLeilao) {
                window.SomLeilao.tique(s <= 3);
                if (s <= 3) vibrar(30);
            }
            ultimoSegundo = s;
        }
    }
    setInterval(tick, 200);

    /* ---------------------------------------------------------------
       Chat
       --------------------------------------------------------------- */
    function desenharChat() {
        var chat = $("chat");
        var c = estado && estado.chat;
        if (!c || !c.aberto) { chat.hidden = true; return; }
        chat.hidden = false;

        var lista = $("chatLista");
        lista.innerHTML = "";
        if (!c.mensagens || !c.mensagens.length) {
            var vazio = document.createElement("li");
            vazio.className = "chat-vazio";
            vazio.textContent = "Ninguém falou ainda. Manda um oi!";
            lista.appendChild(vazio);
        } else {
            c.mensagens.forEach(function (m) { lista.appendChild(linhaChat(m)); });
        }
        lista.scrollTop = lista.scrollHeight;
        atualizarTempoChat();
    }

    function linhaChat(m) {
        var li = document.createElement("li");
        if (!m.autor_id) li.className = "locutor";
        else if (EU && m.autor_id === EU) li.className = "meu";
        var b = document.createElement("span");
        b.className = "autor";
        b.textContent = (EU && m.autor_id === EU ? "Você" : m.autor) + ": ";
        li.appendChild(b);
        li.appendChild(document.createTextNode(m.texto));
        return li;
    }

    function empurrarChat(m) {
        var lista = $("chatLista");
        var vazio = lista.querySelector(".chat-vazio");
        if (vazio) vazio.remove();
        lista.appendChild(linhaChat(m));
        while (lista.children.length > 60) lista.removeChild(lista.firstChild);
        lista.scrollTop = lista.scrollHeight;
    }

    function atualizarTempoChat() {
        var c = estado && estado.chat;
        var alvo = $("chatTempo");
        if (!alvo) return;
        if (!c || !c.aberto || !c.ate) { alvo.textContent = ""; return; }
        var s = Math.max(0, (Date.parse(c.ate) - agora()) / 1000);
        alvo.textContent = "fecha em " + mmss(s);
    }
    setInterval(atualizarTempoChat, 1000);

    /* ---------------------------------------------------------------
       Meus arremates
       --------------------------------------------------------------- */
    var pixPossivel = true;

    function carregarArremates() {
        return fetch(URLS.arremates, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (!d.ok) return;
                pixPossivel = d.pix_possivel !== false;
                desenharArremates(d.arremates || []);
                return d.arremates;
            })
            .catch(function () { /* rede instável: tenta na próxima */ });
    }

    function desenharArremates(itens) {
        var qtd = $("qtdArremates");
        var pendentes = itens.filter(function (a) { return a.status === "aguardando"; }).length;
        qtd.textContent = itens.length;
        $("btnArremates").classList.toggle("pendente", pendentes > 0);

        var corpo = $("gavetaCorpo");
        corpo.innerHTML = "";
        if (!itens.length) {
            var p = document.createElement("p");
            p.className = "gaveta-vazio";
            p.textContent = "Você ainda não arrematou nada. Boa sorte!";
            corpo.appendChild(p);
            return;
        }
        itens.forEach(function (a) { corpo.appendChild(cartaoArremate(a)); });
    }

    function cartaoArremate(a) {
        var div = document.createElement("div");
        div.className = "arremate " + a.status;
        div.dataset.id = a.id;

        if (a.foto) {
            var img = document.createElement("img");
            img.className = "arremate-foto";
            img.src = a.foto;
            img.alt = "";
            div.appendChild(img);
        }

        var corpo = document.createElement("div");
        corpo.className = "arremate-corpo";

        var nome = document.createElement("span");
        nome.className = "arremate-nome";
        nome.textContent = a.lote;
        corpo.appendChild(nome);

        var valor = document.createElement("span");
        valor.className = "arremate-valor";
        valor.textContent = moeda(a.valor);
        corpo.appendChild(valor);

        var selo = document.createElement("span");
        selo.className = "arremate-selo " + a.status;
        selo.textContent = a.status === "pago" ? "✅ Pago"
            : a.status === "aguardando" ? "⏳ Aguardando pagamento"
            : "⌛ Prazo vencido";
        corpo.appendChild(selo);

        if (a.status === "aguardando") {
            var prazo = document.createElement("span");
            prazo.className = "arremate-prazo";
            prazo.dataset.expira = a.expira_em || "";
            prazo.textContent = "Pague em " + mmss(a.segundos);
            corpo.appendChild(prazo);

            if (!pixPossivel) {
                // Sem Mercado Pago configurado não nasce Pix nenhum. Dizer isso é
                // melhor do que oferecer dois botões que nunca vão funcionar.
                var aviso = document.createElement("span");
                aviso.className = "arremate-prazo";
                aviso.textContent = "Combine o pagamento com o locutor.";
                corpo.appendChild(aviso);
            } else {
                var acoes = document.createElement("div");
                acoes.className = "arremate-acoes";

                var bCopiar = document.createElement("button");
                bCopiar.type = "button";
                bCopiar.className = "btn-pagar";
                bCopiar.textContent = "📋 Copiar código Pix";
                bCopiar.addEventListener("click", function () { copiarPix(a.id); });
                acoes.appendChild(bCopiar);

                var bQr = document.createElement("button");
                bQr.type = "button";
                bQr.className = "btn-qr";
                bQr.textContent = "📱 Mostrar QR Code";
                bQr.addEventListener("click", function () { abrirQr(a.id); });
                acoes.appendChild(bQr);

                corpo.appendChild(acoes);
            }
        }

        div.appendChild(corpo);
        return div;
    }

    /* Prazo dos arremates correndo na gaveta aberta. */
    setInterval(function () {
        if (!gavetaAberta) return;
        var faltam = document.querySelectorAll(".arremate-prazo[data-expira]");
        for (var i = 0; i < faltam.length; i++) {
            var el = faltam[i];
            var t = Date.parse(el.dataset.expira);
            if (isNaN(t)) continue;
            var s = Math.max(0, (t - agora()) / 1000);
            el.textContent = s > 0 ? "Pague em " + mmss(s) : "Prazo vencido";
        }
    }, 1000);

    function buscarPix(id) {
        var url = URLS.pix.replace(/0\/pix\/$/, id + "/pix/");
        return fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (r) { return r.json(); });
    }

    function copiarPix(id) {
        buscarPix(id).then(function (d) {
            if (!d.ok) {
                toast(d.msg || "O Pix ainda está sendo gerado. Tente em instantes.", "info");
                return;
            }
            copiarTexto(d.copia_e_cola);
        }).catch(function () { toast("Não consegui buscar o código agora.", "error"); });
    }

    function copiarTexto(texto) {
        if (!texto) { toast("Código indisponível.", "error"); return; }
        function ok() { toast("Código Pix copiado!", "success"); }
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(texto).then(ok).catch(function () { reserva(texto, ok); });
        } else {
            reserva(texto, ok);
        }
    }

    /* Cópia de reserva: precisa de um campo REAL na página (não `hidden`) para
       o `select()` funcionar — mesmo truque do código Pix do sistema do clube. */
    function reserva(texto, ok) {
        var ta = document.createElement("textarea");
        ta.value = texto;
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand("copy"); ok(); }
        catch (e) { toast("Não consegui copiar. Use o QR Code.", "error"); }
        ta.remove();
    }

    function abrirQr(id) {
        buscarPix(id).then(function (d) {
            if (!d.ok) {
                toast(d.msg || "O Pix ainda está sendo gerado. Tente em instantes.", "info");
                return;
            }
            arremateAberto = id;
            codigoPix = d.copia_e_cola || "";
            $("qrItem").textContent = d.lote || "";
            $("qrValor").textContent = moeda(d.valor);
            var img = $("qrImagem");
            if (d.qr_base64) {
                img.src = "data:image/png;base64," + d.qr_base64;
                img.hidden = false;
            } else {
                img.hidden = true;
            }
            $("qrPrazo").textContent = "Pague em " + mmss(d.segundos);
            $("modalQr").hidden = false;
            document.body.classList.add("modal-aberto");
            conferirPagamento();
        }).catch(function () { toast("Não consegui abrir o QR agora.", "error"); });
    }

    function fecharQr() {
        $("modalQr").hidden = true;
        document.body.classList.remove("modal-aberto");
        arremateAberto = null;
    }

    /* Reforço do webhook: enquanto o QR estiver aberto, pergunta ao servidor se
       o Pix caiu. O webhook do Mercado Pago atrasa, e quem acabou de pagar está
       olhando a tela esperando o selo mudar. */
    function conferirPagamento() {
        if (!arremateAberto) return;
        var id = arremateAberto;
        var url = URLS.conferir.replace(/0\/conferir\/$/, id + "/conferir/");
        fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (d && d.pago) {
                    toast("Pagamento confirmado! 🎉", "success");
                    fecharQr();
                    carregarArremates();
                    return;
                }
                if (arremateAberto === id) setTimeout(conferirPagamento, 5000);
            })
            .catch(function () {
                if (arremateAberto === id) setTimeout(conferirPagamento, 8000);
            });
    }

    /* ---------------------------------------------------------------
       Eventos do servidor
       --------------------------------------------------------------- */
    function conectar() {
        if (fonte) fonte.close();
        fonte = new EventSource(URLS.stream);

        fonte.addEventListener("estado", function (e) {
            render(JSON.parse(e.data));
        });

        fonte.addEventListener("lance", function (e) {
            var d = JSON.parse(e.data);
            if (!estado || !estado.ativo) return;

            var euLiderava = euJaLiderei && liderEra(EU);
            estado.lote = d.lote;
            desenharLote(d.lote);
            empurrarLance(d.lance);

            var meu = !!(EU && d.lance.quem_id === EU);
            var meTiraram = euLiderava && !meu;

            flash();
            if (window.SomLeilao) {
                // Perder a liderança tem som PRÓPRIO (descendo): a pessoa entende
                // sem precisar olhar a tela — é para isso que o som existe aqui.
                if (meTiraram) window.SomLeilao.superado();
                else window.SomLeilao.lance();
            }
            vibrar(meTiraram ? [50, 60, 50] : meu ? 40 : 25);
        });

        fonte.addEventListener("lance_desfeito", function (e) {
            var d = JSON.parse(e.data);
            estado.lote = d.lote;
            desenharLote(d.lote);
            toast("O locutor desfez o lance de " + d.quem + ".", "info");
        });

        fonte.addEventListener("lote_aberto", function (e) {
            render(JSON.parse(e.data));
            toast("Novo item em pregão!", "info");
            if (window.SomLeilao) window.SomLeilao.lance();
            vibrar([30, 40, 30]);
        });

        fonte.addEventListener("lote_vendido", function (e) {
            var d = JSON.parse(e.data);
            var euGanhei = d.vendido && EU && d.vencedor_id === EU;
            render(d.estado);

            if (!d.vendido) {
                toast("Item sem lance — volta para a fila.", "info");
                return;
            }
            if (euGanhei) {
                toast("🏆 Você arrematou por " + moeda(d.valor) + "! Pague em até 15 minutos.", "success");
                if (window.SomLeilao) window.SomLeilao.arrematei();
                if (window.Confete) window.Confete.soltar(3500);
                vibrar([60, 50, 60, 50, 120]);
                carregarArremates().then(function () { abrirGaveta(); });
            } else {
                toast("Vendido para " + d.vencedor + " por " + moeda(d.valor) + ".", "info");
                if (window.SomLeilao) window.SomLeilao.vendido();
            }
        });

        fonte.addEventListener("cronometro", function (e) {
            var d = JSON.parse(e.data);
            if (estado && estado.ativo && d.lote) { estado.lote = d.lote; tick(); desenharLote(d.lote); }
        });

        fonte.addEventListener("chat", function (e) {
            var m = JSON.parse(e.data);
            if (estado && estado.chat && estado.chat.aberto) empurrarChat(m);
        });

        fonte.addEventListener("chat_estado", function (e) {
            var d = JSON.parse(e.data);
            if (!estado.chat) estado.chat = { mensagens: [] };
            estado.chat.aberto = d.aberto;
            estado.chat.ate = d.ate;
            desenharChat();
        });

        fonte.addEventListener("online", function (e) {
            var d = JSON.parse(e.data);
            if (estado) estado.online = d.online;
            $("online").textContent = d.online;
        });

        fonte.addEventListener("arremate_pix", function (e) {
            var d = JSON.parse(e.data);
            if (EU && d.participante === EU) carregarArremates();
        });

        fonte.addEventListener("pagamento", function (e) {
            var d = JSON.parse(e.data);
            if (EU && d.participante === EU) {
                toast("Pagamento confirmado: " + d.lote + " 🎉", "success");
                carregarArremates();
            }
        });

        fonte.addEventListener("arremate_expirado", function (e) {
            var d = JSON.parse(e.data);
            render(d.estado);
            if (EU && d.participante === EU) {
                toast("O prazo de " + d.lote + " venceu — o item voltou para a fila.", "error");
                carregarArremates();
            }
        });

        fonte.onerror = function () {
            // O EventSource reconecta sozinho; só avisamos visualmente.
            var selo = $("seloVivo");
            if (selo) selo.classList.add("parado");
        };
    }

    /* ---------------------------------------------------------------
       Ações
       --------------------------------------------------------------- */
    function darLance(evento) {
        var lote = estado && estado.ativo ? estado.lote : null;
        if (!lote) return;

        var btn = $("btnLance");
        onda(btn, evento);
        vibrar(20);

        // Otimista: a tela responde já; o evento do servidor corrige em seguida.
        var pretendido = lote.proximo_valor;
        btn.disabled = true;

        post(URLS.lance, { lote: lote.id, valor_visto: pretendido }).then(function (d) {
            if (!d.ok) {
                toast(d.msg || "Não deu para registrar o lance.", "error");
                if (window.SomLeilao) window.SomLeilao.erro();
                if (d.lote) { estado.lote = d.lote; desenharLote(d.lote); }
                else btn.disabled = false;
                return;
            }
            if (d.lote) { estado.lote = d.lote; desenharLote(d.lote); }
        }).catch(function () {
            toast("Sem conexão. Tente de novo.", "error");
            btn.disabled = false;
        });
    }

    function abrirGaveta() {
        gavetaAberta = true;
        $("gaveta").hidden = false;
        document.body.classList.add("modal-aberto");
    }

    function fecharGaveta() {
        gavetaAberta = false;
        $("gaveta").hidden = true;
        document.body.classList.remove("modal-aberto");
    }

    function alternarSom() {
        var btn = $("btnSom");
        if (!somLigado) {
            somLigado = window.SomLeilao ? window.SomLeilao.ativar() : false;
            btn.textContent = "🔊";
            btn.setAttribute("aria-pressed", "true");
            if (AUDIO_URL && window.AudioLeilao) {
                window.AudioLeilao.ligar(AUDIO_URL, $("audioLocutor"));
            }
            toast("Som ligado.", "success");
        } else {
            somLigado = false;
            if (window.SomLeilao) window.SomLeilao.desativar();
            if (window.AudioLeilao) window.AudioLeilao.desligar();
            btn.textContent = "🔇";
            btn.setAttribute("aria-pressed", "false");
            toast("Som desligado.", "info");
        }
    }

    /* ---------------------------------------------------------------
       Ligações
       --------------------------------------------------------------- */
    $("btnLance").addEventListener("click", darLance);
    $("btnSom").addEventListener("click", alternarSom);
    $("btnArremates").addEventListener("click", function () {
        carregarArremates();
        abrirGaveta();
    });
    $("gavetaFechar").addEventListener("click", fecharGaveta);
    $("gaveta").addEventListener("click", function (e) {
        if (e.target === $("gaveta")) fecharGaveta();
    });

    $("qrFechar").addEventListener("click", fecharQr);
    $("qrCopiar").addEventListener("click", function () { copiarTexto(codigoPix); });

    /* Modal fecha no fundo só quando o mousedown E o click foram no fundo —
       regra do projeto: arrastar para selecionar texto de dentro e soltar fora
       NÃO pode fechar. */
    (function () {
        var overlay = $("modalQr");
        var comecouNoFundo = false;
        overlay.addEventListener("mousedown", function (e) { comecouNoFundo = (e.target === overlay); });
        overlay.addEventListener("click", function (e) {
            if (comecouNoFundo && e.target === overlay) fecharQr();
            comecouNoFundo = false;
        });
    })();

    document.addEventListener("keydown", function (e) {
        if (e.key !== "Escape") return;
        if (!$("modalQr").hidden) fecharQr();
        else if (gavetaAberta) fecharGaveta();
    });

    $("chatForm").addEventListener("submit", function (e) {
        e.preventDefault();
        var campo = $("chatTexto");
        var texto = campo.value.trim();
        if (!texto) return;
        campo.value = "";
        post(URLS.chat, { texto: texto }).then(function (d) {
            if (!d.ok) toast(d.msg || "Não deu para enviar.", "error");
        });
    });

    /* Voltou do segundo plano (celular bloqueado, outro app): o estado pode ter
       envelhecido. Recarrega em vez de mostrar um pregão congelado. */
    document.addEventListener("visibilitychange", function () {
        if (!document.hidden) {
            carregarArremates();
            if (fonte && fonte.readyState === 2) conectar();  // 2 = fechado
        }
    });

    render(estado);
    carregarArremates();
    conectar();
})();
