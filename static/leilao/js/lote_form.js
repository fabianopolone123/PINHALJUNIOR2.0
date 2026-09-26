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

    /* =====================================================================
       A foto é reduzida AQUI, antes de subir
       =====================================================================
       O que faz o cadastro de item demorar não é o servidor: ele leva alguns
       décimos de segundo. É o UPLOAD — a foto sai do celular com 2 a 5 MB, e
       numa internet de celular isso são dezenas de segundos com a tela parada.
       O servidor recebe tudo isso para jogar 90% fora, porque a maior largura
       que ele guarda é 1280.

       Reduzindo antes de enviar, o mesmo cadastro sobe algumas centenas de kB.
       O servidor continua reduzindo do lado dele: isto é melhoria de tempo, não
       a garantia do tamanho — quem entra sem JS manda o arquivo inteiro e o
       cadastro funciona igual.

       A ORIENTAÇÃO é o cuidado que não pode falhar. Foto de celular vem
       deitada, com a rotação só no EXIF, e desenhar num canvas **apaga o
       EXIF**: se o navegador não aplicar a rotação ao ler, a foto sobe deitada
       e o servidor não tem mais como consertar. Por isso tudo passa por
       `createImageBitmap(..., {imageOrientation: "from-image"})`, que aplica a
       rotação na leitura; sem ele, a redução é **pulada** e o arquivo original
       segue inteiro. Item deitado no pregão é pior do que cadastro lento. */
    var LARGURA_ALVO = 1280;
    var QUALIDADE = 0.82;

    function podeReduzir() {
        return typeof createImageBitmap === "function" &&
            typeof HTMLCanvasElement !== "undefined" &&
            typeof HTMLCanvasElement.prototype.toBlob === "function";
    }

    /* As dimensões que o navegador considera CERTAS para esta foto.

       O `<img>` orienta pelo EXIF desde sempre (é o padrão do CSS
       `image-orientation: from-image`), então ele serve de gabarito: se o
       `createImageBitmap` devolver o tamanho trocado em relação a ele, aquele
       navegador **ignorou** o `imageOrientation` e a foto sairia deitada. */
    function medidasCertas(arquivo) {
        return new Promise(function (ok) {
            var url = URL.createObjectURL(arquivo);
            var img = new Image();
            img.onload = function () {
                var m = { largura: img.naturalWidth, altura: img.naturalHeight };
                URL.revokeObjectURL(url);
                ok(m);
            };
            img.onerror = function () { URL.revokeObjectURL(url); ok(null); };
            img.src = url;
        });
    }

    function reduzir(arquivo) {
        // Sempre uma Promise: quem chama não precisa saber se deu certo.
        if (!podeReduzir() || !/^image\//.test(arquivo.type || "") ||
                /svg|gif/i.test(arquivo.type || "")) {
            return Promise.resolve(null);
        }
        return Promise.all([
            createImageBitmap(arquivo, { imageOrientation: "from-image" }),
            medidasCertas(arquivo)
        ]).then(function (par) {
            var bitmap = par[0], certas = par[1];

            function desistir() { bitmap.close && bitmap.close(); return null; }

            if (bitmap.width <= LARGURA_ALVO) return desistir();   // já é pequena

            /* A CONFERÊNCIA que não pode faltar. Desenhar num canvas apaga o
               EXIF: se a rotação não tiver sido aplicada na leitura, a foto sobe
               deitada e o servidor não tem mais como consertar — item deitado no
               pregão é pior do que cadastro lento. Na dúvida, manda o original
               inteiro e deixa o servidor (que ainda tem o EXIF) resolver. */
            if (!certas || certas.largura !== bitmap.width ||
                    certas.altura !== bitmap.height) {
                return desistir();
            }

            var largura = LARGURA_ALVO;
            var altura = Math.round(bitmap.height * largura / bitmap.width);
            var canvas = document.createElement("canvas");
            canvas.width = largura;
            canvas.height = altura;
            canvas.getContext("2d").drawImage(bitmap, 0, 0, largura, altura);
            bitmap.close && bitmap.close();
            return new Promise(function (ok) {
                canvas.toBlob(function (blob) { ok(blob || null); },
                              "image/jpeg", QUALIDADE);
            });
        })
        .catch(function () { return null; });   // qualquer tropeço: manda o original
    }

    var form = campo.form;
    var enviando = false;

    // Depois que o POST de verdade saiu, um segundo toque (o upload leva
    // dezenas de segundos no 4G) reenviava o formulário e o item nascia em
    // dobro, com número novo (revisão de 26/09). `enviado` trava; voltar à
    // página pelo "voltar" do navegador destrava.
    var enviado = false;
    window.addEventListener("pageshow", function () { enviado = false; enviando = false; });

    if (form) {
        form.addEventListener("submit", function (e) {
            if (enviado) { e.preventDefault(); return; }
            if (enviando) { enviado = true; return; }   // a segunda passada é a de verdade
            var arquivo = campo.files && campo.files[0];
            if (!arquivo) { enviado = true; return; }   // sem foto: vai direto, uma vez só

            e.preventDefault();
            var botao = e.submitter;
            if (botao) botao.disabled = true;

            reduzir(arquivo).then(function (blob) {
                if (blob && blob.size < arquivo.size) {
                    var dt = new DataTransfer();
                    // `.jpg` porque o canvas devolve JPEG, seja qual for a
                    // extensão que entrou (HEIC do iPhone, por exemplo).
                    var nomeBase = (arquivo.name || "foto").replace(/\.[^.]+$/, "");
                    dt.items.add(new File([blob], nomeBase + ".jpg", { type: "image/jpeg" }));
                    campo.files = dt.files;
                }
                enviando = true;
                if (botao) {
                    botao.disabled = false;
                    // O botão apertado tem de ir no POST: é ele que diz se é
                    // "Salvar" ou "Salvar e cadastrar outro".
                    botao.click();
                } else {
                    form.submit();
                }
            });
        });
    }
})();
