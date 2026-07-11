/* =========================================================
   Validação de wizard (compartilhada aventureiro + diretoria).
   Acha os campos obrigatórios vazios num escopo (etapa ou form),
   lista os rótulos numa caixa de aviso e permite pular até eles.
   ========================================================= */
(function () {
    "use strict";

    function rotulo(el) {
        var c = el.closest(".campo, .campo-checkbox, .campo-simnao, .assinatura-doc, .campo-foto");
        if (c) {
            var l = c.querySelector(".campo-simnao-rotulo, label");
            if (l) return l.textContent.replace("*", "").trim();
        }
        return el.getAttribute("aria-label") || el.name || "campo";
    }

    // Campos com atributo [required] vazios dentro do escopo.
    function faltantes(escopo) {
        var out = [], vistosRadio = {};
        Array.prototype.forEach.call(escopo.querySelectorAll("[required]"), function (el) {
            var falta = false;
            if (el.type === "radio") {
                if (vistosRadio[el.name]) return;
                vistosRadio[el.name] = true;
                var grupo = escopo.querySelectorAll('input[name="' + el.name + '"]');
                var ok = false;
                Array.prototype.forEach.call(grupo, function (r) { if (r.checked) ok = true; });
                falta = !ok;
            } else if (el.type === "file") {
                falta = !(el.files && el.files.length);
            } else {
                falta = !el.value || !el.value.trim();
            }
            if (falta) out.push({ el: el, rotulo: rotulo(el) });
        });
        return out;
    }

    // Mostra UM toast (padrão do sistema) com o(s) nome(s) do(s) campo(s) que faltam.
    function mostrarAviso(lista) {
        if (!lista || !lista.length) return;
        var nomes = lista.map(function (x) { return x.rotulo || x; });
        var msg;
        if (nomes.length === 1) {
            msg = "Preencha o campo obrigatório: " + nomes[0];
        } else {
            var MAX = 4;
            var mostra = nomes.slice(0, MAX).join(", ");
            var resto = nomes.length - MAX;
            msg = "Preencha os campos obrigatórios: " + mostra + (resto > 0 ? " e mais " + resto : "");
        }
        if (window.mostrarToast) {
            window.mostrarToast(msg, "error");
        } else {
            alert(msg);
        }
    }

    // Toasts fecham sozinhos; nada a limpar (mantido por compatibilidade).
    function limparAviso() {}

    window.WizardValidacao = {
        faltantes: faltantes,
        mostrarAviso: mostrarAviso,
        limparAviso: limparAviso,
    };
})();
