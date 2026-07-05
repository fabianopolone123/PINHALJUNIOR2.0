/* =========================================================
   Presença do clube: marcar presente/ausente (JSON, sem recarregar),
   ampliar a foto do aventureiro num modal, e busca em tempo real.
   JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    // ---- Busca ----
    function normalizar(t) {
        return (t || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
            .toLowerCase().replace(/\s+/g, " ").trim();
    }
    var busca = document.getElementById("buscaPres");
    if (busca) {
        var itens = Array.prototype.slice.call(document.querySelectorAll(".pres-busca"));
        itens.forEach(function (el) { el.dataset.busca = normalizar(el.textContent); });
        var vazio = document.getElementById("presVazio");
        var aplicar = function () {
            var termo = normalizar(busca.value), vis = 0;
            itens.forEach(function (el) {
                var ok = !termo || el.dataset.busca.indexOf(termo) !== -1;
                el.classList.toggle("busca-oculto", !ok);
                if (ok) vis++;
            });
            if (vazio) vazio.hidden = vis !== 0;
        };
        busca.addEventListener("input", aplicar);
        busca.addEventListener("keydown", function (e) {
            if (e.key === "Escape") { busca.value = ""; aplicar(); }
        });
    }

    // ---- Marcar presença ----
    var dados = document.getElementById("presDados");
    if (dados) {
        var CSRF = dados.dataset.csrf, URL = dados.dataset.marcarUrl;
        var contador = document.getElementById("presCount");

        document.addEventListener("click", function (e) {
            var btn = e.target.closest(".pres-marcar");
            if (!btn || btn.dataset.enviando) return;
            var novo = btn.getAttribute("aria-pressed") !== "true";
            btn.dataset.enviando = "1"; btn.disabled = true;
            fetch(URL, {
                method: "POST",
                headers: {
                    "X-CSRFToken": CSRF, "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                body: new URLSearchParams({ aventureiro: btn.dataset.av, presente: novo ? "1" : "0" }).toString(),
            })
                .then(function (r) { return r.json().catch(function () { return { ok: false }; }); })
                .then(function (d) {
                    if (!d.ok) {
                        if (window.mostrarToast) window.mostrarToast(d.erro || "Não foi possível marcar.", "error");
                        return;
                    }
                    btn.setAttribute("aria-pressed", d.presente ? "true" : "false");
                    btn.classList.toggle("presente", d.presente);
                    var txt = btn.querySelector(".pres-marcar-txt");
                    if (txt) txt.textContent = d.presente ? "✅ Presente" : "Marcar";
                    if (contador) contador.textContent = d.presentes;
                })
                .catch(function () {
                    if (window.mostrarToast) window.mostrarToast("Falha de conexão.", "error");
                })
                .finally(function () { delete btn.dataset.enviando; btn.disabled = false; });
        });
    }

    // ---- Modal da foto ampliada ----
    var modal = document.getElementById("fotoModal");
    if (modal) {
        var img = document.getElementById("fotoModalImg");
        var titulo = document.getElementById("fotoModalTitulo");
        var fechar = document.getElementById("fotoModalFechar");
        function abrir(src, nome) {
            img.src = src; img.alt = "Foto de " + nome; titulo.textContent = nome;
            modal.hidden = false; document.body.classList.add("modal-aberto");
        }
        function fecharModal() {
            modal.hidden = true; img.src = ""; document.body.classList.remove("modal-aberto");
        }
        document.addEventListener("click", function (e) {
            var fb = e.target.closest(".pres-foto-btn");
            if (fb && fb.dataset.foto) { abrir(fb.dataset.foto, fb.dataset.nome || ""); }
        });
        if (fechar) fechar.addEventListener("click", fecharModal);
        var fundo = false;
        modal.addEventListener("mousedown", function (e) { fundo = e.target === modal; });
        modal.addEventListener("click", function (e) { if (e.target === modal && fundo) fecharModal(); });
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape" && !modal.hidden) fecharModal();
        });
    }
})();
