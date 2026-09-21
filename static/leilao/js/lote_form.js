/*
 * lote_form.js — os dois caminhos da foto do item, e a prévia.
 *
 * POR QUE DOIS BOTÕES, e não um campo só:
 *
 *   - com `capture="environment"`, o celular abre a câmera e ESCONDE a galeria;
 *   - sem `capture`, o Android 13+ abre o seletor de fotos do sistema, que não
 *     tem câmera.
 *
 * Ou seja, nenhum dos dois sozinho oferece as duas coisas, e o que aparece
 * muda de aparelho para aparelho. Então a escolha sai do menu do sistema e vem
 * para a tela: dois `<input type="file">`, um com `capture` e outro sem, e dois
 * botões dizendo qual é qual. Continua sem biblioteca.
 *
 * O input do formulário (`#id_foto`, o único com `name`) é sempre o que vai no
 * POST. O da câmera não é enviado: o arquivo dele é copiado para o de verdade
 * com `DataTransfer`, que é a única forma de escrever em `input.files`.
 *
 * MELHORIA PROGRESSIVA: os botões nascem `hidden` no template e só aparecem se
 * o navegador tiver `DataTransfer`. Sem isso — ou sem JS — o seletor nativo
 * continua visível e o cadastro funciona como sempre. Ninguém fica sem mandar
 * foto porque a cópia não era suportada.
 */
(function () {
    "use strict";

    var campo = document.getElementById("id_foto");
    var previa = document.getElementById("previaFoto");
    if (!campo || !previa) return;

    var nome = document.getElementById("fotoNome");

    function mostrar(arquivo) {
        if (!arquivo) {
            previa.hidden = true;
            if (nome) nome.hidden = true;
            return;
        }
        // `createObjectURL` não lê o arquivo inteiro na memória (ao contrário
        // do FileReader) — com foto de 5 MB no celular, isso importa.
        var url = URL.createObjectURL(arquivo);
        previa.src = url;
        previa.hidden = false;
        previa.onload = function () { URL.revokeObjectURL(url); };

        // Com os botões ligados, o input nativo fica escondido e some o nome do
        // arquivo que ele mostrava. Quem escolheu da galeria precisa conferir
        // que pegou a foto certa.
        if (nome) {
            nome.textContent = arquivo.name || "Foto selecionada";
            nome.hidden = false;
        }
    }

    campo.addEventListener("change", function () {
        mostrar(campo.files && campo.files[0]);
    });

    // -- os dois botões (só se der para copiar o arquivo da câmera) ----------
    var botoes = document.getElementById("fotoBotoes");
    var camera = document.getElementById("fotoCamera");
    var btnCamera = document.getElementById("btnFotoCamera");
    var btnArquivo = document.getElementById("btnFotoArquivo");

    var podeCopiar = false;
    try {
        podeCopiar = typeof DataTransfer === "function" && !!new DataTransfer();
    } catch (e) {
        podeCopiar = false;
    }

    if (!botoes || !camera || !btnCamera || !btnArquivo || !podeCopiar) return;

    botoes.hidden = false;
    campo.hidden = true;   // continua sendo o campo enviado; só sai da vista

    btnArquivo.addEventListener("click", function () { campo.click(); });
    btnCamera.addEventListener("click", function () { camera.click(); });

    camera.addEventListener("change", function () {
        var arquivo = camera.files && camera.files[0];
        if (!arquivo) return;
        var dt = new DataTransfer();
        dt.items.add(arquivo);
        campo.files = dt.files;   // é ISTO que faz a foto da câmera ser enviada
        mostrar(arquivo);
    });
})();
