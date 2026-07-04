/* =========================================================
   Cadastro de produto da lojinha:
   - adicionar/remover linhas de variação (índice único nos names);
   - mostrar/ocultar a coluna "Estoque" conforme "Controlar estoque".
   JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    var form = document.getElementById("produtoForm");
    var lista = document.getElementById("variacoes");
    var addBtn = document.getElementById("addVariacao");
    var modelo = document.getElementById("var-modelo");
    if (!lista) return;

    function proximoIndice() {
        var max = -1;
        Array.prototype.forEach.call(
            lista.querySelectorAll('input[name="var_idx"]'),
            function (inp) {
                var n = parseInt(inp.value, 10);
                if (!isNaN(n) && n > max) max = n;
            }
        );
        return max + 1;
    }

    function conectarRemover(linha) {
        var rem = linha.querySelector(".var-remover");
        if (!rem) return;
        rem.addEventListener("click", function () {
            if (lista.querySelectorAll(".var-linha").length > 1) {
                linha.remove();
            } else {
                linha.querySelectorAll("input").forEach(function (c) {
                    if (c.name !== "var_idx") c.value = "";
                });
            }
        });
    }

    if (addBtn && modelo) {
        addBtn.addEventListener("click", function () {
            var idx = proximoIndice();
            var html = modelo.innerHTML.replace(/__IDX__/g, idx).trim();
            var temp = document.createElement("div");
            temp.innerHTML = html;
            var nova = temp.firstElementChild;
            if (!nova) return;
            lista.appendChild(nova);
            conectarRemover(nova);
        });
    }
    Array.prototype.forEach.call(lista.querySelectorAll(".var-linha"), conectarRemover);

    // Mostrar/ocultar a coluna "Estoque" conforme "Controlar estoque".
    var chk = form ? form.querySelector('input[name="controla_estoque"]') : null;
    function alternarEstoque() {
        if (form && chk) form.classList.toggle("oculta-estoque", !chk.checked);
    }
    if (chk) {
        chk.addEventListener("change", alternarEstoque);
        alternarEstoque();
    }
})();
