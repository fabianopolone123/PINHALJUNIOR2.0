/* =========================================================
   Tela "Loja" (Diretor): alternância de abas (Gerenciar / Loja),
   confirmação de ações destrutivas e atalho para o carrinho.
   JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    var abas = document.querySelectorAll(".loja-aba");
    var paineis = document.querySelectorAll(".loja-painel");

    function ativar(nome) {
        Array.prototype.forEach.call(abas, function (a) {
            a.classList.toggle("ativa", a.dataset.aba === nome);
        });
        Array.prototype.forEach.call(paineis, function (p) {
            p.hidden = p.dataset.painel !== nome;
        });
        try {
            var url = new URL(window.location.href);
            url.searchParams.set("aba", nome);
            window.history.replaceState({}, "", url);
        } catch (e) { /* ignora */ }
    }

    Array.prototype.forEach.call(abas, function (a) {
        a.addEventListener("click", function () { ativar(a.dataset.aba); });
    });

    // Sub-abas da aba "Vendas" (Resumo / Custos / Pedido ao fornecedor / Compras).
    var subAbas = document.querySelectorAll(".loja-subaba");
    var subSecoes = document.querySelectorAll(".loja-subsecao");
    Array.prototype.forEach.call(subAbas, function (a) {
        a.addEventListener("click", function () {
            var nome = a.dataset.sub;
            Array.prototype.forEach.call(subAbas, function (x) {
                x.classList.toggle("ativa", x === a);
            });
            Array.prototype.forEach.call(subSecoes, function (s) {
                s.hidden = s.dataset.subsecao !== nome;
            });
        });
    });

    // Links que apontam para o carrinho trocam para a aba "Loja".
    Array.prototype.forEach.call(
        document.querySelectorAll('a[href="#carrinho"]'),
        function (link) {
            link.addEventListener("click", function () {
                ativar("loja");
            });
        }
    );

    // Se a página abriu com âncora do carrinho, garante a aba certa.
    if (window.location.hash === "#carrinho") {
        ativar("loja");
        var alvo = document.getElementById("carrinho");
        if (alvo) setTimeout(function () { alvo.scrollIntoView({ behavior: "smooth" }); }, 60);
    }
})();

/* Confirmação de ações destrutivas: <form data-confirmar="..."> */
(function () {
    "use strict";
    document.addEventListener("submit", function (e) {
        var form = e.target;
        if (form && form.dataset && form.dataset.confirmar) {
            if (!window.confirm(form.dataset.confirmar)) e.preventDefault();
        }
    });
})();

/* Modal: lançar custo/pagamento da loja (fechamento seguro). */
(function () {
    "use strict";
    var modal = document.getElementById("modalCustoLoja");
    var btn = document.getElementById("btnCustoLoja");
    if (!modal || !btn) return;
    function fechar() { modal.hidden = true; }
    btn.addEventListener("click", function () { modal.hidden = false; });
    Array.prototype.forEach.call(modal.querySelectorAll("[data-fechar]"), function (el) {
        el.addEventListener("click", fechar);
    });
    var fundoDown = false;
    modal.addEventListener("mousedown", function (e) { fundoDown = e.target === modal; });
    modal.addEventListener("click", function (e) {
        if (e.target === modal && fundoDown) fechar();
        fundoDown = false;
    });
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && !modal.hidden) fechar();
    });
})();

/* =========================================================
   Aba Vendas: marcar entrega (fetch/JSON) + busca nas compras.
   ========================================================= */
(function () {
    "use strict";

    function csrf() {
        var m = document.cookie.match(/(?:^|;\s*)pinhaljunior2_csrftoken=([^;]+)/);
        if (m) return m[1];
        var inp = document.querySelector('input[name=csrfmiddlewaretoken]');
        return inp ? inp.value : "";
    }

    function selo(status) {
        if (status === "entregue") return { cls: "entregue", txt: "✅ Entregue" };
        if (status === "parcial") return { cls: "parcial", txt: "◑ Parcial" };
        return { cls: "pendente", txt: "⏳ A entregar" };
    }

    function setToggle(btn, status) {
        var entregue = status === "entregue";
        btn.dataset.entregar = entregue ? "0" : "1";
        btn.textContent = entregue ? "✅ Entregue" : "Entregar";
        btn.className = "loja-entrega-toggle loja-entrega-" + status;
    }

    // Atualiza selo, botão "entregar tudo" e data-pendente de uma compra.
    function atualizarCompra(compraEl, status) {
        if (!compraEl) return;
        var s = compraEl.querySelector(".loja-entrega-selo");
        if (s) {
            var info = selo(status);
            s.className = "loja-entrega-selo loja-entrega-" + info.cls;
            s.textContent = info.txt;
        }
        var tudo = compraEl.querySelector(".loja-entrega-tudo");
        if (tudo) {
            var entregue = status === "entregue";
            tudo.dataset.entregar = entregue ? "0" : "1";
            tudo.textContent = entregue ? "↩ Desfazer entregas" : "✅ Entregar tudo";
            tudo.className = "btn-secundario loja-entrega-tudo loja-entrega-" + status;
        }
        compraEl.dataset.pendente = status === "entregue" ? "0" : "1";
        if (soPendentes && soPendentes.checked) aplicarFiltro();
    }

    // URLs respeitando o prefixo do app (FORCE_SCRIPT_NAME no VPS). Vêm do template
    // via {% url %}; os caminhos fixos são só fallback para o uso local.
    var comprasEl = document.getElementById("lojaComprasLista");
    var ENTREGA_URL = (comprasEl && comprasEl.dataset.entregaUrl) || "/loja/entrega/";
    var ENTREGA_COMPRA_URL = (comprasEl && comprasEl.dataset.entregaCompraUrl) || "/loja/entrega/compra/";

    function pedir(corpo) {
        return fetch(corpo.compra_id ? ENTREGA_COMPRA_URL : ENTREGA_URL, {
            method: "POST",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": csrf(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: Object.keys(corpo).map(function (k) {
                return k + "=" + encodeURIComponent(corpo[k]);
            }).join("&"),
        }).then(function (r) { return r.json(); });
    }

    document.addEventListener("click", function (e) {
        // Entrega de um item.
        var btn = e.target.closest(".loja-entrega-toggle");
        if (btn) {
            btn.disabled = true;
            pedir({ item_id: btn.dataset.item, entregar: btn.dataset.entregar === "1" ? "1" : "0" })
                .then(function (d) {
                    if (!d || !d.ok) throw new Error();
                    setToggle(btn, d.status);
                    atualizarCompra(btn.closest(".loja-compra"), d.compra_status);
                    btn.disabled = false;
                })
                .catch(function () {
                    if (window.mostrarToast) window.mostrarToast("Não foi possível atualizar a entrega.", "error");
                    btn.disabled = false;
                });
            return;
        }
        // Entregar tudo (ou desfazer) de uma compra.
        var tudo = e.target.closest(".loja-entrega-tudo");
        if (tudo) {
            tudo.disabled = true;
            var alvo = tudo.dataset.entregar === "1" ? "1" : "0";
            pedir({ compra_id: tudo.dataset.compra, entregar: alvo })
                .then(function (d) {
                    if (!d || !d.ok) throw new Error();
                    var compraEl = tudo.closest(".loja-compra");
                    (d.itens || []).forEach(function (it) {
                        var b = compraEl.querySelector('.loja-entrega-toggle[data-item="' + it.id + '"]');
                        if (b) setToggle(b, it.status);
                    });
                    atualizarCompra(compraEl, d.compra_status);
                    if (window.mostrarToast) {
                        window.mostrarToast(alvo === "1" ? "Pedido entregue ✅" : "Entregas desfeitas", alvo === "1" ? "success" : "info");
                    }
                    tudo.disabled = false;
                })
                .catch(function () {
                    if (window.mostrarToast) window.mostrarToast("Não foi possível atualizar as entregas.", "error");
                    tudo.disabled = false;
                });
        }
    });

    // Busca + filtro "só a entregar" + chips de produto.
    var busca = document.getElementById("lojaBuscaCompras");
    var soPendentes = document.getElementById("lojaSoPendentes");
    var lista = document.getElementById("lojaComprasLista");
    var vazio = document.querySelector(".loja-busca-vazio");
    function normal(s) {
        return (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    }
    function aplicarFiltro() {
        if (!lista) return;
        var q = normal(busca ? busca.value.trim() : "");
        var pend = soPendentes && soPendentes.checked;
        var achou = 0;
        Array.prototype.forEach.call(lista.querySelectorAll(".loja-compra"), function (c) {
            var okBusca = !q || normal(c.dataset.busca).indexOf(q) !== -1;
            var okPend = !pend || c.dataset.pendente === "1";
            var ok = okBusca && okPend;
            c.hidden = !ok;
            if (ok) achou++;
        });
        if (vazio) vazio.hidden = achou !== 0;
    }
    if (busca) busca.addEventListener("input", aplicarFiltro);
    if (soPendentes) soPendentes.addEventListener("change", aplicarFiltro);
})();
