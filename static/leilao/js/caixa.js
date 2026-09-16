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

    ligarBusca("buscaPagamentos", "#listaPagamentos .arremate-linha");

    /* =====================================================================
       Pix do arremate — o que o caixa manda para quem vai pagar depois
       ===================================================================== */
    var modalPix = $("modalPix");
    var pixAtual = null;

    function abrirModalPix() {
        if (!modalPix) return;
        modalPix.hidden = false;
        document.body.classList.add("modal-aberto");
    }

    function fecharModalPix() {
        if (!modalPix) return;
        modalPix.hidden = true;
        document.body.classList.remove("modal-aberto");
    }

    if ($("pixFechar")) $("pixFechar").addEventListener("click", fecharModalPix);

    // Fecha no fundo só com mousedown+click no fundo — não fechar ao arrastar
    // uma seleção de dentro para fora (convenção do projeto).
    if (modalPix) {
        var desceuNoFundo = false;
        modalPix.addEventListener("mousedown", function (e) { desceuNoFundo = e.target === modalPix; });
        modalPix.addEventListener("click", function (e) {
            if (desceuNoFundo && e.target === modalPix) fecharModalPix();
        });
    }

    function buscarPix(id) {
        return fetch(URL_PIX.replace(/0\/pix\/$/, id + "/pix/"), {
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
            if ($("pixItem")) $("pixItem").textContent = "nº " + d.numero + " — " + d.lote;
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
        var modal = modalPix && !modalPix.hidden;
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
            li.querySelectorAll('[data-acao="combinado"], [data-acao="prazo"]')
                .forEach(function (b) { b.remove(); });
        }
        li.classList.add("piscou");
        return true;
    }

    if (URL_STREAM && window.EventSource) {
        var fonte = new EventSource(URL_STREAM);

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

        // Linha NOVA (item batido) ou linha que sumiu (prazo vencido): não dá
        // para remendar a lista pelo evento — a página se refaz.
        fonte.addEventListener("lote_vendido", function () { agendarRecarga(); });
        fonte.addEventListener("arremate_expirado", function () { agendarRecarga(); });
    }
})();
