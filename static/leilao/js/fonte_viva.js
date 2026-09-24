/*
 * fonte_viva.js — a conexão ao vivo (SSE) que NÃO desiste.
 *
 * O `EventSource` reconecta sozinho quando a conexão cai no meio — mas, pela
 * especificação, **desiste de vez** se a tentativa de reconexão receber uma
 * resposta que não seja 200 `text/event-stream`: o 502 do Nginx enquanto o
 * serviço do leilão reinicia (todo deploy), o 503 de "lotado", uma página de
 * erro do proxy. Aí `readyState` vira 2 (fechado) e nada mais acontece.
 *
 * No leilão isso era a tela CONGELADA: valor, líder e item parados, sem aviso.
 * E a tela fica acesa de propósito (`tela_acesa.js`), então nem o "voltou para
 * a aba" que religava a conexão acontecia — podia durar a noite inteira.
 *
 * Este módulo embrulha o `EventSource`:
 *   - quando ele fecha de vez, abre outro, com espera CRESCENTE e SORTEADA
 *     (100 celulares percebem a mesma queda no mesmo instante; espera fixa os
 *     faria voltar todos juntos, no segundo em que o serviço acabou de subir —
 *     a mesma lição do áudio, em `audio_ouvir.js`);
 *   - os ouvintes registrados são religados na conexão nova, então quem usa
 *     escreve `fonte.addEventListener(...)` uma vez só, como antes;
 *   - o servidor manda o estado INTEIRO ao conectar, então reconectar é
 *     suficiente para a tela voltar certa (não há replay a fazer).
 *
 * Uso: `var fonte = window.FonteViva.abrir(url, { aoCair: fn, aoVoltar: fn })`.
 */
window.FonteViva = (function () {
    "use strict";

    var ESPERA_INICIAL = 2000;   // ms
    var ESPERA_MAXIMA = 30000;   // ms

    function abrir(url, opcoes) {
        opcoes = opcoes || {};
        var ouvintes = [];        // [nome, fn]
        var es = null;
        var tentativas = 0;
        var relogio = null;
        var fechadoDeProposito = false;

        function espera() {
            var base = Math.min(ESPERA_MAXIMA, ESPERA_INICIAL * Math.pow(2, tentativas));
            // ±40%: espalha a volta de quem caiu junto.
            return Math.round(base * (0.6 + Math.random() * 0.8));
        }

        function agendar() {
            if (relogio || fechadoDeProposito) return;
            var ms = espera();
            tentativas++;
            relogio = setTimeout(function () {
                relogio = null;
                conectar();
            }, ms);
        }

        function conectar() {
            if (es) { try { es.close(); } catch (e) { /* já fechado */ } }
            es = new EventSource(url);
            ouvintes.forEach(function (o) { es.addEventListener(o[0], o[1]); });
            es.addEventListener("open", function () {
                tentativas = 0;
                if (opcoes.aoVoltar) opcoes.aoVoltar();
            });
            es.onerror = function () {
                if (opcoes.aoCair) opcoes.aoCair();
                // 0 = conectando: o próprio EventSource está tentando de novo.
                // 2 = fechado: ele DESISTIU — quem traz de volta somos nós.
                if (es && es.readyState === 2) agendar();
            };
        }

        conectar();

        return {
            addEventListener: function (nome, fn) {
                ouvintes.push([nome, fn]);
                if (es) es.addEventListener(nome, fn);
            },
            /* Reabre JÁ (a aba voltou para a frente, a rede voltou). */
            reabrir: function () {
                if (relogio) { clearTimeout(relogio); relogio = null; }
                fechadoDeProposito = false;
                conectar();
            },
            fechada: function () { return !es || es.readyState === 2; },
            close: function () {
                fechadoDeProposito = true;
                if (relogio) { clearTimeout(relogio); relogio = null; }
                if (es) es.close();
            }
        };
    }

    return { abrir: abrir };
})();
