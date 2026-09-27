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
    // O microfone ESCOLHIDO na mesa ("" = o padrão do computador) e o que está
    // de fato EM USO. Pedido do clube (27/09): no PC da mesa há webcam, fone e
    // microfone de mão, e ninguém sabia qual deles o navegador tinha pego.
    var escolhido = "";
    var emUso = null;          // { id, rotulo, reserva }
    var aoNivelAtual = null;
    // Cada troca de microfone no ar ganha um número: dois cliques seguidos na
    // lista não podem deixar a primeira troca, que chegou por último, vencer.
    var vezDaTroca = 0;

    var FILTROS = { echoCancellation: true, noiseSuppression: true, autoGainControl: true };

    /* Abre o microfone escolhido. Se ele não existe mais (USB/Bluetooth que
       saiu — é justamente o que derruba a transmissão), abre o PADRÃO em vez de
       ficar mudo: no meio do leilão, voz por outro microfone é melhor que
       silêncio. `emUso.reserva` avisa a mesa que não é o escolhido.
       Permissão negada não tem reserva: o erro sobe. */
    async function abrirMicrofone(id) {
        var audio = Object.assign({}, FILTROS);
        if (id) audio.deviceId = { exact: id };
        try {
            var s = await navigator.mediaDevices.getUserMedia({ audio: audio, video: false });
            return { stream: s, reserva: false };
        } catch (e) {
            if (!id || e.name === "NotAllowedError" || e.name === "SecurityError") throw e;
            if (window.console) console.warn("[audio-falar] microfone escolhido indisponível (" + e.name + "); usando o padrão");
            var padrao = await navigator.mediaDevices.getUserMedia({ audio: Object.assign({}, FILTROS), video: false });
            return { stream: padrao, reserva: true };
        }
    }

    function registrarEmUso(stream, reserva) {
        var t = stream.getAudioTracks()[0];
        var cfg = t && t.getSettings ? t.getSettings() : {};
        emUso = { id: cfg.deviceId || "", rotulo: (t && t.label) || "microfone sem nome", reserva: !!reserva };
    }

    /* O MICROFONE que termina (Bluetooth/USB que desconecta, bateria,
       ligação telefônica tomando o microfone): a conexão segue "connected" e
       ninguém ouve nada — a mesa dizia "No ar". Agora é queda, e a religação
       refaz o `getUserMedia` (revisão de 26/09). Vale também para a faixa que
       entrou por uma troca de microfone no ar. */
    function vigiarTrilha(stream, minha) {
        stream.getAudioTracks().forEach(function (t) {
            t.onended = function () {
                if (trilhaEmTroca === stream) { velhaMorreu = true; return; }
                if (minha === geracao && rodando && trilha === stream) caiu("microfone");
            };
            // O iOS (ligação, Siri, troca de app) MUTA a trilha sem
            // encerrá-la: a conexão segue "connected" e ninguém ouve. Muda
            // por mais de 4 s é queda — o MUDO do locutor é outra coisa
            // (`enabled = false`), e não dispara este evento.
            var vigiaMuda = null;
            t.onmute = function () {
                clearTimeout(vigiaMuda);
                vigiaMuda = setTimeout(function () {
                    if (minha === geracao && rodando && trilha === stream && t.muted) caiu("microfone mudo pelo sistema");
                }, 4000);
            };
            t.onunmute = function () { clearTimeout(vigiaMuda); };
        });
    }

    function desligarMedidor() {
        if (medidor) { clearInterval(medidor); medidor = null; }
        if (contexto) { try { contexto.close(); } catch (e) { /* já fechado */ } contexto = null; }
    }

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
        aoNivelAtual = aoNivel;
        try {
            var aberto = await abrirMicrofone(escolhido);
            stream = aberto.stream;
            if (superada()) return false;
            trilha = stream;
            registrarEmUso(stream, aberto.reserva);
            aplicarMudo();
            ligarMedidor(stream, aoNivel);
            vigiarTrilha(stream, minha);

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

    /* Troca o microfone COM A TRANSMISSÃO NO AR, sem derrubar ninguém:
       `replaceTrack` põe a faixa nova na mesma conexão. Parar e transmitir de
       novo derrubaria todos os ouvintes (segundos para voltar). Fora do ar, só
       guarda a escolha para a próxima transmissão.
       As trocas andam em FILA: com duas pendentes, a que terminasse por último
       podia pôr no ar uma faixa que a outra já tinha desligado (silêncio). */
    var filaTroca = Promise.resolve();
    var trilhaEmTroca = null;     // a faixa que está sendo substituída
    var velhaMorreu = false;

    function trocar(id) {
        var anterior = escolhido;
        escolhido = id || "";
        var minhaTroca = ++vezDaTroca;
        var feito = filaTroca.then(function () { return fazerTroca(minhaTroca, anterior); });
        filaTroca = feito.catch(function () { /* a fila segue */ });
        return feito;
    }

    async function fazerTroca(minhaTroca, anterior) {
        if (minhaTroca !== vezDaTroca) return { trocou: false, superada: true };
        if (!rodando || !pc || !trilha) return { trocou: false, foraDoAr: true };
        var minha = geracao;
        var conexao = pc;
        var velha = trilha;
        var novo = null;
        function largar() { if (novo) novo.getTracks().forEach(function (t) { t.stop(); }); }
        function vale() { return minha === geracao && pc === conexao && trilha === velha; }
        trilhaEmTroca = velha;
        velhaMorreu = false;
        try {
            var aberto = await abrirMicrofone(escolhido);
            novo = aberto.stream;
            if (!vale()) { largar(); return { trocou: false, superada: true }; }
            var envios = conexao.getSenders ? conexao.getSenders() : [];
            var envio = envios.filter(function (s) { return s.track && s.track.kind === "audio"; })[0] || envios[0];
            if (!envio) throw new Error("sem faixa de envio para trocar");
            await envio.replaceTrack(novo.getAudioTracks()[0]);
            if (!vale()) { largar(); return { trocou: false, superada: true }; }
            trilha = novo;
            registrarEmUso(novo, aberto.reserva);
            aplicarMudo();
            vigiarTrilha(novo, minha);
            velha.getTracks().forEach(function (t) { t.onended = null; t.onmute = null; t.stop(); });
            desligarMedidor();
            ligarMedidor(novo, aoNivelAtual);
            return { trocou: true };
        } catch (e) {
            if (window.console) console.warn("[audio-falar] troca de microfone: " + e.message);
            largar();
            // Não abriu: a voz segue no microfone de antes, e a escolha volta
            // para ele (senão a próxima religação tentaria o que não abre).
            if (minhaTroca === vezDaTroca) escolhido = anterior;
            return { trocou: false, erro: e.name || e.message, anterior: anterior };
        } finally {
            trilhaEmTroca = null;
            // Aparelho que só abre um microfone por vez (iPhone) encerra o
            // antigo ao abrir o novo; se a troca não vingou, é queda de verdade.
            if (velhaMorreu && trilha === velha && minha === geracao && rodando) caiu("microfone");
            velhaMorreu = false;
        }
    }

    /* Os microfones do aparelho. Sem a permissão do microfone o navegador
       esconde os nomes (e até os ids); `pedir` abre e fecha o microfone uma
       vez para liberá-los. "default"/"communications" são apelidos do Windows
       para um dos outros — a mesa já tem a opção "padrão". */
    async function listar(pedir) {
        var md = navigator.mediaDevices;
        if (!md || !md.enumerateDevices) return { microfones: [], comNomes: false, padrao: "" };
        if (pedir) {
            try {
                var s = await md.getUserMedia({ audio: true, video: false });
                s.getTracks().forEach(function (t) { t.stop(); });
            } catch (e) { /* negado: a lista sai sem nomes */ }
        }
        var todos = await md.enumerateDevices();
        var entradas = todos.filter(function (d) { return d.kind === "audioinput"; });
        var padrao = entradas.filter(function (d) { return d.deviceId === "default"; })[0];
        var mics = entradas.filter(function (d) {
            return d.deviceId && d.deviceId !== "default" && d.deviceId !== "communications";
        });
        return {
            microfones: mics.map(function (d, i) { return { id: d.deviceId, rotulo: d.label || ("Microfone " + (i + 1)) }; }),
            comNomes: mics.some(function (d) { return !!d.label; }),
            padrao: padrao && padrao.label ? padrao.label.replace(/^(Padrão|Default)\s*-\s*/i, "") : ""
        };
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
        emUso = null;
        clearTimeout(vigiaQueda);
        desligarMedidor();
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
        /* Microfone: `escolher` guarda a escolha e, no ar, troca na hora
           (devolve {trocou}); `emUso` diz qual o navegador abriu DE FATO —
           é o que a mesa mostra, e `reserva` avisa que não é o escolhido. */
        listar: listar,
        escolher: trocar,
        escolhido: function () { return escolhido; },
        emUso: function () { return emUso; },
        mudo: function (valor) { mudoAgora = !!valor; aplicarMudo(); return mudoAgora; },
        estaMudo: function () { return mudoAgora; },
        aoCair: function (fn) { aoCair = fn; }
    };
})();
