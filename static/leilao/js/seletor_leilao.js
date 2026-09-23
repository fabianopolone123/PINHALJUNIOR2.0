/*
 * seletor_leilao.js — trocar de leilão nas telas da equipe.
 *
 * Cada opção carrega o ENDEREÇO no `value` (o servidor montou com `{% url %}`),
 * então trocar de leilão é navegar — e não um estado guardado em lugar nenhum.
 * É o que mantém a regra do projeto de pé: **a tela de equipe trabalha sobre o
 * leilão que está na URL**, e a URL continua colável e compartilhável com quem
 * está do outro lado da mesa.
 *
 * O botão "Ir" ao lado não é enfeite: sem JS, o `change` não navega, e ele é o
 * que faz o seletor continuar funcionando.
 */
(function () {
    "use strict";

    document.querySelectorAll("[data-seletor-leilao]").forEach(function (form) {
        var select = form.querySelector("[data-ir]");
        var botao = form.querySelector("[data-ir-botao]");
        if (!select) return;

        function ir() {
            var destino = select.value;
            if (destino && destino !== window.location.pathname) {
                window.location.href = destino;
            }
        }

        select.addEventListener("change", ir);
        if (botao) botao.addEventListener("click", ir);

        // Com JS o botão é redundante — some para não ocupar espaço numa barra
        // que já é estreita no celular.
        if (botao) botao.hidden = true;
    });
})();
