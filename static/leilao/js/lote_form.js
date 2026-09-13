/*
 * lote_form.js — prévia da foto do item.
 *
 * A câmera do celular é aberta pelo atributo `capture` do próprio
 * `<input type="file">` (posto no widget, em forms.py) — nada de biblioteca.
 * Aqui só mostramos o que foi fotografado, porque quem tira foto de um item em
 * cima da mesa precisa ver se ficou torta ANTES de salvar.
 */
(function () {
    "use strict";

    var campo = document.getElementById("id_foto");
    var previa = document.getElementById("previaFoto");
    if (!campo || !previa) return;

    campo.addEventListener("change", function () {
        var arquivo = campo.files && campo.files[0];
        if (!arquivo) { previa.hidden = true; return; }

        // `createObjectURL` não lê o arquivo inteiro na memória (ao contrário do
        // FileReader) — com foto de 5 MB no celular, isso importa.
        var url = URL.createObjectURL(arquivo);
        previa.src = url;
        previa.hidden = false;
        previa.onload = function () { URL.revokeObjectURL(url); };
    });
})();
