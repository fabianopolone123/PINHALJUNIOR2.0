/*
 * palco_show.js — os efeitos da tela "show" do pregão.
 *
 * NÃO é um segundo motor. Lance, chat, Pix e som continuam no `leilao.js`, que
 * serve às duas telas; este arquivo só ESCUTA os avisos dele (`leilao:lance`,
 * `leilao:vendido`, `leilao:chat`…) e enfeita. Por isso ele pode falhar
 * inteiro sem que ninguém perca um lance.
 *
 * Três regras seguram o arquivo num evento com 100 celulares:
 *
 * 1. **Enfeite é o que se descarta primeiro** (regra do módulo: voz e lance
 *    antes de emoji e enfeite). As partículas têm teto, e o teto CAI sozinho
 *    quando o aparelho não aguenta (quadros lentos seguidos). Quem pediu menos
 *    movimento no sistema não recebe partícula nenhuma.
 * 2. **O laço de desenho só roda enquanto há o que desenhar.** Parado, o canvas
 *    não gasta um quadro sequer.
 * 3. **Nada aqui fala com o servidor.** O termômetro da disputa conta os lances
 *    que JÁ chegam pelo stream; nenhuma requisição nova por causa de enfeite.
 */
(function () {
    "use strict";

    function $(id) { return document.getElementById(id); }

    var corpo = document.body;
    if (!corpo || !corpo.classList.contains("tela-show")) return;

    function reduzido() {
        return window.matchMedia &&
            window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    /* Reinicia uma animação de CSS: tira a classe, força o recálculo e põe de
       volta. Sem o recálculo no meio o navegador junta os dois passos e a
       animação não recomeça. */
    function reanimar(el, classe) {
        if (!el) return;
        el.classList.remove(classe);
        void el.offsetWidth;
        el.classList.add(classe);
    }

    /* ---------------------------------------------------------------
       Contador de dígitos (o "caça-níquel" do valor)
       --------------------------------------------------------------- */
    /* Cada dígito é uma fita 0-9 dentro de uma janela de 1em; o valor novo é
       só o `translateY` da fita, e a transição do CSS faz a rolagem. Vírgula,
       ponto e "R$" são caracteres fixos. Quando o número muda de tamanho
       (R$ 95 → R$ 100), a estrutura é refeita — e a rolagem começa do zero,
       que é justamente quando ela mais chama atenção. */
    var contador = $("showValor");
    var textoContador = "";

    function montarContador(texto) {
        contador.innerHTML = "";
        for (var i = 0; i < texto.length; i++) {
            var c = texto.charAt(i);
            if (c >= "0" && c <= "9") {
                var janela = document.createElement("span");
                janela.className = "digito";
                var fita = document.createElement("span");
                fita.className = "fita";
                for (var n = 0; n <= 9; n++) {
                    var s = document.createElement("span");
                    s.textContent = n;
                    fita.appendChild(s);
                }
                fita.style.setProperty("--n", 0);
                janela.appendChild(fita);
                contador.appendChild(janela);
            } else {
                var fixo = document.createElement("span");
                fixo.className = "fixo";
                // Espaço normal colapsa dentro do inline-flex: usa o inseparável.
                fixo.textContent = c === " " ? " " : c;
                contador.appendChild(fixo);
            }
        }
    }

    function mostrarValor(texto, comEfeito) {
        if (!contador || !texto || texto === textoContador) return;
        var mesmaForma = textoContador.length === texto.length &&
            textoContador.replace(/\d/g, "0") === texto.replace(/\d/g, "0");
        if (!mesmaForma) montarContador(texto);
        textoContador = texto;

        var fitas = contador.querySelectorAll(".fita");
        var digitos = texto.replace(/\D/g, "");
        // Um quadro de folga para a fita recém-montada nascer no zero e ROLAR
        // até o dígito, em vez de já aparecer parada nele.
        requestAnimationFrame(function () {
            for (var i = 0; i < fitas.length; i++) {
                fitas[i].style.setProperty("--n", digitos.charAt(i) || 0);
            }
        });
        if (comEfeito) reanimar(contador, "pulou");
    }

    /* ---------------------------------------------------------------
       Partículas (moedas, brasas) — um canvas só
       --------------------------------------------------------------- */
    var canvas = $("showFx");
    var ctx = canvas && canvas.getContext ? canvas.getContext("2d") : null;
    var particulas = [];
    var rodando = false;
    var TETO_INICIAL = 160;
    var teto = TETO_INICIAL;
    var quadrosLentos = 0;
    var ultimoQuadro = 0;
    var L = 0, A = 0;

    function medirCanvas() {
        if (!canvas) return;
        var dpr = Math.min(window.devicePixelRatio || 1, 2);
        L = window.innerWidth;
        A = window.innerHeight;
        canvas.width = Math.round(L * dpr);
        canvas.height = Math.round(A * dpr);
        canvas.style.width = L + "px";
        canvas.style.height = A + "px";
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function adicionar(p) {
        if (!ctx || reduzido() || document.hidden) return;
        if (particulas.length >= teto) return;   // enfeite excedente é descartado
        particulas.push(p);
        if (!rodando) {
            rodando = true;
            medirCanvas();
            ultimoQuadro = 0;
            requestAnimationFrame(quadro);
        }
    }

    function moeda(x, y, vx, vy, tam) {
        adicionar({
            tipo: "moeda", x: x, y: y, vx: vx, vy: vy,
            r: tam || (7 + Math.random() * 5),
            giro: Math.random() * Math.PI * 2,
            vgiro: 0.15 + Math.random() * 0.2,
            vida: 0, max: 90 + Math.random() * 40, g: 0.32
        });
    }

    function brasa(x, y) {
        adicionar({
            tipo: "brasa", x: x, y: y,
            vx: -0.4 + Math.random() * 0.8, vy: -(1.2 + Math.random() * 1.8),
            r: 1.5 + Math.random() * 2.5,
            vida: 0, max: 60 + Math.random() * 50, g: -0.01
        });
    }

    function desenharMoeda(p, alfa) {
        var largura = Math.abs(Math.cos(p.giro)) * p.r;   // a moeda "gira" no eixo
        ctx.globalAlpha = alfa;
        ctx.fillStyle = "#e0a100";
        ctx.beginPath();
        ctx.ellipse(p.x, p.y, Math.max(largura, 1.2), p.r, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = "#ffd84d";
        ctx.beginPath();
        ctx.ellipse(p.x, p.y, Math.max(largura * 0.72, 0.8), p.r * 0.72, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = "rgba(255, 255, 255, 0.85)";
        ctx.beginPath();
        ctx.ellipse(p.x - largura * 0.25, p.y - p.r * 0.35, Math.max(largura * 0.18, 0.4), p.r * 0.2, 0, 0, Math.PI * 2);
        ctx.fill();
    }

    function desenharBrasa(p, alfa) {
        ctx.globalAlpha = alfa;
        ctx.fillStyle = "rgba(255, 150, 40, 0.35)";
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r * 3, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = "#ffd27a";
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
    }

    function quadro(agora) {
        // Vigia de desempenho: quadro acima de ~45 ms (menos de 22 fps) é
        // aparelho sofrendo. Vinte seguidos e o teto cai pela metade — some
        // enfeite, nunca lance.
        if (ultimoQuadro) {
            if (agora - ultimoQuadro > 45) quadrosLentos++;
            else quadrosLentos = Math.max(0, quadrosLentos - 1);
            if (quadrosLentos > 20) {
                teto = Math.max(24, Math.floor(teto / 2));
                quadrosLentos = 0;
                if (particulas.length > teto) particulas.length = teto;
            }
        }
        ultimoQuadro = agora;

        ctx.clearRect(0, 0, L, A);
        var vivas = [];
        for (var i = 0; i < particulas.length; i++) {
            var p = particulas[i];
            p.vida++;
            p.vy += p.g;
            p.x += p.vx;
            p.y += p.vy;
            if (p.giro !== undefined) p.giro += p.vgiro;
            if (p.vida >= p.max || p.y > A + 40 || p.y < -60) continue;
            var alfa = Math.min(1, (p.max - p.vida) / 25);
            if (p.tipo === "moeda") desenharMoeda(p, alfa);
            else desenharBrasa(p, alfa);
            vivas.push(p);
        }
        ctx.globalAlpha = 1;
        particulas = vivas;
        if (particulas.length) requestAnimationFrame(quadro);
        else { ctx.clearRect(0, 0, L, A); rodando = false; }
    }

    /* Moedas pulando do botão de lance. */
    function moedasDoBotao(quantas) {
        var btn = $("btnLance");
        if (!btn) return;
        var r = btn.getBoundingClientRect();
        for (var i = 0; i < quantas; i++) {
            moeda(
                r.left + r.width * (0.25 + Math.random() * 0.5),
                r.top + 6,
                -3.5 + Math.random() * 7,
                -(6 + Math.random() * 6)
            );
        }
    }

    /* Chuva de moedas na tela inteira (o martelo). */
    function chuvaDeMoedas(duracao, densidade) {
        var fim = Date.now() + duracao;
        (function pingar() {
            if (Date.now() > fim) return;
            for (var i = 0; i < densidade; i++) {
                moeda(Math.random() * window.innerWidth, -20, -1 + Math.random() * 2, 1 + Math.random() * 3, 8 + Math.random() * 6);
            }
            setTimeout(pingar, 120);
        })();
    }

    /* ---------------------------------------------------------------
       Termômetro da disputa
       --------------------------------------------------------------- */
    /* Quantos lances chegaram nos últimos 30 s deste item. Oito já é sala
       pegando fogo. É leitura do que aconteceu — nunca pressão: não há prazo
       neste leilão, e o termômetro não inventa lance nenhum. */
    var JANELA_CALOR = 30000;
    var LANCES_PARA_FERVER = 8;
    var lancesRecentes = [];
    var calor = 0;
    var timerBrasas = null;

    function recalcularCalor() {
        var limite = Date.now() - JANELA_CALOR;
        while (lancesRecentes.length && lancesRecentes[0] < limite) lancesRecentes.shift();
        calor = Math.min(1, lancesRecentes.length / LANCES_PARA_FERVER);
        corpo.style.setProperty("--calor", calor.toFixed(2));
        corpo.classList.toggle("quente", calor >= 0.5);

        if (calor >= 0.6 && !timerBrasas && !reduzido()) {
            timerBrasas = setInterval(function () {
                var n = Math.round(1 + calor * 3);
                for (var i = 0; i < n; i++) {
                    var lado = Math.random() < 0.5 ? Math.random() * 40 : window.innerWidth - Math.random() * 40;
                    brasa(lado, window.innerHeight - 10);
                }
            }, 380);
        } else if (calor < 0.6 && timerBrasas) {
            clearInterval(timerBrasas);
            timerBrasas = null;
        }
    }
    setInterval(recalcularCalor, 1000);

    function esfriar() {
        lancesRecentes = [];
        recalcularCalor();
    }

    /* ---------------------------------------------------------------
       Foto, carimbo e troca de item
       --------------------------------------------------------------- */
    var fotoCaixa = $("loteFoto");
    var loteAtual = null;
    var fotoAtual = null;

    function atualizarFundoDaFoto(url) {
        if (!fotoCaixa || url === fotoAtual) return;
        fotoAtual = url;
        // O borrão de fundo é a própria foto. `url()` com aspas escapadas: o
        // endereço vem do servidor, mas não custa nada não confiar na forma.
        fotoCaixa.style.setProperty("--foto", url ? 'url("' + String(url).replace(/"/g, "%22") + '")' : "none");
    }

    function itemNovo() {
        reanimar(fotoCaixa, "entrou");
        reanimar(fotoCaixa, "varre");
        reanimar($("showCarimbo"), "bate");
        esfriar();
    }

    /* ---------------------------------------------------------------
       Chat compacto (ticker) e a folha do bate-papo
       --------------------------------------------------------------- */
    var ticker = $("showTicker");
    var tickerLista = $("showTickerLista");
    var btnChat = $("btnChat");
    var folha = $("showFolha");
    var naoLidas = 0;
    var tickerIniciado = false;
    var VIDA_NO_TICKER = 12000;   // ms: depois disso a bolha vai embora sozinha

    /* No celular o ticker é uma faixa de duas linhas que se esvazia sozinha —
       espaço é o que falta ali. Na tela larga ele ocupa a coluna da direita
       inteira, e duas mensagens soltas numa caixa alta pareciam um chat
       quebrado: lá ele guarda a conversa (12) e não apaga nada. */
    var telaLarga = window.matchMedia ? window.matchMedia("(min-width: 900px) and (min-height: 560px)") : null;
    function largo() { return !!(telaLarga && telaLarga.matches); }
    function quantasNoTicker() { return largo() ? 12 : 2; }

    function linhaTicker(m) {
        var li = document.createElement("li");
        if (m.locutor) li.className = "locutor";
        else if (m.meu) li.className = "meu";
        var autor = document.createElement("span");
        autor.className = "autor";
        autor.textContent = (m.autor || "") + ": ";
        li.appendChild(autor);
        li.appendChild(document.createTextNode(m.texto || ""));
        return li;
    }

    function empurrarTicker(m) {
        if (!tickerLista) return;
        var li = linhaTicker(m);
        tickerLista.appendChild(li);
        while (tickerLista.children.length > quantasNoTicker()) tickerLista.removeChild(tickerLista.firstChild);
        if (!largo()) {
            for (var i = 0; i < tickerLista.children.length - 1; i++) tickerLista.children[i].classList.add("velha");
        }
        ticker.classList.add("tem-msg");
        setTimeout(function () {
            if (!li.parentNode || largo()) return;
            li.classList.add("saindo");
            setTimeout(function () {
                if (li.parentNode) li.parentNode.removeChild(li);
                if (!tickerLista.children.length) ticker.classList.remove("tem-msg");
            }, 500);
        }, VIDA_NO_TICKER);
    }

    function marcarNaoLidas() {
        var badge = $("showNaoLidas");
        if (!badge) return;
        badge.textContent = naoLidas > 9 ? "9+" : naoLidas;
        badge.hidden = naoLidas === 0;
    }

    function abrirFolha() {
        if (!folha) return;
        folha.hidden = false;
        naoLidas = 0;
        marcarNaoLidas();
        var lista = $("chatLista");
        if (lista) lista.scrollTop = lista.scrollHeight;
    }

    function fecharFolha() {
        if (folha) folha.hidden = true;
    }

    if (ticker) ticker.addEventListener("click", abrirFolha);
    if (btnChat) btnChat.addEventListener("click", abrirFolha);
    if ($("showFolhaFechar")) $("showFolhaFechar").addEventListener("click", fecharFolha);
    if (folha) {
        // Fecha no fundo só com mousedown E click no fundo (regra do projeto:
        // arrastar a seleção para fora não pode fechar).
        var comecouNoFundo = false;
        folha.addEventListener("mousedown", function (e) { comecouNoFundo = e.target === folha; });
        folha.addEventListener("click", function (e) {
            if (comecouNoFundo && e.target === folha) fecharFolha();
            comecouNoFundo = false;
        });
    }
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && folha && !folha.hidden) fecharFolha();
    });

    /* ---------------------------------------------------------------
       Emojis: combo e mini explosão
       --------------------------------------------------------------- */
    var combo = { emoji: null, n: 0, em: 0 };
    var JANELA_COMBO = 1200;   // ms entre toques para contar como sequência
    var botoesReacao = $("reacoesBotoes");

    if (botoesReacao) {
        botoesReacao.addEventListener("click", function (e) {
            var btn = e.target.closest(".btn-reacao");
            if (!btn) return;
            reanimar(btn, "pop");

            var emoji = btn.dataset.emoji;
            var agora = Date.now();
            if (combo.emoji === emoji && agora - combo.em < JANELA_COMBO) combo.n++;
            else combo = { emoji: emoji, n: 1, em: agora };
            combo.em = agora;

            if (reduzido()) return;
            // Estouro: seis cópias pequenas saindo do botão em leque.
            for (var i = 0; i < 6; i++) {
                var s = document.createElement("span");
                s.className = "show-estouro";
                s.textContent = emoji;
                var ang = (Math.PI * 2 * i) / 6 + Math.random() * 0.6;
                var dist = 26 + Math.random() * 18;
                s.style.setProperty("--dx", (Math.cos(ang) * dist).toFixed(1) + "px");
                s.style.setProperty("--dy", (Math.sin(ang) * dist - 14).toFixed(1) + "px");
                s.style.setProperty("--giro", (Math.random() * 80 - 40).toFixed(0) + "deg");
                btn.appendChild(s);
                s.addEventListener("animationend", function () { this.remove(); });
            }
            if (combo.n >= 2) {
                var velho = btn.querySelector(".show-combo");
                if (velho) velho.remove();
                var c = document.createElement("span");
                c.className = "show-combo";
                c.textContent = "x" + combo.n + (combo.n >= 5 ? "!" : "");
                btn.appendChild(c);
                c.addEventListener("animationend", function () { this.remove(); });
            }
        });
    }

    /* ---------------------------------------------------------------
       Os avisos do motor
       --------------------------------------------------------------- */
    function superadoAgora() {
        var placar = document.querySelector(".show-placar");
        return !!(placar && placar.classList.contains("superado"));
    }

    /* O mini placar do topo da folha do chat: cópia do que o motor escreveu no
       placar grande (rótulo + valor), para quem está conversando não perder a
       ponta sem saber. Vazio quando não há item em pregão. */
    function espelharPlacar(temLote) {
        var mini = $("showFolhaPlacar");
        if (!mini) return;
        if (!temLote) { mini.textContent = ""; return; }
        var nome = ($("liderNome") || {}).textContent || "";
        var valor = ($("liderValor") || {}).textContent || "";
        var placar = document.querySelector(".show-placar");
        var eu = !!(placar && placar.classList.contains("eu-ganhando"));
        var quem = superadoAgora() ? "🔴 Te superaram" : eu ? "👑 Você" : nome;
        mini.textContent = quem + " · " + valor;
    }

    document.addEventListener("leilao:estado", function (e) {
        var est = e.detail && e.detail.estado;
        var lote = est && est.ativo ? est.lote : null;

        if (lote) {
            if (loteAtual !== lote.id) {
                var primeira = loteAtual === null;
                loteAtual = lote.id;
                // Na primeira pintura (a pessoa acabou de chegar) a foto entra,
                // mas sem carimbo: "NOVO ITEM!" em item que já estava aberto
                // seria mentira.
                if (primeira) reanimar(fotoCaixa, "entrou");
                else itemNovo();
            }
            atualizarFundoDaFoto(lote.foto || null);
        } else {
            loteAtual = null;
            esfriar();
        }
        // O botão de lance mora FORA do bloco do item (para o chat e os
        // emojis ficarem entre eles), então o motor não o esconde sozinho no
        // intervalo — quem esconde é aqui.
        if ($("showAcao")) $("showAcao").hidden = !lote;

        var valor = $("liderValor");
        if (valor) mostrarValor(valor.textContent, false);
        corpo.classList.toggle("superado", superadoAgora());
        espelharPlacar(!!lote);

        // O ticker existe enquanto o chat existe (o motor esconde o `#chat`
        // quando o leilão sai do ar ou o chat fecha).
        var chat = $("chat");
        var chatAberto = !!(chat && !chat.hidden);
        if (ticker) ticker.hidden = !chatAberto;
        if (btnChat) btnChat.hidden = !chatAberto;
        if (!chatAberto) fecharFolha();

        // Na chegada, as duas últimas mensagens da noite já aparecem.
        if (!tickerIniciado && chatAberto && est.chat && est.chat.mensagens) {
            tickerIniciado = true;
            var dadosTela = $("dadosLeilao");
            var eu = dadosTela ? parseInt(dadosTela.dataset.eu, 10) : NaN;
            est.chat.mensagens.slice(-quantasNoTicker()).forEach(function (m) {
                var meu = !!(eu && m.autor_id === eu);
                empurrarTicker({ autor: meu ? "Você" : m.autor, texto: m.texto, meu: meu, locutor: !m.autor_id });
            });
        }
    });

    document.addEventListener("leilao:lance", function (e) {
        var d = e.detail || {};
        lancesRecentes.push(Date.now());
        recalcularCalor();

        var valor = $("liderValor");
        if (valor) mostrarValor(valor.textContent, true);
        reanimar(fotoCaixa, "varre");
        corpo.classList.toggle("superado", superadoAgora());
        espelharPlacar(true);

        var vinheta = $("showVinheta");
        if (d.meTiraram) {
            reanimar(vinheta, "vermelha");
        } else if (d.meu) {
            reanimar(vinheta, "dourada");
            moedasDoBotao(22);
        } else {
            moedasDoBotao(Math.round(4 + calor * 10));
        }
    });

    // O toque responde NA HORA (antes da ida e volta do servidor), como o
    // resto do motor: poucas moedas agora, a festa maior vem com o lance.
    document.addEventListener("leilao:toque_lance", function () { moedasDoBotao(8); });

    document.addEventListener("leilao:lote_aberto", function () {
        // O `leilao:estado` que vem junto já marcou a troca; aqui só garante o
        // carimbo quando o item reabre (item devolvido ao leilão tem o MESMO id).
        reanimar($("showCarimbo"), "bate");
    });

    document.addEventListener("leilao:vendido", function (e) {
        var d = e.detail || {};
        esfriar();
        if (!d.vendido) return;
        chuvaDeMoedas(d.euGanhei ? 3200 : 2000, d.euGanhei ? 6 : 3);
        // O valor da festa sobe contando até o final, como placar de prêmio.
        var alvo = $("festaValor");
        var final = parseFloat(d.valor || 0);
        if (!alvo || !(final > 0) || reduzido()) return;
        var inicio = null;
        var DURACAO = 1400;
        // O relógio vem SEMPRE do requestAnimationFrame: o carimbo dele é o do
        // começo do quadro, que pode ser anterior ao `performance.now()` — e
        // misturar os dois dava tempo negativo (a festa contava "R$ -6,17").
        requestAnimationFrame(function contar(t) {
            if (inicio === null) inicio = t;
            var k = Math.max(0, Math.min(1, (t - inicio) / DURACAO));
            var suave = 1 - Math.pow(1 - k, 3);
            alvo.textContent = "R$ " + (final * suave).toLocaleString("pt-BR", {
                minimumFractionDigits: 2, maximumFractionDigits: 2
            });
            if (k < 1) requestAnimationFrame(contar);
        });
        // Garantia: se o navegador parar de dar quadros (aba no fundo,
        // economia de bateria), o valor CERTO fica na tela mesmo assim. Um
        // prêmio parado em "R$ 0,00" seria pior do que nenhuma animação.
        setTimeout(function () {
            alvo.textContent = "R$ " + final.toLocaleString("pt-BR", {
                minimumFractionDigits: 2, maximumFractionDigits: 2
            });
        }, DURACAO + 250);
    });

    document.addEventListener("leilao:chat", function (e) {
        var m = e.detail || {};
        empurrarTicker(m);
        if (folha && folha.hidden && !m.meu) {
            naoLidas++;
            marcarNaoLidas();
        }
    });

    window.addEventListener("resize", function () { if (rodando) medirCanvas(); });

    // Primeira pintura do contador, antes de qualquer aviso.
    if ($("liderValor")) mostrarValor($("liderValor").textContent, false);
})();
