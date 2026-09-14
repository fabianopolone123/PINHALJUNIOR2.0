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
| Prazo para pagar | Depois disso o item volta para a fila | 15 minutos |
| Duração do chat | Bate-papo entre um item e outro | 120 segundos |

Ele nasce em **rascunho** — ninguém de fora vê nada ainda.

> **Não existe cronômetro.** Nenhum item fecha sozinho: quem bate o martelo é
> você, no botão **VENDIDO**. É por isso que não há tempo por lote nem botão de
> tempo extra para configurar aqui.

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

### O número do item

Cada item ganha um **número** sozinho, na hora do cadastro: nº 1, nº 2, nº 3…
Você não digita nada.

**Escreva esse número no próprio objeto** (etiqueta, fita-crepe, o que for). Ele
é o que liga o que está na tela ao que está na prateleira — e é por ele que a
pessoa do caixa acha a caixa certa na hora de entregar. O roteiro de entrega sai
com o número na frente do nome, justamente por isso.

Três coisas que valem saber:

- **O número não é a posição na fila.** A ordem muda toda vez que vocês
  reorganizam a noite; o número **nunca muda**.
- **Item que volta para a fila** (o arrematante não pagou) volta com **o mesmo
  número** — a etiqueta continua valendo, não precisa reetiquetar nada.
- **Cada leilão começa do nº 1.** Apagar um item não devolve o número dele para
  a fila: se o nº 5 foi apagado, o próximo cadastro é o 6. É de propósito —
  número que já foi colado numa caixa não pode reaparecer em outro objeto.

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
| **🔨 VENDIDO** | Bate o martelo: o item é de quem está na frente |

> **"Abrir próximo" com uma disputa acontecendo joga o item atual de volta para a
> fila e a disputa se perde.** O sistema avisa e pede confirmação. Para vender,
> use **VENDIDO**.

> **Não existe "pausar".** Para segurar o pregão — falar com alguém, resolver um
> problema, dar um respiro —, é só **não abrir o próximo item**. Nada fecha
> sozinho, então você pode demorar o que precisar.

### O relógio da mesa conta para CIMA

Não é contagem regressiva: o número grande mostra **há quanto tempo ninguém dá
lance**. Passando de 30 segundos ele fica vermelho e diz "sala calada — martelo?".

É só uma sugestão, nunca uma ordem: ele **não fecha nada**. O "dou-lhe uma,
dou-lhe duas" é seu, e o item só é vendido quando você aperta **VENDIDO**.

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

- **📋 Copiar roteiro inteiro**: copia tudo formatado, pronto para colar no
  WhatsApp de quem vai entregar.
- **Campo de observação**: anote **quem recebeu**.
- **✅ Entregue**: sai desta lista e vai para "Entregues".

> O roteiro **leva nome e endereço**. É documento de quem entrega — não mande em
> grupo aberto.

#### Dividir entre os entregadores

Digite **quantos entregadores** vocês têm e clique em **Dividir**. A tela monta
uma rota para cada um, com o próprio botão de copiar — é só mandar a de cada um
no WhatsApp dele.

Como ele divide:

- **Junta por bairro.** Todo mundo do mesmo bairro fica com o mesmo entregador.
- **Equilibra as paradas.** O bairro com mais casas vai para quem estiver mais
  leve.
- **Casa com vários itens é uma parada só.** São todos entregues na mesma visita.

> ⚠️ **O sistema não olha mapa.** Ele não sabe a distância entre dois pontos —
> ele junta por bairro, que é o que vocês usariam para falar de região. Pode
> acontecer de dois bairros vizinhos caírem com entregadores diferentes. Quem
> conhece a cidade olha e troca em dez segundos; a divisão é um ponto de
> partida, não uma ordem.

Se você pedir mais entregadores do que há bairros, alguém fica sem rota — e a
tela mostra isso, em vez de inventar uma divisão.

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
Nada se perde: lances, líder e valores estão no banco, e as telas reconectam
sozinhas. Ainda assim, **não faça isso com uma disputa rolando** — quem estiver
com o dedo no botão fica alguns segundos sem conseguir dar lance. Espere o
intervalo.

**"Duas pessoas da mesma casa podem disputar?"**
Só com **WhatsApp diferente**. Com o mesmo número, o sistema entende que é a mesma
pessoa e trava — é o preço de impedir que alguém infle o próprio preço.

**"O item apareceu com 'Voltou para a fila'. Por quê?"**
Alguém arrematou e não pagou em 15 minutos.

**"O dinheiro cai onde?"**
Na **mesma conta** do Mercado Pago que o clube já usa para mensalidades, loja e eventos.

**"Dá para ensaiar sem cobrar de verdade?"**
Dá: em Preparação → Configuração, mude o modo para **Teste**. Aí o Pix é de sandbox e não move
dinheiro. **Volte para Produção antes do evento** — em modo Teste, ninguém consegue pagar de verdade.

**"Quantas pessoas aguenta?"**
Testado com **100 pessoas ao mesmo tempo**, e o lance chega em menos de um quarto
de segundo para todo mundo.

---

## 7. Antes do dia — lista de conferência

- [ ] Leilão criado, itens cadastrados **com foto**, fila na ordem
- [x] Credenciais do **Mercado Pago** — já configuradas (mesma conta do clube, modo Produção)
- [ ] Uma cobrança **real de R$ 1** feita e confirmada, para provar o Pix
- [ ] Papéis distribuídos e **cada voluntário já entrou uma vez** na sua tela
- [ ] Microfone testado **com o celular de outra pessoa** ouvindo
- [ ] Link do leilão divulgado
