/* =========================================================
   Máscara de moeda pt-BR (padrão do sistema). Uso:
     <input type="text" data-moeda data-moeda-alvo="idOculto" inputmode="decimal">
     <input type="hidden" name="valor" id="idOculto">
   Enquanto digita, formata "1.234,56" no campo visível e grava o valor
   LIMPO com ponto decimal ("1234.56") no campo oculto (que é enviado ao
   servidor). Assim o back-end não muda. Funciona com campos adicionados
   dinamicamente (delegação). Sem libs.
   ========================================================= */
(function () {
    "use strict";

    function formatarBR(centavos) {
        var v = (centavos / 100).toFixed(2);          // "1234.56"
        var partes = v.split(".");
        var inteiro = partes[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
        return inteiro + "," + partes[1];
    }

    function limpar(campo) {
        var alvoId = campo.getAttribute("data-moeda-alvo");
        var oculto = alvoId ? document.getElementById(alvoId) : null;
        var digitos = (campo.value || "").replace(/\D/g, "");
        if (!digitos) {
            campo.value = "";
            if (oculto) oculto.value = "";
            return;
        }
        var centavos = parseInt(digitos, 10);
        campo.value = formatarBR(centavos);
        if (oculto) oculto.value = (centavos / 100).toFixed(2);
    }

    // Inicializa: se o oculto já tem valor (edição), formata o visível.
    function inicializar(campo) {
        var alvoId = campo.getAttribute("data-moeda-alvo");
        var oculto = alvoId ? document.getElementById(alvoId) : null;
        var base = "";
        if (oculto && oculto.value) base = oculto.value;
        else if (campo.value) base = campo.value;
        var digitos = base.replace(",", ".");
        var num = parseFloat(digitos);
        if (!isNaN(num) && num > 0) {
            campo.value = formatarBR(Math.round(num * 100));
            if (oculto) oculto.value = num.toFixed(2);
        } else {
            campo.value = "";
            if (oculto) oculto.value = "";
        }
    }

    document.addEventListener("input", function (e) {
        var campo = e.target;
        if (campo && campo.matches && campo.matches("input[data-moeda]")) {
            limpar(campo);
        }
    });

    document.addEventListener("DOMContentLoaded", function () {
        Array.prototype.forEach.call(
            document.querySelectorAll("input[data-moeda]"), inicializar
        );
    });
    // Caso o script carregue após o DOM já pronto.
    if (document.readyState !== "loading") {
        Array.prototype.forEach.call(
            document.querySelectorAll("input[data-moeda]"), inicializar
        );
    }
})();
