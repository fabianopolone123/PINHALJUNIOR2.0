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

/* =========================================================
   Painéis expansíveis (<details>) de "Meus Dados":
   - clicar fora fecha os painéis abertos;
   - abrir um painel recolhe os outros que não contêm o clique
     (comportamento de accordion, evita tela poluída);
   - clicar dentro NÃO fecha;
   - tecla Esc fecha tudo.
   ========================================================= */
(function () {
    "use strict";

    var container = document.querySelector(".conteudo-interno");
    if (!container) return;

    function detalhesAbertos() {
        return Array.prototype.slice.call(
            container.querySelectorAll("details[open]")
        );
    }

    // Fecha todo painel aberto que NÃO contém o elemento clicado.
    document.addEventListener("click", function (evento) {
        detalhesAbertos().forEach(function (d) {
            if (!d.contains(evento.target)) {
                d.open = false;
            }
        });
    });

    // Esc recolhe todos os painéis abertos.
    document.addEventListener("keydown", function (evento) {
        if (evento.key === "Escape") {
            detalhesAbertos().forEach(function (d) {
                d.open = false;
            });
        }
    });
})();

/* =========================================================
   Notificações (toasts): fecham ao clicar e somem sozinhas
   depois de alguns segundos.
   ========================================================= */
(function () {
    "use strict";
    var container = document.querySelector(".mensagens");
    if (!container) return;
    // Move o balão para o <body> para ele aparecer no canto da TELA — fora de
    // qualquer ancestral com transform/animação (ex.: .conteudo-interno), que
    // quebraria o position: fixed e prenderia o toast dentro da região.
    if (container.parentNode !== document.body) {
        document.body.appendChild(container);
    }

    var toasts = Array.prototype.slice.call(container.querySelectorAll(".mensagem"));
    if (!toasts.length) return;

    function fechar(t) {
        if (t.classList.contains("saindo")) return;
        t.classList.add("saindo");
        setTimeout(function () {
            if (t.parentNode) t.parentNode.removeChild(t);
        }, 400);
    }

    toasts.forEach(function (t, i) {
        t.addEventListener("click", function () { fechar(t); });
        setTimeout(function () { fechar(t); }, 4500 + i * 400);
    });
})();
