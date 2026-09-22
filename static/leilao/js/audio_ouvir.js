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
 *
 * O SEGUNDO detalhe que morde (e que já mordeu de verdade): quando a aba sai
 * da frente — celular bloqueado, WhatsApp aberto para mandar um recado — o
 * navegador **derruba a conexão de áudio e não a devolve**. Pior: a reconexão
 * automática desiste depois de algumas tentativas, e aí não sobra nada que
 * tente de novo. A pessoa voltava para o leilão em silêncio e só resolvia
 * fechando o navegador inteiro, que ninguém adivinha.
 *
 * Por isso o módulo escuta `visibilitychange` **ele mesmo**, em vez de confiar
 * que cada tela lembre de chamá-lo: voltar para a frente zera o contador de
 * tentativas e religa se a conexão não estiver de pé. É a mesma lição do
 * `tela_acesa.js`.
 */
window.AudioLeilao = (function () {
    let pc = null;
    let url = "";
    let elemento = null;
    let tentativas = 0;
    let parado = true;
    // "a reconexão automática já desistiu" — o `retomar()` usa isto para saber
    // que precisa recomeçar do zero em vez de esperar um religar que não vem.
    let desistiu = false;

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
        desistiu = false;

        try {
            // A conexão fica numa CONSTANTE local e os handlers conferem que
            // ainda são os da conexão viva (`pc !== conexao`). Sem isso, o
            // `pc.close()` que abre toda reconexão dispara o handler de estado
            // da conexão ANTIGA, que chamaria `religar()` — uma reconexão
            // legítima viraria duas, e o contador de tentativas subiria sozinho.
            const conexao = new RTCPeerConnection({ iceServers: [] });
            pc = conexao;
            conexao.addTransceiver("audio", { direction: "recvonly" });

            conexao.ontrack = function (e) {
                if (pc !== conexao) return;
                elemento.srcObject = e.streams[0];
                tocar();
            };

            conexao.oniceconnectionstatechange = function () {
                if (pc !== conexao) return;
                const s = conexao.iceConnectionState;
                if (s === "failed" || s === "disconnected") {
                    log("conexão de áudio caiu (" + s + ")", true);
                    religar();
                }
            };

            // `connectionState` pega casos que o ICE sozinho não reporta (o
            // processo do navegador suspenso em segundo plano é um deles).
            conexao.onconnectionstatechange = function () {
                if (pc !== conexao) return;
                const s = conexao.connectionState;
                if (s === "failed" || s === "closed") {
                    log("conexão de áudio encerrada (" + s + ")", true);
                    religar();
                }
            };

            const oferta = await conexao.createOffer();
            await conexao.setLocalDescription(oferta);
            await esperarIce(conexao, 2500);

            const resposta = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/sdp" },
                body: conexao.localDescription.sdp
            });
            if (!resposta.ok) throw new Error("WHEP respondeu " + resposta.status);

            // Enquanto o `await` acima corria, outra chamada pode ter assumido
            // a vez: aplicar a resposta numa conexão já descartada quebra.
            if (pc !== conexao) return false;

            const sdp = await resposta.text();
            await conexao.setRemoteDescription({ type: "answer", sdp: sdp });
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
        if (tentativas > 8) {
            // Desistir aqui é para não martelar o servidor com 50 celulares.
            // NÃO é definitivo: `retomar()` recomeça quando a pessoa volta.
            desistiu = true;
            log("desisti de reconectar por ora (volto se a aba voltar)", true);
            return;
        }
        const espera = Math.min(1000 * Math.pow(1.7, tentativas), 20000);
        setTimeout(function () { if (!parado) conectar(); }, espera);
    }

    function desligarConexao() {
        if (pc) {
            const velha = pc;
            pc = null;   // antes do close(), para os handlers se calarem
            try { velha.close(); } catch (e) { /* já fechado */ }
        }
    }

    /* Voltar do segundo plano costuma deixar o <audio> PAUSADO mesmo com a
       conexão de pé: sem isto a pessoa fica olhando um leilão mudo com tudo
       aparentemente funcionando. */
    function tocar() {
        if (!elemento) return;
        const p = elemento.play();
        if (p && p.catch) p.catch(function () { log("navegador segurou o play", true); });
    }

    /* A aba voltou para a frente (ou a rede voltou).
       Três coisas, e as três são necessárias:
       1. zerar o contador — voltar para a tela é sinal novo, e o teto de
          tentativas existe para não martelar o servidor, não para punir quem
          atendeu uma ligação;
       2. religar se a conexão não estiver de pé (ou se já tinha desistido);
       3. se a conexão estiver de pé, ainda assim mandar tocar — o elemento
          volta pausado com frequência. */
    function retomar() {
        if (parado) return;          // a pessoa desligou o som de propósito
        tentativas = 0;
        const viva = pc && pc.connectionState === "connected";
        if (!viva || desistiu) {
            log("retomando o áudio");
            conectar();
        } else {
            tocar();
        }
    }

    document.addEventListener("visibilitychange", function () {
        if (!document.hidden) retomar();
    });
    // Rede que cai e volta tem o mesmo efeito da aba que sai e volta.
    window.addEventListener("online", retomar);

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
        ativo: function () { return !!pc && !parado; },
        // Exposto para a tela poder forçar (o `leilao.js` chama junto da
        // reconexão do SSE, que é o mesmo momento).
        retomar: retomar
    };
})();
