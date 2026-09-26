# Simulador da voz do leilão

Testa o microfone do locutor, o mudo e a escuta **nas telas reais** (mesa e pregão), sem servidor
de áudio. O Chrome abre a página de verdade e, antes de qualquer script dela, o `voz_mock.js`
troca só o que precisaria de rede de áudio: o `RTCPeerConnection`, o servidor WHIP/WHEP (o
`fetch` para `/whip` e `/whep`) e o relógio, que anda 10x mais rápido. Todo o resto
(`audio_falar.js`, `audio_ouvir.js`, `locutor.js`, `leilao.js` e o servidor Django) é o código
real.

Cada cenário roda numa página recém-carregada e termina conferindo o que tem de ser verdade:
quantas conexões ficaram vivas, se sobrou **microfone aberto**, o texto que a mesa mostra, se a
tela do público pediu toque ou abriu janela.

## Como rodar

1. Um banco descartável com o áudio ligado (`ConfigLeilao.audio_ativo=True`, usuário e senha
   de publicação fictícios), um leilão ao vivo com item em pregão e uma conta de locutor.
2. O serviço do leilão no ar, apontando para esse banco (`DJANGO_LEILAO_SQLITE_PATH`), em
   `http://127.0.0.1:8011/`.
3. Uma sessão (chave do cookie `leilao_sessionid`):
   - **mesa**: conta com papel de locutor;
   - **público**: sessão que é participante **e** locutor ao mesmo tempo (o cenário do locutor
     que para de propósito manda o aviso `voz` pelo servidor de verdade).
4. Rodar (defina `PYTHONIOENCODING=utf-8` no Windows):

```bash
python voz_sim.py <sessao_locutor> http://127.0.0.1:8011/locutor/1/ cen_mesa.js
python voz_sim.py <sessao_mista>   http://127.0.0.1:8011/          cen_publico.js
python voz_sim.py <sessao> <url> cen_mesa.js m09_queda_religacao_em_voo_parar_transmitir   # um só
```

O Chrome sai de `CHROME` (variável de ambiente) ou do caminho padrão do Windows.

## A prova de fogo

Um cenário só vale se **falha no código com o defeito**. Ao escrever um novo, rode-o também
contra a versão anterior do arquivo (`git show <commit>:static/leilao/js/...`) e confira que ele
acusa. Foi assim que se descobriu que conferir só o estado final não bastava: no código antigo a
transmissão caía e voltava sozinha, e o final parecia certo — o cenário passou a exigir que a
conexão boa continue **a mesma**.

## Limite

É uma simulação. O que ela prova é a lógica (ordens de clique, quedas, religações, estados,
avisos). O áudio de verdade — MediaMTX, rede do evento, iPhone real — continua pedindo o ensaio
com aparelhos de verdade (ver `docs/DEPLOY_LEILAO.md`).
