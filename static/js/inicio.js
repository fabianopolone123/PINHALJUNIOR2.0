/* =========================================================
   Área interna "Meus Dados"
   - Menu recolhível no celular (abre/fecha a barra lateral).
   Os detalhes de cada aventureiro usam <details>/<summary> nativos,
   por isso não precisam de JS para abrir/fechar.
   ========================================================= */
(function () {
    "use strict";

    var barra = document.getElementById("barraLateral");
    var botao = document.getElementById("botaoMenu");
    var overlay = document.getElementById("overlay");
    if (!barra || !botao || !overlay) return;

    function abrirMenu() {
        barra.classList.add("aberta");
        overlay.hidden = false;
        botao.setAttribute("aria-expanded", "true");
    }

    function fecharMenu() {
        barra.classList.remove("aberta");
        overlay.hidden = true;
        botao.setAttribute("aria-expanded", "false");
    }

    botao.addEventListener("click", function () {
        if (barra.classList.contains("aberta")) {
            fecharMenu();
        } else {
            abrirMenu();
        }
    });

    overlay.addEventListener("click", fecharMenu);
})();
