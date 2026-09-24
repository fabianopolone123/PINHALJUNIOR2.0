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
    // O VIGIA: relógios que percebem "conectado, mas mudo".
    let vigiaMudo = null;      // a faixa avisou que parou de receber
    let vigiaBytes = null;     // ninguém avisou, mas não chega byte nenhum
    let bytesVistos = -1;
    let paradasSeguidas = 0;
    /* A tela precisa SABER que o som caiu — os vigias percebem, mas quem
       resolve é a pessoa.

       Isto vale sobretudo para um caso que nenhuma reconexão conserta: quando
       o navegador **bloqueia** o áudio (política de autoplay, aparelho que
       voltou do bloqueio), o `play()` é recusado e só um **gesto** libera.
       Religar a conexão mil vezes não adianta; o que adianta é pedir um toque. */
    let aoMudar = null;
    let ouvindo = false;

    function avisar(estado) {
        if (ouvindo === estado) return;   // só na virada, nunca repetido
        ouvindo = estado;
        if (aoMudar) {
            try { aoMudar(estado); } catch (e) { /* a tela não derruba o áudio */ }
        }
    }

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
                // Limpa ANTES de reatribuir: o elemento que fica segurando a
                // stream anterior é um dos jeitos de o celular travar o áudio
                // de vez — o caso em que nem desligar e ligar o som resolve.
                elemento.srcObject = null;
                elemento.srcObject = e.streams[0];

                /* A FAIXA avisa quando para de chegar mídia.
                   É exatamente o que acontece quando o locutor encerra a
                   transmissão: a conexão continua DE PÉ (o ICE não cai, o
                   `connectionState` segue "connected") e simplesmente não vem
                   mais som. Sem ouvir isto, nada disparava religar e a pessoa
                   ficava em silêncio para sempre.

                   Os 3 s de espera são porque `mute` também pisca em soluço de
                   rede, e refazer a conexão a cada soluço seria pior. */
                const faixa = e.track;
                if (faixa) {
                    faixa.onmute = function () {
                        if (pc !== conexao) return;
                        log("a voz parou de chegar (faixa muda)", true);
                        clearTimeout(vigiaMudo);
                        /* 3 a 5 s, SORTEADO. Os 3 s existem porque `mute`
                           também pisca em soluço de rede; o sorteio existe
                           porque este aviso chega a todos os celulares no
                           mesmo instante (é o mesmo evento), e uma espera fixa
                           faria os 100 dispararem no mesmo décimo de segundo.
                           Dispersar aqui, na origem, vale mais do que dispersar
                           só as tentativas seguintes. */
                        vigiaMudo = setTimeout(function () {
                            if (pc !== conexao || parado) return;
                            avisar(false);
                            religar();
                        }, 3000 + Math.random() * 2000);
                    };
                    faixa.onunmute = function () {
                        clearTimeout(vigiaMudo);
                        vigiaMudo = null;
                        // Voltou som: o elemento costuma estar pausado.
                        tocar();
                    };
                    faixa.onended = function () {
                        if (pc !== conexao) return;
                        log("a faixa de áudio terminou", true);
                        religar();
                    };
                }

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
            iniciarVigiaBytes(conexao);
            log("ligado");
            return true;
        } catch (e) {
            log("falhou: " + e.message, true);
            religar();
            return false;
        }
    }

    /* O SEGUNDO vigia: ninguém avisou, mas não chega byte nenhum.

       Nem todo navegador dispara `mute` na faixa quando a fonte some — e é
       justamente nos celulares mais antigos, que são os que mais aparecem num
       evento de clube, que ele falha. Então há um relógio conferindo o
       contador de bytes recebidos direto do `getStats()`: três voltas seguidas
       sem crescer (15 s) com a conexão "de pé" significa conexão morta.

       15 s e não 5: o locutor faz pausas ao falar, e o RTP continua mandando
       mesmo em silêncio — o que para de crescer é quando a FONTE some. */
    function iniciarVigiaBytes(conexao) {
        clearInterval(vigiaBytes);
        bytesVistos = -1;
        paradasSeguidas = 0;
        vigiaBytes = setInterval(function () {
            if (pc !== conexao || parado) return;
            if (!conexao.getStats) return;
            conexao.getStats(null).then(function (relatorio) {
                if (pc !== conexao || parado) return;
                let bytes = null;
                relatorio.forEach(function (r) {
                    if (r.type === "inbound-rtp" && r.kind === "audio") {
                        bytes = r.bytesReceived;
                    }
                });
                if (bytes === null) return;
                if (bytes > bytesVistos) {
                    bytesVistos = bytes;
                    paradasSeguidas = 0;
                    return;
                }
                paradasSeguidas++;
                if (paradasSeguidas >= 3) {
                    log("conectado, mas sem áudio chegando — religando", true);
                    avisar(false);
                    religar();
                }
            }).catch(function () { /* getStats falhou; a próxima volta tenta */ });
        }, 5000);
    }

    /* Reconexão com espera crescente: o locutor pode ter parado de falar por um
       instante, e 50 celulares martelando o servidor não ajudariam ninguém. */
    /* Reconexão que NÃO desiste — e este é o conserto do caso mais chato.

       Antes, depois de 8 falhas o módulo parava de tentar até a aba sair e
       voltar. Só que o caso real é outro: **o locutor encerra a transmissão e
       volta minutos depois**, com a pessoa olhando a tela o tempo todo. A aba
       nunca sai da frente, nada dispara `retomar()`, e o celular fica mudo
       para sempre — até reiniciar o aparelho, que foi o que o clube relatou.

       O motivo de existir um freio continua valendo (50 celulares não podem
       martelar o servidor), mas ele é **o intervalo**, não um teto de
       desistência: a espera cresce até 20 s e fica ali. Cinquenta aparelhos
       tentando a cada 20 s são 2,5 pedidos por segundo, cada um um 404 curto
       do MediaMTX enquanto não há ninguém no ar — barato, e o áudio volta
       sozinho no instante em que o locutor retoma. */
    function religar() {
        if (parado) return;
        tentativas++;
        const base = Math.min(1000 * Math.pow(1.7, Math.min(tentativas, 8)), 20000);

        /* A ESPERA É SORTEADA — e isto não é capricho.

           Quando o locutor encerra a transmissão, os celulares percebem o
           silêncio **no mesmo instante**: é o mesmo evento para todo mundo.
           Com uma espera fixa, as tentativas de todos ficam **sincronizadas**
           para o resto da noite — em vez de 100 aparelhos espalhados em 20
           segundos, são 100 pedidos **no mesmo segundo**, de 20 em 20.

           E o pior momento é justamente o melhor: quando o locutor volta, as
           100 negociações de áudio acontecem todas juntas, no mesmo vCPU que
           roda o leilão e o MediaMTX — a rajada cai bem na hora em que a sala
           precisa do som de volta.

           Sorteando ±40%, o bando se espalha sozinho: a primeira volta já
           desalinha os relógios e eles não voltam a se juntar. */
        const espera = Math.round(base * (0.6 + Math.random() * 0.8));
        setTimeout(function () { if (!parado) conectar(); }, espera);
    }

    function desligarConexao() {
        clearTimeout(vigiaMudo);
        clearInterval(vigiaBytes);
        vigiaMudo = null;
        vigiaBytes = null;
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
        if (p && p.then) {
            p.then(function () { avisar(true); }).catch(function () {
                // AQUI está o caso que nenhuma reconexão resolve: o navegador
                // recusou tocar e só um gesto da pessoa libera. A tela precisa
                // pedir esse gesto.
                log("navegador segurou o play — precisa de um toque", true);
                if (!parado) avisar(false);
            });
        } else {
            // Navegador antigo: `play()` sem promessa. Assume que foi.
            avisar(true);
        }
    }

    /* A aba voltou para a frente (ou a rede voltou).
       Três coisas, e as três são necessárias:
       1. zerar o contador — voltar para a tela é sinal novo, e o teto de
          tentativas existe para não martelar o servidor, não para punir quem
          atendeu uma ligação;
       2. religar se a conexão não estiver de pé;
       3. se a conexão estiver de pé, ainda assim mandar tocar — o elemento
          volta pausado com frequência. */
    function retomar() {
        if (parado) return;          // a pessoa desligou o som de propósito
        tentativas = 0;
        const viva = pc && pc.connectionState === "connected";
        if (!viva) {
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
            // Tocar o 🔊 é um pedido EXPLÍCITO: começa do zero.
            //
            // Sem esta linha, o contador de tentativas sobrevivia às falhas
            // anteriores — depois de uma sequência ruim ele já estava no teto,
            // e cada clique valia UMA tentativa que nascia estourada. Se o
            // locutor ainda não tivesse voltado naquele instante exato, o
            // módulo desistia de novo na hora. Era isto que fazia "nem
            // clicando no ícone o som voltar".
            tentativas = 0;
            return conectar();
        },
        desligar: function () {
            // A pessoa desligou de propósito: não é "perdi o som", e a tela
            // não pode pedir para religar o que ela acabou de calar.
            parado = true;
            ouvindo = false;
            desligarConexao();
            if (elemento) { elemento.srcObject = null; }
        },

        /* A tela se inscreve para saber quando o som cai e quando volta.

           Ela existe porque há um caso que **nenhuma reconexão resolve**: o
           navegador recusa tocar e só um gesto da pessoa libera. Detectar o
           silêncio sem pedir esse toque é chegar até a metade do problema. */
        aoMudar: function (fn) { aoMudar = fn; },
        ouvindo: function () { return ouvindo; },
        ativo: function () { return !!pc && !parado; },
        // Exposto para a tela poder forçar (o `leilao.js` chama junto da
        // reconexão do SSE, que é o mesmo momento).
        retomar: retomar
    };
})();
