/* =========================================================
   Pad de assinatura (dedo/mouse) — modal com <canvas>.
   JS puro, sem bibliotecas. Cada documento tem um botão
   [data-action="open-signature" data-signature-target="idDoHidden"],
   um <input type="hidden" data-signature-field> e um bloco de preview
   [data-signature-preview data-signature-for="idDoHidden"].
   O traço é gravado como PNG (data-URL) no hidden e enviado no submit.
   ========================================================= */
(function () {
    "use strict";

    var modal = document.getElementById("signature-modal");
    if (!modal) return;
    var canvas = modal.querySelector("canvas");
    var btnLimpar = modal.querySelector('[data-action="clear-signature"]');
    var btnSalvar = modal.querySelector('[data-action="save-signature"]');
    if (!canvas || !btnLimpar || !btnSalvar) return;

    var ctx = canvas.getContext("2d");
    var desenhando = false;
    var ponteiroAtivo = null;
    var campoAtivo = null;

    // ---- Preview de cada documento ----
    function elementosPreview(idAlvo) {
        var raiz = document.querySelector(
            '[data-signature-preview][data-signature-for="' + idAlvo + '"]'
        );
        return {
            texto: raiz ? raiz.querySelector("[data-signature-preview-text]") : null,
            imagem: raiz ? raiz.querySelector("[data-signature-preview-img]") : null,
            bloco: raiz,
        };
    }

    function renderPreview(campo) {
        if (!campo) return;
        var el = elementosPreview(campo.id);
        var tem = !!campo.value;
        if (el.texto) el.texto.textContent = tem ? "Assinatura registrada ✓" : "Sem assinatura ainda.";
        if (el.imagem) {
            if (tem) {
                el.imagem.src = campo.value;
                el.imagem.hidden = false;
            } else {
                el.imagem.removeAttribute("src");
                el.imagem.hidden = true;
            }
        }
        if (el.bloco) el.bloco.classList.toggle("assinado", tem);
    }

    // ---- Canvas: dimensiona conforme o container (nítido no mobile) ----
    function ajustarCanvas() {
        var wrap = canvas.parentElement;
        var largura = wrap ? wrap.clientWidth : 300;
        var altura = Math.max(160, Math.round(largura * 0.45));
        var dpr = window.devicePixelRatio || 1;
        canvas.width = largura * dpr;
        canvas.height = altura * dpr;
        canvas.style.width = largura + "px";
        canvas.style.height = altura + "px";
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.lineWidth = 2.5;
        ctx.strokeStyle = "#0b3d91";
    }

    function limparCanvas() {
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.restore();
        desenhando = false;
        ponteiroAtivo = null;
    }

    // ---- Abrir / fechar modal ----
    function abrirModal(idAlvo) {
        var campo = document.getElementById(idAlvo);
        if (!campo) return;
        campoAtivo = campo;
        modal.classList.add("visivel");
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("sem-scroll");
        // Dimensiona depois de exibir (o container já tem largura).
        requestAnimationFrame(function () {
            ajustarCanvas();
            limparCanvas();
        });
    }

    function fecharModal() {
        modal.classList.remove("visivel");
        modal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("sem-scroll");
        campoAtivo = null;
    }

    function salvarAssinatura() {
        if (!campoAtivo) return fecharModal();
        campoAtivo.value = canvas.toDataURL("image/png");
        renderPreview(campoAtivo);
        fecharModal();
    }

    function limparAssinatura() {
        limparCanvas();
    }

    // ---- Coordenadas do traço ----
    function coords(evento) {
        var rect = canvas.getBoundingClientRect();
        return { x: evento.clientX - rect.left, y: evento.clientY - rect.top };
    }

    function iniciar(evento) {
        evento.preventDefault();
        desenhando = true;
        ponteiroAtivo = evento.pointerId != null ? evento.pointerId : null;
        var p = coords(evento);
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        if (ponteiroAtivo != null && canvas.setPointerCapture) {
            try { canvas.setPointerCapture(ponteiroAtivo); } catch (e) { /* ignora */ }
        }
    }

    function mover(evento) {
        if (!desenhando) return;
        evento.preventDefault();
        var p = coords(evento);
        ctx.lineTo(p.x, p.y);
        ctx.stroke();
    }

    function parar() {
        if (!desenhando) return;
        desenhando = false;
        if (ponteiroAtivo != null && canvas.releasePointerCapture) {
            try { canvas.releasePointerCapture(ponteiroAtivo); } catch (e) { /* ignora */ }
        }
        ponteiroAtivo = null;
    }

    canvas.addEventListener("pointerdown", iniciar);
    canvas.addEventListener("pointermove", mover);
    canvas.addEventListener("pointerup", parar);
    canvas.addEventListener("pointerleave", parar);
    canvas.addEventListener("pointercancel", parar);
    canvas.addEventListener("contextmenu", function (e) { e.preventDefault(); });

    btnLimpar.addEventListener("click", limparAssinatura);
    btnSalvar.addEventListener("click", salvarAssinatura);

    Array.prototype.forEach.call(
        document.querySelectorAll('[data-action="open-signature"]'),
        function (botao) {
            botao.addEventListener("click", function () {
                var alvo = botao.dataset.signatureTarget;
                if (alvo) abrirModal(alvo);
            });
        }
    );

    Array.prototype.forEach.call(
        modal.querySelectorAll('[data-action="close-signature"]'),
        function (t) { t.addEventListener("click", fecharModal); }
    );

    // Fecha no fundo só com mousedown+click no fundo (padrão do projeto).
    var fundoDown = false;
    modal.addEventListener("mousedown", function (e) { fundoDown = e.target === modal; });
    modal.addEventListener("click", function (e) {
        if (e.target === modal && fundoDown) fecharModal();
        fundoDown = false;
    });
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && modal.classList.contains("visivel")) fecharModal();
    });

    // Estado inicial dos previews (ex.: quando o formulário volta com erro).
    Array.prototype.forEach.call(
        document.querySelectorAll("[data-signature-field]"),
        renderPreview
    );
})();
