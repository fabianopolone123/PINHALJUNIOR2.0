/*
 * entregas_quadro.js — arrastar as paradas entre os entregadores.
 *
 * O servidor divide por bairro, mas não sabe que um bairro é perto do outro:
 * ele compara NOMES de bairro, e sem mapa é tudo o que pode fazer. Quem sabe
 * que "isso aqui é tudo o mesmo lado" é a equipe — este arquivo é a mão dela.
 *
 * Três regras que este arquivo aplica:
 *
 * 1. **Cada arrastada salva na hora.** Não existe botão "salvar": a equipe está
 *    montando rota no fim de uma noite longa, e um trabalho perdido por falta de
 *    clique seria pior do que qualquer outra falha daqui.
 * 2. **O texto da rota vem do servidor** a cada movimento, como todo texto
 *    copiável do projeto. O botão de copiar nunca monta frase nenhuma — se ele
 *    montasse, a mensagem do WhatsApp e a tela poderiam discordar.
 * 3. **Se o servidor recusar, o cartão volta.** A tela não pode mostrar uma
 *    divisão que o banco não tem: é ela que vira a mensagem mandada ao
 *    voluntário.
 *
 * É tela de computador, por decisão: a interação é arrastar com o mouse.
 */
(function () {
    "use strict";

    var dados = document.getElementById("dadosQuadro");
    var quadro = document.getElementById("quadro");
    if (!dados || !quadro) return;

    var CSRF = dados.dataset.csrf;
    var URL_ACAO = dados.dataset.acaoUrl;

    function toast(msg, tipo) {
        if (window.mostrarToast) window.mostrarToast(msg, tipo || "info");
    }

    function acao(corpo) {
        // O leilão DESTA tela vai junto: sem ele o servidor adivinhava ("o que
        // está no ar") e o botão agia no leilão errado.
        if (dados.dataset.leilao && corpo.leilao === undefined) corpo.leilao = dados.dataset.leilao;
        return fetch(URL_ACAO, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": CSRF,
                "X-Requested-With": "XMLHttpRequest"
            },
            body: JSON.stringify(corpo)
        }).then(function (r) { return r.json(); });
    }

    /* ---- o que o servidor devolve depois de cada mudança ---- */
    /* Só a resposta do pedido MAIS RECENTE redesenha o resumo. Duas arrastadas
       rápidas mandam dois pedidos; se a resposta do primeiro chegasse depois,
       ela gravava o roteiro VELHO no texto que a equipe copia para o
       WhatsApp do entregador. */
    var pedidoSeq = 0;
    var ultimoAplicado = 0;
    function aplicarResumo(d, seq) {
        if (!d) return;
        if (seq !== undefined) {
            if (seq < ultimoAplicado) return;
            ultimoAplicado = seq;
        }
        var fila = quadro.querySelector('.coluna[data-entregador="0"] [data-contagem]');
        if (fila && typeof d.a_distribuir === "number") {
            fila.textContent = d.a_distribuir + " parada(s)";
        }
        (d.colunas || []).forEach(function (c) {
            var col = quadro.querySelector('.coluna[data-entregador="' + c.numero + '"]');
            if (!col) return;
            var cont = col.querySelector("[data-contagem]");
            if (cont) cont.textContent = c.paradas + " parada(s) · " + c.itens + " item(ns)";
            var reg = col.querySelector("[data-regioes]");
            if (reg) reg.textContent = (c.regioes || []).join(" · ");
            var txt = col.querySelector("[data-texto]");
            if (txt) txt.value = c.texto;
        });
    }

    /* ---- arrastar ---- */
    var arrastado = null;
    var origem = null;

    quadro.addEventListener("dragstart", function (e) {
        var parada = e.target.closest(".parada");
        if (!parada) return;
        arrastado = parada;
        origem = parada.parentElement;
        parada.classList.add("arrastando");
        // Sem dado no dataTransfer o Firefox não inicia o arrasto.
        e.dataTransfer.setData("text/plain", parada.dataset.participante || "");
        e.dataTransfer.effectAllowed = "move";
    });

    quadro.addEventListener("dragend", function () {
        if (arrastado) arrastado.classList.remove("arrastando");
        limparAlvos();
        arrastado = null;
        origem = null;
    });

    function limparAlvos() {
        Array.prototype.forEach.call(
            quadro.querySelectorAll("[data-solta].alvo"),
            function (z) { z.classList.remove("alvo"); }
        );
    }

    quadro.addEventListener("dragover", function (e) {
        var zona = e.target.closest("[data-solta]");
        if (!zona || !arrastado) return;
        // Sem o preventDefault o navegador recusa a soltura.
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
        if (!zona.classList.contains("alvo")) {
            limparAlvos();
            zona.classList.add("alvo");
        }
    });

    quadro.addEventListener("dragleave", function (e) {
        var zona = e.target.closest("[data-solta]");
        if (zona && !zona.contains(e.relatedTarget)) zona.classList.remove("alvo");
    });

    quadro.addEventListener("drop", function (e) {
        var zona = e.target.closest("[data-solta]");
        if (!zona || !arrastado) return;
        e.preventDefault();
        limparAlvos();
        if (zona === origem) return;

        var cartao = arrastado;
        var volta = origem;
        var coluna = zona.closest(".coluna");
        var numero = parseInt(coluna.dataset.entregador, 10) || 0;

        // Move na tela primeiro: quem arrasta precisa ver o cartão chegar.
        zona.appendChild(cartao);

        var seq = ++pedidoSeq;
        acao({
            acao: "entrega_mover",
            participante: cartao.dataset.participante,
            entregador: numero
        }).then(function (d) {
            if (!d || !d.ok) throw new Error((d && d.msg) || "");
            aplicarResumo(d, seq);
        }).catch(function (erro) {
            // O banco é quem manda: desfaz na tela para não mandar ao voluntário
            // uma rota que ninguém guardou.
            if (volta) volta.appendChild(cartao);
            toast(erro.message || "Não consegui salvar. A parada voltou.", "error");
        });
    });

    /* ---- nome do entregador ---- */
    var esperando = null;
    quadro.addEventListener("input", function (e) {
        var campo = e.target.closest("[data-nome]");
        if (!campo) return;
        // Espera a pessoa parar de digitar: um POST por letra encheria o banco
        // de escritas e faria o texto da rota piscar a cada tecla.
        window.clearTimeout(esperando);
        esperando = window.setTimeout(function () { salvarNome(campo); }, 600);
    });

    quadro.addEventListener("change", function (e) {
        var campo = e.target.closest("[data-nome]");
        if (campo) {
            window.clearTimeout(esperando);
            salvarNome(campo);
        }
    });

    function salvarNome(campo) {
        var seq = ++pedidoSeq;
        acao({
            acao: "entrega_nome",
            entregador: campo.dataset.nome,
            nome: campo.value
        }).then(function (d) {
            if (!d || !d.ok) throw new Error((d && d.msg) || "");
            aplicarResumo(d, seq);
        }).catch(function () {
            toast("Não consegui salvar o nome.", "error");
        });
    }

    /* ---- refazer a divisão: pergunta antes, porque apaga trabalho ---- */
    document.addEventListener("submit", function (e) {
        var f = e.target;
        if (f && f.dataset && f.dataset.confirmar && !window.confirm(f.dataset.confirmar)) {
            e.preventDefault();
        }
    });
})();
