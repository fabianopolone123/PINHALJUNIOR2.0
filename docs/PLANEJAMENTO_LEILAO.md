# Planejamento — Leilão online ao vivo (`/leilao/`)

> Módulo **novo e independente** do sistema do clube: leilão ao vivo, em tempo real, para ~50
> pessoas simultâneas (teto de projeto: **100**), **todas remotas**. Registrado em 2026-09-13.
> Decisões de arquitetura tomadas com o usuário antes da primeira linha de código.

---

## 1. O que é

Um leilão conduzido por um **locutor** que fala ao vivo, com os participantes **em casa**, no celular.
Cada item ("lote") é aberto, recebe lances de R$ 5 em R$ 5 e é arrematado por quem estiver na frente
quando o cronômetro zera. Quem arremata tem **15 minutos** para pagar por Pix, **sem sair da tela do
leilão**; passou disso, o item **volta para a fila**. Entre um lote e outro abre um **chat** por um tempo
configurável.

**A sensação que o módulo tem de entregar:** lance novo é um acontecimento. Tem que estourar na tela de
todo mundo ao mesmo tempo, com som e movimento, em menos de meio segundo. Um leilão em que o valor
aparece com dois segundos de atraso não é um leilão — é um formulário.

## 2. Decisões de arquitetura (fechadas)

| Decisão | Escolha | Por quê |
|---|---|---|
| Transporte tempo real | **SSE** (Server-Sent Events) num serviço **ASGI próprio** | O servidor empurra; 100 conexões ociosas custam quase nada de CPU. Lance é `POST` comum — não precisa de canal bidirecional. |
| Voz do locutor | **MediaMTX** (WHIP/WHEP) **no próprio VPS** | Binário Go único, cliente em `RTCPeerConnection` puro (**sem biblioteca JS externa**), atraso de 200-500 ms. |
| Código e banco | App `leilao` **no mesmo repositório**, **banco SQLite próprio**, **serviço próprio** | Reaproveita o cliente de pagamento e o padrão visual, mas 50 pessoas martelando lance **não encostam** no banco do clube. |
| Entrega | **Módulo inteiro pronto** antes de qualquer uso real | Decisão do usuário. Internamente ainda é construído em fases (§10), cada uma testada. |
| Público | **100% remoto** | O áudio é essencial e o **cronômetro na tela é a autoridade** do lance — nunca a voz, que sempre chega com algum atraso. |

### 2.1 Dependência nova autorizada

- **`uvicorn`** (Python) — servidor ASGI. Autorizado pelo usuário ao escolher SSE. Entra num
  `requirements-leilao.txt` **separado**, para não mexer no ambiente do sistema do clube.
- **`mediamtx`** — binário Go, instalado **fora** do Python (como o Nginx é). Não é dependência de código.
- **Nada de JS externo**: WebRTC é API nativa do navegador; o QR Code vem pronto do Mercado Pago em
  base64; som é sintetizado em **WebAudio**; confete e animações são CSS/canvas escritos à mão.

## 3. Por que dois serviços (e não um)

O sistema do clube roda em **gunicorn síncrono**. SSE segura a conexão aberta: com workers síncronos,
**cada participante ocuparia um worker inteiro**, e 50 pessoas derrubariam o site do clube junto.

Então o leilão sobe como um **segundo serviço**, na mesma base de código:

```
pinhaljunior.com.br/sistema-novo/  → pinhaljunior2.service        → gunicorn sync      → db.sqlite3
pinhaljunior.com.br/leilao/        → pinhaljunior_leilao.service  → uvicorn (1 worker) → leilao.sqlite3
```

**Um único worker uvicorn, de propósito.** Três consequências boas:

1. O "hub" de eventos vive na memória do processo — **sem Redis**, sem fila, sem peça nova.
2. Só existe **um escritor** no SQLite: não há disputa de lock, que é o calcanhar do SQLite.
3. O cronômetro e a expiração dos 15 minutos rodam num **laço `asyncio` único** dentro do processo —
   sem cron, sem worker de fila.

O limite disso é conhecido e aceito: **não dá para escalar horizontalmente** (dois processos teriam dois
hubs e dois relógios). Para 100 pessoas num evento do clube, um processo sobra. Se um dia precisar
crescer, o caminho é trocar o hub em memória por Redis pub/sub — e **só isso** muda.

## 4. Isolamento do banco e reuso do pagamento

O serviço do leilão sobe com um módulo de settings próprio (`config/settings_leilao.py`), que herda o do
clube e troca: banco, `ROOT_URLCONF`, apps instalados, prefixo de URL e **nome dos cookies**
(`leilao_sessionid` — se repetir o nome, um app derruba a sessão do outro, armadilha que o `settings.py`
do clube já documenta).

**O app `core` NÃO é instalado no serviço do leilão.** O que se reaproveita é `core/mercadopago.py`, que é
**biblioteca pura**: só chama `urllib` e recebe um objeto de configuração de quem chama
(`config.access_token`, `config.webhook_secret`). O leilão passa o **seu** `ConfigLeilao`. Nada de importar
model do clube, nada de duas aplicações escrevendo no mesmo arquivo de banco.

**Consequência a aceitar:** as credenciais do Mercado Pago são **digitadas de novo** na tela de
configuração do leilão. É o preço do isolamento, e é o certo — o leilão pode até usar outra conta.

## 5. Como o tempo real funciona

### 5.1 O canal

- `GET /leilao/stream/` → `text/event-stream`, view **assíncrona**, uma conexão por participante.
- O navegador reconecta sozinho (`EventSource` faz isso de graça). Ao (re)conectar, o servidor manda
  **primeiro um `estado` completo** — assim não existe cliente dessincronizado, nem lógica de "replay".
- Batimento (`: ping`) a cada 15 s, senão o Nginx fecha a conexão ociosa.
- No Nginx: `proxy_buffering off` + `proxy_read_timeout` alto. Sem isso o SSE **não passa** (o proxy segura
  os pedaços). A view também manda `X-Accel-Buffering: no` como reforço.

### 5.2 Os eventos

| Evento | Quando | Carrega |
|---|---|---|
| `estado` | ao conectar | tudo: lote atual, valor, quem ganha, prazo, fila, chat |
| `lance` | a cada lance | valor novo, nome de quem lidera, prazo novo |
| `lote_aberto` / `lote_vendido` | locutor abre/fecha | lote, valor final, vencedor |
| `chat` / `chat_estado` | mensagem, abre/fecha | texto, autor |
| `arremate` / `pagamento` | fechou / pagou | id do arremate, situação |
| `online` | entra/sai gente | contagem |

**O fluxo é um broadcast só.** A personalização ("VOCÊ está ganhando", "seu Pix") acontece **no cliente**,
que sabe o próprio id — o servidor serializa **uma vez** e escreve para todos. É isso que faz 100 conexões
custarem pouco. O que é privado (código Pix, endereço) **nunca** entra no broadcast: sai por `GET` próprio,
autenticado pela sessão.

### 5.3 Lance sem corrida

O `POST /leilao/lance/` é **síncrono** (o Django executa em threadpool), protegido por:

1. um **lock por lote** no processo (só há um processo — o lock é suficiente e é barato);
2. `transaction.atomic()` com **UPDATE condicional** (`WHERE valor_atual = <o que o cliente viu>`), então
   dois toques no mesmo milissegundo **não** viram dois incrementos de R$ 5 em cima do mesmo valor;
3. regra de leilão: **ninguém cobre o próprio lance** (quem já lidera tem o botão travado);
4. limite de 1 lance a cada 300 ms por participante — contra dedo nervoso e contra script.

O cliente ainda **pinta o lance na hora** (otimista) e corrige quando o evento volta: a tela responde ao
toque em 0 ms, e a verdade continua sendo a do servidor.

### 5.4 O relógio é do servidor

O lote guarda **`fecha_em`** (data/hora absoluta). O cliente só desenha a diferença. Ninguém ganha ou perde
por ter o relógio do celular adiantado, e quem recarrega a página cai no mesmo segundo que os outros.

- Padrão: **60 s** por lote, **reiniciando a cada lance** (regra clássica anti-"lance no último segundo").
- O locutor pode **+30 s**, **pausar** e **fechar na hora** ("dou-lhe uma, dou-lhe duas, vendido").
- Zerou: vira `vendido` (com vencedor) ou `sem_lance` (volta para a fila).

### 5.5 O laço central (`tick`)

Uma corrotina única, a cada 1 s: fecha lote vencido, expira arremate não pago, devolve o item à fila, manda
o batimento. É o coração do módulo — **um lugar só** decide o tempo de tudo.

## 6. Dinheiro (Pix + os 15 minutos)

1. Lote fecha → nasce um **`Arremate`** com `expira_em = agora + 15 min` (configurável).
2. O sistema cria a cobrança Pix na hora (`criar_pix`, validade do QR casada com o prazo) e avisa **só o
   vencedor** pelo stream.
3. Na tela dele, **sem sair do leilão**: um painel com **📋 Copiar código** e **📱 Mostrar QR** (a imagem
   base64 que o próprio MP devolve — sem gerador de QR, sem biblioteca), e o prazo correndo.
4. Pagou → **webhook** `/leilao/webhooks/mercadopago/` (público, `@csrf_exempt`, idempotente, assinatura
   conferida) → marca pago → evento no stream → o item entra em **"Meus arremates"** com selo **✅ Pago**.
   Como webhook atrasa, existe também uma consulta de reforço enquanto o painel estiver aberto.
5. Não pagou em 15 min → arremate **expirado**, lote **volta para a fila** (contando quantas vezes voltou),
   e o locutor vê isso na tela dele. O participante que furou pode ser **bloqueado** com um clique.

**Ele nunca perde o leilão para pagar** — esse é o ponto do desenho. O pagamento é uma gaveta que abre por
cima da tela, e o lote seguinte continua rolando atrás.

## 7. As telas

### 7.1 Entrada (`/leilao/entrar/`)

Link único divulgado pelo clube. Pede **nome completo, WhatsApp e endereço completo** (CEP, rua, número,
complemento, bairro, cidade, UF). Sem senha: a pessoa é reconhecida por **cookie de sessão assinado**;
voltando depois, cai direto no leilão.

> **Sugestão registrada (a decisão é do usuário):** pedir o endereço **só de quem arremata** deixaria a
> porta de entrada bem mais leve — digitar endereço completo no celular espanta gente que entraria só para
> olhar. Fica anotado; o plano segue o pedido original, com o endereço na entrada.

### 7.2 Leilão (`/leilao/`) — a tela do participante

Uma tela só, que nunca recarrega:

- **foto grande** do item, nome e descrição curta;
- **quem está ganhando** em letra enorme + **valor** enorme;
- **cronômetro** regressivo (vermelho e pulsando nos últimos 10 s);
- **botão gigante de lance** com o valor que ele vai pagar (`DAR LANCE — R$ 85`);
- dois estados impossíveis de confundir: **🟢 VOCÊ ESTÁ GANHANDO** × **🔴 TE SUPERARAM**;
- entre lotes, o **chat** ocupa o lugar do botão;
- rodapé: **Meus arremates (n)** e o botão **🔊 Ativar som** (navegador só libera áudio depois de um toque —
  é ele que destrava o som dos lances **e** a voz do locutor).

### 7.3 Locutor (`/leilao/locutor/`)

Tudo numa tela, pensada para quem está falando ao mesmo tempo:

- lote atual, valor, líder, **cronômetro grande** com `+30 s` / pausar / **VENDIDO**;
- **histórico de lances ao vivo** (quem, quanto, quando) com **desfazer último lance** (erro acontece);
- **fila de lotes** com ↑↓ e "abrir este agora";
- **🎙️ microfone**: ligar/desligar a transmissão, com medidor de nível (para saber que está indo som);
- **💰 pagamentos**: arrematado × pago × vencido, com **marcar como pago na mão** (quem pagou fora do Pix);
- **👥 participantes**: contato e endereço (é o que entrega o item), bloquear;
- **💬 chat**: abrir/fechar, duração, apagar mensagem.

### 7.4 Cadastro de lotes (`/leilao/lotes/`)

Nome, descrição curta, **lance inicial**, incremento e **foto**. A foto abre a **câmera do celular** direto
(`<input type="file" accept="image/*" capture="environment">` — nativo, sem biblioteca). O servidor
redimensiona com **Pillow** (já é dependência) para ~1200 px + miniatura: foto de celular tem 4 MB, e 50
pessoas baixando 4 MB ao mesmo tempo estragam o evento.

## 8. Efeitos (o "visualmente legal")

Sem biblioteca, tudo escrito à mão:

- **Som sintetizado em WebAudio** — um "ping" cristalino a cada lance, "tique" nos 10 s finais, acorde
  ascendente no "vendido". Zero arquivo para baixar, zero latência de carregamento.
- **Vibração** no celular a cada lance (`navigator.vibrate`).
- Valor que **salta e pisca**, nome do líder que **entra deslizando**, botão com **onda ao toque**.
- **Confete** em canvas para quem arremata.
- Tudo respeitando `prefers-reduced-motion` (regra do projeto) e com o som **desligado por padrão** até o
  toque de "Ativar som".

## 9. Áudio ao vivo (WebRTC)

- **MediaMTX** como serviço systemd; o locutor **publica** (WHIP) e cada participante **escuta** (WHEP).
- O navegador usa `RTCPeerConnection` puro + um `fetch()` com o SDP: ~40 linhas de JS, nenhuma dependência.
- Sinalização passa pelo **Nginx no 443** (mesma origem, HTTPS); a **mídia** vai direto por **UDP** para o
  IP do VPS — exige liberar a faixa UDP no firewall.
- Credencial de publicação só na página do locutor (restrita); leitura é aberta a quem está no leilão.

### 9.1 As contas (e o risco real)

Voz em Opus dá ~40 kbps por ouvinte, já com cabeçalho de rede:

| | 50 ouvintes | 100 ouvintes |
|---|---|---|
| Subida do VPS | ~2 Mbps | ~4 Mbps |
| Pacotes/s | ~2.500 | ~5.000 |
| CPU (estimada) | ~5-10% | ~10-20% |

Banda não é problema (a porta é de 100 Mbps ou mais). **O risco não é a média de CPU — é o engasgo.**
Áudio precisa entregar um pacote a cada 20 ms; se outro dos 11 sites do VPS segurar o vCPU por 150 ms, o som
**picota para todos**. Mitigação combinada com o usuário: **parar os outros serviços no dia do evento** e dar
prioridade de CPU ao processo de áudio (`CPUWeight` no systemd).

### 9.2 Teste de carga é obrigatório, e antes do dia

- **Lances/SSE**: comando `leilao_carga` abre N conexões SSE e dispara lances, medindo o atraso entre o
  `POST` e o evento chegar (p50/p95). Roda de outra máquina.
- **Áudio**: mais difícil de simular com fidelidade. O plano é medir com 10-15 aparelhos reais, acompanhar
  CPU/rede no servidor e **extrapolar pela conta de pacotes** (que é linear). **É estimativa, não prova** —
  por isso a caixa de áudio da tela é **plugável**: reprovando, ela passa a apontar para uma live externa sem
  reescrever o resto.

## 10. Fases de construção (internas — a entrega é única)

1. **Fundação** — app, settings/serviço/banco separados, models, migrations, entrada do participante.
2. **Motor** — hub SSE, lance com lock, cronômetro do servidor, laço `tick`, abrir/fechar lote.
3. **Locutor** — painel completo, fila, desfazer lance, cadastro de lotes com câmera e Pillow.
4. **Dinheiro** — Pix, webhook, 15 minutos, volta para a fila, "Meus arremates".
5. **Chat** entre lotes, com moderação.
6. **Efeitos** — WebAudio, animações, vibração, confete, responsividade fina no celular.
7. **Áudio** — MediaMTX, páginas WHIP/WHEP, prioridade de CPU.
8. **Prova** — suíte de testes, teste de carga, deploy, documentação e ensaio geral.

## 11. Riscos assumidos

| Risco | Mitigação |
|---|---|
| Engasgo de áudio no vCPU compartilhado | Parar os outros serviços no dia + `CPUWeight` + teste antes + plano B plugável |
| Um processo só (sem escala horizontal) | Aceito para 100 pessoas; caminho de saída é trocar o hub por Redis |
| SQLite sob rajada de lances | Banco próprio + escritor único + escrita minúscula (uma linha por lance) |
| Webhook do MP atrasar | Consulta de reforço enquanto o painel de pagamento estiver aberto |
| Queda de internet do participante | `EventSource` reconecta sozinho e o servidor remanda o estado inteiro |
| Dados pessoais (endereço, telefone) | Ficam **só** no banco do leilão, nunca no Git; telas com endereço são restritas ao locutor |

## 12. O que este módulo **não** faz

- Não tem vínculo com o cadastro do clube (quem participa **não** precisa ser do clube).
- Não entra no Financeiro do clube (o dinheiro do leilão é controlado na tela do próprio leilão).
- Não faz lance automático ("robô"/proxy bidding) nem lance por valor digitado — é só o botão de +R$ 5 — e
  não leiloa dois lotes ao mesmo tempo: **um lote por vez**, como o locutor conduz.
- Não tem aplicativo: é web, no navegador do celular.
