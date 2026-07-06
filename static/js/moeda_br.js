/* =========================================================
   Máscara de moeda pt-BR (padrão do sistema). Dois modos:

   1) Par visível + oculto (o campo enviado é o oculto):
        <input type="text" data-moeda data-moeda-alvo="idOculto" inputmode="decimal">
        <input type="hidden" name="valor" id="idOculto">

   2) Inline (o próprio campo é enviado — sem data-moeda-alvo). Útil para
      campos de formulário Django e linhas de variação adicionadas por JS:
        <input type="text" name="valor" data-moeda inputmode="decimal">
      Enquanto digita mostra "1.234,56"; ao **enviar o formulário** o valor
      é normalizado para o limpo ("1234.56") pouco antes do submit.

   Em ambos, enquanto digita formata "1.234,56" no campo visível e o valor
   LIMPO com ponto decimal ("1234.56") é o que chega ao servidor — o back-end
   não muda. Funciona com campos adicionados dinamicamente (delegação). Sem libs.
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

    // Modo inline: normaliza o próprio campo para o valor limpo ("1234.56").
    function normalizarInline(campo) {
        var digitos = (campo.value || "").replace(/\D/g, "");
        campo.value = digitos ? (parseInt(digitos, 10) / 100).toFixed(2) : "";
    }

    document.addEventListener("input", function (e) {
        var campo = e.target;
        if (campo && campo.matches && campo.matches("input[data-moeda]")) {
            limpar(campo);
        }
    });

    // Antes de enviar qualquer formulário, converte os campos inline
    // (data-moeda sem alvo) para o valor limpo que o back-end espera.
    document.addEventListener("submit", function (e) {
        var form = e.target;
        if (!form || !form.querySelectorAll) return;
        Array.prototype.forEach.call(
            form.querySelectorAll("input[data-moeda]:not([data-moeda-alvo])"),
            normalizarInline
        );
    }, true);

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
