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

    /* ---------------------------------------------------------------
       Ruído — a matéria-prima de palma, gaveta e torcida
       ---------------------------------------------------------------
       Um buffer só, criado na primeira vez e reaproveitado por todos os
       disparos: gerar dois segundos de ruído a cada palma seria trabalho de
       CPU no meio do pregão, e é justamente a hora em que ela falta. */
    let bufferRuido = null;

    function ruido() {
        if (!ctx) return null;
        if (!bufferRuido) {
            const n = Math.floor(ctx.sampleRate * 2);
            bufferRuido = ctx.createBuffer(1, n, ctx.sampleRate);
            const dados = bufferRuido.getChannelData(0);
            for (let i = 0; i < n; i++) dados[i] = Math.random() * 2 - 1;
        }
        return bufferRuido;
    }

    /* Um trecho de ruído filtrado, com envelope. É com isto que se faz palma
       (banda alta, estalo curto), gaveta (banda baixa, batida) e torcida
       (banda média, longa). */
    function sopro(opcoes) {
        if (!ctx) return;
        const buf = ruido();
        if (!buf) return;
        const t = ctx.currentTime + (opcoes.inicio || 0);
        const dur = opcoes.duracao;

        const fonte = ctx.createBufferSource();
        fonte.buffer = buf;
        // Começa num ponto aleatório: duas palmas seguidas lendo o mesmo
        // pedaço de ruído soam idênticas, e o ouvido percebe a repetição.
        fonte.loop = true;
        fonte.loopStart = 0;
        fonte.loopEnd = buf.duration;

        const filtro = ctx.createBiquadFilter();
        filtro.type = opcoes.tipo || "bandpass";
        filtro.frequency.setValueAtTime(opcoes.freq, t);
        if (opcoes.freqFim) {
            filtro.frequency.exponentialRampToValueAtTime(opcoes.freqFim, t + dur);
        }
        filtro.Q.value = opcoes.q || 1;

        const g = ctx.createGain();
        const ataque = opcoes.ataque || 0.002;
        g.gain.setValueAtTime(0.0001, t);
        g.gain.exponentialRampToValueAtTime(opcoes.volume, t + ataque);
        g.gain.exponentialRampToValueAtTime(0.0001, t + dur);

        fonte.connect(filtro);
        filtro.connect(g);
        g.connect(mestre);
        fonte.start(t, Math.random() * (buf.duration - dur - 0.05));
        fonte.stop(t + dur + 0.02);
    }

    /* Uma palma: estalo curto de banda alta. O que a faz soar como mão, e não
       como chiado, é a duração — poucos centésimos — e o ataque instantâneo. */
    function palma(inicio, volume) {
        sopro({
            inicio: inicio,
            duracao: 0.03 + Math.random() * 0.04,
            freq: 1100 + Math.random() * 1600,
            q: 0.8,
            volume: volume,
            ataque: 0.001,
        });
    }

    /* Uma PLATEIA batendo palmas: muitas mãos, nenhuma no mesmo instante.
       A densidade começa alta e vai rareando, que é como aplauso de verdade
       termina — se todas as palmas fossem espalhadas por igual, soaria como
       chuva. */
    function palmas(inicio, duracao, quantas) {
        for (let i = 0; i < quantas; i++) {
            // `i²` concentra as palmas no começo.
            const p = Math.pow(i / quantas, 1.7);
            const quando = inicio + p * duracao + Math.random() * 0.05;
            palma(quando, 0.05 + Math.random() * 0.07);
        }
    }

    /* A torcida: ruído de banda média com a frequência subindo e caindo, que é
       o contorno de um "uhuuul" coletivo. Não é uma voz — é o conjunto. */
    function torcida(inicio, duracao, volume) {
        sopro({
            inicio: inicio,
            duracao: duracao,
            freq: 520,
            freqFim: 1150,
            q: 0.9,
            volume: volume,
            ataque: 0.12,
        });
        sopro({
            inicio: inicio + duracao * 0.45,
            duracao: duracao * 0.7,
            freq: 1250,
            freqFim: 640,
            q: 0.8,
            volume: volume * 0.8,
            ataque: 0.1,
        });
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

        /* Lance novo: CAIXA REGISTRADORA — pedido do clube, e o som certo:
           lance é dinheiro entrando.

           Três peças, nesta ordem: o estalo do mecanismo, o sino (duas
           parciais desafinadas entre si, que é o que soa metálico em vez de
           musical) e a gaveta abrindo, grave e curta.

           Fica em ~0,35 s de propósito: ele toca a CADA lance, e numa disputa
           quente são vários por minuto. Som comprido aqui viraria zoeira na
           terceira vez. */
        lance: function () {
            tocar(function () {
                sopro({ inicio: 0, duracao: 0.035, freq: 3600, q: 0.7, volume: 0.1 });
                nota(1760, 0.015, 0.3, 0.2, "triangle");
                nota(2489, 0.03, 0.26, 0.14, "triangle");
                sopro({ inicio: 0.12, duracao: 0.1, freq: 190, freqFim: 90,
                        tipo: "lowpass", q: 0.6, volume: 0.18 });
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

        /* Martelo: a SALA COMEMORA — palmas e gritaria, pedido do clube.

           É sintetizado como todo o resto (nada de arquivo no repositório): a
           palma é um estalo curto de ruído filtrado, e são dezenas delas em
           instantes diferentes; a torcida é ruído de banda média com a
           frequência subindo e caindo, que é o contorno de um "uhuul"
           coletivo.

           Aqui pode ser longo e caro — acontece UMA vez por item, ao contrário
           do lance. O martelo é o momento do leilão; é o único em que vale
           gastar. */
        vendido: function () {
            tocar(function () {
                nota(523.25, 0, 0.14, 0.26, "triangle");
                nota(783.99, 0.09, 0.3, 0.28, "triangle");
                torcida(0.05, 1.3, 0.09);
                palmas(0.08, 1.5, 38);
            });
        },

        /* Fui EU que arrematei: a mesma comemoração, mais cheia e com a
           fanfarra por cima — é a hora da pessoa. */
        arrematei: function () {
            tocar(function () {
                nota(523.25, 0, 0.14, 0.3, "triangle");
                nota(659.25, 0.09, 0.14, 0.3, "triangle");
                nota(783.99, 0.18, 0.14, 0.3, "triangle");
                nota(1046.5, 0.27, 0.5, 0.36, "triangle");
                torcida(0.05, 1.7, 0.12);
                palmas(0.1, 1.9, 52);
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
