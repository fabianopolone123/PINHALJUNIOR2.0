/* =========================================================
   Cadastro de Aventureiro — wizard de etapas
   JavaScript puro, sem bibliotecas externas.
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
    var V = window.WizardValidacao;

    var total = passos.length;
    var atual = 0; // índice (0-based)

    // Ajusta a numeração exibida nos pontos conforme o total real de etapas.
    // (No fluxo de "novo aventureiro" a etapa "Conta" não existe.)
    pontos.forEach(function (ponto, i) {
        var numero = ponto.querySelector("span");
        if (numero) numero.textContent = String(i + 1);
    });

    function mostrar(indice) {
        atual = Math.max(0, Math.min(indice, total - 1));

        passos.forEach(function (p, i) {
            p.classList.toggle("ativo", i === atual);
        });
        pontos.forEach(function (ponto, i) {
            ponto.classList.toggle("ativo", i === atual);
            ponto.classList.toggle("concluida", i < atual);
        });

        // Barra de progresso
        var pct = ((atual + 1) / total) * 100;
        if (preenchido) preenchido.style.width = pct + "%";

        // Botões
        btnVoltar.hidden = atual === 0;
        var ultimo = atual === total - 1;
        btnProximo.hidden = ultimo;
        btnFinalizar.hidden = !ultimo;

        reaproveitarTermoImagem();
        if (typeof preencherTermoImagem === "function") preencherTermoImagem();
        if (ultimo) montarRevisao();

        // Rola para o topo do card
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    btnProximo.addEventListener("click", function () {
        var falta = V ? V.faltantes(passos[atual]) : [];
        if (falta.length) {
            V.mostrarAviso(falta);
            try { falta[0].el.focus(); } catch (e) { /* ignora */ }
            return;
        }
        if (V) V.limparAviso();
        mostrar(atual + 1);
    });
    btnVoltar.addEventListener("click", function () {
        if (V) V.limparAviso();
        mostrar(atual - 1);
    });

    // Permite clicar num ponto de etapa já visitado/adiante
    pontos.forEach(function (ponto, i) {
        ponto.addEventListener("click", function () {
            mostrar(i);
        });
    });

    /* ---------- Campos condicionais ---------- */
    // (a) checkbox: mostra quando marcado.
    Array.prototype.forEach.call(document.querySelectorAll(".condicional[data-depende]"), function (bloco) {
        var controle = document.getElementById(bloco.getAttribute("data-depende"));
        if (!controle) return;
        function atualizar() { bloco.classList.toggle("visivel", controle.checked); }
        controle.addEventListener("change", atualizar);
        atualizar();
    });
    // (b) grupo de radios Sim/Não: mostra quando o valor selecionado bate (padrão "sim").
    Array.prototype.forEach.call(document.querySelectorAll(".condicional[data-depende-nome]"), function (bloco) {
        var nome = bloco.getAttribute("data-depende-nome");
        var valor = bloco.getAttribute("data-depende-valor") || "sim";
        var radios = document.getElementsByName(nome);
        if (!radios.length) return;
        function atualizar() {
            var sel = null;
            Array.prototype.forEach.call(radios, function (r) { if (r.checked) sel = r.value; });
            bloco.classList.toggle("visivel", sel === valor);
        }
        Array.prototype.forEach.call(radios, function (r) { r.addEventListener("change", atualizar); });
        atualizar();
    });

    /* ---------- Preview da foto 3x4 ---------- */
    var inputFoto = document.getElementById("id_av-foto");
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

    /* ---------- Atalhos: copiar pai/mãe para responsável legal ---------- */
    function copiar(prefixo, parentesco) {
        var mapa = {
            nome: "id_av-resp_nome",
            cpf: "id_av-resp_cpf",
            email: "id_av-resp_email",
            whatsapp: "id_av-resp_whatsapp",
        };
        var origem = {
            nome: document.getElementById("id_av-" + prefixo + "_nome"),
            cpf: document.getElementById("id_av-" + prefixo + "_cpf"),
            email: document.getElementById("id_av-" + prefixo + "_email"),
            whatsapp: document.getElementById("id_av-" + prefixo + "_whatsapp"),
        };
        Object.keys(mapa).forEach(function (chave) {
            var destino = document.getElementById(mapa[chave]);
            if (destino && origem[chave]) destino.value = origem[chave].value;
        });
        var campoParentesco = document.getElementById("id_av-resp_parentesco");
        if (campoParentesco && !campoParentesco.value) campoParentesco.value = parentesco;
    }
    var btnPai = document.getElementById("copiarPai");
    var btnMae = document.getElementById("copiarMae");
    if (btnPai) btnPai.addEventListener("click", function () { copiar("pai", "Pai"); });
    if (btnMae) btnMae.addEventListener("click", function () { copiar("mae", "Mãe"); });

    /* ---------- Reaproveitar dados dos responsáveis ---------- */
    // No cadastro de um novo aventureiro, o backend envia os dados de
    // pai/mãe/responsável legal do último cadastro em um <script> JSON.
    var reusarCheck = document.getElementById("reusarResponsaveis");
    var dadosAnterioresEl = document.getElementById("dadosResponsaveisAnteriores");
    if (reusarCheck && dadosAnterioresEl) {
        var dadosAnteriores = {};
        try {
            dadosAnteriores = JSON.parse(dadosAnterioresEl.textContent) || {};
        } catch (e) {
            dadosAnteriores = {};
        }
        var avisoReuso = document.getElementById("avisoReuso");
        reusarCheck.addEventListener("change", function () {
            if (!reusarCheck.checked) {
                if (avisoReuso) avisoReuso.hidden = true;
                return;
            }
            Object.keys(dadosAnteriores).forEach(function (campo) {
                var destino = document.getElementById("id_av-" + campo);
                if (destino) destino.value = dadosAnteriores[campo] || "";
            });
            if (avisoReuso) avisoReuso.hidden = false;
        });
    }

    /* ---------- Revisão final ---------- */
    function valor(id) {
        var el = document.getElementById(id);
        if (!el) return "—";
        if (el.tagName === "SELECT") {
            return el.options[el.selectedIndex] ? el.options[el.selectedIndex].text : "—";
        }
        return el.value ? el.value : "—";
    }
    function marcado(id) {
        var el = document.getElementById(id);
        return el && el.checked ? "Sim" : "Não";
    }
    function assinou(id) {
        var el = document.getElementById(id);
        return el && el.value ? "Assinado ✓" : "Pendente";
    }
    function montarRevisao() {
        var revisao = document.getElementById("revisao");
        if (!revisao) return;
        var itens = [];
        // O usuário só existe no cadastro inicial (não no de novo aventureiro).
        if (document.getElementById("id_conta-username")) {
            itens.push(["Usuário", valor("id_conta-username")]);
        }
        itens = itens.concat([
            ["Nome do aventureiro", valor("id_av-nome_completo")],
            ["Sexo", valor("id_av-sexo")],
            ["Data de nascimento", valor("id_av-data_nascimento")],
            ["CPF do aventureiro", valor("id_av-cpf")],
            ["Responsável legal", valor("id_av-resp_nome")],
            ["CPF do responsável", valor("id_av-resp_cpf")],
            ["WhatsApp do responsável", valor("id_av-resp_whatsapp")],
            ["Declaração médica", assinou("assinatura_declaracao_medica")],
            ["Autorização de imagem", assinou("assinatura_termo_imagem")],
        ]);
        revisao.innerHTML = itens
            .map(function (par) {
                return (
                    '<div class="revisao-item"><strong>' +
                    par[0] +
                    "</strong><span>" +
                    par[1] +
                    "</span></div>"
                );
            })
            .join("");
    }

    /* ---------- Validação de envio (aceites obrigatórios) ---------- */
    // Descobre o índice da etapa que contém um campo (os índices mudam quando
    // a etapa "Conta" não existe, no fluxo de novo aventureiro).
    function indicePasso(id) {
        var el = document.getElementById(id);
        var passo = el ? el.closest(".passo") : null;
        return passo ? passos.indexOf(passo) : -1;
    }
    // As três assinaturas são obrigatórias (substituem os antigos checkboxes).
    var ASSINATURAS = [
        ["assinatura_declaracao_medica", "a declaração médica"],
        ["assinatura_termo_imagem", "a autorização de uso de imagem"],
        ["assinatura_inscricao", "a ficha de inscrição"],
    ];
    form.addEventListener("submit", function (evento) {
        var falta = V ? V.faltantes(form) : [];
        for (var i = 0; i < ASSINATURAS.length; i++) {
            var campo = document.getElementById(ASSINATURAS[i][0]);
            if (campo && !campo.value) falta.push({ el: campo, rotulo: "Assinatura: " + ASSINATURAS[i][1] });
        }
        if (falta.length) {
            evento.preventDefault();
            if (V) V.mostrarAviso(falta);
            var passo = falta[0].el.closest(".passo");
            if (passo) mostrar(passos.indexOf(passo));
        }
    });

    /* ---------- Preenche o termo de imagem com os dados digitados ---------- */
    function preencherTermoImagem() {
        var alvos = document.querySelectorAll("#termoImagem [data-fill]");
        Array.prototype.forEach.call(alvos, function (el) {
            var campo = document.getElementById(el.dataset.fill);
            var texto = campo && campo.value.trim() ? campo.value.trim() : (el.dataset.vazio || "");
            el.textContent = texto;
        });
    }
    // Reaproveita dados já digitados (aventureiro/responsável) no termo de imagem,
    // para não redigitar. Só preenche o que estiver vazio.
    function reaproveitarTermoImagem() {
        var mapa = {
            "id_img-nome_menor": "id_av-nome_completo",
            "id_img-resp_nome": "id_av-resp_nome",
            "id_img-resp_cpf": "id_av-resp_cpf",
            "id_img-resp_endereco": "id_av-endereco",
            "id_img-resp_bairro": "id_av-bairro",
            "id_img-resp_cidade": "id_av-cidade",
            "id_img-resp_estado": "id_av-estado",
        };
        Object.keys(mapa).forEach(function (destinoId) {
            var destino = document.getElementById(destinoId);
            var origem = document.getElementById(mapa[destinoId]);
            if (destino && origem && !destino.value && origem.value) {
                destino.value = origem.value;
            }
        });
    }

    var termoImagem = document.getElementById("termoImagem");
    if (termoImagem) {
        // Atualiza ao digitar nos campos do termo de imagem (prefixo "img").
        Array.prototype.forEach.call(
            document.querySelectorAll('[id^="id_img-"]'),
            function (campo) { campo.addEventListener("input", preencherTermoImagem); }
        );
        preencherTermoImagem();
    }

    // Estado inicial
    mostrar(0);
})();
