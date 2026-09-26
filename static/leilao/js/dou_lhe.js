/*
 * dou_lhe.js — o "dou-lhe uma / dou-lhe duas" na tela de quem está disputando.
 *
 * Ligado nas DUAS telas do pregão (a show e a clássica). Não fala com o
 * servidor: escuta o aviso `leilao:dou_lhe` que o motor (`leilao.js`) emite
 * quando o locutor aperta o botão na mesa, e desenha:
 *
 *   - "uma": o carimbo DOU-LHE UMA! por cima da foto e um brilho dourado nas
 *     bordas da tela, uma vez;
 *   - "duas": o carimbo maior, vermelho, a tela treme, as bordas ficam
 *     PULSANDO como batimento e o botão de lance pulsa junto — e fica assim
 *     até acontecer alguma coisa: lance novo, item novo ou martelo.
 *
 * A intensidade cresce de propósito: é a sala ouvindo o locutor levantar o
 * martelo. Mas o limite é o mesmo da tela show (REGRAS_CODEX): anúncio
 * verdadeiro do locutor, nunca pressão inventada — não há contagem, e o texto
 * diz o que é ("ainda dá para dar lance"), não "última chance".
 *
 * Nada aqui pega toque: o carimbo mora dentro da foto e a vinheta é
 * `pointer-events: none`. Carrega ANTES do motor, como os efeitos da show.
 */
(function () {
    "use strict";

    function $(id) { return document.getElementById(id); }

    var corpo = document.body;
    var reduzido = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    var vinheta = null;
    var loteMarcado = null;
    var relogioCarimbo = null;

    function garantirVinheta() {
        if (vinheta) return vinheta;
        vinheta = document.createElement("div");
        vinheta.className = "dou-lhe-vinheta";
        vinheta.setAttribute("aria-hidden", "true");
        corpo.appendChild(vinheta);
        return vinheta;
    }

    function reanimar(el, classe) {
        if (!el) return;
        el.classList.remove(classe);
        void el.offsetWidth;
        el.classList.add(classe);
    }

    function limpar() {
        loteMarcado = null;
        corpo.classList.remove("dou-lhe-1", "dou-lhe-2");
        var c = $("douLhe");
        if (c) { c.classList.remove("bate"); c.hidden = true; }
        clearTimeout(relogioCarimbo);
    }

    function carimbo(vez, sub) {
        var c = $("douLhe");
        if (!c) return;
        var titulo = c.querySelector(".dou-lhe-titulo");
        var linha = c.querySelector(".dou-lhe-sub");
        if (titulo) titulo.textContent = vez === 2 ? "DOU-LHE DUAS!" : "DOU-LHE UMA!";
        if (linha) linha.textContent = sub || "";
        c.className = "dou-lhe-carimbo vez-" + vez;
        c.hidden = false;
        reanimar(c, "bate");
        clearTimeout(relogioCarimbo);
        // O "uma" sai de cena; o "duas" fica no canto da foto até o próximo
        // acontecimento — é o estado em que o pregão está.
        if (vez === 1) {
            relogioCarimbo = setTimeout(function () { c.hidden = true; }, 2600);
        }
    }

    document.addEventListener("leilao:dou_lhe", function (e) {
        try {
            var d = e.detail || {};
            var vez = d.vez === 2 ? 2 : 1;
            loteMarcado = d.lote;
            corpo.classList.remove("dou-lhe-1", "dou-lhe-2");
            corpo.classList.add("dou-lhe-" + vez);

            var sub = d.euGanhando
                ? "Você está ganhando!"
                : (vez === 2 ? "Ainda dá para dar lance" : "");
            carimbo(vez, sub);

            var v = garantirVinheta();
            v.classList.remove("uma", "duas");
            void v.offsetWidth;
            v.classList.add(vez === 2 ? "duas" : "uma");

            // As DUAS classes saem antes: a do "duas" ficava presa no body, e
            // como a regra dela vem depois no CSS, o "uma" seguinte tremia
            // forte (ou nem tremia, porque a animação não reiniciava).
            corpo.classList.remove("treme", "treme-forte");
            if (!reduzido) reanimar(corpo, vez === 2 ? "treme-forte" : "treme");
        } catch (erro) { /* enfeite nunca derruba a tela */ }
    });

    // Qualquer acontecimento no pregão encerra o "dou-lhe": o lance novo
    // recomeça o martelo, e item novo ou martelo batido mudam de assunto.
    ["leilao:lance", "leilao:lote_aberto", "leilao:vendido"].forEach(function (nome) {
        document.addEventListener(nome, limpar);
    });
    document.addEventListener("leilao:estado", function (e) {
        var est = (e.detail || {}).estado;
        var lote = est && est.ativo ? est.lote : null;
        if (loteMarcado !== null && (!lote || lote.id !== loteMarcado)) limpar();
    });
})();
