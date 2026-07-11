/* =========================================================
   Cadastro de Diretoria — wizard de etapas
   JavaScript puro, sem bibliotecas externas.
   (Mesmo padrão do cadastro de aventureiro, adaptado.)
   ========================================================= */
(function () {
    "use strict";

    var form = document.getElementById("cadastroForm");
    if (!form) return;

    var passos = Array.prototype.slice.call(document.querySelectorAll(".passo"));
    var pontos = Array.prototype.slice.call(document.querySelectorAll(".etapa-ponto"));
    var preenchido = document.getElementById("progressoPreenchido");
    var btnVoltar = document.getElementById("btnVoltar");
    var btnProximo = document.getElementById("btnProximo");
    var btnFinalizar = document.getElementById("btnFinalizar");

    var total = passos.length;
    var atual = 0;

    function mostrar(indice) {
        atual = Math.max(0, Math.min(indice, total - 1));
        passos.forEach(function (p, i) { p.classList.toggle("ativo", i === atual); });
        pontos.forEach(function (ponto, i) {
            ponto.classList.toggle("ativo", i === atual);
            ponto.classList.toggle("concluida", i < atual);
        });
        var pct = ((atual + 1) / total) * 100;
        if (preenchido) preenchido.style.width = pct + "%";
        btnVoltar.hidden = atual === 0;
        var ultimo = atual === total - 1;
        btnProximo.hidden = ultimo;
        btnFinalizar.hidden = !ultimo;
        if (ultimo) montarRevisao();
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    btnProximo.addEventListener("click", function () { mostrar(atual + 1); });
    btnVoltar.addEventListener("click", function () { mostrar(atual - 1); });
    pontos.forEach(function (ponto, i) {
        ponto.addEventListener("click", function () { mostrar(i); });
    });

    /* ---------- Campos condicionais (checkbox "Sim") ---------- */
    var condicionais = Array.prototype.slice.call(document.querySelectorAll(".condicional[data-depende]"));
    condicionais.forEach(function (bloco) {
        var controle = document.getElementById(bloco.getAttribute("data-depende"));
        if (!controle) return;
        function atualizar() { bloco.classList.toggle("visivel", controle.checked); }
        controle.addEventListener("change", atualizar);
        atualizar();
    });

    /* ---------- Cônjuge aparece conforme o estado civil ---------- */
    var estadoCivil = document.getElementById("id_dir-estado_civil");
    var blocoConjuge = document.getElementById("blocoConjuge");
    if (estadoCivil && blocoConjuge) {
        function atualizarConjuge() {
            var v = estadoCivil.value;
            blocoConjuge.classList.toggle("visivel", v === "casado" || v === "uniao_estavel");
        }
        estadoCivil.addEventListener("change", atualizarConjuge);
        atualizarConjuge();
    }

    /* ---------- Preview da foto ---------- */
    var inputFoto = document.getElementById("id_dir-foto");
    var preview = document.getElementById("fotoPreview");
    if (inputFoto && preview) {
        inputFoto.addEventListener("change", function () {
            var arquivo = inputFoto.files && inputFoto.files[0];
            if (arquivo && /^image\//.test(arquivo.type)) {
                preview.src = URL.createObjectURL(arquivo);
                preview.hidden = false;
            } else {
                preview.hidden = true;
            }
        });
    }

    /* ---------- Preenche o termo de imagem com os dados digitados ---------- */
    function preencherTermoImagem() {
        var alvos = document.querySelectorAll("#termoImagem [data-fill]");
        Array.prototype.forEach.call(alvos, function (el) {
            var campo = document.getElementById(el.dataset.fill);
            var texto = "";
            if (campo) {
                if (campo.tagName === "SELECT") {
                    texto = campo.options[campo.selectedIndex] ? campo.options[campo.selectedIndex].text : "";
                } else {
                    texto = campo.value.trim();
                }
            }
            el.textContent = texto || (el.dataset.vazio || "");
        });
    }
    var termoImagem = document.getElementById("termoImagem");
    if (termoImagem) {
        Array.prototype.forEach.call(
            document.querySelectorAll('[id^="id_dir-"]'),
            function (campo) {
                campo.addEventListener("input", preencherTermoImagem);
                campo.addEventListener("change", preencherTermoImagem);
            }
        );
        preencherTermoImagem();
    }

    /* ---------- Revisão final ---------- */
    function valor(id) {
        var el = document.getElementById(id);
        if (!el) return "—";
        if (el.tagName === "SELECT") {
            return el.options[el.selectedIndex] && el.value ? el.options[el.selectedIndex].text : "—";
        }
        return el.value ? el.value : "—";
    }
    function aceito(id) {
        var el = document.getElementById(id);
        return el && el.checked ? "Aceito ✓" : "Pendente";
    }
    function montarRevisao() {
        var revisao = document.getElementById("revisao");
        if (!revisao) return;
        var itens = [
            ["Usuário", valor("id_conta-username")],
            ["Nome completo", valor("id_dir-nome_completo")],
            ["CPF", valor("id_dir-cpf")],
            ["Data de nascimento", valor("id_dir-data_nascimento")],
            ["WhatsApp", valor("id_dir-whatsapp")],
            ["E-mail", valor("id_dir-email")],
            ["Escolaridade", valor("id_dir-escolaridade")],
            ["Compromisso de voluntário", aceito("id_aceite_compromisso")],
            ["Declaração médica", aceito("id_aceite_medica")],
            ["Autorização de imagem", aceito("id_aceite_imagem")],
        ];
        revisao.innerHTML = itens.map(function (par) {
            return '<div class="revisao-item"><strong>' + par[0] + "</strong><span>" + par[1] + "</span></div>";
        }).join("");
    }

    /* ---------- Validação de envio (aceites obrigatórios) ---------- */
    var ACEITES = [
        ["id_aceite_compromisso", "o compromisso de voluntário"],
        ["id_aceite_medica", "a declaração médica"],
        ["id_aceite_imagem", "a autorização de uso de imagem"],
    ];
    function indicePasso(id) {
        var el = document.getElementById(id);
        var passo = el ? el.closest(".passo") : null;
        return passo ? passos.indexOf(passo) : -1;
    }
    form.addEventListener("submit", function (evento) {
        for (var i = 0; i < ACEITES.length; i++) {
            var campo = document.getElementById(ACEITES[i][0]);
            if (campo && !campo.checked) {
                evento.preventDefault();
                mostrar(indicePasso(ACEITES[i][0]));
                alert("É necessário aceitar " + ACEITES[i][1] + " para finalizar.");
                return;
            }
        }
    });

    mostrar(0);
})();
