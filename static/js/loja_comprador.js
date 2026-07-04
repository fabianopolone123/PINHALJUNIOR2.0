/* =========================================================
   Lojinha (pública): lembra os dados do comprador entre pedidos.
   Ao enviar, guarda nome/WhatsApp/e-mail no localStorage do próprio
   aparelho; ao abrir a loja de novo, preenche automaticamente
   (funciona no celular e no computador). JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    var CHAVE = "pinhaljr_comprador";
    var campos = ["comprador_nome", "comprador_whatsapp", "comprador_email"];
    var form = document.getElementById("lojaForm");
    if (!form) return;

    function ler() {
        try {
            return JSON.parse(localStorage.getItem(CHAVE)) || {};
        } catch (e) {
            return {};
        }
    }

    // Preenche só o que estiver vazio (não sobrescreve o que o servidor mandou).
    var dados = ler();
    campos.forEach(function (id) {
        var el = document.getElementById(id);
        if (el && !el.value && dados[id]) el.value = dados[id];
    });

    // Ao enviar, memoriza os dados atuais para o próximo pedido.
    form.addEventListener("submit", function () {
        var salvar = {};
        campos.forEach(function (id) {
            var el = document.getElementById(id);
            if (el) salvar[id] = el.value.trim();
        });
        try {
            localStorage.setItem(CHAVE, JSON.stringify(salvar));
        } catch (e) { /* localStorage indisponível: segue sem lembrar */ }
    });
})();
