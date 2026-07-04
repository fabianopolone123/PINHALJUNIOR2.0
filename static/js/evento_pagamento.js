/* =========================================================
   Tela de pagamento (simulada): botão "Copiar" do código Pix
   copia e cola. JS puro, com fallback para navegadores antigos.
   ========================================================= */
(function () {
    "use strict";

    var btn = document.getElementById("btnCopiarPix");
    if (!btn) return;
    var input = document.getElementById(btn.dataset.target);
    if (!input) return;

    function feedback() {
        // Notificação padrão do sistema (toast). Cai no texto do botão se, por
        // algum motivo, o módulo de toast não estiver carregado.
        if (typeof window.mostrarToast === "function") {
            window.mostrarToast("Código Pix copiado!", "success");
        }
        var txt = btn.textContent;
        btn.textContent = "Copiado!";
        setTimeout(function () { btn.textContent = txt; }, 2500);
    }

    btn.addEventListener("click", function () {
        var valor = input.value;
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(valor).then(feedback, selecionarManual);
        } else {
            selecionarManual();
        }
    });

    function selecionarManual() {
        input.removeAttribute("readonly");
        input.focus();
        input.select();
        try { document.execCommand("copy"); } catch (e) { /* ignora */ }
        input.setAttribute("readonly", "readonly");
        feedback();
    }
})();
