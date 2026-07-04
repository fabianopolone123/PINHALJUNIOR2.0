/* =========================================================
   Página de inscrição do evento:
   - adicionar/remover linhas de participante (cada linha tem um índice
     único usado nos names dos campos, inclusive os "por participante");
   - a última linha não é removida, apenas limpa.
   JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    var lista = document.getElementById("participantes");
    var addBtn = document.getElementById("addParticipante");
    var modelo = document.getElementById("part-modelo");
    if (!lista) return;

    // Próximo índice = maior part_idx atual + 1 (evita colisão após reenvio).
    function proximoIndice() {
        var max = -1;
        Array.prototype.forEach.call(
            lista.querySelectorAll('input[name="part_idx"]'),
            function (inp) {
                var n = parseInt(inp.value, 10);
                if (!isNaN(n) && n > max) max = n;
            }
        );
        return max + 1;
    }

    function conectarRemover(linha) {
        var rem = linha.querySelector(".part-remover");
        if (!rem) return;
        rem.addEventListener("click", function () {
            if (lista.querySelectorAll(".part-linha").length > 1) {
                linha.remove();
            } else {
                // Última linha: apenas limpa os campos (mantém o índice).
                linha.querySelectorAll("input, textarea, select").forEach(function (campo) {
                    if (campo.type === "checkbox") campo.checked = false;
                    else if (campo.name !== "part_idx") campo.value = "";
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

    Array.prototype.forEach.call(lista.querySelectorAll(".part-linha"), conectarRemover);
})();
