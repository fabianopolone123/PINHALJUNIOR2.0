/*
 * som.js — efeitos sonoros do leilão, SINTETIZADOS na hora (WebAudio).
 *
 * Por que sintetizar em vez de tocar arquivos:
 * - zero download (num leilão, 50 celulares baixando .mp3 no mesmo segundo é
 *   banda desperdiçada justamente quando o pregão está pegando fogo);
 * - zero latência — o "ping" do lance sai no mesmo instante do evento;
 * - zero dependência e zero arquivo binário no repositório (regra do projeto).
 *
 * O navegador SÓ deixa tocar som depois de um gesto da pessoa. Por isso nada
 * soa até alguém apertar o botão 🔊 — que chama `ativar()`.
 */
window.SomLeilao = (function () {
    let ctx = null;
    let mestre = null;
    let ligado = false;

    function ativar() {
        if (!ctx) {
            const AC = window.AudioContext || window.webkitAudioContext;
            if (!AC) return false;
            ctx = new AC();
            mestre = ctx.createGain();
            mestre.gain.value = 0.5;
            mestre.connect(ctx.destination);
        }
        if (ctx.state === "suspended") ctx.resume();
        ligado = true;
        return true;
    }

    function desativar() {
        ligado = false;
    }

    /* Uma nota: onda + envelope. O envelope (ataque rápido, queda suave) é o
       que faz soar como "ping" e não como um bipe de forno. */
    function nota(freq, inicio, duracao, volume, tipo) {
        if (!ctx) return;
        const t = ctx.currentTime + inicio;
        const osc = ctx.createOscillator();
        const g = ctx.createGain();
        osc.type = tipo || "sine";
        osc.frequency.setValueAtTime(freq, t);
        g.gain.setValueAtTime(0.0001, t);
        g.gain.exponentialRampToValueAtTime(volume, t + 0.012);
        g.gain.exponentialRampToValueAtTime(0.0001, t + duracao);
        osc.connect(g);
        g.connect(mestre);
        osc.start(t);
        osc.stop(t + duracao + 0.02);
    }

    function tocar(fn) {
        if (!ligado || !ctx) return;
        if (ctx.state === "suspended") ctx.resume();
        fn();
    }

    return {
        ativar: ativar,
        desativar: desativar,
        ligado: function () { return ligado; },

        /* Lance novo: duas notas subindo. Curto, cristalino, não cansa em 200
           repetições numa noite. */
        lance: function () {
            tocar(function () {
                nota(880, 0, 0.11, 0.32, "triangle");
                nota(1318.5, 0.055, 0.13, 0.26, "triangle");
            });
        },

        /* Eu fui superado: duas notas descendo — a pessoa entende sem ler. */
        superado: function () {
            tocar(function () {
                nota(440, 0, 0.12, 0.3, "sawtooth");
                nota(330, 0.07, 0.16, 0.24, "sawtooth");
            });
        },

        /* Contagem final: tique seco a cada segundo. */
        tique: function (urgente) {
            tocar(function () {
                nota(urgente ? 1200 : 800, 0, 0.05, urgente ? 0.3 : 0.18, "square");
            });
        },

        /* Martelo: acorde maior ascendente. */
        vendido: function () {
            tocar(function () {
                nota(523.25, 0, 0.16, 0.3, "triangle");
                nota(659.25, 0.1, 0.16, 0.3, "triangle");
                nota(783.99, 0.2, 0.34, 0.34, "triangle");
            });
        },

        /* Fui EU que arrematei: fanfarra um pouco mais longa. */
        arrematei: function () {
            tocar(function () {
                nota(523.25, 0, 0.14, 0.3, "triangle");
                nota(659.25, 0.09, 0.14, 0.3, "triangle");
                nota(783.99, 0.18, 0.14, 0.3, "triangle");
                nota(1046.5, 0.27, 0.5, 0.36, "triangle");
            });
        },

        /* Aviso/erro discreto. */
        erro: function () {
            tocar(function () {
                nota(220, 0, 0.16, 0.22, "square");
            });
        }
    };
})();

/*
 * musica.js (dentro do som.js) — base ambiente de fundo.
 *
 * Duas fontes possíveis:
 *  1. Um ARQUIVO que o clube subiu (Preparação → Configuração). Toca em laço.
 *  2. Sem arquivo, uma base SINTETIZADA aqui mesmo: acordes lentos em pad.
 *     Zero download, zero arquivo no repositório e nenhuma questão de direito
 *     autoral — que é o motivo de ela existir.
 *
 * Quem liga, desliga e ajusta o volume é o LOCUTOR, para todo mundo junto: ele
 * sente a sala. O volume nasce baixo de propósito — é fundo, não show, e tem de
 * caber debaixo da voz dele.
 */
window.MusicaLeilao = (function () {
    var ctx = null;
    var mestre = null;
    var tocando = false;
    var volume = 0.18;
    var arquivoUrl = "";
    var elemento = null;   // <audio> quando há arquivo
    var fonteArquivo = null;
    var timerAcordes = null;

    // Progressão lenta e "aberta", que não cansa em duas horas nem briga com a
    // voz: I – vi – IV – V em Dó, uma oitava abaixo do canto.
    var ACORDES = [
        [130.81, 164.81, 196.00],   // Dó
        [110.00, 130.81, 164.81],   // Lá menor
        [87.31, 130.81, 174.61],    // Fá
        [98.00, 123.47, 146.83]     // Sol
    ];
    var passo = 0;

    function garantirContexto() {
        if (ctx) return true;
        var AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) return false;
        ctx = new AC();
        mestre = ctx.createGain();
        mestre.gain.value = 0;
        mestre.connect(ctx.destination);
        return true;
    }

    /* Um acorde em pad: entra devagar, segura, sai devagar. O ataque lento é o
       que faz soar como fundo e não como alguém tocando teclado. */
    function acorde(freqs, duracao) {
        var t = ctx.currentTime;
        freqs.forEach(function (f, i) {
            var osc = ctx.createOscillator();
            var g = ctx.createGain();
            var filtro = ctx.createBiquadFilter();

            osc.type = i === 0 ? "sine" : "triangle";
            osc.frequency.setValueAtTime(f, t);
            // Desafina um fio: duas ondas idênticas soam eletrônicas.
            osc.detune.setValueAtTime((i - 1) * 4, t);

            filtro.type = "lowpass";
            filtro.frequency.setValueAtTime(900, t);

            g.gain.setValueAtTime(0.0001, t);
            g.gain.exponentialRampToValueAtTime(0.22 / freqs.length, t + duracao * 0.35);
            g.gain.exponentialRampToValueAtTime(0.0001, t + duracao);

            osc.connect(filtro);
            filtro.connect(g);
            g.connect(mestre);
            osc.start(t);
            osc.stop(t + duracao + 0.1);
        });
    }

    function tocarSintetizada() {
        if (!tocando || arquivoUrl) return;
        acorde(ACORDES[passo % ACORDES.length], 4.2);
        passo++;
    }

    function aplicarVolume() {
        if (mestre && ctx) {
            // Rampa curta: volume que pula em degrau é desagradável.
            mestre.gain.cancelScheduledValues(ctx.currentTime);
            mestre.gain.linearRampToValueAtTime(
                tocando ? volume : 0, ctx.currentTime + 0.4
            );
        }
        if (elemento) elemento.volume = tocando ? Math.min(1, volume) : 0;
    }

    return {
        /* Chamado junto do "ativar som" — precisa de gesto da pessoa. */
        preparar: function (url, elementoAudio) {
            arquivoUrl = url || "";
            elemento = elementoAudio || null;
            if (!garantirContexto()) return false;
            if (ctx.state === "suspended") ctx.resume();

            if (arquivoUrl && elemento) {
                elemento.src = arquivoUrl;
                elemento.loop = true;
                elemento.volume = 0;
            }
            return true;
        },

        ligar: function () {
            if (!ctx && !elemento) return;
            tocando = true;
            if (ctx && ctx.state === "suspended") ctx.resume();

            if (arquivoUrl && elemento) {
                var p = elemento.play();
                if (p && p.catch) p.catch(function () { /* sem gesto ainda */ });
            } else if (!timerAcordes) {
                tocarSintetizada();
                timerAcordes = setInterval(tocarSintetizada, 4000);
            }
            aplicarVolume();
        },

        desligar: function () {
            tocando = false;
            aplicarVolume();
            if (timerAcordes) { clearInterval(timerAcordes); timerAcordes = null; }
            // O <audio> só pausa depois do fade, senão corta seco.
            if (elemento) setTimeout(function () { if (!tocando) elemento.pause(); }, 450);
        },

        volume: function (pct) {
            volume = Math.max(0, Math.min(100, Number(pct) || 0)) / 100;
            aplicarVolume();
        },

        tocando: function () { return tocando; }
    };
})();
