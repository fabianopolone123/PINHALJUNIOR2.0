/*
 * caixa.js — pagamentos e entrega.
 *
 * Tela de conferência, não de pregão: nada de tempo real aqui. O caixa trabalha
 * numa fila de conferência, e uma tela que se redesenha sozinha no meio disso
 * atrapalharia mais do que ajudaria.
 *
 * Toda ação vai para o MESMO POST da equipe (`/equipe/acao/`), que decide no
 * servidor se o papel da pessoa permite. Esconder botão não protege nada.
 */
(function () {
    "use strict";

    function $(id) { return document.getElementById(id); }

    var dados = $("dadosMesa");
    if (!dados) return;

    var CSRF = dados.dataset.csrf;
    var URL_ACAO = dados.dataset.acaoUrl;

    function toast(msg, tipo) {
        if (window.mostrarToast) window.mostrarToast(msg, tipo || "info");
    }

    function acao(corpo) {
        return fetch(URL_ACAO, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": CSRF,
                "X-Requested-With": "XMLHttpRequest"
            },
            body: JSON.stringify(corpo)
        })
            .then(function (r) { return r.json().catch(function () { return {}; }); })
            .catch(function () {
                toast("Sem conexão com o servidor.", "error");
                return null;
            });
    }

    /* ---- Abas ---- */
    document.querySelectorAll(".mesa-aba").forEach(function (b) {
        b.addEventListener("click", function () {
            document.querySelectorAll(".mesa-aba").forEach(function (x) { x.classList.remove("ativa"); });
            b.classList.add("ativa");
            document.querySelectorAll(".mesa-secao").forEach(function (s) {
                s.hidden = s.dataset.secao !== b.dataset.aba;
                s.classList.toggle("ativa", !s.hidden);
            });
        });
    });

    /* ---- Ações ---- */
    document.addEventListener("click", function (e) {
        var alvo = e.target.closest("[data-acao]");
        if (!alvo) return;

        var corpo = { acao: alvo.dataset.acao, arremate: alvo.dataset.arremate };

        if (alvo.dataset.acao === "pago") {
            if (!window.confirm("Confirmar que este item foi pago?")) return;
        }

        if (alvo.dataset.acao === "combinado") {
            // O combinado é o registro do que foi falado — sem ele, daqui a uma
            // hora ninguém lembra o que a pessoa disse.
            var obs = window.prompt(
                "O que ficou combinado? (ex.: paga amanhã de manhã, vai passar no clube)",
                ""
            );
            if (obs === null) return;   // desistiu
            corpo.observacao = obs;
        }

        if (alvo.dataset.acao === "entregue") {
            if (alvo.dataset.desfazer) {
                if (!window.confirm("Desmarcar esta entrega?")) return;
                corpo.desfazer = true;
            } else {
                // A observação fica na linha do item (quem recebeu, rastreio).
                var linha = alvo.closest(".entrega");
                var campo = linha ? linha.querySelector(".entrega-obs") : null;
                if (campo) corpo.observacao = campo.value;
            }
        }

        alvo.disabled = true;
        acao(corpo).then(function (d) {
            if (!d) { alvo.disabled = false; return; }
            toast(d.msg || "Pronto.", d.ok ? "success" : "error");
            if (d.ok) window.location.reload();
            else alvo.disabled = false;
        });
    });

    /* ---- Busca (padrão do usuarios.js: sem acento, sem caixa) ---- */
    function ligarBusca(campoId, seletor) {
        var campo = $(campoId);
        if (!campo) return;
        campo.addEventListener("input", function () {
            var termo = campo.value.normalize("NFD").replace(/[̀-ͯ]/g, "")
                .toLowerCase().trim();
            document.querySelectorAll(seletor).forEach(function (li) {
                var alvo = (li.dataset.busca || "").normalize("NFD")
                    .replace(/[̀-ͯ]/g, "").toLowerCase();
                // Esconder com CLASSE, não com `hidden`: item `display:flex`
                // ignora o [hidden] do navegador (armadilha já registrada).
                li.classList.toggle("busca-oculto", termo !== "" && alvo.indexOf(termo) === -1);
            });
        });
    }

    ligarBusca("buscaPagamentos", "#listaPagamentos .arremate-linha");
})();
