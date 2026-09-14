# Manual do Leilão — para a equipe do clube

> Escrito para os **voluntários** que vão operar o leilão, não para quem programa.
> Se você procura como o sistema foi construído por dentro, veja
> `docs/PLANEJAMENTO_LEILAO.md`; se procura como publicar no servidor,
> `docs/DEPLOY_LEILAO.md`.

Endereço do leilão: **https://pinhaljunior.com.br/leilao/**
Entrada da equipe: **https://pinhaljunior.com.br/leilao/equipe/entrar/**

---

## 1. Quem faz o quê

São **três funções**, porque numa noite de leilão raramente é a mesma pessoa. Cada
um entra no **mesmo endereço** e cai direto na sua tela.

| | Função | O que faz |
|---|---|---|
| 📦 | **Preparação** | Cadastra os itens, monta a fila, cria o leilão e coloca no ar |
| 🎤 | **Locutor** | Conduz o pregão: abre o item, bate o martelo, fala ao microfone |
| 💰 | **Caixa** | Confere quem pagou e cuida da entrega |

O **Diretor** enxerga as três e é quem distribui as funções.

**Uma pessoa pode ter mais de uma função.** Se você tem só uma, o sistema já te
joga direto nela ao entrar.

**Duas coisas de propósito:**

- **O locutor não confirma pagamento.** Quem bate o martelo não é quem confere o
  dinheiro — e quem está conduzindo já tem trabalho suficiente.
- **Só se entrega o que foi pago.** O item só aparece na lista de entrega depois
  que o pagamento caiu.

---

## 2. Antes do evento (Preparação)

### Criar o leilão

Em **📦 Preparação**, preencha o formulário "Novo leilão":

| Campo | O que é | Sugestão |
|---|---|---|
| Nome | Aparece na tela de todo mundo | "Leilão do Clube — Novembro" |
| Incremento do lance | Quanto cada toque no botão soma | R$ 5,00 |
| Cronômetro do lote | Tempo de cada item | 60 segundos |
| Botão de tempo extra | Quanto o seu "+30s" acrescenta | 30 segundos |
| Prazo para pagar | Depois disso o item volta para a fila | 15 minutos |
| Duração do chat | Bate-papo entre um item e outro | 120 segundos |

Ele nasce em **rascunho** — ninguém de fora vê nada ainda.

> **Reiniciar o cronômetro a cada lance** vem marcado. É a regra clássica: quem
> dá lance no último segundo reabre o tempo para os outros responderem. Deixe
> marcado, a não ser que queira leilão de tempo fixo.

### Cadastrar os itens

Na linha do leilão, clique em **📦 Itens** → **+ Cadastrar item**.

- **Foto**: no celular, o botão **abre a câmera direto**. Tire a foto do item ali
  mesmo. A imagem é reduzida sozinha para carregar rápido na tela de todo mundo.
- **Descrição**: uma linha. É o que cabe embaixo da foto no celular.
- **Lance inicial**: o primeiro toque no botão paga **exatamente este valor** (não
  soma o incremento).
- **Incremento próprio**: deixe vazio para usar o do leilão. Preencha só num item
  caro, em que R$ 5 por vez demoraria a noite toda.

Use **"Salvar e cadastrar outro"** para emendar vários de uma vez.

> ⚠️ **O item vai para o leilão que está na tela.** Se você estiver preparando o
> leilão de dezembro enquanto o de novembro acontece, os itens vão para o de
> dezembro — desde que você tenha entrado por ele.

### Ordenar a fila

Na lista de itens, os botões ▲▼ mudam a ordem. É a ordem em que o locutor vai
abrindo. Deixe os itens mais fortes para o fim — quando há mais gente na sala.

### Colocar no ar

De volta em **📦 Preparação**, botão **▶ No ar**.

> Colocar um leilão no ar **encerra** o que estiver rolando. E um leilão **sem
> itens não vai ao ar** — o sistema recusa.

---

## 3. Durante o evento (Locutor)

Tela: **🎤 Locutor**.

### O que você vê

- **O item atual** com foto, valor, quem está ganhando e o próximo valor
- **Cronômetro grande**, legível de longe
- **Lances deste item**, ao vivo
- **Fila** dos próximos

### Os botões

| Botão | Quando usar |
|---|---|
| **▶ Abrir próximo** | Começa o próximo item da fila |
| **+30s** | Deu vontade de esticar; a plateia está animando |
| **⏸ Pausar** | Precisou parar para falar, resolver algo |
| **🔨 VENDIDO** | Bate o martelo agora, sem esperar o cronômetro |
| **↩ Desfazer lance** | Alguém tocou sem querer, ou você errou |

> **"Abrir próximo" com uma disputa acontecendo joga o item atual de volta para a
> fila e a disputa se perde.** O sistema avisa e pede confirmação. Para vender,
> use **VENDIDO**.

### O cronômetro

Cada lance **reinicia** os 60 segundos (se a opção estiver marcada). Nos últimos
10 segundos ele fica vermelho e a tela de todo mundo faz "tique" — é a hora do
"dou-lhe uma, dou-lhe duas".

Zerou o tempo: o item é **vendido** para quem estava na frente. Se ninguém deu
lance, ele volta para a fila.

### O microfone

Botão **🎤 Transmitir**. O navegador vai pedir permissão do microfone — aceite.
A barrinha mostra que está saindo som: **se ela não mexe quando você fala, ninguém
está te ouvindo**.

Quem está no leilão precisa apertar **🔊** na própria tela para escutar — o
navegador não deixa tocar som sozinho.

### O chat

Abre sozinho entre um item e outro, pelo tempo configurado. Você pode abrir e
fechar na mão, e mandar **avisos** que aparecem destacados.

### Se alguém abusar

Aba **👥 Pessoas** → **Bloquear**. A pessoa para de dar lance na hora, e **entrar
de novo não resolve para ela** — o bloqueio segue a pessoa.

---

## 4. O dinheiro e a entrega (Caixa)

Tela: **💰 Caixa**.

### Aba Pagamentos

Cada item batido vira um **arremate** com **15 minutos** para pagar. Na tela do
arrematante aparecem dois botões — copiar o código Pix e mostrar o QR Code —
**sem sair do leilão**, para ele continuar disputando os próximos itens.

Quando o Pix cai, o selo muda para **Pago** sozinho.

**Marcar pago** é para quem acertou por fora (dinheiro, transferência, etc.).
Esses aparecem com a etiqueta "na mão", para você saber depois.

> **Não pagou em 15 minutos?** O arremate vence, o item **volta para a fila** e
> pode ser leiloado de novo. Nada para você fazer.

### Aba A entregar

Só aparece aqui o que **já foi pago**. Cada linha traz o item, o nome, o WhatsApp
e o **endereço**.

- **📋 Copiar roteiro de entrega**: copia tudo formatado, pronto para colar no
  WhatsApp de quem vai entregar ou montar a rota.
- **Campo de observação**: anote quem recebeu, o código de rastreio, o combinado.
- **✅ Entregue**: sai desta lista e vai para "Entregues".

> O roteiro **leva nome e endereço**. É documento de quem entrega — não mande em
> grupo aberto.

---

## 5. Como é para quem participa

1. Recebe o link **https://pinhaljunior.com.br/leilao/**
2. Preenche nome, WhatsApp e endereço (**sem senha, sem cadastro**)
3. Cai direto na tela do leilão

Na tela ele vê a foto grande, **quem está ganhando**, o **valor** e um botão
enorme que soma R$ 5 por toque. A cada lance a tela pisca, toca um som e vibra o
celular — dá para saber que entrou lance sem estar olhando.

Dois estados impossíveis de confundir:

- 🟢 **VOCÊ ESTÁ GANHANDO** — o botão trava, para não cobrir o próprio lance
- 🔴 **TE SUPERARAM** — e fica assim até ele cobrir

**Trava de segurança:** ninguém consegue dar lance contra si mesmo, **nem abrindo
o leilão no celular e no computador ao mesmo tempo**. O sistema reconhece a
pessoa pelo WhatsApp.

No rodapé, **🏆 Meus arremates** mostra o que ele já levou e o que falta pagar.

---

## 6. Perguntas que vão aparecer

**"Posso preparar o próximo leilão enquanto este acontece?"**
Pode. Crie o leilão novo e cadastre os itens entrando por ele. O que está no ar
não é afetado.

**"E se cair a internet do participante?"**
A tela reconecta sozinha e volta com tudo atualizado. Ele não perde nada.

**"E se eu precisar reiniciar o sistema no meio?"**
O cronômetro é guardado no servidor, então ele volta no ponto certo. Mas **não
faça isso com uma disputa rolando**: se demorar mais do que faltava, o item é
batido na hora. Espere o intervalo.

**"Duas pessoas da mesma casa podem disputar?"**
Só com **WhatsApp diferente**. Com o mesmo número, o sistema entende que é a mesma
pessoa e trava — é o preço de impedir que alguém infle o próprio preço.

**"O item apareceu com 'Voltou para a fila'. Por quê?"**
Alguém arrematou e não pagou em 15 minutos.

**"Quantas pessoas aguenta?"**
Testado com **100 pessoas ao mesmo tempo**, e o lance chega em menos de um quarto
de segundo para todo mundo.

---

## 7. Antes do dia — lista de conferência

- [ ] Leilão criado, itens cadastrados **com foto**, fila na ordem
- [ ] Credenciais do **Mercado Pago** preenchidas em Preparação → Configuração
      (sem elas o leilão funciona, mas **não gera Pix** — o caixa dá baixa na mão)
- [ ] Uma cobrança **real de R$ 1** feita e confirmada, para provar o Pix
- [ ] Papéis distribuídos e **cada voluntário já entrou uma vez** na sua tela
- [ ] Microfone testado **com o celular de outra pessoa** ouvindo
- [ ] Link do leilão divulgado
