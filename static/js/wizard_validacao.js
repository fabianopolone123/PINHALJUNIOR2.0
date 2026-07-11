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

    function mostrarAviso(lista) {
        var box = document.getElementById("avisoValidacao");
        var ul = document.getElementById("avisoValidacaoLista");
        if (!box || !ul) return;
        if (!lista.length) { box.hidden = true; return; }
        ul.innerHTML = lista.map(function (x) {
            return "<li>" + (x.rotulo || x) + "</li>";
        }).join("");
        box.hidden = false;
        box.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    function limparAviso() {
        var box = document.getElementById("avisoValidacao");
        if (box) box.hidden = true;
    }

    window.WizardValidacao = {
        faltantes: faltantes,
        mostrarAviso: mostrarAviso,
        limparAviso: limparAviso,
    };
})();
