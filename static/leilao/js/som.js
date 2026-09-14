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
