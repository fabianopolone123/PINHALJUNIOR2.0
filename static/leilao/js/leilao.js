/*
 * leilao.js — a tela do participante.
 *
 * Recebe os eventos do pregão por SSE (`EventSource`) e redesenha. Decisões que
 * explicam o arquivo inteiro:
 *
 * 1. **O toque responde na hora** (otimista): o botão pinta o novo valor antes
 *    da resposta do servidor, e o evento que volta corrige. A verdade continua
 *    sendo a do servidor — a tela só não fica parada esperando a rede.
 * 2. **Reconexão não tem lógica de replay.** O `EventSource` reconecta sozinho
 *    e o servidor manda o estado INTEIRO; quem volta está sempre correto.
 * 3. **A tela do participante mostra POUCO de propósito**: o item, quem está
 *    ganhando, o valor e o botão. Sem cronômetro (quem fecha é o locutor), sem
 *    histórico de lances e sem quantos itens faltam — saber o que vem pela
 *    frente muda como a pessoa dá lance, e o suspense é do leilão.
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

    /* O som da sala é SEMPRE ligado (pedido do clube em 26/09): a caixa
       registradora do lance e a comemoração do martelo não têm mais
       interruptor na mesa. Quem não quiser som em casa usa o 🔊 da própria
       tela, que é o do aparelho dela. */
    var offset = 0;            // relógio do servidor − relógio daqui
    var fonte = null;          // EventSource
    var loteId = null;
    var valorMostrado = null;
    var liderMostrado = "-";
    // "Já liderei este item alguma vez" — é o que distingue *perder a liderança*
    // de *nunca ter dado lance*. Sem isso, quem só assiste veria "te superaram".
    var euJaLiderei = false;
    var somLigado = false;
    var gavetaAberta = false;
    var arremateAberto = null;
    // Cada abertura do QR ganha um número; a conferência do pagamento só
    // continua enquanto for a da abertura ATUAL. Sem isto, fechar e abrir o QR
    // rápido deixava cadeias antigas vivas, e cada uma consultava o Mercado
    // Pago a cada 5 s.
    var geracaoQr = 0;
    var liberadoVisto = null;
    var codigoPix = "";
    var pixPossivel = true;

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

    function toast(msg, tipo) {
        if (window.mostrarToast) window.mostrarToast(msg, tipo || "info");
    }

    function vibrar(padrao) {
        if (navigator.vibrate) { try { navigator.vibrate(padrao); } catch (e) { /* nada */ } }
    }

    /* O motor AVISA o que aconteceu; quem quiser enfeitar escuta.

       É o que deixa existir mais de uma tela sobre este mesmo arquivo: a tela
       clássica ignora os avisos, e a tela "show" (`palco_show.js`) desenha os
       efeitos em cima deles. Lance, Pix e chat continuam num lugar só — as
       duas telas nunca discordam sobre o que aconteceu no pregão.

       Aviso é enfeite: um ouvinte que quebre não pode levar o motor junto. */
    function emitir(nome, detalhe) {
        try {
            document.dispatchEvent(new CustomEvent("leilao:" + nome, { detail: detalhe || {} }));
        } catch (e) { /* enfeite que falhou não derruba o pregão */ }
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
        $("reacoesBotoes").hidden = !temLeilao;

        var selo = $("seloVivo");
        if (selo) selo.classList.toggle("parado", !lote);

        if (estado && typeof estado.online === "number") {
            $("online").textContent = estado.online;
        }

        if (lote) desenharLote(lote);
        if (temLeilao && !lote) desenharFesta();
        desenharChat();
        desenharBarra();
        precarregarProxima();

        // O locutor liberou os pagamentos: quem está com a conta aberta vê o
        // botão de pagar na hora (antes seguia lendo "o pagamento abre no fim"
        // até fechar e abrir de novo), e quem tem algo a pagar é avisado.
        var liberado = !!(estado && estado.leilao && estado.leilao.pagamentos_liberados);
        if (liberadoVisto === false && liberado) {
            carregarArremates().then(function (itens) {
                if ($("btnArremates").classList.contains("pendente")) {
                    toast("💳 Pagamentos liberados! Toque em “Meus arremates” para pagar.", "success");
                }
            });
        }
        liberadoVisto = liberado;
        emitir("estado", { estado: estado, euGanhando: !!(lote && souEu(lote.lider)) });
    }

    var festaMostrada = null;

    /* A festa do intervalo: o nome de quem acabou de arrematar, grande e se
       mexendo. Sem isso o intervalo é uma tela morta — e o intervalo é
       justamente quando a sala conversa e se anima para o próximo item. */
    function desenharFesta() {
        var v = estado && estado.ultimo_vendido;
        var festa = $("festa");
        var simples = $("intervaloSimples");
        var boas = $("boasVindas");

        // ANTES do primeiro item isto não é intervalo — é gente chegando. Quem
        // entra e lê "Intervalo" acha que perdeu o começo do leilão.
        var comecou = estado && estado.comecou;
        if (boas) boas.hidden = Boolean(comecou);
        if (!comecou) {
            festa.hidden = true;
            simples.hidden = true;
            desenharBoasVindas();
            return;
        }

        if (!v) {
            festa.hidden = true;
            simples.hidden = false;
            return;
        }
        festa.hidden = false;
        simples.hidden = true;

        $("festaItem").textContent = v.item || "";
        $("festaNome").textContent = v.vencedor || "";
        $("festaValor").textContent = moeda(v.valor);

        var foto = $("festaFoto");
        if (v.foto) { foto.src = v.foto; foto.hidden = false; } else { foto.hidden = true; }

        var euGanhei = souEu({ id: null, chave: v.vencedor_chave });
        $("festaParabens").textContent = euGanhei ? "Você levou! 🏆" : "Parabéns!";

        // Reinicia a animação só quando a venda é OUTRA — senão ela recomeça a
        // cada evento que chega e fica tremendo sem parar.
        var marca = (v.item || "") + "|" + (v.vencedor || "") + "|" + v.valor;
        if (marca !== festaMostrada) {
            festaMostrada = marca;
            festa.classList.remove("entrando");
            void festa.offsetWidth;
            festa.classList.add("entrando");
            if (window.Confete) window.Confete.soltar(2500);
        }
    }

    var boasVindasMarca = null;

    /* A tela de quem chega antes de começar. O texto é do clube (editável na
       preparação, inclusive com o leilão no ar) e vem em LINHAS — a tela monta
       a lista; o servidor não manda HTML. */
    function desenharBoasVindas() {
        var bv = (estado && estado.boas_vindas) || {};
        var titulo = $("bvTitulo");
        var lista = $("bvLista");
        if (titulo) titulo.textContent = bv.titulo || "Seja bem-vindo!";

        var marca = JSON.stringify(bv.linhas || []);
        if (lista && marca !== boasVindasMarca) {
            boasVindasMarca = marca;
            lista.innerHTML = "";
            (bv.linhas || []).forEach(function (linha) {
                var li = document.createElement("li");
                li.textContent = linha;
                lista.appendChild(li);
            });
        }

        // Quantas pessoas já estão esperando. É o número que o locutor usa para
        // decidir a hora de começar — e, para quem está na tela, é o que mostra
        // que o leilão está vivo antes de o primeiro item abrir.
        var quantos = $("bvOnline");
        if (quantos && estado && typeof estado.online === "number") {
            // A frase inteira, com o plural certo. "0 pessoa(s)" é o tipo de
            // texto que denuncia sistema — e esta é a primeira tela que a
            // pessoa vê do clube.
            var n = estado.online;
            quantos.textContent =
                n <= 1 ? "Você já está aqui. O pessoal vai chegando…"
                       : n === 2 ? "Você e mais 1 pessoa já estão aqui"
                                 : "Você e mais " + (n - 1) + " pessoas já estão aqui";
        }
    }

    var precarregadas = {};

    /* Baixa a foto do PRÓXIMO item enquanto o atual ainda está em disputa —
       assim a troca é instantânea em vez de piscar um quadro vazio justo no
       segundo em que todo mundo está olhando. Vem só a URL: nem o nome do
       próximo item, nem quantos faltam. */
    function precarregarProxima() {
        var url = estado && estado.proxima_foto;
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
            // Item antigo (cadastrado antes de peso/dimensões existirem) fica
            // sem a linha, em vez de mostrar uma vazia.
            var medidas = $("loteMedidas");
            medidas.textContent = lote.medidas || "";
            medidas.hidden = !lote.medidas;
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
            valorMostrado = null;
            liderMostrado = "-";
            euJaLiderei = false;
        }

        // "Sou eu que estou ganhando?" — pelo id OU pela chave da pessoa. A
        // segunda cobre quem abriu o leilão em dois aparelhos: são registros
        // diferentes, mesma pessoa. Sem ela, o botão ficaria ativo no segundo
        // aparelho e a pessoa cobriria o próprio lance.
        var euGanhando = souEu(lote.lider);
        if (euGanhando) euJaLiderei = true;

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
        // um piscar. É a informação mais importante da tela para quem disputa,
        // e ela pode estar olhando o celular só de vez em quando.
        var superado = !euGanhando && lote.tem_lance && euJaLiderei;

        var pregao = document.querySelector(".pregao");
        pregao.classList.toggle("eu-ganhando", euGanhando && lote.tem_lance);
        pregao.classList.toggle("superado", superado);
        if (superado) rotulo.textContent = "🔴 TE SUPERARAM";

        var btn = $("btnLance");
        $("btnLanceValor").textContent = moeda(lote.proximo_valor);
        $("dicaIncremento").textContent = moeda(lote.incremento);
        btn.classList.toggle("ganhando", euGanhando);
        btn.disabled = euGanhando;
        btn.querySelector(".btn-lance-rotulo").textContent =
            euGanhando ? "VOCÊ ESTÁ GANHANDO"
            : superado ? "COBRIR O LANCE"
            : "DAR LANCE";
        $("acaoDica").hidden = euGanhando;
    }

    /* A resposta do POST do lance só vale se NÃO for mais velha do que o que
       já está na tela. O lance volta por dois caminhos — a resposta HTTP e o
       stream — e, com dois lances quase juntos em 4G, o stream do lance de
       OUTRA pessoa pode chegar antes da resposta do meu. Aplicar a resposta
       atrasada redesenhava "VOCÊ ESTÁ GANHANDO" para quem já tinha sido
       superado, e o martelo ia para o outro. */
    function respostaAindaVale(novo) {
        if (!novo) return false;
        var atual = estado && estado.lote;
        if (!atual) return true;                  // nada na tela para proteger
        if (atual.id !== novo.id) return false;   // já é outro item em pregão
        return parseFloat(novo.valor_atual || 0) >= parseFloat(atual.valor_atual || 0);
    }

    /* "Esta pessoa sou eu?" — id ou chave (dois aparelhos = dois registros). */
    function souEu(pessoa) {
        if (!pessoa) return false;
        if (EU && pessoa.id === EU) return true;
        return !!(EU_CHAVE && pessoa.chave === EU_CHAVE);
    }

    function desenharBarra() {
        var info = $("barraInfo");
        if (!estado || !estado.ativo) { info.textContent = ""; return; }
        // NÃO dizemos quantos faltam. "Vendidos" é o que já aconteceu — não
        // entrega o que vem pela frente.
        var n = estado.vendidos || 0;
        info.textContent = n === 0 ? "" : n === 1 ? "1 já vendido" : n + " já vendidos";
    }

    /* ---------------------------------------------------------------
       Chat (aberto o leilão inteiro, sem contagem)
       --------------------------------------------------------------- */
    function desenharChat() {
        var chat = $("chat");
        var c = estado && estado.chat;
        // `estado.ativo` junto: a caixa não pode ficar de pé depois de o leilão
        // sair do ar — o servidor recusaria tudo que fosse digitado nela. Hoje
        // `chat.aberto` já deriva do status no servidor, mas manter as duas
        // condições aqui custa nada e a tela nunca abre porta que o servidor fecha.
        if (!c || !c.aberto || !(estado && estado.ativo)) {
            chat.hidden = true;
            document.body.classList.remove("chat-aberto");
            return;
        }
        chat.hidden = false;
        // Com o chat aberto, a coluna de emojis muda de lado: ela mora no canto
        // inferior DIREITO, que é exatamente onde fica o botão de enviar a
        // mensagem — no celular um cobria o outro e o ➤ não recebia o toque.
        document.body.classList.add("chat-aberto");

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
    }

    /* A mensagem é minha? Pelo id OU pela chave — dois aparelhos da mesma
       pessoa são dois registros (a mesma regra do "o líder sou eu"). */
    function mensagemMinha(m) {
        return !!m.autor_id && souEu({ id: m.autor_id, chave: m.autor_chave });
    }

    function linhaChat(m) {
        var li = document.createElement("li");
        if (!m.autor_id) li.className = "locutor";
        else if (mensagemMinha(m)) li.className = "meu";
        var b = document.createElement("span");
        b.className = "autor";
        b.textContent = (mensagemMinha(m) ? "Você" : m.autor) + ": ";
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

    // Sem contagem no chat: ele fica aberto o leilão inteiro, então não há
    // "fecha em 1:23" para desenhar (e o `#chatTempo` saiu do template junto).

    /* ---------------------------------------------------------------
       Meus arremates
       --------------------------------------------------------------- */
    function carregarArremates() {
        return fetch(URLS.arremates, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (!d.ok) return;
                pixPossivel = d.pix_possivel !== false;
                desenharArremates(d);
                return d.arremates;
            })
            .catch(function () { /* rede instável: tenta na próxima */ });
    }

    function desenharArremates(d) {
        var itens = d.arremates || [];
        var qtd = $("qtdArremates");
        var abertos = d.quantos_abertos || 0;
        qtd.textContent = itens.length;
        $("btnArremates").classList.toggle("pendente", abertos > 0);

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

        if (!abertos) return;   // tudo pago: nada a somar nem a cobrar

        /* O TOTAL embaixo da lista. É a pergunta que a pessoa faz ("quanto deu
           no fim?") e a razão de a tela existir: ela não paga mais item a item. */
        var tot = document.createElement("div");
        tot.className = "conta-total";
        var rot = document.createElement("span");
        rot.className = "conta-total-rotulo";
        rot.textContent = abertos > 1 ? "Total de " + abertos + " itens" : "Total";
        var val = document.createElement("span");
        val.className = "conta-total-valor";
        val.textContent = moeda(d.total);
        tot.appendChild(rot);
        tot.appendChild(val);
        corpo.appendChild(tot);

        if (!pixPossivel) {
            // Sem Mercado Pago configurado não nasce Pix nenhum. Dizer isso é
            // melhor do que oferecer um botão que nunca vai funcionar.
            var aviso = document.createElement("p");
            aviso.className = "conta-aviso";
            aviso.textContent = "Combine o pagamento com a organização.";
            corpo.appendChild(aviso);
            return;
        }

        if (!d.liberado) {
            /* Ainda não liberado: a tela DIZ isso, em vez de mostrar um botão
               que o servidor vai recusar. Quem está no meio dos lances não
               precisa pensar em pagamento agora — é esse o ponto de ter tirado
               o prazo de 15 minutos. */
            var espera = document.createElement("p");
            espera.className = "conta-aviso";
            espera.textContent = "O pagamento abre no fim do leilão. Aproveite o pregão!";
            corpo.appendChild(espera);
            return;
        }

        var acoes = document.createElement("div");
        acoes.className = "conta-acoes";

        var bCopiar = document.createElement("button");
        bCopiar.type = "button";
        bCopiar.className = "btn-pagar";
        bCopiar.textContent = "📋 Copiar código Pix";
        bCopiar.addEventListener("click", function () { copiarPix(); });
        acoes.appendChild(bCopiar);

        var bQr = document.createElement("button");
        bQr.type = "button";
        bQr.className = "btn-qr";
        bQr.textContent = "📱 Mostrar QR Code";
        bQr.addEventListener("click", function () { abrirQr(); });
        acoes.appendChild(bQr);

        corpo.appendChild(acoes);
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

        /* Sem relógio e sem botão POR ITEM: o pagamento é um só, pelo total,
           e mora no rodapé da lista. Aqui fica só o que a pessoa levou. */
        var selo = document.createElement("span");
        selo.className = "arremate-selo " + a.status;
        selo.textContent = a.status === "pago" ? "✅ Pago"
            : a.status === "combinado" ? "🤝 Pagamento combinado"
            : "🏆 Arrematado";
        corpo.appendChild(selo);

        div.appendChild(corpo);
        return div;
    }

    /* UMA cobrança, pelo total do que a pessoa levou — não uma por item.
       O servidor cria (ou devolve a que já existe) e recusa antes de o locutor
       liberar, então a tela não precisa se defender sozinha. */
    function buscarPix() {
        return fetch(URLS.pix, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (r) { return r.json(); });
    }

    function copiarPix() {
        buscarPix().then(function (d) {
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

    function abrirQr() {
        buscarPix().then(function (d) {
            if (!d.ok) {
                toast(d.msg || "O Pix ainda está sendo gerado. Tente em instantes.", "info");
                // Com o QR aberto, um código que já não vale não pode ficar na
                // tela para ser copiado.
                if (arremateAberto) fecharQr();
                return;
            }
            arremateAberto = true;
            codigoPix = d.copia_e_cola || "";
            $("qrItem").textContent = d.quantos > 1
                ? d.quantos + " itens arrematados" : "1 item arrematado";
            $("qrValor").textContent = moeda(d.valor);
            var img = $("qrImagem");
            if (d.qr_base64) {
                img.src = "data:image/png;base64," + d.qr_base64;
                img.hidden = false;
            } else {
                img.hidden = true;
            }
            // Sem contagem: o código não vence numa janela de minutos.
            $("qrPrazo").textContent = "";
            $("modalQr").hidden = false;
            document.body.classList.add("modal-aberto");
            geracaoQr++;
            conferirPagamento(geracaoQr);
        }).catch(function () { toast("Não consegui abrir o QR agora.", "error"); });
    }

    function fecharQr() {
        geracaoQr++;
        $("modalQr").hidden = true;
        document.body.classList.remove("modal-aberto");
        arremateAberto = false;
    }

    /* Reforço do webhook: enquanto o QR estiver aberto, pergunta ao servidor se
       o Pix caiu. O webhook do Mercado Pago atrasa, e quem acabou de pagar está
       olhando a tela esperando o selo mudar. */
    function conferirPagamento(geracao) {
        if (geracao !== geracaoQr) return;
        if (!arremateAberto) return;
        fetch(URLS.conferir, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (d && d.pago) {
                    toast("Pagamento confirmado! 🎉", "success");
                    fecharQr();
                    carregarArremates();
                    return;
                }
                // Era `arremateAberto === id`, com um `id` que não existia
                // desde que o pagamento virou UM Pix pelo total: o
                // ReferenceError matava a volta e o reforço parava na
                // primeira conferência. Corrigido em 24/09.
                if (arremateAberto) setTimeout(function () { conferirPagamento(geracao); }, 5000);
            })
            .catch(function () {
                if (arremateAberto) setTimeout(function () { conferirPagamento(geracao); }, 8000);
            });
    }

    /* ---------------------------------------------------------------
       Eventos do servidor
       --------------------------------------------------------------- */
    function conectar() {
        if (fonte) fonte.close();
        // A `FonteViva` traz a conexão de volta quando o EventSource DESISTE
        // (502 no reinício do serviço, 503 de lotado) — sem ela a tela
        // congelava sem aviso. Ver `fonte_viva.js`.
        fonte = window.FonteViva
            ? window.FonteViva.abrir(URLS.stream, {
                aoCair: function () {
                    var selo = $("seloVivo");
                    if (selo) selo.classList.add("parado");
                }
            })
            : new EventSource(URLS.stream);

        fonte.addEventListener("estado", function (e) {
            render(JSON.parse(e.data));
        });

        fonte.addEventListener("lance", function (e) {
            var d = JSON.parse(e.data);
            if (!estado || !estado.ativo) return;

            var lote = estado.lote;
            var euLiderava = !!(lote && souEu(lote.lider));
            estado.lote = d.lote;
            desenharLote(d.lote);

            var meu = souEu({ id: d.lance.quem_id, chave: d.lance.quem_chave });
            var meTiraram = euLiderava && !meu;

            flash();
            if (window.SomLeilao) {
                // Perder a liderança tem som PRÓPRIO (descendo): a pessoa
                // entende sem precisar olhar — é para isso que o som existe.
                if (meTiraram) window.SomLeilao.superado();
                else window.SomLeilao.lance();
            }
            vibrar(meTiraram ? [50, 60, 50] : meu ? 40 : 25);
            emitir("lance", {
                lote: d.lote, meu: meu, meTiraram: meTiraram,
                euGanhando: souEu(d.lote && d.lote.lider)
            });
        });

        fonte.addEventListener("lote_aberto", function (e) {
            // Item aberto é SEMPRE rodada nova, mesmo com o mesmo id (item
            // devolvido ao leilão volta com o id de antes). Sem zerar aqui, quem
            // liderou a rodada anterior via "TE SUPERARAM" no primeiro lance de
            // outra pessoa — e nome/foto editados na fila não eram redesenhados.
            loteId = null;
            // A gaveta aberta sozinha no arremate anterior não pode cobrir o
            // botão de lance do item que acabou de abrir.
            if (gavetaAberta) fecharGaveta();
            render(JSON.parse(e.data));
            toast("Novo item! 🔔", "info");
            if (window.SomLeilao) window.SomLeilao.lance();
            vibrar([30, 40, 30]);
            emitir("lote_aberto", { lote: estado && estado.lote });
        });

        /* O locutor anunciou "dou-lhe uma/duas". Vale só para o item que está
           na tela (o anúncio de um item que já trocou é ignorado). O efeito
           visual é do `dou_lhe.js`; aqui ficam o som e a vibração, que são do
           motor como os do lance. */
        fonte.addEventListener("dou_lhe", function (e) {
            var d = JSON.parse(e.data);
            var lote = estado && estado.ativo ? estado.lote : null;
            if (!lote || lote.id !== d.lote) return;
            var euGanhando = souEu(lote.lider);
            if (window.SomLeilao && window.SomLeilao.douLhe) window.SomLeilao.douLhe(d.vez);
            vibrar(d.vez === 2 ? [90, 60, 90, 60, 180] : [70, 50, 70]);
            emitir("dou_lhe", { vez: d.vez, lote: d.lote, euGanhando: euGanhando });
        });

        fonte.addEventListener("lote_vendido", function (e) {
            var d = JSON.parse(e.data);
            var euGanhei = d.vendido && souEu({ id: d.vencedor_id, chave: d.vencedor_chave });
            render(d.estado);
            emitir("vendido", { vendido: !!d.vendido, euGanhei: !!euGanhei, valor: d.valor });

            if (!d.vendido) {
                toast("Item sem lance — pode voltar mais tarde.", "info");
                return;
            }
            if (euGanhei) {
                // Sem prazo: o pagamento é no fim, num Pix só (21/09). O aviso
                // ainda prometia "15 minutos" de um relógio que não existe.
                toast("🏆 Você arrematou por " + moeda(d.valor) + "!", "success");
                if (window.SomLeilao) window.SomLeilao.arrematei();
                if (window.Confete) window.Confete.soltar(3500);
                vibrar([60, 50, 60, 50, 120]);
                carregarArremates().then(function () { abrirGaveta(); });
            } else {
                toast("Vendido para " + d.vencedor + " por " + moeda(d.valor) + ".", "info");
                if (window.SomLeilao) window.SomLeilao.vendido();
            }
        });

        fonte.addEventListener("chat", function (e) {
            var m = JSON.parse(e.data);
            if (estado && estado.chat && estado.chat.aberto) {
                empurrarChat(m);
                emitir("chat", {
                    autor: mensagemMinha(m) ? "Você" : m.autor,
                    texto: m.texto, meu: mensagemMinha(m), locutor: !m.autor_id
                });
            }
        });

        // Sem `chat_estado`: o chat fica aberto o leilão inteiro, e se está
        // aberto ou não vem no `estado` como todo o resto.

        // A voz do locutor VOLTOU: quem estava esperando reconecta já, em vez
        // de só na próxima tentativa agendada (até ~20 s depois). Cada celular
        // sorteia até 4 s: 100 negociações de áudio no mesmo instante cairiam
        // todas no mesmo vCPU do servidor de áudio.
        fonte.addEventListener("voz", function (e) {
            var d = JSON.parse(e.data || "{}");
            if (!d.no_ar || !somLigado || !window.AudioLeilao || !window.AudioLeilao.vozVoltou) return;
            setTimeout(function () { window.AudioLeilao.vozVoltou(); }, Math.random() * 4000);
        });

        fonte.addEventListener("reacoes", function (e) {
            if (window.Reacoes) window.Reacoes.receber(JSON.parse(e.data));
        });

        fonte.addEventListener("online", function (e) {
            var d = JSON.parse(e.data);
            if (estado) estado.online = d.online;
            $("online").textContent = d.online;
            // A frase "já estão aqui" é da tela de espera — justamente a fase
            // em que este número muda o tempo todo. Sem redesenhar, ela
            // congelava no valor de quando a pessoa conectou.
            if (estado && estado.ativo && !estado.comecou) desenharBoasVindas();
        });

        fonte.addEventListener("arremate_combinado", function (e) {
            var d = JSON.parse(e.data);
            if (EU && d.participante === EU) {
                toast("Pagamento combinado com a organização. 🤝", "success");
                carregarArremates();
            }
        });

        fonte.addEventListener("arremate_pix", function (e) {
            var d = JSON.parse(e.data);
            if (!EU || d.participante !== EU) return;
            carregarArremates();
            // O Pix pode ter sido REFEITO (prazo esticado, pagamento combinado).
            // Com o modal aberto, a pessoa ficaria olhando um código que já não
            // é o dela — e copiaria esse.
            // Comparava `String(arremateAberto)` com `d.arremate` — mas o evento
            // não traz arremate (o Pix é da pessoa) e `arremateAberto` virou
            // booleano: nunca batia, e quem estava com o QR aberto seguia
            // copiando o código antigo. O evento já é só desta pessoa.
            if (arremateAberto) {
                abrirQr();
            }
        });

        fonte.addEventListener("arremate_prazo", function (e) {
            var d = JSON.parse(e.data);
            if (!EU || d.participante !== EU) return;
            toast("A organização te deu mais tempo para pagar. ⏱️", "success");
            carregarArremates();
        });

        fonte.addEventListener("pagamento", function (e) {
            var d = JSON.parse(e.data);
            if (EU && d.participante === EU) {
                toast("Pagamento confirmado: " + d.lote + " 🎉", "success");
                carregarArremates();
                // Um item da conta foi quitado (Pix ou baixa na mão do caixa):
                // o QR aberto é da conta ANTIGA. Pede o de novo — o servidor
                // refaz pelo valor que sobrou ou diz que não há mais nada.
                if (arremateAberto) abrirQr();
            }
        });

        // Sem a FonteViva (arquivo não carregou), o aviso visual de sempre.
        if (!window.FonteViva) {
            fonte.onerror = function () {
                var selo = $("seloVivo");
                if (selo) selo.classList.add("parado");
            };
        }
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
        emitir("toque_lance", {});

        var pretendido = lote.proximo_valor;
        btn.disabled = true;

        post(URLS.lance, { lote: lote.id, valor_visto: pretendido }).then(function (d) {
            if (!d.ok) {
                toast(d.msg || "Não deu para registrar o lance.", "error");
                if (window.SomLeilao) window.SomLeilao.erro();
                if (d.lote && respostaAindaVale(d.lote)) { estado.lote = d.lote; desenharLote(d.lote); }
                else if (estado && estado.lote) desenharLote(estado.lote);   // devolve o botão ao estado certo
                else btn.disabled = false;
                return;
            }
            if (d.lote && respostaAindaVale(d.lote)) { estado.lote = d.lote; desenharLote(d.lote); }
            else if (estado && estado.lote) desenharLote(estado.lote);
            // Os efeitos (contador, mini placar) acompanham o redesenho.
            emitir("estado", { estado: estado, euGanhando: !!(estado && estado.lote && souEu(estado.lote.lider)) });
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
        // A trava de rolagem é do QR também: fechar a gaveta com o QR aberto
        // não pode soltá-la.
        if ($("modalQr").hidden) document.body.classList.remove("modal-aberto");
    }

    /* ---------------------------------------------------------------
       Som: a porta de entrada
       --------------------------------------------------------------- */
    function ligarSom() {
        // Os caminhos vêm do servidor (o `{% static %}` acrescenta o hash do
        // conteúdo em produção). É na ativação que os arquivos baixam: a
        // pessoa acabou de tocar a porta do som e está parada olhando a tela —
        // buscar no primeiro lance atrasaria justo o som do evento.
        somLigado = window.SomLeilao ? window.SomLeilao.ativar({
            lance: dados.dataset.somLance,
            arremate: dados.dataset.somArremate
        }) : false;
        $("btnSom").textContent = "🔊";
        $("btnSom").setAttribute("aria-pressed", "true");

        if (AUDIO_URL && window.AudioLeilao) {
            window.AudioLeilao.ligar(AUDIO_URL, $("audioLocutor"));
        }
    }

    function desligarSom() {
        somLigado = false;
        if (window.SomLeilao) window.SomLeilao.desativar();
        if (window.AudioLeilao) window.AudioLeilao.desligar();
        $("btnSom").textContent = "🔇";
        $("btnSom").setAttribute("aria-pressed", "false");
    }

    /* ---------------------------------------------------------------
       "O som parou" — a janela que PEDE o toque
       ---------------------------------------------------------------
       Os vigias do `audio_ouvir.js` percebem o silêncio e religam sozinhos,
       mas há um caso que reconexão nenhuma conserta: quando o navegador recusa
       tocar (política de autoplay, aparelho que voltou do bloqueio), só um
       **gesto** libera o áudio. Esta janela não é um aviso — o botão dentro
       dela É o gesto que o navegador está esperando. */
    var modalSom = window.ModalLeilao ? window.ModalLeilao.ligar($("modalSomCaiu")) : null;
    var caladoDesde = 0;

    function mostrarSomCaiu() {
        if (!modalSom || !somLigado) return;
        // Quem fechou na mão tem um minuto de paz: insistir num leilão ao vivo
        // é pior do que ficar quieto.
        if (Date.now() - caladoDesde < 60000) return;
        modalSom.abrir();
    }

    if (window.AudioLeilao && window.AudioLeilao.aoMudar) {
        window.AudioLeilao.aoMudar(function (estaOuvindo) {
            if (estaOuvindo) {
                // Voltou: a janela some sozinha, sem a pessoa precisar fechar.
                if (modalSom) modalSom.fechar();
            } else {
                mostrarSomCaiu();
            }
        });
    }

    if ($("btnVoltarASomar")) {
        $("btnVoltarASomar").addEventListener("click", function () {
            // Este clique é o gesto. Refaz o caminho inteiro da porta do som:
            // reativa os efeitos e reconecta a voz do zero.
            if (modalSom) modalSom.fechar();
            ligarSom();
        });
    }

    if ($("modalSomCaiu")) {
        // Fechar na mão marca a hora — é o que dá o minuto de silêncio.
        $("modalSomCaiu").addEventListener("click", function (e) {
            if (e.target.closest("[data-fechar-modal]") || e.target === this) {
                caladoDesde = Date.now();
            }
        });
    }

    function fecharPorta() {
        var porta = $("portaSom");
        if (porta) porta.hidden = true;
    }

    /* A tela não pode apagar no meio do pregão.
       Entre um lance e outro ninguém toca em nada, e para o celular isso é
       aparelho parado: o protetor entra em 30 s e a pessoa perde o item. Vale
       para quem entrou COM som e para quem entrou no mudo — o toque na porta já
       é o gesto que a API exige. */
    function segurarTela() {
        if (window.TelaAcesa) window.TelaAcesa.ligar();
    }

    /* ---------------------------------------------------------------
       Ligações
       --------------------------------------------------------------- */
    $("btnPortaSom").addEventListener("click", function () {
        ligarSom();
        segurarTela();
        fecharPorta();
        toast("Som ligado. Bom leilão!", "success");
    });

    $("btnLance").addEventListener("click", darLance);
    $("btnSom").addEventListener("click", function () {
        if (somLigado) desligarSom(); else ligarSom();
    });
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

    /* Reações */
    if (window.Reacoes) {
        window.Reacoes.ligar($("reacoesTrilho"), function (emoji, quantos) {
            post(URLS.reagir, { emoji: emoji, quantos: quantos });
        }, dados.dataset.rajada);
        $("reacoesBotoes").addEventListener("click", function (e) {
            var btn = e.target.closest(".btn-reacao");
            if (!btn) return;
            window.Reacoes.tocar(btn.dataset.emoji);
            vibrar(12);
        });
    }

    /* Voltou do segundo plano (celular bloqueado, outro app): o estado pode ter
       envelhecido. Recarrega em vez de mostrar um pregão congelado.

       A VOZ precisa do mesmo cuidado, e por muito tempo não teve: o navegador
       derruba a conexão de áudio quando a aba sai da frente e não a devolve.
       Quem voltava ouvia silêncio e só resolvia fechando o navegador. O módulo
       de áudio também escuta `visibilitychange` sozinho; chamar aqui é de
       propósito — este é o ponto em que a tela já decidiu que voltou, e uma
       chamada a mais no `retomar()` não custa nada (ele confere antes de agir). */
    document.addEventListener("visibilitychange", function () {
        if (!document.hidden) {
            carregarArremates();
            var caiu = fonte && (fonte.fechada ? fonte.fechada() : fonte.readyState === 2);
            if (caiu) conectar();
            if (somLigado && window.AudioLeilao && window.AudioLeilao.retomar) {
                window.AudioLeilao.retomar();
            }
        }
    });

    render(estado);
    carregarArremates();
    conectar();
})();
