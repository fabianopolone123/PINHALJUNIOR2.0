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
   Notificações (toasts): padrão ÚNICO do sistema. Fecham ao clicar e
   somem sozinhas depois de ~4,5s (mesmo tempo da barrinha de progresso).
   Expõe window.mostrarToast(texto, tipo) para criar toast pelo JS
   (ex.: "copiado!"). Seguro em qualquer página (cria o contêiner se faltar).
   ========================================================= */
(function () {
    "use strict";

    var DURACAO = 4500;  // casa com a animação `toast-barra` (4.5s) em inicio.css

    // Garante o contêiner .mensagens no <body> — fora de qualquer ancestral com
    // transform/animação (ex.: .conteudo-interno), que quebraria o position: fixed.
    function garantirContainer() {
        var c = document.querySelector(".mensagens");
        if (!c) {
            c = document.createElement("div");
            c.className = "mensagens";
            document.body.appendChild(c);
        } else if (c.parentNode !== document.body) {
            document.body.appendChild(c);
        }
        return c;
    }

    function fechar(t) {
        if (t.classList.contains("saindo")) return;
        t.classList.add("saindo");
        setTimeout(function () {
            if (t.parentNode) t.parentNode.removeChild(t);
        }, 400);
    }

    function agendar(t, atraso) {
        t.addEventListener("click", function () { fechar(t); });
        setTimeout(function () { fechar(t); }, atraso);
    }

    // Toasts vindos do servidor (framework de messages do Django).
    var container = document.querySelector(".mensagens");
    if (container) {
        if (container.parentNode !== document.body) {
            document.body.appendChild(container);
        }
        Array.prototype.slice.call(container.querySelectorAll(".mensagem"))
            .forEach(function (t, i) { agendar(t, DURACAO + i * 400); });
    }

    // Cria um toast pelo JS (mesmo visual/tempo dos toasts do servidor).
    window.mostrarToast = function (texto, tipo) {
        var c = garantirContainer();
        var t = document.createElement("div");
        t.className = "mensagem mensagem-" + (tipo || "info");
        t.setAttribute("role", "status");
        t.textContent = texto;
        c.appendChild(t);
        agendar(t, DURACAO);
        return t;
    };
})();
