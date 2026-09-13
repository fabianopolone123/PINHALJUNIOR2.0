/* =========================================================
   Copiar para o clipboard um texto que já veio PRONTO do
   servidor. Cada botão `.btn-copiar-lista` aponta, por
   `data-fonte`, para a <textarea class="copiar-fonte"> com o
   texto; o aviso do toast vem do `data-aviso` (opcional).

   Usado pelo painel do evento (lista de inscritos) e pela aba
   Parcelas das Mensalidades — é UM arquivo para as duas telas;
   ao criar uma terceira, ligue-o de novo em vez de duplicar.

   Mesmo caminho do "Copiar" do código Pix (evento_pagamento.js):
   clipboard quando existe, seleção + execCommand como reserva, e
   o toast padrão do sistema como aviso. A textarea fica fora da
   tela em vez de `hidden`: a reserva precisa de select() num
   campo que exista de fato (ver .copiar-fonte em eventos.css).
   ========================================================= */
(function () {
    "use strict";

    var botoes = Array.prototype.slice.call(
        document.querySelectorAll(".btn-copiar-lista")
    );
    if (!botoes.length) return;

    botoes.forEach(function (btn) {
        var fonte = document.getElementById(btn.dataset.fonte);
        if (!fonte) return;

        function feedback() {
            if (typeof window.mostrarToast === "function") {
                window.mostrarToast(
                    btn.dataset.aviso || "Lista copiada! Já pode colar.",
                    "success"
                );
            }
            // Confirmação também no próprio botão, para quem clicou olhando ali.
            var antes = btn.innerHTML;
            btn.innerHTML = "✅ Copiado!";
            setTimeout(function () { btn.innerHTML = antes; }, 2500);
        }

        function copiarManual() {
            fonte.removeAttribute("readonly");
            fonte.focus();
            fonte.select();
            try { document.execCommand("copy"); } catch (e) { /* ignora */ }
            fonte.setAttribute("readonly", "readonly");
            btn.focus();  // o foco não pode ficar num campo fora da tela
            feedback();
        }

        btn.addEventListener("click", function () {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(fonte.value).then(feedback, copiarManual);
            } else {
                copiarManual();
            }
        });
    });
})();
