/*
 * confete.js — comemoração de quem arremata. Canvas puro, sem biblioteca.
 *
 * Só roda quando alguém ganha um item — é evento raro e curto, então pode ser
 * caprichado sem pesar no celular. O canvas fica com `pointer-events:none`
 * (CSS), então nunca rouba o toque do botão de lance que está atrás.
 *
 * Respeita `prefers-reduced-motion`: quem pediu menos movimento não recebe nada.
 */
window.Confete = (function () {
    const cores = ["#ffd166", "#62c462", "#4a90d9", "#ff6b52", "#ffffff"];
    let rodando = false;

    function reduzido() {
        return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    function soltar(duracao) {
        const canvas = document.getElementById("confete");
        if (!canvas || rodando || reduzido()) return;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        const L = window.innerWidth;
        const A = window.innerHeight;
        canvas.width = L * dpr;
        canvas.height = A * dpr;
        canvas.style.width = L + "px";
        canvas.style.height = A + "px";
        ctx.scale(dpr, dpr);

        const total = L < 480 ? 90 : 150;
        const pecas = [];
        for (let i = 0; i < total; i++) {
            pecas.push({
                x: Math.random() * L,
                y: -20 - Math.random() * A * 0.5,
                l: 6 + Math.random() * 7,
                a: 8 + Math.random() * 8,
                vy: 2 + Math.random() * 3.2,
                vx: -1.2 + Math.random() * 2.4,
                giro: Math.random() * Math.PI,
                vgiro: -0.12 + Math.random() * 0.24,
                cor: cores[(Math.random() * cores.length) | 0]
            });
        }

        rodando = true;
        const fim = performance.now() + (duracao || 3000);

        function quadro(agora) {
            ctx.clearRect(0, 0, L, A);
            let vivos = 0;
            for (let i = 0; i < pecas.length; i++) {
                const p = pecas[i];
                p.x += p.vx;
                p.y += p.vy;
                p.giro += p.vgiro;
                p.vy += 0.035;               // gravidade
                p.vx += Math.sin(p.y / 45) * 0.02;  // balanço do papel caindo
                if (p.y < A + 30) vivos++;

                ctx.save();
                ctx.translate(p.x, p.y);
                ctx.rotate(p.giro);
                ctx.fillStyle = p.cor;
                ctx.fillRect(-p.l / 2, -p.a / 2, p.l, p.a);
                ctx.restore();
            }
            if (vivos > 0 && agora < fim) {
                requestAnimationFrame(quadro);
            } else {
                ctx.clearRect(0, 0, L, A);
                rodando = false;
            }
        }
        requestAnimationFrame(quadro);
    }

    return { soltar: soltar };
})();
