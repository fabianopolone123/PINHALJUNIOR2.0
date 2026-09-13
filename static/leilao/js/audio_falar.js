/*
 * audio_falar.js — o locutor publica a própria voz (WHIP / WebRTC).
 *
 * Mesmo princípio do `audio_ouvir.js`: `RTCPeerConnection` nativo + um `POST`
 * com o SDP. Nenhuma biblioteca.
 *
 * Os três filtros do `getUserMedia` (cancelamento de eco, supressão de ruído,
 * ganho automático) não são enfeite: o locutor vai estar com o som do ambiente
 * por perto, e sem eles a transmissão vira microfonia na primeira vez que
 * alguém deixar uma caixa de som ligada ao lado.
 */
window.AudioFalar = (function () {
    var pc = null;
    var trilha = null;
    var contexto = null;
    var medidor = null;
    var rodando = false;

    function esperarIce(conexao, limite) {
        return new Promise(function (resolve) {
            if (conexao.iceGatheringState === "complete") return resolve();
            var pronto = false;
            function fim() {
                if (pronto) return;
                pronto = true;
                conexao.removeEventListener("icegatheringstatechange", checar);
                resolve();
            }
            function checar() { if (conexao.iceGatheringState === "complete") fim(); }
            conexao.addEventListener("icegatheringstatechange", checar);
            setTimeout(fim, limite || 2500);
        });
    }

    /* Medidor de nível: o locutor precisa VER que está saindo som. Sem isso, a
       única forma de descobrir que o microfone está mudo é alguém reclamar no
       chat — tarde demais. */
    function ligarMedidor(stream, aoNivel) {
        try {
            var AC = window.AudioContext || window.webkitAudioContext;
            if (!AC || !aoNivel) return;
            contexto = new AC();
            var origem = contexto.createMediaStreamSource(stream);
            var analisador = contexto.createAnalyser();
            analisador.fftSize = 512;
            origem.connect(analisador);
            var buffer = new Uint8Array(analisador.frequencyBinCount);

            medidor = setInterval(function () {
                analisador.getByteTimeDomainData(buffer);
                var soma = 0;
                for (var i = 0; i < buffer.length; i++) {
                    var v = (buffer[i] - 128) / 128;
                    soma += v * v;
                }
                aoNivel(Math.sqrt(soma / buffer.length));
            }, 100);
        } catch (e) {
            /* medidor é conforto, não requisito */
        }
    }

    /* O MediaMTX protege a PUBLICAÇÃO com usuário e senha (quem escuta é
       liberado). Sem este cabeçalho o servidor responde 401 e o locutor fica
       mudo sem entender por quê. A credencial só aparece na página do locutor,
       que já é restrita à equipe. */
    function autorizacao(usuario, senha) {
        if (!usuario) return null;
        return "Basic " + btoa(usuario + ":" + (senha || ""));
    }

    async function iniciar(url, aoNivel, usuario, senha) {
        if (!url) return false;
        parar();
        try {
            var stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                },
                video: false
            });
            trilha = stream;
            ligarMedidor(stream, aoNivel);

            pc = new RTCPeerConnection({ iceServers: [] });
            stream.getAudioTracks().forEach(function (t) { pc.addTrack(t, stream); });

            var oferta = await pc.createOffer();
            await pc.setLocalDescription(oferta);
            await esperarIce(pc, 2500);

            var cabecalhos = { "Content-Type": "application/sdp" };
            var auth = autorizacao(usuario, senha);
            if (auth) cabecalhos["Authorization"] = auth;

            var resposta = await fetch(url, {
                method: "POST",
                headers: cabecalhos,
                body: pc.localDescription.sdp
            });
            if (resposta.status === 401) {
                throw new Error("o servidor de audio recusou o usuario/senha de publicacao");
            }
            if (!resposta.ok) throw new Error("WHIP respondeu " + resposta.status);

            var sdp = await resposta.text();
            await pc.setRemoteDescription({ type: "answer", sdp: sdp });
            rodando = true;
            return true;
        } catch (e) {
            if (window.console) console.warn("[audio-falar] " + e.message);
            parar();
            return false;
        }
    }

    function parar() {
        rodando = false;
        if (medidor) { clearInterval(medidor); medidor = null; }
        if (contexto) { try { contexto.close(); } catch (e) { /* já fechado */ } contexto = null; }
        if (trilha) {
            trilha.getTracks().forEach(function (t) { t.stop(); });
            trilha = null;
        }
        if (pc) { try { pc.close(); } catch (e) { /* já fechado */ } pc = null; }
    }

    return {
        iniciar: iniciar,
        parar: parar,
        ativo: function () { return rodando; }
    };
})();
