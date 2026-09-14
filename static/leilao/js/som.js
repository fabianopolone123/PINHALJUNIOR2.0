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
 * Música de fundo — instrumental, animada "mas nem tanto".
 *
 * Duas fontes possíveis:
 *  1. Um ARQUIVO que o clube subiu (Preparação → Configuração). Toca em laço.
 *  2. Sem arquivo, uma peça SINTETIZADA aqui mesmo. Zero download, zero arquivo
 *     no repositório e nenhuma questão de direito autoral — que é o motivo de
 *     ela existir.
 *
 * A peça tem três camadas, e o equilíbrio entre elas é o ponto:
 *  - **baixo** nos tempos 1 e 3 → dá o passo, é o que faz soar "animado";
 *  - **arpejo** em colcheias → dá movimento sem ocupar espaço;
 *  - **pad** sustentado bem baixo → cola tudo e tira o ar de caixinha.
 * Nada de melodia: melodia disputa com a voz de quem está narrando, e aqui a
 * voz é que manda.
 *
 * O agendamento é por LOOKAHEAD (agenda ~120 ms à frente, a cada 25 ms). Com
 * `setInterval` disparando nota a nota, o ritmo balança — o relógio do
 * navegador não é preciso, o relógio do WebAudio é.
 */
window.MusicaLeilao = (function () {
    var ctx = null;
    var mestre = null;
    var tocando = false;
    var volume = 0.18;
    var arquivoUrl = "";
    var elemento = null;      // <audio> quando há arquivo
    var relogio = null;       // timer do agendador
    var proximoTempo = 0;     // quando cai a próxima semínima (relógio do áudio)
    var passo = 0;

    var BPM = 104;            // animado, mas sem virar corrida
    var SEMINIMA = 60 / BPM;
    var LOOKAHEAD_MS = 25;
    var HORIZONTE = 0.12;     // segundos agendados à frente

    // Dó maior: I – V – vi – IV. É a progressão mais alegre que existe e não
    // cansa — a mesma de metade das músicas de festa.
    var HARMONIA = [
        { baixo: 65.41,  notas: [261.63, 329.63, 392.00] },  // Dó
        { baixo: 49.00,  notas: [246.94, 293.66, 392.00] },  // Sol
        { baixo: 55.00,  notas: [261.63, 329.63, 440.00] },  // Lá menor
        { baixo: 43.65,  notas: [261.63, 349.23, 440.00] }   // Fá
    ];

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

    /* Uma nota com envelope. `ataque` curto = percussivo; longo = pad. */
    function nota(freq, inicio, duracao, ganho, tipo, ataque, corte) {
        var osc = ctx.createOscillator();
        var g = ctx.createGain();
        var filtro = ctx.createBiquadFilter();

        osc.type = tipo;
        osc.frequency.setValueAtTime(freq, inicio);

        filtro.type = "lowpass";
        filtro.frequency.setValueAtTime(corte || 2200, inicio);

        g.gain.setValueAtTime(0.0001, inicio);
        g.gain.exponentialRampToValueAtTime(ganho, inicio + (ataque || 0.01));
        g.gain.exponentialRampToValueAtTime(0.0001, inicio + duracao);

        osc.connect(filtro);
        filtro.connect(g);
        g.connect(mestre);
        osc.start(inicio);
        osc.stop(inicio + duracao + 0.05);
    }

    /* Agenda UM tempo (semínima) da peça. */
    function agendarTempo(n, quando) {
        var compasso = Math.floor(n / 4) % HARMONIA.length;
        var tempo = n % 4;
        var acorde = HARMONIA[compasso];

        // Baixo nos tempos 1 e 3 — o passo da música.
        if (tempo === 0 || tempo === 2) {
            nota(acorde.baixo, quando, 0.42, 0.30, "triangle", 0.012, 700);
        }

        // Pad: entra no começo do compasso e segura o compasso inteiro.
        if (tempo === 0) {
            acorde.notas.forEach(function (f) {
                nota(f / 2, quando, SEMINIMA * 4, 0.045, "sine", 0.5, 1200);
            });
        }

        // Arpejo em colcheias: duas por tempo, subindo e descendo.
        var ordem = [0, 1, 2, 1];
        for (var i = 0; i < 2; i++) {
            var f = acorde.notas[ordem[(tempo * 2 + i) % ordem.length]];
            // A segunda colcheia é mais fraca: dá suingue em vez de metrônomo.
            var g = i === 0 ? 0.085 : 0.055;
            nota(f * 2, quando + i * (SEMINIMA / 2), 0.20, g, "triangle", 0.008, 3000);
        }
    }

    function agendador() {
        if (!tocando || arquivoUrl) return;
        while (proximoTempo < ctx.currentTime + HORIZONTE) {
            agendarTempo(passo, proximoTempo);
            proximoTempo += SEMINIMA;
            passo++;
        }
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
        /* Chamado junto do "ligar som" — precisa de gesto da pessoa. */
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
            if (tocando) return;
            tocando = true;
            if (ctx && ctx.state === "suspended") ctx.resume();

            if (arquivoUrl && elemento) {
                var p = elemento.play();
                if (p && p.catch) p.catch(function () { /* sem gesto ainda */ });
            } else if (!relogio) {
                // Um respiro antes do primeiro tempo: agendar no instante exato
                // costuma estourar o começo da primeira nota.
                proximoTempo = ctx.currentTime + 0.1;
                agendador();
                relogio = setInterval(agendador, LOOKAHEAD_MS);
            }
            aplicarVolume();
        },

        desligar: function () {
            if (!tocando) return;
            tocando = false;
            aplicarVolume();
            // Para o agendador só DEPOIS do fade, senão a música corta seca.
            setTimeout(function () {
                if (tocando) return;
                if (relogio) { clearInterval(relogio); relogio = null; }
                if (elemento) elemento.pause();
            }, 500);
        },

        volume: function (pct) {
            volume = Math.max(0, Math.min(100, Number(pct) || 0)) / 100;
            aplicarVolume();
        },

        tocando: function () { return tocando; }
    };
})();
