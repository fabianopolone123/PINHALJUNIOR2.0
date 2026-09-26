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
    // Os dados da mesa são DO LEILÃO DA URL (a mesa pode estar num leilão que
    // não é o que está no ar).
    var URL_DADOS = dados.dataset.dadosUrl +
        (dados.dataset.leilao ? (dados.dataset.dadosUrl.indexOf("?") < 0 ? "?" : "&") + "leilao=" + dados.dataset.leilao : "");
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
        // O leilão DESTA tela vai junto: sem ele o servidor adivinhava ("o que
        // está no ar") e o botão agia no leilão errado.
        if (dados.dataset.leilao && corpo.leilao === undefined) corpo.leilao = dados.dataset.leilao;
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
    /* Tamanho e peso do item em pregão. Some quando o item é antigo e não tem
       medida cadastrada — rótulo sem valor na mesa faz o locutor procurar na
       tela um dado que não existe. */
    function medidasMesa(texto) {
        var el = $("mesaMedidas");
        if (!el) return;
        el.textContent = texto || "";
        el.hidden = !texto;
    }

    /* O nome de quem está ganhando ACENDE a cada lance novo.
       O locutor não fica lendo a tela: ele está falando, olhando a sala e o
       microfone. Sem um movimento, a troca da ponta é uma palavra que muda de
       lugar num canto do monitor — e é justamente o que ele tem de anunciar em
       voz alta. É o mesmo efeito que a tela do público ganhou (`assume-a-ponta`),
       pela mesma razão.

       Aqui ele dispara a CADA lance, não só quando o nome muda: na mesa o que
       interessa é "entrou lance agora", e é isso que o locutor repete. (Hoje as
       duas coisas andam juntas, porque ninguém cobre o próprio lance — comparar
       o valor também é o que segura o efeito se essa regra mudar um dia.)

       Item novo NÃO acende: abrir o próximo é ação da própria mesa, o locutor
       acabou de clicar e ainda não há lance nenhum. */
    var mesaLoteMostrado = null;
    var mesaLiderMostrado = null;
    var mesaValorMostrado = null;

    function acenderLider(lote) {
        var el = $("mesaLider");
        if (!el) return;

        var nome = lote && lote.lider ? lote.lider.nome : null;
        var valor = lote ? String(lote.valor_atual) : null;
        var mesmoLote = !!lote && mesaLoteMostrado === lote.id;
        var novidade = mesmoLote && !!lote.tem_lance &&
            (nome !== mesaLiderMostrado || valor !== mesaValorMostrado);

        mesaLoteMostrado = lote ? lote.id : null;
        mesaLiderMostrado = nome;
        mesaValorMostrado = valor;

        if (!novidade) return;
        el.classList.remove("lance-novo");
        void el.offsetWidth;   // reinicia a animação
        el.classList.add("lance-novo");
    }

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
            medidasMesa(lote.medidas);
            $("mesaValor").textContent = moeda(lote.tem_lance ? lote.valor_atual : lote.lance_inicial);
            $("mesaLider").textContent = lote.lider ? lote.lider.nome : "ninguém ainda";
            $("mesaProximo").textContent = moeda(lote.proximo_valor);
            if (lote.foto) { foto.src = lote.foto; foto.hidden = false; } else { foto.hidden = true; }
        } else {
            $("mesaEtiqueta").textContent = "Nenhum item em pregão";
            $("mesaNome").textContent = "—";
            $("mesaDesc").textContent = "";
            medidasMesa("");
            $("mesaValor").textContent = moeda(0);
            $("mesaLider").textContent = "—";
            $("mesaProximo").textContent = moeda(0);
            foto.hidden = true;
        }
        acenderLider(lote);
        pintarMartelo();

        desenharFila();
        desenharChatMesa();
        tick();
    }

    /* Em que tempo do martelo o item está: {lote, vez} do último "dou-lhe".
       Zera com lance novo, item novo ou martelo batido — o "dou-lhe duas" de
       antes do lance não vale mais depois dele. */
    var martelo = { lote: null, vez: 0 };

    function zerarMartelo() { martelo = { lote: null, vez: 0 }; pintarMartelo(); }

    function pintarMartelo() {
        var lote = estado && estado.ativo ? estado.lote : null;
        var vale = lote && martelo.lote === lote.id ? martelo.vez : 0;
        var card = document.querySelector(".cartao.lote-atual");
        if (card) {
            card.classList.toggle("martelo-1", vale === 1);
            card.classList.toggle("martelo-2", vale === 2);
        }
        document.querySelectorAll('[data-acao="dou_lhe"]').forEach(function (b) {
            var vez = parseInt(b.dataset.vez, 10);
            b.classList.toggle("feito", vale >= vez);
            // Sem item ou sem lance não há o que anunciar (o servidor recusa
            // também); o botão apagado diz isso antes do clique.
            b.disabled = !(lote && lote.tem_lance);
        });
    }

    /* ---------------------------------------------------------------
       A emoção do lance na mesa
       --------------------------------------------------------------- */
    /* O locutor não lê a tela — ele sente o movimento. A cada lance a borda
       do card pisca, o valor pula, sobe o "+R$ 5" e saem moedas de dentro da
       caixa do valor; com lances rápidos aparece o selo de ritmo e o efeito
       cresce. Tudo dentro do card (nada voa por cima dos botões) e SEM som:
       com o microfone aberto no alto-falante, o som da mesa voltaria para a
       sala pela transmissão. */
    var reduzido = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    var batidas = [];          // horários dos lances do item atual
    var batidasLote = null;

    function reanimar(el, classe) {
        if (!el) return;
        el.classList.remove(classe);
        void el.offsetWidth;
        el.classList.add(classe);
    }

    function festejarLance(lote) {
        var agora = Date.now();
        if (!lote || batidasLote !== lote.id) { batidas = []; batidasLote = lote ? lote.id : null; }
        batidas = batidas.filter(function (t) { return agora - t < 20000; }).concat([agora]);
        var ritmo = batidas.length;
        var quente = ritmo >= 3;

        var card = document.querySelector(".cartao.lote-atual");
        if (card) {
            card.classList.toggle("quente", quente);
            reanimar(card, "lance-agora");
        }
        reanimar($("mesaValor"), "pulou");

        var selo = $("mesaCombo");
        if (selo) {
            selo.hidden = !quente;
            if (quente) {
                selo.textContent = "🔥 " + ritmo + " lances em 20 s";
                selo.classList.toggle("fogo", ritmo >= 6);
                reanimar(selo, "entrou");
            }
        }

        var fx = $("mesaFx");
        if (!fx || reduzido) return;
        var mais = document.createElement("span");
        mais.className = "mais";
        mais.textContent = "+" + moeda(lote && lote.incremento ? lote.incremento : 5);
        fx.appendChild(mais);
        // Mais moedas quanto mais quente — mas com teto: a mesa pode estar
        // num notebook velho transmitindo voz ao mesmo tempo.
        var quantas = Math.min(14, 4 + ritmo * 2);
        for (var i = 0; i < quantas; i++) {
            var m = document.createElement("span");
            m.className = "moeda";
            // 💰 e 💵 existem desde os aparelhos antigos (o 🪙 é de 2020 e vira
            // quadrado vazio em celular velho).
            m.textContent = i % 3 === 0 ? "💰" : "💵";
            m.style.left = Math.round(8 + Math.random() * 80) + "%";
            m.style.setProperty("--dx", Math.round(Math.random() * 60 - 30) + "px");
            m.style.setProperty("--giro", Math.round(Math.random() * 360 - 180) + "deg");
            m.style.animationDelay = Math.round(Math.random() * 180) + "ms";
            fx.appendChild(m);
        }
        setTimeout(function () {
            while (fx.firstChild) fx.removeChild(fx.firstChild);
        }, 1400);
    }

    function esfriarMesa() {
        batidas = [];
        batidasLote = null;
        var selo = $("mesaCombo");
        if (selo) selo.hidden = true;
        var card = document.querySelector(".cartao.lote-atual");
        if (card) card.classList.remove("quente");
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
            // `data-acao`, e não um ouvinte próprio: é o caminho único dos
            // botões da mesa, onde mora a pergunta "este item está em disputa,
            // abrir outro mesmo assim?". O ouvinte próprio pulava a pergunta, e
            // um toque na fila jogava fora um pregão com lances.
            b.dataset.acao = "abrir";
            b.dataset.lote = l.id;
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

    /* Quem está disputando o item, por pessoa: os 4 que mais deram lance em
       cima (medalha, quantos, até quanto; coroa em quem ganha), depois todo
       o resto pelo maior lance. A ordem vem pronta do servidor. */
    var MEDALHAS = ["🥇", "🥈", "🥉", "4º"];

    function desenharDisputa(lista) {
        var ol = $("disputa");
        if (!ol) return;
        lista = lista || [];
        ol.innerHTML = "";
        var conta = $("contaDisputa");
        if (conta) conta.textContent = lista.length ? "(" + lista.length + (lista.length === 1 ? " pessoa)" : " pessoas)") : "";
        if (!lista.length) {
            var vazio = document.createElement("li");
            vazio.className = "vazio";
            vazio.textContent = "Nenhum lance ainda.";
            ol.appendChild(vazio);
            return;
        }
        var posicao = 0;
        lista.forEach(function (p, i) {
            var li = document.createElement("li");
            var classes = [];
            if (p.topo) classes.push("topo");
            if (p.lider) classes.push("ganhando");   // `.lider` já é do placar do público (leilao.css)
            // Uma folga visual entre os 4 de cima e o resto da lista.
            if (!p.topo && i > 0 && lista[i - 1].topo) classes.push("separa");
            li.className = classes.join(" ");

            var pos = document.createElement("span");
            pos.className = "pos";
            pos.textContent = p.topo ? MEDALHAS[posicao++] || "" : "·";
            var nome = document.createElement("span");
            nome.className = "nome";
            nome.textContent = (p.lider ? "👑 " : "") + p.quem;
            var valor = document.createElement("span");
            valor.className = "valor";
            valor.textContent = moeda(p.maior);
            var n = document.createElement("span");
            n.className = "n";
            n.textContent = p.n + (p.n === 1 ? " lance" : " lances");
            li.appendChild(pos);
            li.appendChild(nome);
            li.appendChild(valor);
            li.appendChild(n);
            ol.appendChild(li);
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
            // Sem "fecha em": o chat não tem mais relógio — fica aberto
            // enquanto o leilão está no ar. O `ate` saiu do estado junto com a
            // contagem, e esta linha continuou calculando com ele, escrevendo
            // "fecha em NaN:NaN" na mesa a noite inteira.
            alvo.textContent = c && c.aberto ? "aberto" : "fechado para os participantes";
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
                    desenharDisputa(d.disputa);
                    // A fila e o histórico do chat NÃO vêm no broadcast: o
                    // público não pode saber quantos itens faltam, e o fio da
                    // conversa da noite é só da mesa.
                    desenharFila(d.fila, d.restam_na_fila);
                    desenharChatMesa(d.chat);
                    desenharOnline(d);
                })
                .catch(function () { /* a próxima volta resolve */ });
        }, 700);
    }

    // `FonteViva`: a mesa também congelava quando o EventSource desistia
    // (502 no reinício do serviço) — e é a tela que menos pode parar.
    var fonte = window.FonteViva ? window.FonteViva.abrir(URL_STREAM) : new EventSource(URL_STREAM);

    fonte.addEventListener("estado", function (e) { render(JSON.parse(e.data)); recarregarDados(); });
    fonte.addEventListener("lote_aberto", function (e) {
        martelo = { lote: null, vez: 0 };
        esfriarMesa();
        render(JSON.parse(e.data));
        recarregarDados();
    });
    fonte.addEventListener("lance", function (e) {
        var d = JSON.parse(e.data);
        martelo = { lote: null, vez: 0 };      // lance novo recomeça o martelo
        if (estado && estado.ativo) { estado.lote = d.lote; render(estado); }
        festejarLance(d.lote);
        recarregarDados();
    });
    /* O anúncio vem pelo stream, e não pela resposta do clique: assim duas
       telas de mesa abertas ficam no mesmo tempo do martelo. */
    fonte.addEventListener("dou_lhe", function (e) {
        var d = JSON.parse(e.data);
        martelo = { lote: d.lote, vez: d.vez };
        pintarMartelo();
        toast(d.vez === 2 ? "🔨🔨 Dou-lhe duas!" : "🔨 Dou-lhe uma!", "info");
    });

    fonte.addEventListener("lote_vendido", function (e) {
        var d = JSON.parse(e.data);
        zerarMartelo();
        esfriarMesa();
        render(d.estado);
        desenharHistorico([]);
        desenharDisputa([]);
        if (d.vendido) toast("Vendido para " + d.vencedor + " — " + moeda(d.valor), "success");
        else toast("Item sem lance. Dá para abrir de novo pela aba Itens.", "info");
    });
    fonte.addEventListener("chat", function (e) {
        // Teto: a mesa fica aberta a noite inteira e não pode acumular memória.
        chatCache = chatCache.concat([JSON.parse(e.data)]).slice(-120);
        desenharChatMesa();
    });
    // O evento `chat_estado` NÃO EXISTE MAIS: o chat fica aberto enquanto o
    // leilão está no ar, e isso já vem em `estado.chat.aberto`.
    fonte.addEventListener("online", function (e) {
        var d = JSON.parse(e.data);
        if (estado) estado.online = d.online;
        if ($("online")) $("online").textContent = d.online;
        // Entrou ou saiu alguém: o card "Online agora" busca os nomes de novo.
        // O `recarregarDados` já junta rajadas (700 ms), então uma sala
        // chegando de uma vez vira poucos pedidos, e só desta tela.
        recarregarDados();
    });
    fonte.addEventListener("pagamento", function () {
        toast("Pagamento confirmado.", "success");
    });

    /* As reações do público sobem AQUI TAMBÉM.

       O locutor conduz sem plateia na frente: o público está em casa, no
       celular, e o emoji é o aplauso que este leilão tem. Sem ele a mesa é uma
       tela de números — e é pela reação da sala que ele decide esticar a
       conversa num item ou partir para o martelo.

       A mesa só OUVE: não há botão de reagir aqui. O resumo é o mesmo
       broadcast que vai para todo mundo (o hub entrega tudo a todos), então
       isto não custa requisição nenhuma a mais — é um evento que já chegava e
       a mesa jogava fora. Por isso também não há crédito a descontar: nada sai
       desta tela. */
    if (window.Reacoes) {
        window.Reacoes.ligar($("reacoesTrilho"), null);
        fonte.addEventListener("reacoes", function (e) {
            window.Reacoes.receber(JSON.parse(e.data));
        });
    }

    /* ---------------------------------------------------------------
       Quem já chegou — a lista por trás do contador
       --------------------------------------------------------------- */
    /* O número de gente é o que decide a hora de começar, e a pergunta
       seguinte é sempre "quem já chegou?". Os nomes vêm do `/locutor/dados/`,
       que é autenticado — nunca do broadcast, que é lido por todos os
       celulares da sala. */
    var modalQuem = window.ModalLeilao ? window.ModalLeilao.ligar($("modalQuemChegou")) : null;

    /* Serve às DUAS listas: a janela do 👥 e o card "Online agora" do pregão.
       Um desenho só, para as duas nunca discordarem. */
    function desenharQuemChegou(dados, ul, nota, conta) {
        ul = ul || $("quemLista");
        nota = nota || $("quemNota");
        if (!ul) return;
        if (conta) {
            var n = ((dados && dados.conectados_nomes) || []).length;
            conta.textContent = n ? String(n) : "";
        }
        var nomes = (dados && dados.conectados_nomes) || [];
        ul.innerHTML = "";

        if (!nomes.length) {
            var vazio = document.createElement("li");
            vazio.className = "vazio";
            vazio.textContent = "Ninguém conectado agora.";
            ul.appendChild(vazio);
        } else {
            nomes.forEach(function (p) {
                var li = document.createElement("li");
                var nome = document.createElement("span");
                nome.className = "nome";
                nome.textContent = p.nome;
                li.appendChild(nome);
                // Duas abas da mesma pessoa (celular e computador) são UMA
                // entrada; o selo explica por que a lista pode ser menor que o
                // contador, em vez de deixar parecer que o número mente.
                if (p.telas > 1) {
                    var selo = document.createElement("span");
                    selo.className = "selo selo-fila";
                    selo.textContent = p.telas + " telas";
                    li.appendChild(selo);
                }
                ul.appendChild(li);
            });
        }

        if (nota) {
            var conectados = (dados && dados.conectados) || 0;
            var semNome = conectados - nomes.reduce(function (s, p) { return s + p.telas; }, 0);
            var partes = [conectados + " conexão" + (conectados === 1 ? "" : "ões")];
            if (nomes.length) partes.push(nomes.length + " pessoa" + (nomes.length === 1 ? "" : "s"));
            // Quem ainda está na tela de entrada conta no número e não tem nome.
            if (semNome > 0) partes.push(semNome + " ainda sem cadastro");
            nota.textContent = partes.join(" · ");
        }
    }

    function desenharOnline(dados) {
        desenharQuemChegou(dados, $("onlineLista"), $("onlineNota"), $("contaOnline"));
    }

    var btnQuem = $("btnQuemChegou");
    if (btnQuem && modalQuem) {
        btnQuem.addEventListener("click", function () {
            var ul = $("quemLista");
            if (ul) ul.innerHTML = "<li class=\"vazio\">Carregando…</li>";
            modalQuem.abrir();
            // Busca na hora: a lista muda a cada pessoa que entra, e mostrar a
            // de dois minutos atrás seria pior do que não mostrar.
            fetch(URL_DADOS, { headers: { "X-Requested-With": "XMLHttpRequest" } })
                .then(function (r) { return r.json(); })
                .then(function (d) { desenharQuemChegou(d); })
                .catch(function () {
                    if (ul) ul.innerHTML = "<li class=\"vazio\">Sem conexão com o servidor.</li>";
                });
        });
    }

    /* ---------------------------------------------------------------
       Botões
       --------------------------------------------------------------- */
    /* Bilheteria: a alavanca que abre o pagamento para todo mundo no fim.
       Com guarda: ligar um listener num id que não existe é TypeError em cima
       de null, o arquivo morre naquela linha e nada depois é ligado — e esta
       tela é a mesa do locutor no meio do evento. (Sem escrever o atalho de
       busca por id aqui: o teste que varre os ids lê o arquivo CRU, comentário
       incluído, e acharia que a tela precisa de um elemento chamado "id".) */
    var btnLiberar = document.getElementById("btnLiberar");
    if (btnLiberar) {
        btnLiberar.addEventListener("click", function () {
            var liberado = btnLiberar.dataset.liberado === "1";
            acao({ acao: "liberar", liberar: !liberado }).then(function (d) {
                if (!d || !d.ok) return;
                var agora = !!d.liberado;
                btnLiberar.dataset.liberado = agora ? "1" : "";
                btnLiberar.textContent = agora ? "🔒 Fechar pagamentos" : "💳 Liberar pagamentos";
                var txt = document.getElementById("bilheteriaEstado");
                if (txt) {
                    txt.textContent = agora
                        ? "Liberado: quem arrematou já vê o botão de pagar."
                        : "Fechado: ninguém paga ainda. Abra quando o leilão terminar.";
                }
            });
        });
    }

    document.addEventListener("click", function (e) {
        var alvo = e.target.closest("[data-acao]");
        if (!alvo) return;
        var qual = alvo.dataset.acao;

        if (qual === "microfone") return;   // tratado abaixo

        var corpo = { acao: qual };
        if (alvo.dataset.lote) corpo.lote = alvo.dataset.lote;
        if (alvo.dataset.arremate) corpo.arremate = alvo.dataset.arremate;
        if (alvo.dataset.participante) corpo.participante = alvo.dataset.participante;
        if (alvo.dataset.direcao) corpo.direcao = alvo.dataset.direcao;
        if (alvo.dataset.vez) corpo.vez = parseInt(alvo.dataset.vez, 10);

        var emPregao = estado && estado.ativo ? estado.lote : null;
        // O "dou-lhe" leva o item que ESTA tela mostra: se ele acabou de
        // trocar, o servidor recusa em vez de anunciar em cima do item novo.
        if (qual === "dou_lhe") {
            if (!emPregao) return;
            corpo.lote = emPregao.id;
        }

        // Bater o martelo mexe em dinheiro: confirma — MENOS depois do "dou-lhe
        // duas" sem lance novo, que é o terceiro tempo natural do martelo.
        var depoisDoDuas = qual === "fechar" && emPregao &&
            martelo.lote === emPregao.id && martelo.vez === 2;
        if (qual === "fechar" && !depoisDoDuas &&
            !window.confirm("Bater o martelo e fechar este item?")) return;

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

        // Abrir e VENDIDO ficam travados enquanto o pedido anda: um toque duplo
        // em "Abrir próximo" abria DOIS itens seguidos (o primeiro voltava para
        // a fila sem aviso, porque ainda não tinha lance).
        var travar = qual === "abrir" || qual === "fechar" || qual === "dou_lhe";
        if (travar) {
            if (alvo.disabled) return;
            alvo.disabled = true;
        }
        acao(corpo).then(function (d) {
            if (travar) alvo.disabled = false;
            if (qual === "dou_lhe") { pintarMartelo(); return; }
            if (!d) return;
            if (qual === "pago" || qual === "bloquear") { window.location.reload(); return; }
            recarregarDados();
        }, function () { if (travar) alvo.disabled = false; });
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
    var btnMudo = $("btnMudo");
    // O locutor QUER estar no ar (apertou Transmitir e não apertou Parar).
    // É o que separa "a conexão caiu, religue" de "ele desligou de propósito".
    var querNoAr = false;
    var relogioVoz = null;
    var quedasSeguidas = 0;

    function estadoMic(texto) { $("microEstado").textContent = texto; }

    function mostrarNoAr() {
        btnMic.textContent = "⏹ Parar transmissão";
        btnMic.classList.add("ligado");
        estadoMic(window.AudioFalar.estaMudo()
            ? "🔇 No MUDO — a transmissão continua, mas ninguém ouve você."
            : "🔴 No ar — todos que ligaram o som estão ouvindo você.");
    }

    // O Mudo é independente do Transmitir: desligar a transmissão não o solta
    // (nem o esconde). Ele continua valendo para a próxima vez que ligar.
    function mostrarDesligado() {
        btnMic.textContent = "🎤 Transmitir";
        btnMic.classList.remove("ligado");
        $("microBarra").style.width = "0%";
    }

    function textoDesligado() {
        return window.AudioFalar && window.AudioFalar.estaMudo()
            ? "Desligado, com o MUDO armado: a voz vai entrar no ar já no mudo."
            : "Desligado. Ninguém está ouvindo você pelo sistema.";
    }

    function ligarVoz() {
        return window.AudioFalar.iniciar(
            btnMic.dataset.whip,
            function (nivel) {
                $("microBarra").style.width = Math.min(100, nivel * 140) + "%";
            },
            btnMic.dataset.whipUsuario,
            btnMic.dataset.whipSenha
        ).then(function (ok) {
            // O locutor apertou PARAR enquanto esta ligação estava a caminho
            // (a religação automática leva alguns segundos): ela não pode
            // terminar colocando a voz no ar de novo.
            if (ok && !querNoAr) {
                window.AudioFalar.parar();
                return false;
            }
            if (ok) {
                quedasSeguidas = 0;
                mostrarNoAr();
                // Avisa as telas: quem estava esperando reconecta JÁ, em vez
                // de só na próxima tentativa agendada (até ~20 s depois).
                acao({ acao: "voz", no_ar: true });
            }
            return ok;
        });
    }

    /* A transmissão caiu sem o locutor pedir (celular bloqueou, Wi-Fi
       oscilou): religa sozinha, com espera crescente, até ele apertar Parar.
       Antes a mesa seguia dizendo "No ar" com ninguém ouvindo. */
    function religarVoz() {
        if (!querNoAr) return;
        clearTimeout(relogioVoz);
        var espera = Math.min(15000, 2000 * Math.pow(2, quedasSeguidas));
        quedasSeguidas++;
        estadoMic("⚠️ A transmissão caiu — religando sozinha… (continue falando quando voltar)");
        relogioVoz = setTimeout(function () {
            if (!querNoAr) return;
            ligarVoz().then(function (ok) {
                if (ok) toast("A transmissão voltou.", "success");
                else religarVoz();
            });
        }, espera);
    }

    if (btnMic && window.AudioFalar) {
        window.AudioFalar.aoCair(function () {
            toast("A transmissão de voz caiu. Religando…", "error");
            religarVoz();
        });

        btnMic.addEventListener("click", function () {
            if (querNoAr) {
                querNoAr = false;
                clearTimeout(relogioVoz);
                window.AudioFalar.parar();
                mostrarDesligado();
                estadoMic(textoDesligado());
                acao({ acao: "voz", no_ar: false });
                return;
            }
            querNoAr = true;
            quedasSeguidas = 0;
            btnMic.disabled = true;
            estadoMic("Pedindo acesso ao microfone…");
            ligarVoz().then(function (ok) {
                btnMic.disabled = false;
                if (ok) {
                    toast("Transmissão de voz ligada.", "success");
                } else {
                    querNoAr = false;
                    mostrarDesligado();
                    estadoMic("Não consegui transmitir. Confira o microfone e o servidor de áudio.");
                    toast("Falha ao ligar o microfone.", "error");
                }
            });
        });
    }

    if (btnMudo && window.AudioFalar) {
        btnMudo.addEventListener("click", function () {
            var mudo = window.AudioFalar.mudo(!window.AudioFalar.estaMudo());
            btnMudo.classList.toggle("ativo", mudo);
            btnMudo.textContent = mudo ? "🎙️ Voltar a falar" : "🔇 Mudo";
            // Mudo NUNCA liga nem desliga a transmissão: só troca o texto do
            // estado. Com a voz fora do ar, ele fica armado para a próxima vez.
            if (querNoAr) {
                mostrarNoAr();
                toast(mudo ? "Microfone no mudo — a transmissão continua." : "Microfone de volta.", mudo ? "info" : "success");
            } else {
                estadoMic(textoDesligado());
            }
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
