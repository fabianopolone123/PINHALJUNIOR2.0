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
    // MUDO: o microfone para de mandar voz, mas a transmissão continua de pé.
    // É o jeito certo de pausar: parar e voltar derruba a conexão de TODOS os
    // ouvintes, que levam alguns segundos para reconectar; no mudo ninguém
    // perde nada, e o som volta no mesmo instante em que o locutor desmuta.
    var mudoAgora = false;
    var aoCair = null;
    var vigiaQueda = null;
    // Cada `iniciar` ganha um número; só o da vez pode mexer no estado do
    // módulo. Duas ligações ao mesmo tempo acontecem de verdade (uma religação
    // automática a caminho + o locutor apertando Parar e Transmitir), e antes
    // a que perdia a vez derrubava a outra no `catch` — ou deixava o microfone
    // de uma delas aberto e dois publicadores no mesmo caminho do servidor.
    var geracao = 0;

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

    /* "No ar" só quando a conexão está DE PÉ. O `setRemoteDescription` volta
       antes de o ICE/DTLS terminar: numa rede que passa o POST (TCP) e barra a
       mídia (UDP), a mesa dizia "No ar", avisava a sala inteira para
       reconectar, caía ~30 s depois e recomeçava — em laço (revisão de 26/09).
       Polling e não evento: é o mesmo em todo navegador. */
    function esperarConectar(conexao, limite) {
        return new Promise(function (resolve) {
            var inicio = Date.now();
            var vigia = setInterval(function () {
                var s = conexao.connectionState;
                if (s === "connected") { clearInterval(vigia); resolve(true); }
                else if (s === "failed" || s === "closed" || Date.now() - inicio > limite) {
                    clearInterval(vigia); resolve(false);
                }
            }, 100);
        });
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
        var minha = ++geracao;
        var stream = null;
        var conexao = null;
        // Perdeu a vez para outra chamada (ou para um Parar): limpa SÓ o que
        // é desta chamada e sai sem tocar no estado do módulo.
        function superada() {
            if (minha === geracao) return false;
            if (stream) stream.getTracks().forEach(function (t) { t.stop(); });
            if (conexao) { try { conexao.close(); } catch (e) { /* já fechada */ } }
            return true;
        }
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                },
                video: false
            });
            if (superada()) return false;
            trilha = stream;
            aplicarMudo();
            ligarMedidor(stream, aoNivel);
            // O MICROFONE que termina (Bluetooth/USB que desconecta, bateria,
            // ligação telefônica tomando o microfone): a conexão segue
            // "connected" e ninguém ouve nada — a mesa dizia "No ar". Agora é
            // queda, e a religação refaz o `getUserMedia` (revisão de 26/09).
            stream.getAudioTracks().forEach(function (t) {
                t.onended = function () {
                    if (minha === geracao && rodando) caiu("microfone");
                };
            });

            conexao = new RTCPeerConnection({ iceServers: [] });
            pc = conexao;
            stream.getAudioTracks().forEach(function (t) { conexao.addTrack(t, stream); });

            /* A transmissão do PRÓPRIO locutor também cai (celular bloqueado,
               Wi-Fi que oscila) — e antes nada avisava: a mesa seguia dizendo
               "🔴 No ar" com ninguém ouvindo. `disconnected` pisca em soluço de
               rede, então espera 4 s antes de dar como caída; `failed` é
               definitivo. Só vale para a conexão viva (`pc === conexao`): o
               `close()` do parar dispara `closed`, e isso não é queda. */
            conexao.onconnectionstatechange = function () {
                if (pc !== conexao || !rodando) return;
                var s = conexao.connectionState;
                clearTimeout(vigiaQueda);
                if (s === "failed") {
                    caiu(s);
                } else if (s === "disconnected") {
                    vigiaQueda = setTimeout(function () {
                        if (pc === conexao && rodando && conexao.connectionState !== "connected") caiu(s);
                    }, 4000);
                }
            };

            var oferta = await conexao.createOffer();
            if (superada()) return false;
            await conexao.setLocalDescription(oferta);
            await esperarIce(conexao, 2500);
            if (superada()) return false;

            var cabecalhos = { "Content-Type": "application/sdp" };
            var auth = autorizacao(usuario, senha);
            if (auth) cabecalhos["Authorization"] = auth;

            // Tempo máximo: sem resposta do servidor de áudio, o botão
            // Transmitir ficava travado até o proxy desistir (60 s).
            var controle = window.AbortController ? new AbortController() : null;
            var relogio = controle ? setTimeout(function () { controle.abort(); }, 15000) : null;
            var resposta;
            try {
                resposta = await fetch(url, {
                    method: "POST",
                    headers: cabecalhos,
                    body: conexao.localDescription.sdp,
                    signal: controle ? controle.signal : undefined
                });
            } finally {
                if (relogio) clearTimeout(relogio);
            }
            if (superada()) return false;
            if (resposta.status === 401) {
                throw new Error("o servidor de audio recusou o usuario/senha de publicacao");
            }
            if (!resposta.ok) throw new Error("WHIP respondeu " + resposta.status);

            var sdp = await resposta.text();
            if (superada()) return false;
            await conexao.setRemoteDescription({ type: "answer", sdp: sdp });
            if (superada()) return false;
            var conectou = await esperarConectar(conexao, 12000);
            if (superada()) return false;
            if (!conectou) throw new Error("a conexão de voz não fechou (rede barrando a mídia?)");
            rodando = true;
            return true;
        } catch (e) {
            if (window.console) console.warn("[audio-falar] " + e.message);
            // Só derruba o estado do módulo se esta ainda é a chamada da vez;
            // senão, limpa só o que é dela (a outra segue viva).
            if (!superada()) parar();
            return false;
        }
    }

    function caiu(motivo) {
        rodando = false;
        if (aoCair) aoCair(motivo);
    }

    function aplicarMudo() {
        if (!trilha) return;
        trilha.getAudioTracks().forEach(function (t) { t.enabled = !mudoAgora; });
    }

    function parar() {
        geracao++;          // qualquer `iniciar` a caminho perde a vez
        rodando = false;
        clearTimeout(vigiaQueda);
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
        ativo: function () { return rodando; },
        /* A queda foi um SOLUÇO: a conexão antiga voltou sozinha a
           "connected" (e o microfone segue vivo). Reaproveita em vez de
           publicar de novo — republicar troca o publicador no servidor e
           derruba todos os ouvintes, que levam segundos para voltar (26/09). */
        reaproveitar: function () {
            var viva = trilha && trilha.getAudioTracks().some(function (t) { return t.readyState === "live"; });
            if (pc && viva && pc.connectionState === "connected") {
                rodando = true;
                return true;
            }
            return false;
        },
        /* Mudo sem derrubar a transmissão (ver `mudoAgora`). O medidor cai a
           zero junto — o locutor VÊ que está mudo. */
        mudo: function (valor) { mudoAgora = !!valor; aplicarMudo(); return mudoAgora; },
        estaMudo: function () { return mudoAgora; },
        aoCair: function (fn) { aoCair = fn; }
    };
})();
