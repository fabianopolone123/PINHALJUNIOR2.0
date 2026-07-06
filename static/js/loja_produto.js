/* =========================================================
   Vitrine — configuração de um produto da Loja do Clube:
   - subtotal ao vivo (radios de escolha única + itens com quantidade);
   - aviso "soft" de itens obrigatórios não selecionados (modal): a pessoa
     pode continuar (já possui) ou voltar e revisar;
   - guarda a seleção em andamento no localStorage para não se perder ao
     recarregar (limpa ao adicionar ao carrinho).
   JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    var form = document.getElementById("lojaConfigForm");
    if (!form) return;
    var totalEl = document.getElementById("lojaCfgTotal");
    var pid = (form.querySelector('input[name="produto_id"]') || {}).value || "0";
    var chave = "loja_cfg_" + pid;

    function moeda(v) {
        return "R$ " + v.toFixed(2).replace(".", ",").replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    }

    function calcular() {
        var total = 0;
        form.querySelectorAll('input[type="radio"]:checked').forEach(function (r) {
            total += parseFloat(r.dataset.preco || "0") || 0;
        });
        form.querySelectorAll(".loja-qtd").forEach(function (i) {
            var q = parseInt(i.value, 10) || 0;
            total += q * (parseFloat(i.dataset.preco || "0") || 0);
        });
        if (totalEl) totalEl.textContent = moeda(total);
    }

    form.addEventListener("input", calcular);
    form.addEventListener("change", calcular);

    /* ---- Persistência da seleção em andamento ---- */
    function salvar() {
        try {
            var dados = { radios: {}, itens: {}, av: "" };
            form.querySelectorAll('input[type="radio"]:checked').forEach(function (r) {
                dados.radios[r.name] = r.value;
            });
            form.querySelectorAll(".loja-qtd").forEach(function (i) {
                if ((parseInt(i.value, 10) || 0) > 0) dados.itens[i.name] = i.value;
            });
            var av = form.querySelector('[name="aventureiro_id"]');
            if (av) dados.av = av.value;
            localStorage.setItem(chave, JSON.stringify(dados));
        } catch (e) { /* ignora */ }
    }

    function restaurar() {
        try {
            var raw = localStorage.getItem(chave);
            if (!raw) return;
            var dados = JSON.parse(raw);
            Object.keys(dados.radios || {}).forEach(function (nome) {
                var r = form.querySelector('input[type="radio"][name="' + nome + '"][value="' + dados.radios[nome] + '"]');
                if (r && !r.disabled) r.checked = true;
            });
            Object.keys(dados.itens || {}).forEach(function (nome) {
                var i = form.querySelector('.loja-qtd[name="' + nome + '"]');
                if (i) i.value = dados.itens[nome];
            });
            var av = form.querySelector('select[name="aventureiro_id"]');
            if (av && dados.av) av.value = dados.av;
        } catch (e) { /* ignora */ }
    }

    restaurar();
    calcular();
    form.addEventListener("input", salvar);
    form.addEventListener("change", salvar);

    /* ---- Aviso soft de itens obrigatórios ---- */
    var modal = document.getElementById("modalObrig");
    var modalLista = document.getElementById("modalObrigLista");
    var confirmado = false;

    function faltantes() {
        var faltam = [];
        // Grupos de escolha única obrigatórios sem seleção.
        form.querySelectorAll('.loja-cfg-grupo[data-modo="unica"][data-obrig="1"]').forEach(function (g) {
            var algum = g.querySelector('input[type="radio"]:checked');
            if (!algum) faltam.push(g.dataset.nome || "Item obrigatório");
        });
        // Itens obrigatórios com quantidade zero.
        form.querySelectorAll('.loja-qtd[data-obrig="1"]').forEach(function (i) {
            if ((parseInt(i.value, 10) || 0) <= 0) faltam.push(i.dataset.nome || "Item obrigatório");
        });
        return faltam;
    }

    function abrirModal(lista) {
        if (!modal || !modalLista) return;
        modalLista.innerHTML = "";
        lista.forEach(function (nome) {
            var li = document.createElement("li");
            li.textContent = nome;
            modalLista.appendChild(li);
        });
        modal.hidden = false;
    }
    function fecharModal() { if (modal) modal.hidden = true; }

    form.addEventListener("submit", function (e) {
        if (confirmado) { limparPersistencia(); return; }
        var faltam = faltantes();
        if (faltam.length && modal) {
            e.preventDefault();
            abrirModal(faltam);
        } else {
            limparPersistencia();
        }
    });

    function limparPersistencia() {
        try { localStorage.removeItem(chave); } catch (e) { /* ignora */ }
    }

    if (modal) {
        var btnContinuar = document.getElementById("modalObrigContinuar");
        var btnVoltar = document.getElementById("modalObrigVoltar");
        var btnFechar = document.getElementById("modalObrigFechar");
        if (btnContinuar) btnContinuar.addEventListener("click", function () {
            confirmado = true;
            fecharModal();
            form.submit();
        });
        if (btnVoltar) btnVoltar.addEventListener("click", fecharModal);
        if (btnFechar) btnFechar.addEventListener("click", fecharModal);
        modal.addEventListener("click", function (e) {
            if (e.target === modal) fecharModal();
        });
    }
})();
