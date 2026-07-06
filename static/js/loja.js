/* =========================================================
   Tela "Loja" (Diretor): alternância de abas (Gerenciar / Loja),
   confirmação de ações destrutivas e atalho para o carrinho.
   JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    var abas = document.querySelectorAll(".loja-aba");
    var paineis = document.querySelectorAll(".loja-painel");

    function ativar(nome) {
        Array.prototype.forEach.call(abas, function (a) {
            a.classList.toggle("ativa", a.dataset.aba === nome);
        });
        Array.prototype.forEach.call(paineis, function (p) {
            p.hidden = p.dataset.painel !== nome;
        });
        try {
            var url = new URL(window.location.href);
            url.searchParams.set("aba", nome);
            window.history.replaceState({}, "", url);
        } catch (e) { /* ignora */ }
    }

    Array.prototype.forEach.call(abas, function (a) {
        a.addEventListener("click", function () { ativar(a.dataset.aba); });
    });

    // Links que apontam para o carrinho trocam para a aba "Loja".
    Array.prototype.forEach.call(
        document.querySelectorAll('a[href="#carrinho"]'),
        function (link) {
            link.addEventListener("click", function () {
                ativar("loja");
            });
        }
    );

    // Se a página abriu com âncora do carrinho, garante a aba certa.
    if (window.location.hash === "#carrinho") {
        ativar("loja");
        var alvo = document.getElementById("carrinho");
        if (alvo) setTimeout(function () { alvo.scrollIntoView({ behavior: "smooth" }); }, 60);
    }
})();

/* Confirmação de ações destrutivas: <form data-confirmar="..."> */
(function () {
    "use strict";
    document.addEventListener("submit", function (e) {
        var form = e.target;
        if (form && form.dataset && form.dataset.confirmar) {
            if (!window.confirm(form.dataset.confirmar)) e.preventDefault();
        }
    });
})();
