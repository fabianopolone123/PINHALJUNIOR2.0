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

    var total = passos.length;
    var atual = 0; // índice (0-based)

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

        if (ultimo) montarRevisao();

        // Rola para o topo do card
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    btnProximo.addEventListener("click", function () {
        mostrar(atual + 1);
    });
    btnVoltar.addEventListener("click", function () {
        mostrar(atual - 1);
    });

    // Permite clicar num ponto de etapa já visitado/adiante
    pontos.forEach(function (ponto, i) {
        ponto.addEventListener("click", function () {
            mostrar(i);
        });
    });

    /* ---------- Campos condicionais (aparecem ao marcar "Sim") ---------- */
    var condicionais = Array.prototype.slice.call(document.querySelectorAll(".condicional"));
    condicionais.forEach(function (bloco) {
        var idControle = bloco.getAttribute("data-depende");
        var controle = document.getElementById(idControle);
        if (!controle) return;

        function atualizar() {
            bloco.classList.toggle("visivel", controle.checked);
        }
        controle.addEventListener("change", atualizar);
        atualizar(); // estado inicial (útil quando o form volta com erro)
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
    function montarRevisao() {
        var revisao = document.getElementById("revisao");
        if (!revisao) return;
        var itens = [
            ["Usuário", valor("id_conta-username")],
            ["Nome do aventureiro", valor("id_av-nome_completo")],
            ["Sexo", valor("id_av-sexo")],
            ["Data de nascimento", valor("id_av-data_nascimento")],
            ["CPF do aventureiro", valor("id_av-cpf")],
            ["Responsável legal", valor("id_av-resp_nome")],
            ["CPF do responsável", valor("id_av-resp_cpf")],
            ["WhatsApp do responsável", valor("id_av-resp_whatsapp")],
            ["Declaração médica aceita", marcado("id_av-declaracao_medica_aceita")],
            ["Autorização de imagem aceita", marcado("id_av-autorizacao_imagem_aceita")],
        ];
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
    form.addEventListener("submit", function (evento) {
        var decl = document.getElementById("id_av-declaracao_medica_aceita");
        var img = document.getElementById("id_av-autorizacao_imagem_aceita");
        if (decl && !decl.checked) {
            evento.preventDefault();
            mostrar(4); // etapa 5 (declaração)
            alert("É necessário aceitar a declaração médica para finalizar.");
            return;
        }
        if (img && !img.checked) {
            evento.preventDefault();
            mostrar(5); // etapa 6 (autorização de imagem)
            alert("É necessário aceitar a autorização de uso de imagem para finalizar.");
            return;
        }
    });

    // Estado inicial
    mostrar(0);
})();
