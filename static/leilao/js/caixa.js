/*
 * caixa.js — pagamentos e entrega.
 *
 * **O pagamento chega sozinho.** Antes esta tela era estática de propósito, e o
 * caixa só via "Pago" depois de apertar F5 — na prática ele ficava recarregando
 * a página para saber se o Pix tinha caído, ou pior, não recarregava e cobrava
 * quem já havia pagado. Agora ela ouve o mesmo stream (SSE) do pregão.
 *
 * Duas regras do redesenho, aprendidas aqui:
 *
 * 1. **A linha muda na hora** (selo, cor, botões) — é o retorno que o caixa
 *    precisa ver no segundo em que acontece.
 * 2. **A recarga é adiada** enquanto alguém está digitando ou com o modal
 *    aberto: o item pago precisa aparecer na aba "A entregar" e os totais têm
 *    de fechar, mas nada disso justifica apagar o "quem recebeu" no meio de uma
 *    frase. Não dando, entra o botão 🔄 no topo.
 *
 * Toda ação vai para o MESMO POST da equipe (`/equipe/acao/`), que decide no
 * servidor se o papel da pessoa permite. Esconder botão não protege nada.
 */
(function () {
    "use strict";

    function $(id) { return document.getElementById(id); }

    var dados = $("dadosMesa");
    if (!dados) return;

    var CSRF = dados.dataset.csrf;
    var URL_ACAO = dados.dataset.acaoUrl;
    var URL_PIX = dados.dataset.pixUrl || "";
    var URL_STREAM = dados.dataset.stream || "";

    function toast(msg, tipo) {
        if (window.mostrarToast) window.mostrarToast(msg, tipo || "info");
    }

    function acao(corpo) {
        // O leilão DESTA tela vai junto: sem ele o servidor adivinhava ("o que
        // está no ar") e o botão agia no leilão errado.
        if (dados.dataset.leilao && corpo.leilao === undefined) corpo.leilao = dados.dataset.leilao;
        return fetch(URL_ACAO, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": CSRF,
                "X-Requested-With": "XMLHttpRequest"
            },
            body: JSON.stringify(corpo)
        })
            .then(function (r) { return r.json().catch(function () { return {}; }); })
            .catch(function () {
                toast("Sem conexão com o servidor.", "error");
                return null;
            });
    }

    /* ---- Abas ----
       A aba fica guardada na sessão do navegador porque esta tela **recarrega
       sozinha** quando um pagamento cai: sem isso, quem montou as rotas de
       entrega era jogado de volta para "Pagamentos" no meio do trabalho.
       `sessionStorage` pode estourar (aba anônima, cookies bloqueados), então
       toda leitura e escrita vai em try/catch — a tela precisa funcionar sem. */
    var CHAVE_ABA = "leilao_caixa_aba";

    function lembrarAba(nome) {
        try { sessionStorage.setItem(CHAVE_ABA, nome); } catch (e) { /* sem storage */ }
    }

    function abaLembrada() {
        try { return sessionStorage.getItem(CHAVE_ABA); } catch (e) { return null; }
    }

    function mostrarAba(nome) {
        var botao = document.querySelector('.mesa-aba[data-aba="' + nome + '"]');
        if (!botao) return false;
        document.querySelectorAll(".mesa-aba").forEach(function (x) { x.classList.remove("ativa"); });
        botao.classList.add("ativa");
        document.querySelectorAll(".mesa-secao").forEach(function (s) {
            s.hidden = s.dataset.secao !== nome;
            s.classList.toggle("ativa", !s.hidden);
        });
        return true;
    }

    document.querySelectorAll(".mesa-aba").forEach(function (b) {
        b.addEventListener("click", function () {
            mostrarAba(b.dataset.aba);
            lembrarAba(b.dataset.aba);
        });
    });

    // Quem acabou de pedir a divisão das entregas está olhando as rotas: a
    // página volta nelas, não na primeira aba.
    var guardada = abaLembrada();
    if (window.location.search.indexOf("entregadores=") !== -1) {
        mostrarAba("entregar");
        lembrarAba("entregar");
    } else if (guardada) {
        mostrarAba(guardada);
    }

    /* ---- Ações ---- */
    document.addEventListener("click", function (e) {
        var alvo = e.target.closest("[data-acao]");
        if (!alvo) return;

        var corpo = { acao: alvo.dataset.acao, arremate: alvo.dataset.arremate };

        if (alvo.dataset.minutos) corpo.minutos = alvo.dataset.minutos;

        if (alvo.dataset.acao === "pago") {
            if (!window.confirm("Confirmar que este item foi pago?")) return;
        }

        if (alvo.dataset.acao === "combinado") {
            // O combinado é o registro do que foi falado — sem ele, daqui a uma
            // hora ninguém lembra o que a pessoa disse.
            var obs = window.prompt(
                "O que ficou combinado? (ex.: paga amanhã de manhã, vai passar no clube)",
                ""
            );
            if (obs === null) return;   // desistiu
            corpo.observacao = obs;
        }

        if (alvo.dataset.acao === "entregue") {
            if (alvo.dataset.desfazer) {
                if (!window.confirm("Desmarcar esta entrega?")) return;
                corpo.desfazer = true;
            } else {
                // A observação fica na linha do item (quem recebeu, rastreio).
                var linha = alvo.closest(".entrega");
                var campo = linha ? linha.querySelector(".entrega-obs") : null;
                if (campo) corpo.observacao = campo.value;
            }
        }

        alvo.disabled = true;
        acao(corpo).then(function (d) {
            if (!d) { alvo.disabled = false; return; }
            toast(d.msg || "Pronto.", d.ok ? "success" : "error");
            if (d.ok) window.location.reload();
            else alvo.disabled = false;
        });
    });

    /* ---- Busca (padrão do usuarios.js: sem acento, sem caixa) ---- */
    function ligarBusca(campoId, seletor) {
        var campo = $(campoId);
        if (!campo) return;
        campo.addEventListener("input", function () {
            var termo = campo.value.normalize("NFD").replace(/[̀-ͯ]/g, "")
                .toLowerCase().trim();
            document.querySelectorAll(seletor).forEach(function (li) {
                var alvo = (li.dataset.busca || "").normalize("NFD")
                    .replace(/[̀-ͯ]/g, "").toLowerCase();
                // Esconder com CLASSE, não com `hidden`: item `display:flex`
                // ignora o [hidden] do navegador (armadilha já registrada).
                li.classList.toggle("busca-oculto", termo !== "" && alvo.indexOf(termo) === -1);
            });
        });
    }

    // A lista de pagamentos agora é de PESSOAS, não de itens.
    ligarBusca("buscaPagamentos", "#listaPagamentos .conta-linha");

    /* =====================================================================
       Pix do arremate — o que o caixa manda para quem vai pagar depois
       ===================================================================== */
    var modalPix = $("modalPix");
    var pixAtual = null;

    // O comportamento do modal (X, fundo com mousedown+click, Esc, travar o
    // scroll) mora no `modal.js`, num lugar só. Estava copiado em cada arquivo
    // que abria uma janela, e a regra do fundo é fácil de esquecer ao
    // reescrever.
    var jm = window.ModalLeilao;
    var pixModal = jm ? jm.ligar(modalPix) : { abrir: function () {}, fechar: function () {} };
    function abrirModalPix() { pixModal.abrir(); }
    function fecharModalPix() { pixModal.fechar(); }

    if ($("pixFechar")) $("pixFechar").addEventListener("click", fecharModalPix);

    // O `id` aqui é o da PESSOA: a cobrança é uma só, pelo total do que ela
    // levou. Era por arremate, e quem levou três itens via três botões que
    // devolviam o mesmo código com valores diferentes escritos ao lado.
    function buscarPix(id) {
        // O leilão DESTA tela vai junto: a pessoa pode dever outro leilão, e
        // o Pix dela sai primeiro pelo mais antigo (revisão de 26/09).
        var url = URL_PIX.replace(/0\/pix\/$/, id + "/pix/") +
            (dados.dataset.leilao ? "?leilao=" + encodeURIComponent(dados.dataset.leilao) : "");
        return fetch(url, {
            headers: { "X-Requested-With": "XMLHttpRequest" }
        }).then(function (r) { return r.json(); });
    }

    document.addEventListener("click", function (e) {
        var alvo = e.target.closest("[data-pix]");
        if (!alvo) return;
        var id = alvo.dataset.pix;
        alvo.disabled = true;
        buscarPix(id).then(function (d) {
            alvo.disabled = false;
            if (!d || !d.ok) {
                toast((d && d.msg) || "Não consegui pegar o Pix agora.", "error");
                return;
            }
            pixAtual = d;
            // O que a pessoa deve, e por quê: um item nomeado, ou a contagem
            // deles. O VALOR é sempre o total — é o que o código cobra.
            if ($("pixItem")) {
                var itens = d.itens || [];
                $("pixItem").textContent = itens.length === 1
                    ? d.nome + " · nº " + itens[0].numero + " — " + itens[0].nome
                    : d.nome + " · " + itens.length + " itens";
            }
            if ($("pixValor")) $("pixValor").textContent = "R$ " + d.valor;
            if ($("pixCodigo")) $("pixCodigo").value = d.copia_e_cola;
            var wa = $("pixWhatsapp");
            if (wa) {
                if (d.whatsapp) {
                    wa.href = d.whatsapp + "?text=" + encodeURIComponent(d.texto);
                    wa.hidden = false;
                } else {
                    wa.hidden = true;
                }
            }
            abrirModalPix();
        }).catch(function () {
            alvo.disabled = false;
            toast("Sem conexão com o servidor.", "error");
        });
    });

    if ($("pixCopiar")) {
        $("pixCopiar").addEventListener("click", function () {
            if (!pixAtual) return;
            var campo = $("pixCodigo");
            function pronto() {
                toast("Código Pix copiado!", "success");
            }
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(pixAtual.copia_e_cola).then(pronto).catch(function () {
                    campo.select();
                    document.execCommand("copy");
                    pronto();
                });
            } else {
                campo.select();
                document.execCommand("copy");
                pronto();
            }
        });
    }

    /* =====================================================================
       Tempo real: o pagamento chega sozinho
       ===================================================================== */
    var recarregaAgendada = null;

    function ocupado() {
        // Digitando (o "quem recebeu" da entrega) ou com o Pix aberto na tela:
        // recarregar aqui apagaria o trabalho de quem está no meio dele.
        var foco = document.activeElement;
        var digitando = foco && /^(INPUT|TEXTAREA|SELECT)$/.test(foco.tagName);
        // As TRÊS janelas contam — antes só a do Pix, e a recarga fechava a
        // conta que o caixa estava lendo ou apagava o motivo da devolução.
        var modal = [modalPix, $("modalConta"), $("modalDevolver")].some(function (m) {
            return m && !m.hidden;
        });
        return Boolean(digitando || modal);
    }

    function mostrarBotaoAtualizar() {
        if ($("avisoNovidade")) return;
        var barra = document.createElement("button");
        barra.id = "avisoNovidade";
        barra.type = "button";
        barra.className = "aviso-novidade";
        barra.textContent = "🔄 Há novidades — atualizar";
        barra.addEventListener("click", function () { window.location.reload(); });
        document.body.appendChild(barra);
    }

    function agendarRecarga() {
        if (recarregaAgendada) return;
        recarregaAgendada = setTimeout(function () {
            recarregaAgendada = null;
            if (ocupado()) {
                mostrarBotaoAtualizar();
                return;
            }
            window.location.reload();
        }, 1400);
    }

    function pintarLinha(id, situacao, rotulo) {
        var li = $("arremate" + id);
        if (!li) return false;
        // Reescrever `className` inteiro apagava o `busca-oculto`: a linha
        // filtrada pela busca voltava a aparecer sozinha quando o pagamento
        // dela caía.
        var oculto = li.classList.contains("busca-oculto");
        li.className = "arremate-linha " + situacao + (oculto ? " busca-oculto" : "");
        var selo = li.querySelector("[data-selo]");
        if (selo) {
            selo.className = "selo selo-" + situacao;
            selo.textContent = rotulo;
        }
        if (situacao === "pago") {
            // Os botões de cobrança somem na hora: insistir com quem acabou de
            // pagar é o erro que esta tela existe para evitar.
            li.querySelectorAll("[data-acao], [data-pix]").forEach(function (b) { b.remove(); });
        } else if (situacao === "combinado") {
            // O "vai pagar depois" já foi dado, e o prazo deixou de correr.
            // Deixar os dois botões de pé convida um segundo clique.
            li.querySelectorAll('[data-acao="combinado"]')
                .forEach(function (b) { b.remove(); });
        }
        li.classList.add("piscou");
        return true;
    }

    if (URL_STREAM && window.EventSource) {
        var fonte = window.FonteViva ? window.FonteViva.abrir(URL_STREAM) : new EventSource(URL_STREAM);

        fonte.addEventListener("pagamento", function (e) {
            var d = JSON.parse(e.data || "{}");
            pintarLinha(d.arremate, "pago", "Pago");
            toast("💰 Pagamento confirmado: " + (d.lote || "item"), "success");
            agendarRecarga();
        });

        fonte.addEventListener("arremate_combinado", function (e) {
            var d = JSON.parse(e.data || "{}");
            pintarLinha(d.arremate, "combinado", "Combinado — vai pagar depois");
            // Pode ter sido OUTRA pessoa do caixa que combinou: os totais
            // fecham na recarga.
            agendarRecarga();
        });

        // Linha NOVA (item batido): não dá para remendar a lista pelo evento —
        // a página se refaz. (O `arremate_expirado` saiu com o prazo, em
        // 21/09: nada mais publica esse evento.)
        fonte.addEventListener("lote_vendido", function () { agendarRecarga(); });
    }
    /* =====================================================================
       A conta de UMA pessoa — o pagamento é dela, não do item
       ===================================================================== */
    var modalConta = jm ? jm.ligar($("modalConta")) : null;

    function abrirConta(id) {
        var fonte = document.getElementById("conta-detalhe-" + id);
        var corpo = $("contaCorpo");
        if (!fonte || !corpo || !modalConta) return;
        // Clona do que o SERVIDOR já mandou pronto: sem `fetch`, o modal abre
        // igual com a conexão ruim de um salão de festas. Mesmo padrão do
        // `#detalhesFonte` da tela "Usuários" do clube.
        corpo.innerHTML = "";
        corpo.appendChild(fonte.cloneNode(true));
        corpo.firstChild.removeAttribute("id");   // ids duplicados no documento
        var titulo = $("contaTitulo");
        if (titulo) titulo.textContent = fonte.dataset.titulo || "Conta";
        modalConta.abrir();
    }

    document.addEventListener("click", function (e) {
        var alvo = e.target.closest("[data-abrir-conta]");
        if (!alvo) return;
        abrirConta(alvo.dataset.abrirConta);
    });

    /* "Copiar dados": o texto vem PRONTO do servidor (`ficha_texto`), numa
       textarea da própria ficha — procurada a partir do botão, porque o
       conteúdo do modal é clonado e ids se repetiriam. */
    document.addEventListener("click", function (e) {
        var botao = e.target.closest("[data-copiar-ficha]");
        if (!botao) return;
        var caixaFicha = botao.closest(".conta-pessoa");
        var fonte = caixaFicha && caixaFicha.querySelector(".copiar-fonte");
        if (!fonte) return;
        var texto = fonte.value;
        function pronto() { toast("Dados copiados.", "success"); }
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(texto).then(pronto).catch(function () { copiarNaMarra(texto, pronto); });
        } else {
            copiarNaMarra(texto, pronto);
        }
    });

    function copiarNaMarra(texto, pronto) {
        // Cópia de reserva: precisa de um campo REAL na página (não `hidden`).
        var ta = document.createElement("textarea");
        ta.value = texto;
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        var ok = false;
        try { ok = document.execCommand("copy"); } catch (erro) { ok = false; }
        ta.remove();
        // `execCommand` devolve `false` quando não copiou (acesso fora de
        // HTTPS, navegador que recusa): dizer "copiado" aí mandava o caixa
        // colar texto vazio no WhatsApp de quem entrega.
        if (ok) pronto();
        else toast("Não consegui copiar — selecione o texto e copie na mão.", "error");
    }

    /* =====================================================================
       Voltar o item ao leilão — com MOTIVO
       ===================================================================== */
    var modalDevolver = jm ? jm.ligar($("modalDevolver")) : null;
    var devolvendo = null;

    document.addEventListener("click", function (e) {
        var alvo = e.target.closest("[data-devolver]");
        if (!alvo || !modalDevolver) return;
        devolvendo = alvo.dataset.devolver;
        if ($("devolverItem")) $("devolverItem").textContent = alvo.dataset.item || "";
        // O aviso de "já pagou" muda o significado do botão: não é estorno, é
        // doação. Quem aperta precisa ler isso ANTES.
        var aviso = $("devolverAvisoPago");
        if (aviso) aviso.hidden = alvo.dataset.pago !== "1";
        if ($("devolverMotivo")) $("devolverMotivo").value = "";
        modalDevolver.abrir();
    });

    if ($("devolverConfirmar")) {
        $("devolverConfirmar").addEventListener("click", function () {
            if (!devolvendo) return;
            var campo = $("devolverMotivo");
            var motivo = campo ? campo.value.trim() : "";
            if (!motivo) {
                // O servidor recusa igual; isto só evita a ida e volta.
                toast("Escreva por que o item está voltando ao leilão.", "error");
                if (campo) campo.focus();
                return;
            }
            var botao = this;
            botao.disabled = true;
            acao({ acao: "devolver", arremate: devolvendo, motivo: motivo }).then(function (d) {
                botao.disabled = false;
                if (!d || !d.ok) return;
                if (modalDevolver) modalDevolver.fechar();
                if (modalConta) modalConta.fechar();
                // A conta da pessoa, os totais e a aba "A entregar" mudaram
                // todos de uma vez: a página se refaz.
                agendarRecarga();
            }).catch(function () { botao.disabled = false; });
        });
    }
})();
