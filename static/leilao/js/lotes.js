/*
 * lotes.js — lista de itens e lista de leilões.
 *
 * Duas coisas só: reordenar a fila (▲▼) e confirmar o que é destrutivo. A
 * confirmação segue o padrão do sistema do clube: `form[data-confirmar]` com
 * guarda no submit.
 */
(function () {
    "use strict";

    var dados = document.getElementById("dadosMesa");

    var movendo = false;

    if (dados && dados.dataset.acaoUrl) {
        document.addEventListener("click", function (e) {
            var alvo = e.target.closest("[data-acao='mover']");
            if (!alvo) return;
            // Um movimento por vez: a página recarrega no fim, e o clique duplo
            // andava DUAS posições (revisão de 26/09).
            if (movendo) return;
            movendo = true;
            fetch(dados.dataset.acaoUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": dados.dataset.csrf,
                    "X-Requested-With": "XMLHttpRequest"
                },
                body: JSON.stringify({
                    acao: "mover",
                    // O leilão desta tela — reordenar o do mês que vem com
                    // outro no ar dava 404 e "Sem conexão".
                    leilao: dados.dataset.leilao,
                    lote: alvo.dataset.lote,
                    direcao: alvo.dataset.direcao
                })
            }).then(function (r) { return r.json(); })
              .then(function (d) {
                  if (d && d.ok) { window.location.reload(); return; }
                  movendo = false;
                  if (window.mostrarToast) window.mostrarToast((d && d.msg) || "Não deu.", "error");
              })
              .catch(function () {
                  movendo = false;
                  if (window.mostrarToast) window.mostrarToast("Sem conexão.", "error");
              });
        });
    }

    document.querySelectorAll("form[data-confirmar]").forEach(function (form) {
        form.addEventListener("submit", function (e) {
            if (!window.confirm(form.dataset.confirmar)) e.preventDefault();
        });
    });
})();
