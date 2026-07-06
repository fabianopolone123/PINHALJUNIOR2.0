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

/* =========================================================
   Aba Vendas: marcar entrega (fetch/JSON) + busca nas compras.
   ========================================================= */
(function () {
    "use strict";

    function csrf() {
        var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        if (m) return m[1];
        var inp = document.querySelector('input[name=csrfmiddlewaretoken]');
        return inp ? inp.value : "";
    }

    function selo(status) {
        if (status === "entregue") return { cls: "entregue", txt: "✅ Entregue" };
        if (status === "parcial") return { cls: "parcial", txt: "◑ Parcial" };
        return { cls: "pendente", txt: "⏳ A entregar" };
    }

    function atualizarSeloCompra(compraEl, status) {
        if (!compraEl) return;
        var s = compraEl.querySelector(".loja-entrega-selo");
        if (!s) return;
        var info = selo(status);
        s.className = "loja-entrega-selo loja-entrega-" + info.cls;
        s.textContent = info.txt;
    }

    document.addEventListener("click", function (e) {
        var btn = e.target.closest(".loja-entrega-toggle, .loja-entregar-btn");
        if (!btn) return;
        var itemId = btn.dataset.item;
        var entregar = btn.dataset.entregar === "1" ? "1" : "0";
        btn.disabled = true;

        fetch("/loja/entrega/", {
            method: "POST",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": csrf(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: "item_id=" + encodeURIComponent(itemId) + "&entregar=" + entregar,
        })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (!d || !d.ok) {
                    if (window.mostrarToast) window.mostrarToast("Não foi possível atualizar a entrega.", "error");
                    btn.disabled = false;
                    return;
                }
                if (btn.classList.contains("loja-entregar-btn")) {
                    // Item da lista "A entregar": some ao entregar.
                    var li = btn.closest(".loja-entregar-item");
                    if (li) li.remove();
                    if (window.mostrarToast) window.mostrarToast("Entrega registrada ✅", "success");
                } else {
                    // Toggle dentro da compra.
                    var entregue = d.status === "entregue";
                    btn.dataset.entregar = entregue ? "0" : "1";
                    btn.textContent = entregue ? "✅ Entregue" : "Entregar";
                    btn.className = "loja-entrega-toggle loja-entrega-" + d.status;
                    atualizarSeloCompra(btn.closest(".loja-compra"), d.compra_status);
                }
                btn.disabled = false;
            })
            .catch(function () {
                if (window.mostrarToast) window.mostrarToast("Falha de conexão.", "error");
                btn.disabled = false;
            });
    });

    // Busca nas compras.
    var busca = document.getElementById("lojaBuscaCompras");
    var lista = document.getElementById("lojaComprasLista");
    if (busca && lista) {
        var vazio = document.querySelector(".loja-busca-vazio");
        function normal(s) {
            return (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
        }
        busca.addEventListener("input", function () {
            var q = normal(busca.value.trim());
            var achou = 0;
            Array.prototype.forEach.call(lista.querySelectorAll(".loja-compra"), function (c) {
                var ok = !q || normal(c.dataset.busca).indexOf(q) !== -1;
                c.hidden = !ok;
                if (ok) achou++;
            });
            if (vazio) vazio.hidden = achou !== 0;
        });
    }
})();
