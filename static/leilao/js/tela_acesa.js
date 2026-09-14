/*
 * tela_acesa.js — impede o celular de apagar a tela durante o leilão.
 *
 * O problema: quem está assistindo não TOCA em nada entre um lance e outro. Para
 * o Android/iOS isso é "aparelho parado", e o protetor de tela entra depois de
 * 30 s. A pessoa perde o item por causa do economizador de bateria.
 *
 * A solução é a mesma do YouTube: **Screen Wake Lock API**. Enquanto o bloqueio
 * está de pé, o sistema não conta o tempo ocioso.
 *
 * Três detalhes que fazem a diferença entre funcionar e parecer funcionar:
 *
 *  1. **O bloqueio CAI sozinho** toda vez que a aba sai da frente (trocar de
 *     app, atender uma ligação, bloquear o aparelho na mão). Ele não volta
 *     sozinho — por isso o `visibilitychange` aqui é obrigatório, não um
 *     capricho.
 *  2. **Só funciona em HTTPS** (contexto seguro). Em `http://` o navegador nem
 *     expõe a API. Em produção é https, e no `runserver` a ausência é normal.
 *  3. **iOS só tem isso a partir do Safari 16.4.** Para os aparelhos mais
 *     velhos existe a manha do vídeo mudo em laço: o sistema entende "está
 *     assistindo vídeo" e segura a tela. O vídeo é gerado aqui na hora por
 *     canvas — nenhum arquivo entra no repositório.
 *
 * Chame `ligar()` a partir de um GESTO da pessoa (o mesmo toque que liga o som
 * serve). Sem gesto, o fallback de vídeo não tem permissão para tocar.
 */
window.TelaAcesa = (function () {
    "use strict";

    var bloqueio = null;      // WakeLockSentinel
    var querendo = false;     // a intenção da pessoa, que sobrevive às quedas
    var video = null;         // plano B
    var avisou = false;

    function suportado() {
        return "wakeLock" in navigator && navigator.wakeLock;
    }

    function pedir() {
        if (!querendo || bloqueio || document.visibilityState !== "visible") return;
        if (!suportado()) { planoB(); return; }

        navigator.wakeLock.request("screen").then(function (b) {
            bloqueio = b;
            // O próprio navegador solta o bloqueio ao esconder a aba; sem este
            // aviso a gente acharia que ainda está de pé e nunca pediria de novo.
            b.addEventListener("release", function () { bloqueio = null; });
        }).catch(function () {
            // Bateria fraca, modo de economia, contexto não seguro: tudo cai
            // aqui. Não é erro para mostrar a ninguém — é só tentar o plano B.
            planoB();
        });
    }

    /* Plano B: vídeo mudo em laço, feito no navegador.
       Dois pixels pretos bastam — o que segura a tela é o fato de haver um
       <video> tocando, não o que ele mostra. */
    function planoB() {
        if (video || !querendo) return;
        var tela = document.createElement("canvas");
        tela.width = tela.height = 2;
        if (!tela.captureStream) return;   // navegador antigo demais; desiste quieto

        var ctx = tela.getContext("2d");
        ctx.fillRect(0, 0, 2, 2);

        video = document.createElement("video");
        video.muted = true;
        video.setAttribute("muted", "");
        video.playsInline = true;
        video.setAttribute("playsinline", "");   // sem isto o iOS abre em tela cheia
        video.loop = true;
        // Fora da tela, mas NÃO com display:none nem hidden: vídeo que o
        // navegador considera invisível é pausado, e aí não segura nada.
        video.style.cssText =
            "position:fixed;width:1px;height:1px;opacity:0.01;pointer-events:none;" +
            "left:0;bottom:0;z-index:-1";
        try {
            video.srcObject = tela.captureStream(1);   // 1 quadro por segundo
        } catch (e) {
            video = null;
            return;
        }
        document.body.appendChild(video);
        var p = video.play();
        if (p && p.catch) p.catch(function () { soltarVideo(); });
    }

    function soltarVideo() {
        if (!video) return;
        try { video.pause(); video.srcObject = null; } catch (e) { /* já foi */ }
        if (video.parentNode) video.parentNode.removeChild(video);
        video = null;
    }

    // A volta para a aba é o momento de repor o bloqueio que o sistema derrubou.
    document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "visible") pedir();
    });

    return {
        ligar: function () {
            querendo = true;
            pedir();
            if (!suportado() && !avisou) {
                avisou = true;
                return false;   // quem chamou decide se avisa a pessoa
            }
            return true;
        },

        desligar: function () {
            querendo = false;
            soltarVideo();
            if (bloqueio) {
                try { bloqueio.release(); } catch (e) { /* já soltou */ }
                bloqueio = null;
            }
        },

        ativa: function () { return !!bloqueio || !!video; },
        suportado: suportado
    };
})();
