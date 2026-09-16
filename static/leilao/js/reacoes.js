/*
 * reacoes.js — os emojis que sobem na tela de todo mundo.
 *
 * Duas coisas seguram este arquivo em pé num evento com 50 pessoas:
 *
 * 1. **O toque NÃO vira uma requisição.** Os toques são juntados aqui e vão em
 *    uma requisição a cada meio segundo, com a contagem. Martelar o botão 20
 *    vezes manda uma mensagem, não 20 — o pregão é que não pode perder banda.
 * 2. **O desenho tem teto.** Mais de ~30 emojis subindo ao mesmo tempo não cabe
 *    na tela e derruba celular fraco. O excedente é descartado no desenho, não
 *    enfileirado: reação atrasada não é reação.
 *
 * Quem toca vê os próprios emojis na hora (não espera a ida e volta), e o que
 * volta do servidor é o dos outros.
 *
 * **Cada toque solta uma rajada** (o servidor multiplica; a tela lê o mesmo
 * número em `data-rajada` para não desenhar duas vezes). Um emoji sozinho some
 * no meio do pregão, e o efeito existe para a sala parecer cheia — mas isso não
 * custa uma requisição a mais: o que muda é a CONTAGEM dentro do resumo que já
 * ia de meio em meio segundo.
 *
 * **O que eu mandei volta para mim.** O resumo é um broadcast: o servidor não
 * sabe (nem deve saber) quem tocou o quê. Por isso o que sai daqui fica anotado
 * como crédito e é descontado do próximo resumo — senão quem toca vê tudo em
 * dobro, que é como estava antes.
 */
window.Reacoes = (function () {
    var trilho = null;
    var enviar = null;          // callback que manda ao servidor
    var pendentes = {};         // emoji -> quantos, esperando o envio
    var timerEnvio = null;
    var vivos = 0;

    var TETO_NA_TELA = 30;
    var INTERVALO_ENVIO = 500;  // ms
    var rajada = 1;             // quantos por toque (vem do servidor)
    var credito = {};           // emoji -> {quantos, em} já desenhado aqui

    // Crédito velho é crédito perdido: se a requisição não chegou (rede ruim), o
    // resumo nunca virá com aquele emoji, e um crédito pendurado comeria os
    // emojis DOS OUTROS pela noite inteira.
    var VALIDADE_CREDITO = 4000;  // ms

    function reduzido() {
        return window.matchMedia &&
            window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    /* Solta UM emoji subindo. Cada um sai de um ponto e com uma curva
       diferente, senão viram uma fileira marchando. */
    function soltar(emoji) {
        if (!trilho || vivos >= TETO_NA_TELA || reduzido()) return;
        vivos++;

        var el = document.createElement("span");
        el.className = "reacao-flutua";
        el.textContent = emoji;

        // Ponto de partida e desvio, em variáveis CSS (a animação é do CSS).
        el.style.setProperty("--saida", (Math.random() * 70 - 35).toFixed(1) + "px");
        el.style.setProperty("--desvio", (Math.random() * 90 - 45).toFixed(1) + "px");
        el.style.setProperty("--giro", (Math.random() * 50 - 25).toFixed(1) + "deg");
        el.style.setProperty("--escala", (0.8 + Math.random() * 0.6).toFixed(2));
        el.style.animationDuration = (2.4 + Math.random() * 1.4).toFixed(2) + "s";

        trilho.appendChild(el);
        el.addEventListener("animationend", function () {
            el.remove();
            vivos--;
        });
    }

    /* Vários de uma vez (o que vem do servidor): espalha no tempo em vez de
       despejar tudo no mesmo quadro, que é o que faz parecer natural. */
    function soltarVarios(emoji, quantos) {
        var total = Math.min(quantos, TETO_NA_TELA);
        for (var i = 0; i < total; i++) {
            setTimeout(function () { soltar(emoji); }, i * 90);
        }
    }

    function despachar() {
        timerEnvio = null;
        var lote = pendentes;
        pendentes = {};
        if (!enviar) return;
        Object.keys(lote).forEach(function (emoji) {
            enviar(emoji, lote[emoji]);
        });
    }

    /* Quanto deste emoji EU já desenhei e ainda não vi voltar. */
    function descontar(emoji, quantos) {
        var c = credito[emoji];
        if (!c) return quantos;
        if (Date.now() - c.em > VALIDADE_CREDITO) {
            delete credito[emoji];
            return quantos;
        }
        var usado = Math.min(c.quantos, quantos);
        c.quantos -= usado;
        if (c.quantos <= 0) delete credito[emoji];
        return quantos - usado;
    }

    return {
        ligar: function (elementoTrilho, aoEnviar, porToque) {
            trilho = elementoTrilho;
            enviar = aoEnviar;
            rajada = Math.max(1, Math.min(parseInt(porToque, 10) || 1, 10));
        },

        /* Alguém daqui tocou: mostra a rajada na hora e junta para mandar. */
        tocar: function (emoji) {
            soltarVarios(emoji, rajada);
            var c = credito[emoji];
            if (c && Date.now() - c.em <= VALIDADE_CREDITO) {
                c.quantos += rajada;
                c.em = Date.now();
            } else {
                credito[emoji] = { quantos: rajada, em: Date.now() };
            }
            pendentes[emoji] = (pendentes[emoji] || 0) + 1;
            if (!timerEnvio) timerEnvio = setTimeout(despachar, INTERVALO_ENVIO);
        },

        /* Chegou o resumo do servidor (o que TODO MUNDO mandou, inclusive eu). */
        receber: function (resumo) {
            Object.keys(resumo || {}).forEach(function (emoji) {
                var quantos = descontar(emoji, resumo[emoji]);
                if (quantos > 0) soltarVarios(emoji, quantos);
            });
        }
    };
})();
