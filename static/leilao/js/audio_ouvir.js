/*
 * audio_ouvir.js — escuta a voz do locutor (WHEP / WebRTC).
 *
 * WebRTC **puro**, sem SDK: `RTCPeerConnection` é API nativa do navegador e a
 * negociação WHEP é um `POST` com o SDP no corpo. São ~40 linhas — por isso o
 * projeto não precisa de biblioteca externa nenhuma para ter áudio ao vivo com
 * menos de meio segundo de atraso.
 *
 * O servidor do outro lado é o MediaMTX (um binário Go), que recebe a voz do
 * locutor por WHIP e reparte para todo mundo por WHEP.
 *
 * Detalhe que sempre morde: o navegador **não toca áudio** sem um gesto da
 * pessoa. Quem chama `ligar()` é o botão 🔊 — nunca a carga da página.
 */
window.AudioLeilao = (function () {
    let pc = null;
    let url = "";
    let elemento = null;
    let tentativas = 0;
    let parado = true;

    function log(msg, erro) {
        if (window.console) console[erro ? "warn" : "log"]("[audio] " + msg);
    }

    /* Espera o ICE terminar de juntar candidatos.
       O WHEP clássico manda UM SDP completo (sem trickle), então precisamos do
       gathering fechado antes do POST. O timeout existe porque em rede móvel o
       "complete" às vezes nunca chega — com os candidatos que já temos, conecta. */
    function esperarIce(conexao, limiteMs) {
        return new Promise(function (resolve) {
            if (conexao.iceGatheringState === "complete") return resolve();
            let pronto = false;
            function terminar() {
                if (pronto) return;
                pronto = true;
                conexao.removeEventListener("icegatheringstatechange", checar);
                resolve();
            }
            function checar() {
                if (conexao.iceGatheringState === "complete") terminar();
            }
            conexao.addEventListener("icegatheringstatechange", checar);
            setTimeout(terminar, limiteMs || 2500);
        });
    }

    async function conectar() {
        if (!url || !elemento) return false;
        desligarConexao();
        parado = false;

        try {
            pc = new RTCPeerConnection({ iceServers: [] });
            pc.addTransceiver("audio", { direction: "recvonly" });

            pc.ontrack = function (e) {
                elemento.srcObject = e.streams[0];
                const p = elemento.play();
                if (p && p.catch) p.catch(function () { log("navegador segurou o play", true); });
            };

            pc.oniceconnectionstatechange = function () {
                const s = pc.iceConnectionState;
                if (s === "failed" || s === "disconnected") {
                    log("conexão de áudio caiu (" + s + ")", true);
                    religar();
                }
            };

            const oferta = await pc.createOffer();
            await pc.setLocalDescription(oferta);
            await esperarIce(pc, 2500);

            const resposta = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/sdp" },
                body: pc.localDescription.sdp
            });
            if (!resposta.ok) throw new Error("WHEP respondeu " + resposta.status);

            const sdp = await resposta.text();
            await pc.setRemoteDescription({ type: "answer", sdp: sdp });
            tentativas = 0;
            log("ligado");
            return true;
        } catch (e) {
            log("falhou: " + e.message, true);
            religar();
            return false;
        }
    }

    /* Reconexão com espera crescente: o locutor pode ter parado de falar por um
       instante, e 50 celulares martelando o servidor não ajudariam ninguém. */
    function religar() {
        if (parado) return;
        tentativas++;
        if (tentativas > 8) { log("desisti de reconectar", true); return; }
        const espera = Math.min(1000 * Math.pow(1.7, tentativas), 20000);
        setTimeout(function () { if (!parado) conectar(); }, espera);
    }

    function desligarConexao() {
        if (pc) {
            try { pc.close(); } catch (e) { /* já fechado */ }
            pc = null;
        }
    }

    return {
        ligar: function (endereco, elementoAudio) {
            url = endereco;
            elemento = elementoAudio;
            return conectar();
        },
        desligar: function () {
            parado = true;
            desligarConexao();
            if (elemento) { elemento.srcObject = null; }
        },
        ativo: function () { return !!pc && !parado; }
    };
})();
