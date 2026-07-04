/* =========================================================
   Página de inscrição do evento:
   - adicionar/remover linhas de participante;
   - checkbox "diretoria" reflete num input hidden (para o valor
     ir alinhado por índice mesmo quando desmarcado).
   JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    var lista = document.getElementById("participantes");
    var addBtn = document.getElementById("addParticipante");
    var modelo = document.getElementById("part-modelo");
    if (!lista) return;

    function conectarRemover(linha) {
        var rem = linha.querySelector(".part-remover");
        if (!rem) return;
        rem.addEventListener("click", function () {
            if (lista.querySelectorAll(".part-linha").length > 1) {
                linha.remove();
            } else {
                // Última linha: apenas limpa os campos.
                linha.querySelectorAll("input").forEach(function (inp) {
                    if (inp.type === "checkbox") inp.checked = false;
                    else if (inp.classList.contains("part-diretoria-val")) inp.value = "0";
                    else inp.value = "";
                });
            }
        });
    }

    // Checkbox "diretoria" → atualiza o hidden alinhado (delegação de evento).
    lista.addEventListener("change", function (e) {
        if (e.target.classList.contains("part-diretoria-check")) {
            var linha = e.target.closest(".part-linha");
            var hid = linha ? linha.querySelector(".part-diretoria-val") : null;
            if (hid) hid.value = e.target.checked ? "1" : "0";
        }
    });

    if (addBtn && modelo) {
        addBtn.addEventListener("click", function () {
            var frag = modelo.content.cloneNode(true);
            lista.appendChild(frag);
            conectarRemover(lista.lastElementChild);
        });
    }

    Array.prototype.forEach.call(lista.querySelectorAll(".part-linha"), conectarRemover);
})();
