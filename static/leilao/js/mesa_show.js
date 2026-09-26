/*
 * mesa_show.js — a camada da mesa "show" (em teste ao lado da clássica).
 *
 * NÃO mexe no leilão. Quem abre item, bate o martelo, liga o microfone e fala
 * no chat continua sendo o `locutor.js` — o motor das duas mesas. Este arquivo
 * só ESCUTA os avisos `mesa:*` que o motor emite e desenha em cima:
 *
 *   - o placar da noite (vendido, recebido, itens batidos, maior arremate…),
 *     com os números rolando quando mudam;
 *   - o anel do silêncio (enche de 0 a 30 s sem lance);
 *   - o ritmo da disputa (lances no último minuto) e o calor da tela;
 *   - o gráfico do item e o placar de quem está disputando;
 *   - o próximo da fila, com foto;
 *   - os carimbos de NOVO ITEM / VENDIDO, com confete;
 *   - o estado da voz no topo e a hora.
 *
 * Nenhuma requisição sai daqui: tudo vem do que o motor já recebeu (o stream
 * e o `/locutor/dados/?resumo=1`). Se este arquivo quebrar, a mesa continua
 * funcionando — só perde o enfeite.
 *
 * Carrega ANTES do `locutor.js`: o primeiro `mesa:estado` sai na carga dele.
 */
(function () {
    "use strict";

    function $(id) { return document.getElementById(id); }
    if (!$("msItem")) return;

    var reduzido = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);

    function num(v) {
        var n = parseFloat(v || 0);
        return isNaN(n) ? 0 : n;
    }

    function moeda(n) {
        return "R$ " + num(n).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function inteiro(n) { return Math.round(num(n)).toLocaleString("pt-BR"); }

    function ouvir(nome, fn) {
        document.addEventListener("mesa:" + nome, function (e) {
            // Um desenho com defeito não pode levar os outros junto.
            try { fn(e.detail || {}); } catch (erro) { /* só enfeite */ }
        });
    }

    /* Reinicia uma animação de CSS: tira a classe, força o recálculo, põe de novo. */
    function pulsar(el, classe) {
        if (!el) return;
        el.classList.remove(classe);
        void el.offsetWidth;
        el.classList.add(classe);
    }

    function texto(id, valor) {
        var el = $(id);
        if (el) el.textContent = valor;
    }

    function limpar(el) { while (el && el.firstChild) el.removeChild(el.firstChild); }

    function li(classe, conteudo) {
        var item = document.createElement("li");
        if (classe) item.className = classe;
        if (conteudo !== undefined) item.textContent = conteudo;
        return item;
    }

    function span(classe, conteudo) {
        var s = document.createElement("span");
        if (classe) s.className = classe;
        s.textContent = conteudo;
        return s;
    }

    /* ---------------------------------------------------------------
       Números que rolam
       --------------------------------------------------------------- */
    /* O número desliza do valor anterior para o novo. Na PRIMEIRA pintura não
       rola (a tela acabou de abrir, não "aconteceu" nada), e com movimento
       reduzido pedido pelo aparelho, só troca. O texto final é sempre o exato
       — a animação nunca termina num valor arredondado. */
    function rolar(el, alvo, formato) {
        if (!el) return;
        var de = el._msValor;
        el._msValor = alvo;
        if (de === undefined || de === alvo || reduzido) {
            el.textContent = formato(alvo);
            return;
        }
        // Relógio SÓ do `requestAnimationFrame` (o início é o carimbo do 1º
        // quadro): misturar com `performance.now()` já deu tempo negativo na
        // tela do público, e a festa contou "R$ -6,17" (REGRAS_CODEX).
        var inicio = null;
        var duracao = 700;
        cancelAnimationFrame(el._msQuadro);
        clearTimeout(el._msGarantia);
        function passo(t) {
            if (inicio === null) inicio = t;
            var p = Math.max(0, Math.min(1, (t - inicio) / duracao));
            var suave = 1 - Math.pow(1 - p, 3);
            el.textContent = formato(p < 1 ? de + (alvo - de) * suave : alvo);
            if (p < 1) el._msQuadro = requestAnimationFrame(passo);
        }
        el._msQuadro = requestAnimationFrame(passo);
        // Garantia do valor final: aba em segundo plano para de dar quadros, e
        // o número ficaria parado no meio do caminho.
        el._msGarantia = setTimeout(function () {
            cancelAnimationFrame(el._msQuadro);
            el.textContent = formato(alvo);
        }, duracao + 150);
        if (alvo > de) pulsar(el, "ms-subiu");
    }

    /* ---------------------------------------------------------------
       Relógio
       --------------------------------------------------------------- */
    function relogio() {
        texto("msRelogio", new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }));
    }
    relogio();
    setInterval(relogio, 5000);

    /* ---------------------------------------------------------------
       Item em pregão: valor, anel, ritmo
       --------------------------------------------------------------- */
    var loteId = null;
    var liderAtual = null;
    // Horários (no relógio DESTE aparelho) dos lances do item atual — é com
    // eles que o ritmo é contado. Vêm do histórico da mesa e dos lances que
    // chegam pelo stream.
    var batidas = [];

    ouvir("estado", function (d) {
        var e = d.estado || {};
        var lote = e.ativo ? e.lote : null;
        var novoLote = (lote ? lote.id : null) !== loteId;
        liderAtual = lote && lote.lider ? lote.lider.nome : null;

        if (novoLote) {
            loteId = lote ? lote.id : null;
            batidas = [];
            desenharRitmo();
            var v = $("mesaValor");
            if (v) v._msValor = undefined;      // item novo não "rola" do anterior
            if (!lote) anel(0, false, true);
        }

        var valor = $("mesaValor");
        if (lote && valor) {
            rolar(valor, num(lote.tem_lance ? lote.valor_atual : lote.lance_inicial), moeda);
        }
        var item = $("msItem");
        if (item) item.classList.toggle("ms-vazio", !lote);
    });

    var CIRCUNFERENCIA = 2 * Math.PI * 52;

    function anel(segundos, temLance, desligado) {
        var cheio = $("msAnelCheio");
        var caixa = $("msAnel");
        if (!cheio || !caixa) return;
        var fracao = desligado ? 0 : Math.min(1, segundos / 30);
        cheio.style.strokeDasharray = CIRCUNFERENCIA.toFixed(1);
        cheio.style.strokeDashoffset = (CIRCUNFERENCIA * (1 - fracao)).toFixed(1);
        caixa.classList.toggle("apertado", !desligado && segundos >= 15 && segundos < 30);
        caixa.classList.toggle("final", !desligado && segundos >= 30);
        caixa.classList.toggle("desligado", !!desligado);
    }
    anel(0, false, true);

    ouvir("tick", function (d) { anel(d.parado || 0, d.tem_lance, false); });

    function desenharRitmo() {
        var agora = Date.now();
        batidas = batidas.filter(function (t) { return agora - t < 60000; });
        var n = batidas.length;
        var calor = Math.min(1, n / 10);
        var barra = $("msCalor");
        if (barra) barra.style.width = Math.round(calor * 100) + "%";
        document.body.style.setProperty("--calor", calor.toFixed(2));

        var frase;
        if (!loteId) frase = "sem item em pregão";
        else if (n === 0) frase = liderAtual ? "esfriou — nenhum lance no último minuto" : "aguardando o 1º lance";
        else if (n >= 8) frase = "🔥 pegando fogo — " + n + " lances no último minuto";
        else if (n >= 4) frase = "quente — " + n + " lances no último minuto";
        else frase = "morno — " + n + " lance" + (n === 1 ? "" : "s") + " no último minuto";
        texto("msRitmo", frase);

        var ritmo = barra && barra.parentNode;
        if (ritmo) ritmo.classList.toggle("fogo", n >= 8);
    }
    setInterval(desenharRitmo, 2000);

    ouvir("lance", function (d) {
        if (d.lote && d.lote.id !== loteId) return;
        batidas.push(Date.now());
        desenharRitmo();
        pulsar($("msItem"), "ms-lance-novo");
    });

    /* ---------------------------------------------------------------
       Carimbos e confete
       --------------------------------------------------------------- */
    var relogioCarimbo = null;

    function carimbo(titulo, sub, tipo) {
        var el = $("msCarimbo");
        if (!el) return;
        limpar(el);
        var caixa = document.createElement("div");
        caixa.className = "ms-carimbo-caixa";
        caixa.appendChild(span("ms-carimbo-titulo", titulo));
        if (sub) caixa.appendChild(span("ms-carimbo-sub", sub));
        el.appendChild(caixa);
        el.className = "ms-carimbo " + tipo;
        pulsar(el, "mostrar");
        clearTimeout(relogioCarimbo);
        relogioCarimbo = setTimeout(function () { el.classList.remove("mostrar"); }, 2600);
    }

    var CORES = ["#ffc53d", "#62c462", "#4a90d9", "#ff6b52", "#ffffff", "#ffd166"];

    function confete() {
        var palco = $("msConfete");
        if (!palco || reduzido) return;
        limpar(palco);
        // Teto baixo de propósito: a mesa pode estar num notebook velho,
        // transmitindo voz ao mesmo tempo.
        for (var i = 0; i < 28; i++) {
            var p = document.createElement("i");
            var angulo = Math.random() * Math.PI * 2;
            var raio = 90 + Math.random() * 140;
            p.style.setProperty("--dx", Math.round(Math.cos(angulo) * raio) + "px");
            p.style.setProperty("--dy", Math.round(Math.sin(angulo) * raio - 40) + "px");
            p.style.setProperty("--giro", Math.round(Math.random() * 720 - 360) + "deg");
            p.style.background = CORES[i % CORES.length];
            p.style.animationDelay = Math.round(Math.random() * 120) + "ms";
            palco.appendChild(p);
        }
        setTimeout(function () { limpar(palco); }, 1900);
    }

    ouvir("lote_aberto", function (d) {
        var lote = d && d.ativo ? d.lote : null;
        carimbo("NOVO ITEM", lote ? lote.nome : "", "novo");
    });

    ouvir("vendido", function (d) {
        if (d.vendido) {
            carimbo("VENDIDO!", (d.vencedor || "") + " · " + moeda(d.valor), "vendido");
            confete();
        } else {
            carimbo("SEM LANCE", "dá para abrir de novo pela aba Itens", "sem");
        }
    });

    /* ---------------------------------------------------------------
       Voz, sala e chat
       --------------------------------------------------------------- */
    ouvir("voz", function (d) {
        var el = $("msNoAr");
        if (!el) return;
        var estado = d.caiu ? "caiu" : !d.no_ar ? "off" : d.mudo ? "mudo" : "on";
        el.dataset.estado = estado;
        el.textContent = {
            off: "🎙️ Voz desligada",
            on: "🔴 NO AR",
            mudo: "🔇 NO MUDO",
            caiu: "⚠️ Voz caiu — religando"
        }[estado];
    });

    var onlineAntes = null;
    ouvir("online", function (d) {
        if (onlineAntes !== null && d.online > onlineAntes) pulsar($("btnQuemChegou"), "ms-chegou");
        onlineAntes = d.online;
    });

    ouvir("chat", function (m) {
        // Só mensagem do PÚBLICO acende o card: a do locutor ele mesmo mandou.
        if (m && m.autor_id) pulsar(document.querySelector(".ms-chat"), "ms-chat-novo");
    });

    /* ---------------------------------------------------------------
       O que vem do /locutor/dados/
       --------------------------------------------------------------- */
    ouvir("dados", function (d) {
        var e = d.estado || {};
        var lote = e.ativo ? e.lote : null;
        var historico = (d.historico || []).filter(function (l) { return !l.cancelado; });

        semearRitmo(historico, e.servidor_em, lote);
        grafico(historico, lote);
        disputa(historico, lote);
        proximo(d.fila || [], d.restam_na_fila || 0);
        if (d.noite) noite(d.noite);
    });

    /* O ritmo nasce do histórico (a mesa pode ter sido aberta no meio de um
       item quente) e depois segue pelos lances do stream. O horário do lance é
       do servidor; convertido para o relógio deste aparelho pela diferença que
       o próprio `servidor_em` informa. */
    function semearRitmo(historico, servidorEm, lote) {
        if (!lote || lote.id !== loteId) return;
        var servidor = Date.parse(servidorEm || "");
        var diferenca = isNaN(servidor) ? 0 : Date.now() - servidor;
        batidas = historico
            .map(function (l) { return Date.parse(l.em) + diferenca; })
            .filter(function (t) { return !isNaN(t); });
        desenharRitmo();
    }

    var SVG = "http://www.w3.org/2000/svg";

    function grafico(historico, lote) {
        var svg = $("msGrafico");
        var vazio = $("msGraficoVazio");
        if (!svg) return;
        limpar(svg);
        texto("msLancesConta", historico.length ? "(" + historico.length + ")" : "");

        // O histórico chega do mais novo para o mais antigo.
        var valores = historico.map(function (l) { return num(l.valor); }).reverse();
        if (lote && valores.length) valores.unshift(num(lote.lance_inicial));
        if (vazio) vazio.hidden = valores.length > 1;
        if (valores.length < 2) return;

        var L = 300, A = 90, margem = 8;
        var min = Math.min.apply(null, valores);
        var max = Math.max.apply(null, valores);
        var faixa = max - min || 1;
        var pontos = valores.map(function (v, i) {
            var x = (i / (valores.length - 1)) * L;
            var y = A - margem - ((v - min) / faixa) * (A - margem * 2);
            return [x, y];
        });
        var linha = pontos.map(function (p) { return p[0].toFixed(1) + "," + p[1].toFixed(1); }).join(" ");

        var defs = document.createElementNS(SVG, "defs");
        var grad = document.createElementNS(SVG, "linearGradient");
        grad.setAttribute("id", "msGradGrafico");
        grad.setAttribute("x1", "0"); grad.setAttribute("x2", "0");
        grad.setAttribute("y1", "0"); grad.setAttribute("y2", "1");
        [["0", "0.45"], ["1", "0"]].forEach(function (s) {
            var stop = document.createElementNS(SVG, "stop");
            stop.setAttribute("offset", s[0]);
            stop.setAttribute("stop-color", "#ffc53d");
            stop.setAttribute("stop-opacity", s[1]);
            grad.appendChild(stop);
        });
        defs.appendChild(grad);
        svg.appendChild(defs);

        var area = document.createElementNS(SVG, "polygon");
        area.setAttribute("points", "0," + A + " " + linha + " " + L + "," + A);
        area.setAttribute("class", "ms-grafico-area");
        svg.appendChild(area);

        var traco = document.createElementNS(SVG, "polyline");
        traco.setAttribute("points", linha);
        traco.setAttribute("class", "ms-grafico-linha");
        svg.appendChild(traco);

        var ultimo = pontos[pontos.length - 1];
        var ponto = document.createElementNS(SVG, "circle");
        ponto.setAttribute("cx", ultimo[0].toFixed(1));
        ponto.setAttribute("cy", ultimo[1].toFixed(1));
        ponto.setAttribute("r", "4");
        ponto.setAttribute("class", "ms-grafico-ponto");
        svg.appendChild(ponto);
    }

    /* Quem está disputando ESTE item: quantos lances cada um deu e até onde
       foi. É o que dá ao locutor a narração pronta — "a Ana e o João estão
       brigando por essa cesta!". */
    function disputa(historico, lote) {
        var ul = $("msDisputa");
        if (!ul) return;
        limpar(ul);
        var porPessoa = {};
        var ordem = [];
        historico.forEach(function (l) {
            var chave = l.quem_chave || l.quem_id || l.quem;
            if (!porPessoa[chave]) {
                porPessoa[chave] = { quem: l.quem, n: 0, maior: 0 };
                ordem.push(chave);
            }
            porPessoa[chave].n += 1;
            porPessoa[chave].maior = Math.max(porPessoa[chave].maior, num(l.valor));
        });
        var pessoas = ordem.map(function (k) { return porPessoa[k]; })
            .sort(function (a, b) { return b.maior - a.maior || b.n - a.n; })
            .slice(0, 5);

        if (!pessoas.length) {
            ul.appendChild(li("vazio", lote ? "Ninguém ainda — o 1º lance abre a briga." : "Nenhum item em pregão."));
            return;
        }
        var maisLances = Math.max.apply(null, pessoas.map(function (p) { return p.n; }));
        pessoas.forEach(function (p, i) {
            var item = li(i === 0 ? "lider" : "");
            var topo = document.createElement("div");
            topo.className = "ms-disputa-topo";
            topo.appendChild(span("ms-disputa-nome", (i === 0 ? "👑 " : "") + p.quem));
            topo.appendChild(span("ms-disputa-valor", moeda(p.maior)));
            item.appendChild(topo);
            var barra = document.createElement("span");
            barra.className = "ms-disputa-barra";
            var cheio = document.createElement("span");
            cheio.style.width = Math.max(8, Math.round((p.n / maisLances) * 100)) + "%";
            barra.appendChild(cheio);
            item.appendChild(barra);
            item.appendChild(span("ms-disputa-n", p.n + " lance" + (p.n === 1 ? "" : "s")));
            ul.appendChild(item);
        });
    }

    function proximo(fila, restam) {
        var p = fila[0];
        var foto = $("msProximoFoto");
        texto("msProximoNome", p ? "nº " + p.numero + " — " + p.nome : "Fila vazia");
        var partes = [];
        if (p) {
            partes.push("inicial " + moeda(p.lance_inicial));
            if (p.medidas) partes.push(p.medidas);
            if (p.voltas) partes.push("voltou " + p.voltas + "x");
            if (restam > 1) partes.push("depois dele, mais " + (restam - 1));
        }
        texto("msProximoLinha", partes.join(" · "));
        if (foto) {
            if (p && p.foto) {
                if (foto.getAttribute("src") !== p.foto) foto.src = p.foto;
                foto.hidden = false;
            } else {
                foto.hidden = true;
            }
        }
        var card = $("msProximo");
        if (card) card.classList.toggle("ms-vazio", !p);
    }

    /* ---------------------------------------------------------------
       Placar da noite + aba Noite
       --------------------------------------------------------------- */
    function noite(n) {
        rolar($("msKpiVendido"), num(n.vendido), moeda);
        texto("msKpiRecebido", "recebido " + moeda(n.recebido));
        texto("msKpiItens", n.vendidos + " / " + n.itens);
        var barra = $("msKpiItensBarra");
        if (barra) barra.style.width = (n.itens ? Math.round((n.vendidos / n.itens) * 100) : 0) + "%";
        rolar($("msKpiFila"), n.na_fila, inteiro);
        texto("msKpiSemLance", n.sem_lance
            ? n.sem_lance + " sem lance (dá para reabrir)"
            : "nenhum sem lance");
        if (n.maior) {
            rolar($("msKpiMaior"), num(n.maior.valor), moeda);
            texto("msKpiMaiorQuem", "nº " + n.maior.numero + " " + n.maior.nome + (n.maior.quem ? " · " + n.maior.quem : ""));
        } else {
            texto("msKpiMaior", "—");
            texto("msKpiMaiorQuem", "ainda nenhum");
        }
        rolar($("msKpiLances"), n.lances, inteiro);
        texto("msKpiQuem", n.quem_deu_lance
            ? n.quem_deu_lance + " pessoa" + (n.quem_deu_lance === 1 ? "" : "s") + " já deu lance"
            : "ninguém deu lance");
        rolar($("msKpiMedia"), num(n.ticket_medio), moeda);

        andamento(n);
        ranking(n.top || []);
        ultimos(n.ultimos || []);
    }

    function andamento(n) {
        var caixa = $("msAndamento");
        if (!caixa) return;
        limpar(caixa);
        var total = n.itens || 0;
        var partes = [
            ["vendido", "Batidos", n.vendidos],
            ["aberto", "Em pregão", n.em_pregao],
            ["fila", "Na fila", n.na_fila],
            ["sem_lance", "Sem lance", n.sem_lance]
        ];
        var barra = document.createElement("div");
        barra.className = "ms-andamento-barra";
        partes.forEach(function (p) {
            if (!p[2] || !total) return;
            var s = document.createElement("span");
            s.className = "parte-" + p[0];
            s.style.width = ((p[2] / total) * 100).toFixed(2) + "%";
            s.title = p[1] + ": " + p[2];
            barra.appendChild(s);
        });
        caixa.appendChild(barra);

        var legenda = document.createElement("ul");
        legenda.className = "ms-andamento-legenda";
        partes.forEach(function (p) {
            var item = li("parte-" + p[0]);
            item.appendChild(span("ms-bolinha", ""));
            item.appendChild(span("", p[1]));
            item.appendChild(span("ms-andamento-n", String(p[2] || 0)));
            legenda.appendChild(item);
        });
        caixa.appendChild(legenda);

        var resumo = document.createElement("p");
        resumo.className = "micro-ajuda";
        resumo.textContent = total
            ? Math.round(((n.vendidos || 0) / total) * 100) + "% da noite batida · " + total + " itens no total"
            : "Nenhum item cadastrado.";
        caixa.appendChild(resumo);
    }

    var MEDALHAS = ["🥇", "🥈", "🥉", "4º", "5º"];

    function ranking(top) {
        var ol = $("msTop");
        if (!ol) return;
        limpar(ol);
        if (!top.length) { ol.appendChild(li("vazio", "Ninguém arrematou ainda.")); return; }
        top.forEach(function (t, i) {
            var item = li("");
            item.appendChild(span("ms-medalha", MEDALHAS[i] || ""));
            var corpo = document.createElement("span");
            corpo.className = "ms-top-corpo";
            corpo.appendChild(span("ms-top-nome", t.quem));
            corpo.appendChild(span("ms-top-itens", t.itens + (t.itens === 1 ? " item" : " itens")));
            item.appendChild(corpo);
            item.appendChild(span("ms-top-total", moeda(t.total)));
            ol.appendChild(item);
        });
    }

    function ultimos(lista) {
        var ul = $("msUltimos");
        if (!ul) return;
        limpar(ul);
        if (!lista.length) { ul.appendChild(li("vazio", "Nenhum item batido ainda.")); return; }
        lista.forEach(function (a) {
            var item = li("");
            var corpo = document.createElement("span");
            corpo.className = "ms-ultimo-corpo";
            corpo.appendChild(span("ms-ultimo-item", "nº " + a.numero + " " + a.item));
            corpo.appendChild(span("ms-ultimo-quem", a.quem));
            item.appendChild(corpo);
            var fim = document.createElement("span");
            fim.className = "ms-ultimo-fim";
            fim.appendChild(span("ms-ultimo-valor", moeda(a.valor)));
            fim.appendChild(span("selo " + (a.pago ? "selo-pago" : "selo-aguardando"), a.pago ? "pago" : "a pagar"));
            item.appendChild(fim);
            ul.appendChild(item);
        });
    }
})();
