/*
 * modal.js — as janelas suspensas do leilão, num lugar só.
 *
 * O desenho (o `.modal-overlay`, o X, o fundo escuro) já vem do `base.css` do
 * sistema. O que se repetia de arquivo em arquivo era o COMPORTAMENTO — abrir,
 * travar o scroll, fechar no X, no fundo e no Esc —, e com ele a regra que o
 * projeto exige e que é fácil esquecer ao escrever de novo:
 *
 *   **fecha no fundo só quando o `mousedown` E o `click` aconteceram no
 *   próprio fundo.**
 *
 * Sem isso, quem começa a arrastar para SELECIONAR um texto de dentro do modal
 * e solta o mouse fora dele vê a janela fechar na cara — perdendo o que estava
 * lendo ou digitando. É por isso que não basta ouvir o `click`.
 */
window.ModalLeilao = (function () {
    "use strict";

    function fechar(overlay) {
        if (!overlay || overlay.hidden) return;
        overlay.hidden = true;
        // A classe é do body, não do overlay: é ela que trava a rolagem da
        // página atrás. Só sai quando NENHUM modal está aberto — duas janelas
        // na mesma tela (o caixa tem) destravariam o scroll cedo demais.
        if (!document.querySelector(".modal-overlay:not([hidden])")) {
            document.body.classList.remove("modal-aberto");
        }
    }

    function abrir(overlay) {
        if (!overlay) return;
        overlay.hidden = false;
        document.body.classList.add("modal-aberto");
        // Foco no primeiro campo: o modal quase sempre existe para digitar
        // alguma coisa, e quem abre no celular não quer procurar o cursor.
        var campo = overlay.querySelector("input:not([type=hidden]), textarea, select");
        if (campo) {
            try { campo.focus(); } catch (e) { /* navegador antigo */ }
        }
    }

    return {
        abrir: abrir,
        fechar: fechar,

        /* Liga um overlay: X, fundo e Esc. Devolve {abrir, fechar} para quem
           precisa controlar de fora. */
        ligar: function (overlay) {
            if (!overlay) return { abrir: function () {}, fechar: function () {} };

            overlay.querySelectorAll("[data-fechar-modal]").forEach(function (b) {
                b.addEventListener("click", function () { fechar(overlay); });
            });

            var desceuNoFundo = false;
            overlay.addEventListener("mousedown", function (e) {
                desceuNoFundo = e.target === overlay;
            });
            overlay.addEventListener("click", function (e) {
                if (desceuNoFundo && e.target === overlay) fechar(overlay);
            });

            document.addEventListener("keydown", function (e) {
                if (e.key === "Escape") fechar(overlay);
            });

            return {
                abrir: function () { abrir(overlay); },
                fechar: function () { fechar(overlay); }
            };
        }
    };
})();
