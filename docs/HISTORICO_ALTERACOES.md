# Histórico de Alterações

Registro cronológico das alterações do projeto Clube de Aventureiros Pinhal Júnior.

Formato de cada entrada:

```
## YYYY-MM-DD - Título da alteração

### Resumo
Descrição curta do que foi feito.

### Arquivos criados/alterados
- arquivo: explicação

### Decisões tomadas
- decisão técnica importante

### Pendências
- item ainda não feito
```

---

## 2026-09-21 - Leilão: a foto do item ganha dois botões (câmera e arquivo)

### Resumo
Correção do que subiu poucas horas antes. Tirar o `capture` devolveu a galeria
e **custou a câmera**: o clube testou no celular e só apareceu "escolher
arquivos".

### O que foi feito
O motivo é do sistema, não do site: no **Android 13+** o navegador abre o
**seletor de fotos do Android** para `accept="image/*"`, e esse seletor não tem
câmera. Juntando com o comportamento anterior:

- **com** `capture`: abre a câmera, esconde a galeria;
- **sem** `capture`: abre o seletor de fotos, esconde a câmera.

Nenhum dos dois sozinho serve, e o que aparece muda de aparelho para aparelho.
Então a escolha saiu do menu do sistema e veio para a tela: **dois botões** e
**dois inputs**, um com `capture` e outro sem.

### Arquivos criados/alterados
- `templates/leilao/lote_form.html`: os dois botões, o input da câmera (sem
  `name`) e o `#fotoNome`.
- `static/leilao/js/lote_form.js`: reescrito — copia o arquivo da câmera para o
  campo do formulário com `DataTransfer` e liga os botões; só se ativa quando
  `DataTransfer` existe.
- `static/leilao/css/locutor.css`: `.foto-botoes`, `.btn-foto`, `.foto-nome`.
- `leilao/tests.py`: `FotoDoItemCameraOuArquivoTests` (4 testes) no lugar do
  `FotoDoItemAceitaGaleriaTests`, que guardava a solução anterior.
- `docs/MANUAL_LEILAO.md`: instrução da equipe.

### Decisões tomadas
- **Só o input do formulário tem `name`.** Dois inputs com `name="foto"` iriam
  os dois no POST, e o vazio poderia sobrescrever a foto escolhida.
- **Melhoria progressiva.** Os botões nascem `hidden` e só aparecem com JS +
  `DataTransfer`; sem isso o seletor nativo fica de pé. Cadastro que depende de
  JS para aceitar foto deixaria alguém travado na véspera do evento.
- **Entrou o `#fotoNome`**: escondendo o input nativo, escondeu-se junto o nome
  do arquivo que ele mostrava, e quem escolhe da galeria precisa conferir que
  pegou a foto certa.

### Verificação
- Suíte do leilão: **323 testes OK**.
- **Render real + sonda headless** (485px): botões de 202px lado a lado, campo
  nativo escondido, input da câmera presente, `ESTOURA=false`.
- Aprendizado de bancada registrado no `REGRAS_CODEX`: `body.tela-entrada` é
  **flex**, e a sonda injetada no `<body>` virava irmã flex, espremendo o card
  para 147px e fazendo a captura parecer vazia. Sonda agora reporta pelo
  `document.title`.

### Pendências
- **Deploy NÃO feito**, a pedido do clube: o sistema estava em uso no VPS e o
  passo do leilão (§7.1) reinicia o `pinhaljunior_leilao.service`. O código
  está commitado e no GitHub; falta rodar o deploy + o passo extra quando
  houver janela.

---

## 2026-09-21 - Leilão: a foto do item aceita a galeria, não só a câmera

### Resumo
Pedido do clube: cadastrar item pelo celular anexando uma foto que já existe,
e não só fotografando na hora.

### O que foi feito
O campo de foto tinha `capture="environment"`, atributo que **força** o celular
a abrir a câmera e tira a galeria da frente. Removido. Ficou só o
`accept="image/*"`, que é o que faz o celular oferecer os dois caminhos — tirar
agora ou escolher uma existente — e o computador abrir o seletor normal.

Continua sem biblioteca (é nativo do `<input type="file">`) e a redução com
Pillow não muda.

### Arquivos criados/alterados
- `leilao/forms.py`: widget da `foto` sem `capture`; docstring do `LoteForm`.
- `templates/leilao/lote_form.html`: comentário e o texto de ajuda, que
  prometia só a câmera.
- `static/leilao/js/lote_form.js`: comentário do cabeçalho.
- `leilao/tests.py`: `FotoDoItemAceitaGaleriaTests` (3 testes).
- `docs/MANUAL_LEILAO.md`: instrução da equipe.

### Decisões tomadas
- **O atributo sai, não vira opção.** Não há tela para "quero a câmera": quem
  está com o celular na mão já sabe se a foto existe, e o seletor nativo do
  próprio sistema operacional oferece as duas coisas melhor do que qualquer
  botão que se inventasse.
- **Teste-guarda**, no padrão das outras remoções do módulo
  (`SemMusicaDeFundoTests`, `SemDesfazerLanceTests`): o `capture` é uma linha
  fácil de alguém repor achando que ajuda.

### Verificação
- Suíte do leilão: **322 testes OK** (+3).
- HTML renderizado conferido:
  `<input type="file" name="foto" accept="image/*" class="campo-file" id="id_foto">`.

---

## 2026-09-21 - Leilão: o pregão não sobrevive ao leilão, e o lance se faz notar

### Resumo
O clube abriu a mesa do locutor **sem nenhum leilão ao vivo** e ela mostrava
"item em pregão, sala calada", contando o silêncio de um item aberto dias
antes. Dois defeitos somados, os dois com a mesma raiz que o bug do chat já
tinha ensinado: **o que é do pregão tem de morrer com o pregão**.

No mesmo pedido, o efeito do lance novo no nome do líder ficou muito mais
destacado — e a verificação pegou de quebra uma rolagem horizontal.

### O que foi feito
**1. O lote não fica mais aberto para trás.** `mudar_status` fechava o
`chat_aberto_ate` ao sair do ar e esquecia o lote, que ficava `status="aberto"`
no banco para sempre. Agora `_devolver_lotes_abertos` devolve o item **limpo**
para a fila (`valor_atual` zerado, `lider` nulo), no mesmo idioma que o
`abrir_lote` já usava. Vale também para o leilão que sai do ar para dar lugar a
outro, que é por onde o órfão da produção nasceu.

**2. A guarda passou para o estado.** `estado_publico` respondia `ativo: True`
para qualquer leilão não-nulo, confiando em quem chamava. A tela pública
acertava por acidente (passa `Leilao.ao_vivo()`, que é `None`); a mesa **cai
para o leilão mais recente** quando não há nada no ar e por isso recebia um
pregão inventado. Agora ele mesmo exige `status == "ao_vivo"`, como o
`Leilao.chat_aberto` já fazia.

**3. O lance se faz notar.** O nome de quem assume a ponta cresce e acende
(`assume-a-ponta`: pico 1,18 + brilho dourado, 0,72s) em vez do deslize
discreto de antes, que se perdia para quem estava olhando o botão. Nome em
repouso de 1,32rem para 1,5rem (1,85rem no ecrã largo).

### Arquivos criados/alterados
- `leilao/servicos.py`: `_devolver_lotes_abertos` e os dois pontos de
  `mudar_status` que o chamam (sair do ar; sair para dar lugar a outro).
- `leilao/estado.py`: `estado_publico` exige `status == "ao_vivo"`.
- `static/leilao/css/leilao.css`: `assume-a-ponta` no lugar de `entra-nome`,
  `.lider-nome` maior, e `overflow-x: clip` + `overflow-clip-margin` no
  `.pregao`.
- `leilao/tests.py`: `PregaoNaoSobreviveAoLeilaoTests` (6 testes).

### Decisões tomadas
- **O item aberto volta para a FILA** quando o leilão encerra (escolha do
  clube, entre "volta para a fila", "vira sem lance" e "não deixar encerrar").
  Ninguém arrematou, então ele fica disponível de novo.
- **A guarda mora no `estado_publico`**, não no `locutor_view`. Consertar só o
  chamador deixaria o próximo chamador repetir o erro.
- **`clip`, não `hidden`**, para conter o estouro: `hidden` criaria caixa de
  rolagem; `clip` com `overflow-clip-margin: 24px` segura a rolagem e deixa o
  brilho vazar para fora do card.

### Verificação
- Suíte do leilão: **319 testes OK** (+6).
- **Sonda headless** (Chrome `--headless=new`, 390px): o pico da animação com
  nome de 60 letras sem espaço estourava **27px** (`scrollWidth` 527 ×
  `clientWidth` 500) e criava rolagem horizontal; com o `clip`, zero estouro em
  todos os nomes testados.
- Órfão da produção (leilão 3, item nº 3, zero lances) devolvido à fila.

### Pendências
- **O áudio ao vivo continua sem prova sob carga** — o MediaMTX nunca teve um
  ouvinte de verdade neste servidor. Medido em 21/09, de outra máquina: 100 e
  **200 conexões SSE** mantidas, zero quedas, servidor 90-98% ocioso em regime
  (pico só na chegada). Falta o ensaio com 10-15 aparelhos reais e ouvido
  humano, que é a única prova honesta da voz.

---

## 2026-09-19 - Leilão: peso e dimensões do item, obrigatórios no cadastro

### Resumo
Pedido do clube: o cadastro de item do leilão passou a **exigir** o **peso**
(kg) e as **três dimensões** (altura, largura e profundidade, em cm), e a
medida passou a aparecer em todas as telas em que o item aparece.

O motivo é a **entrega**, que é a parte do leilão que acontece depois e longe:
o voluntário escolhe o carro **antes de sair de casa**, e descobrir na porta da
pessoa que o item não cabe custa a viagem inteira. De quebra, quem dá lance
passa a saber o tamanho do que está comprando.

### O que foi feito
Quatro campos novos no `Lote` e uma property que monta o texto
(`1,5 kg · 40 × 30 × 25 cm`) para **todas** as telas: cadastro, lista da
preparação, tela pública do pregão, mesa do locutor, tela do caixa e
roteiro/quadro de entrega.

### Arquivos criados/alterados
- `leilao/models.py`: `peso_kg`, `altura_cm`, `largura_cm`, `profundidade_cm`
  (com `MinValueValidator` e `MaxValueValidator`; constantes `MAX_PESO_KG` e
  `MAX_LADO_CM`) e as properties `peso_numero`, `peso_texto`, `dimensoes` e
  `medidas_texto`. Migration **0010**.
- `leilao/forms.py`: `peso_para_decimal` (vírgula **e** ponto) e o `LoteForm`
  exigindo os quatro campos; `clean_peso_kg` recusa vazio e zero.
- `leilao/estado.py`: chave **`medidas`** no `lote_publico` (texto pronto).
- `leilao/entregas.py`: a medida entra no `texto_da_rota`, recuada sob o item.
- `templates/leilao/lote_form.html`: `fieldset` "Tamanho e peso" (duas grades,
  ver Decisões), `lotes.html`, `leilao.html`, `locutor.html`, `caixa.html` e
  `_parada_entrega.html`.
- `static/leilao/js/leilao.js` e `locutor.js`: desenham a linha e a **escondem**
  quando o item não tem medida.
- `static/leilao/css/leilao.css` (`.medidas`, `.ajuda-bloco`, `.lote-medidas`),
  `locutor.css` (`.mesa-medidas`, `.arremate-medidas`), `entregas.css`
  (`.parada-medidas`).
- `leilao/management/commands/leilao_demo.py`: os 6 itens fictícios nascem com
  peso e medidas (e o comando completa os que já existiam).
- `leilao/tests.py`: `PesoEDimensoesTests` (**25 casos**), o fixture `criar_lote`
  passou a preencher as medidas e o POST do `PreparacaoTests` ganhou os campos
  novos. Suíte do leilão: 288 → **313, tudo OK**.
- `docs/MANUAL_LEILAO.md`, `docs/REGRAS_CODEX.md`, `docs/ESTADO_ATUAL.md`.

### Decisões tomadas
- **A obrigatoriedade está no `LoteForm`, não no model.** No banco os quatro
  campos aceitam vazio: os itens cadastrados antes da migration existem e
  continuam válidos, e gravar `0` neles seria **inventar uma medida** para quem
  vai dirigir até a casa da pessoa. A lista da preparação marca esses itens com
  "sem peso/medidas — completar ao editar", que é onde se descobre o que falta
  antes da noite da entrega. Editar um item antigo pede o preenchimento — é a
  hora natural de completar.
- **Zero não passa.** "Obrigatório" que aceita `0 kg`/`0 cm` não obriga nada:
  chega na entrega valendo o mesmo que em branco.
- **O peso é `CharField` no form, e não `DecimalField` com `localize=True`.**
  Em pt-BR o Django lê `"1.5"` como **separador de milhar** e devolve **15** —
  um item de 1,5 kg viraria um de 15 kg sem avisar ninguém. `peso_para_decimal`
  trata vírgula e ponto como decimal; o clube não leiloa nada de mil quilos,
  então a hipótese perdida é impossível e o erro evitado é real. Há teste.
- **A máscara `moeda_br.js` ficou de fora**: ela é de valor em **R$** (regra do
  projeto) e leria "40" como R$ 0,40. Centímetro é inteiro, `NumberInput`
  com `min="1"`.
- **O texto é montado num lugar só** (`Lote.medidas_texto`). Formatar no
  template ou no JS faria a mesma medida aparecer de jeitos diferentes em telas
  diferentes, e a equipe desconfia do número quando ele muda de cara.
- **Vai no broadcast** porque medida **pode ser dita em voz alta** — é o tamanho
  do que está à venda, não dado de ninguém (ao contrário de Pix, telefone e
  endereço). Vai o **texto pronto**, não os quatro números.
- **Meia dimensão não vira texto.** `40 × ? × 25` parece defeito do sistema, não
  item incompleto; `dimensoes` exige os três lados.
- **`10,00` vira `10 kg`, nunca `1`.** O corte dos zeros à direita para no ponto
  decimal — há teste para as quatro variações.
- **Duas grades no formulário, não uma.** A `.entrada-grade` tem 6 colunas e a
  `.col-num` ocupa 2: os quatro campos juntos somariam 8 e quebrariam a linha no
  meio das dimensões. Peso é uma medida; altura/largura/profundidade são outra,
  e as três cabem exatas numa linha.
- **Há teto, e ele não é regra de negócio: é o freio do dígito a mais.**
  Conferindo os caminhos de entrada um a um, `999999999999` passava na altura —
  e uma medida dessas quebra a tela do pregão para as 100 pessoas que estão
  olhando. Teto em 1.000 kg e 1.000 cm (10 m): nenhum item de leilão de clube
  chega perto, o que chega perto é o dedo escorregando no teclado. No mesmo
  passe, o mínimo `1` passou a ser declarado no **form** — o
  `PositiveIntegerField` entrega o campo com `min_value=0` e era esse validador
  que respondia ao negativo, dizendo "maior ou igual a 0".
- **Um 500 encontrado e fechado no caminho**: `Decimal("nan")` **não** levanta
  na conversão — levanta na primeira comparação de ordem (`peso <= 0`), e aí já
  é erro 500 na tela de cadastro. `peso_para_decimal` passou a recusar tudo o
  que não é finito (`nan`, `inf`), virando a mesma recusa educada de `"abc"`.
  Há teste.
- **Conferido sem navegador**: formulário renderizado pelo test client +
  Chrome headless, e a **sonda de overflow** (`scrollWidth` × `clientWidth`) não
  acusou estouro em 500px nem em 1280px.

### Deploy
**Publicado em 19/09/2026**, commit `2843f91`. Sequência:

1. Conferido que **nenhum leilão estava ao vivo** (§7.1 avisa que reiniciar com
   um lote aberto pode fazer o laço central subir com o prazo vencido e bater o
   martelo na hora). Os três leilões em produção estão encerrados.
2. Backup do banco do leilão em
   `backup/leilao_antes_medidas_20260920_002539.sqlite3` — o
   `pinhaljunior2-deploy` faz backup **só do `db.sqlite3` do clube**.
3. `pinhaljunior2-deploy` (4e75a19 → 2843f91), healthcheck OK.
4. O passo extra do §7.1: `migrate` (aplicou `leilao/0010`), `collectstatic`
   (67 arquivos), `chown` e restart do `pinhaljunior_leilao.service`.
5. Conferência: `/leilao/entrar/` e `/` em **200**, SSE devolvendo
   `event: estado`, **um worker só** e os três serviços ativos. Confirmado em
   produção que o formulário exige os quatro campos e que a vírgula é aceita.

### Pendências
- Os **16 itens já cadastrados em produção** ficaram sem medida, como previsto.
  Não há migração de dados possível: ninguém sabe o peso deles. A lista da
  preparação os marca com "sem peso/medidas — completar ao editar".

---

## 2026-09-17 - Leilão: quadro de entregas (arrastar quem leva o quê)

### Resumo
Pergunta do clube, conferindo a divisão de entregas: *"se não há cálculo de
rota, como ele sabe que um endereço é perto do outro?"*. A resposta honesta é
**ele não sabe** — compara o **nome** do bairro, e é tudo o que dá para fazer sem
mapa. Dois bairros vizinhos são, para o código, tão distantes quanto dois nos
extremos da cidade.

Comprar mapa seria dependência externa nova, chave paga e uma chamada por
endereço na noite do evento. A decisão foi outra: **a divisão automática vira
ponto de partida e a palavra final passa a ser da equipe**, que conhece a cidade.

### O que foi feito
Um **quadro** em `/caixa/entregas/`: coluna "a distribuir" + uma coluna por
entregador, com as paradas em cartões que se arrastam entre elas. Cada cartão é
uma **pessoa** (com todos os itens dela) e traz o **bairro em destaque** — é por
ele que a equipe decide o que é perto do quê.

### Arquivos criados/alterados
- `leilao/models.py`: `EntregadorLeilao` (a coluna — rótulo, não cadastro) e
  `AtribuicaoEntrega` (a parada e o seu entregador). Migration **0009**.
- `leilao/entregas.py`: `paradas_de`/`ordenar_paradas` extraídos de `dividir`,
  novo `quadro()`, `texto_da_rota(..., nome=)` e `_uniformizar_rotulos`.
- `leilao/views.py`: `entregas_quadro_view`, `entregas_redistribuir_view` e as
  ações `entrega_mover`/`entrega_nome` no POST único da equipe. A divisão saiu
  da tela do caixa.
- `templates/leilao/entregas_quadro.html`, `_parada_entrega.html`, `caixa.html`.
- `static/leilao/css/entregas.css`, `static/leilao/js/entregas_quadro.js`.
- `leilao/tests.py`: +17 testes (`QuadroDeEntregasTests`, 17 casos) e a
  adaptação dos dois de `TelaDeDividirEntregasTests` que liam `context["rotas"]`,
  agora apontando para o quadro. Suíte do leilão: 271 → **288, tudo OK**.
- `docs/MANUAL_LEILAO.md`, `docs/REGRAS_CODEX.md`, `docs/ESTADO_ATUAL.md`,
  `CLAUDE.md`.

### Decisões tomadas
- **Cada arrastada salva na hora, e a recusa desfaz na tela.** Não há botão
  "salvar": a equipe monta rota no fim de uma noite longa. E a tela não pode
  mostrar uma divisão que o banco não tem — é ela que vira a mensagem mandada ao
  voluntário.
- **Semeia uma vez só.** O quadro nasce dividido por bairro; quem paga depois cai
  em "a distribuir". Resemear por cima apagaria o trabalho manual, que é o que o
  quadro existe para guardar. Para recomeçar existe o botão, que pergunta antes.
- **Diminuir colunas devolve a parada para a fila**, não apaga a atribuição: um
  clique de configuração não pode custar o trabalho das outras colunas.
- **O entregador é rótulo, não cadastro.** Nome digitado na hora, valendo só
  naquele leilão — os voluntários mudam a cada evento, e uma agenda seria mais
  uma tela para manter o ano inteiro. O nome entra no topo da mensagem.
- **Tela de computador, por decisão do clube.** Arrastar com o mouse; as colunas
  rolam na horizontal em vez de empilhar, porque ver duas colunas ao mesmo tempo
  é o que torna o arrastar possível.
- **A conferência é do servidor**: `entrega_mover` recusa quem não tem entrega
  pendente naquele leilão e entregador que não existe. Esconder o cartão não
  protege nada.

### Corrigido junto (achado na conferência do módulo)
- **O mesmo bairro abria um cabeçalho por grafia** na rota impressa ("Centro",
  "centro", "CENTRO" viravam três regiões para quem lê). O agrupamento sempre
  esteve certo; o rótulo é que era por pessoa. Agora é **um por região**, a
  grafia mais usada, preferindo a escrita como nome próprio. O teste que existia
  só conferia que caíam na mesma rota, nunca o rótulo.
- **O docstring de `_chave_regiao` prometia o que não fazia**: dava como exemplo
  "Jd. Paulista" × "jardim paulista", que a normalização **não** junta (ela trata
  caixa, acento e espaço, não abreviação). Reescrito, dizendo quem resolve esse
  caso — o quadro.

### Deploy
Em produção em 17/09/2026, commit `4e75a19`. **Tem migration**, então valeu o
passo extra do leilão (`docs/DEPLOY_LEILAO.md` §7.1): depois do
`pinhaljunior2-deploy`, `migrate` (aplicou a `leilao/0009`), `collectstatic` com
as settings do leilão e `restart` do `pinhaljunior_leilao.service`. Conferido
**antes de reiniciar que não havia pregão ao vivo** — reiniciar no meio de um
lote pode fechá-lo no ato, se o prazo vencer durante a subida. Os dois sites
responderam 200.

### Pendências
- O ponto 3 da conferência continua aberto por escolha: **um bairro dominante
  deixa a divisão automática muito desigual** (12/2/0 com 3 entregadores). Agora
  incomoda menos, porque o quadro é feito para corrigir isso na mão, mas a tela
  não avisa antes.
- A UF é campo oculto fixo em `"SP"` e entra em toda linha de endereço da rota.

---

## 2026-09-17 - Mensalidades: editar um mês não joga mais a pessoa para o topo

### Resumo
Relatado pelo clube: em **Mensalidades → Aventureiros**, procurar a criança,
abrir o card e isentar um mês devolvia o painel **na aba Resumo**, com o card
fechado e a busca apagada. Como isentar o ano de uma criança é **mês a mês**, era
procurar o nome de novo a cada clique.

### A causa
As três ações do card (isenção/desconto, ✏️ editar o mês e "Gerar {ano}") são
POST + redirect, e o redirect levava só `?ano=`. O padrão da tela é a aba
**Resumo**, então a volta caía ainda mais longe do que parecia. "Marcar pago" não
sofria disso porque é AJAX — fica na página.

### Arquivos alterados
- `core/views.py`: novo `_volta_mensalidades(request, ano, av_id)`, usado pelos
  três redirects (o de erro do editar também). A view passa `av_aberto`, `busca`
  e `so_deve` ao template.
- `templates/core/mensalidades.html`: o `<details>` do aventureiro ganhou `id` e
  abre sozinho (`av_aberto`); a busca e o "só quem deve" voltam preenchidos.
- `templates/core/_mens_volta.html` (novo): os três campos ocultos de estado de
  tela, incluídos pelos formulários marcados com `data-volta`.
- `static/js/mensalidades.js`: preenche os ocultos no submit, refaz o filtro na
  chegada e rola até o card reaberto.
- `core/tests.py`: +8 testes (`MensalidadeVoltaEdicaoTests`).
- `docs/REGRAS_CODEX.md`, `docs/ESTADO_ATUAL.md`.

### Decisões tomadas
- **O aventureiro vem do SERVIDOR, não da tela.** A cobrança editada sabe de quem
  é (`m.aventureiro_id`), então o card certo reabre **mesmo sem JS** — e um
  campo oculto a mais não vira uma forma de mandar o usuário para outro lugar.
- **Só o que o servidor não tem como saber viaja no formulário**: o texto da
  busca, o "só quem deve" e a aba. É estado de tela; sem JS a volta perde só o
  filtro, nunca o aventureiro.
- **Não virou AJAX.** Seria mais liso, mas a isenção recalcula **todos** os meses
  em aberto do ano: atualizar isso no navegador significaria repetir em JS o
  desenho das linhas de mês. O redirect devolve os valores já recalculados pelo
  servidor, e o toast continua saindo pelo `messages`.
- **O card que voltou aberto escapa do "só quem deve"** até a pessoa mexer no
  filtro: isentar zera a dívida, e ver o card sumir logo depois de salvar parece
  que a edição falhou.
- **`av` inválido na URL não é 404** — é só um card a menos aberto.

### Deploy
Em produção em 17/09/2026, commit `9c7adb9`, healthcheck OK. **Sem migration.**

### Pendências
- As mesmas da aba de cobrança de parcelas (filtro client-side; a linha não diz
  de qual lançamento veio a parcela).

---

## 2026-09-17 - Cobrança de parcelas: só o que venceu e o que vence neste mês

### Resumo
Relatado pelo clube, dois sintomas do mesmo problema na aba **📨 Cobrar parcelas**:

1. a mensagem levava o **parcelamento inteiro** — um acerto em 10x saía com as
   **10** parcelas e um `{total}` que a pessoa não deve hoje;
2. **quem já pagou a parcela do mês continuava sendo cobrado**, por causa das
   parcelas dos meses seguintes, que ainda nem venceram.

### A causa
`_cobrancas_parcelas_familias` filtrava só por `status="aberta"`. Parcela
"aberta" inclui a que vence daqui a oito meses, então:

- a lista de itens da mensagem (e o `{total}`, que é a soma dela) trazia tudo; e
- bastava **uma** parcela futura em aberto para a conta continuar na lista de
  cobrança, mesmo com a do mês quitada.

A regra certa já existia do outro lado da mesma tela: as mensalidades usam
`_q_mens_vencidas()` — *"cobra o mês atual e os meses anteriores em aberto, NUNCA
meses à frente"*. As parcelas do clube nunca ganharam o equivalente.

### Arquivos alterados
- `core/views.py`: novo `_q_parcelas_cobraveis()` (vencidas + as que vencem
  **dentro do mês atual**; parcela **sem vencimento** entra), aplicado em
  `_cobrancas_parcelas_familias`.
- `templates/core/mensalidades.html`: a barra passa a dizer "pessoa(s) com
  parcela **vencida ou deste mês**", o detalhe vira "A cobrar:", o card vazio
  vira "Nada para cobrar agora" e uma nota explica a regra — senão o Diretor
  estranha não achar alguém que ele sabe que tem parcelamento.
- `core/tests.py`: +6 testes; o `setUp` da classe passou a vencer a 1ª parcela
  **neste mês** (um lançamento todo no futuro não aparece mais na cobrança).
- `docs/REGRAS_CODEX.md`, `docs/ESTADO_ATUAL.md`.

### Decisões tomadas
- **A página pública NÃO encolheu.** `_parcelas_abertas_conta` continua
  mostrando o lançamento inteiro: lá a pessoa **pode adiantar** parcela, e é o
  mesmo link que a cobrança manda. A cobrança diz o que vence agora; a página
  mostra o acerto todo. São perguntas diferentes, e há teste para cada uma.
- **Parcela sem vencimento é cobrada.** O campo é `null=True`; dívida sem data é
  dívida de agora, e a decisão contrária a esconderia da cobrança para sempre.
- **A trava é do servidor.** Quem não deve nada este mês some da lista *e* do
  envio: o `parcela_cobranca_enviar_view` monta os destinatários pela mesma
  função, então `usuario_id` forjado no POST não cobra ninguém (há teste).
- **Os textos padrão não mudaram** — "parcelas em aberto" continua verdade para
  o que a mensagem leva agora, e mexer nas constantes `MENSAGEM_*_PADRAO` pediria
  migration (são `default=` de campo).

### Deploy
Em produção em 17/09/2026, commit `e3a2598`, healthcheck OK. **Sem migration** —
a correção não mexe em model, só na query que monta a lista de cobrança. O VPS
vinha do `8cbfc6a`: o `c435333` era só documentação e não chegou a ser publicado
sozinho.

### Pendências
- Continua valendo: o filtro "só quem já me mandou mensagem" é **client-side**
  (o botão individual não o respeita e o servidor não tem gate de WhatsApp); e a
  linha da cobrança não diz **de qual lançamento** a parcela veio.

---

## 2026-09-17 - Cobrança: "sem WhatsApp cadastrado" para quem tem o número

### Resumo
Relatado pelo clube: pessoas da **diretoria** aparecendo na cobrança como "sem
WhatsApp cadastrado", com o botão de enviar desabilitado, tendo o número gravado
na ficha.

Confirmado no banco de produção: das **10** contas com parcela em aberto, **2**
são diretoria **sem filho no clube** — nenhum aventureiro, WhatsApp preenchido na
ficha.

### A causa: um fallback que prometia e não fazia
`_numeros_conta` lê **só a tabela de aventureiros** (pai/mãe/responsável legal das
fichas). Numa conta de diretoria sem filho no clube ele devolve lista vazia, e a
tela conclui que não há número.

Havia até um degrau escrito para isso:

```python
# Sem número nos aventureiros (conta só de diretoria), usa o da ficha.
if not numero:
    numero = _whatsapp_familia(u)
```

Só que `_whatsapp_familia` fazia **exatamente a mesma conta** que acabara de
falhar — `_resolver_origem_numero(_numeros_conta(usuario), origem)` — e devolvia
a mesma string vazia. O comentário dizia "usa o da ficha"; o código nunca tocava
na ficha.

O degrau que faltava (**`_whatsapp_diretoria`**) já existia, e é o que a
recuperação de senha usa desde sempre. A armadilha inclusive já estava escrita lá:
*"`_numeros_conta` não basta: ele só lê os aventureiros e devolve vazio numa conta
só de diretoria."*

### O bug irmão
`_resolver_origem_numero` olhava só o **responsável legal** e desistia:

```python
elif mapa.get("resp"): origem = "resp"
else:                  origem = ""      # ← ignorava pai e mãe
```

Ou seja, a ficha preenchida apenas com o WhatsApp **do pai** ou **da mãe** também
virava "sem número". Nenhuma conta em produção cai nisso hoje, mas é a mesma
classe de erro: dizer que não há número quando há.

### Arquivos alterados
- `core/views.py`: `_whatsapp_familia` cai em `_whatsapp_diretoria`;
  `_resolver_origem_numero` usa o primeiro número disponível; `_cobrancas_familias`
  e `_cobrancas_parcelas_familias` aplicam o mesmo degrau (antes só a segunda
  tentava, e sem efeito).
- `core/tests.py`: +2 testes.
- `docs/REGRAS_CODEX.md`, `docs/ESTADO_ATUAL.md`.

### Decisões tomadas
- **As duas abas de cobrança resolvem o número igual.** Achar números diferentes
  para a mesma conta em telas diferentes é o tipo de divergência que ninguém
  percebe até mandar a mensagem para o lugar errado.
- **Escolher um número é melhor do que dizer que não há.** Quando não há escolha
  nem responsável legal, vale o primeiro que existir.
- **`_whatsapp_diretoria` é o degrau canônico** de quem não tem aventureiro —
  não reescrever essa busca em cada tela.

### Deploy
Em produção em 17/09/2026, commit `8cbfc6a`, healthcheck OK. **Sem migration** —
a correção não mexe em model, só na resolução do número.

### Limpeza dos parcelamentos (a pedido do clube, no mesmo dia)
Todos os lançamentos foram apagados da produção para recadastro do zero: **20
lançamentos e 89 parcelas** (14 ativos + 6 cancelados). Antes de apagar foi
conferido que **não havia nenhuma parcela paga**, nenhum `Pagamento` vinculado e
nenhum `CobrancaParcelaEnviada` — ou seja, nada de dinheiro saiu do caixa nem do
extrato, e nenhum histórico de cobrança foi perdido.

Backup em `/var/www/pinhaljunior2/backup/db_antes_limpar_parcelamentos_20260917_023938.sqlite3`,
feito pela **API de backup do SQLite**, não por cópia de arquivo: com o serviço
rodando, um `cp` pode gravar um arquivo inconsistente.

> **Ao repetir uma limpeza dessas, confira as parcelas PAGAS primeiro.** Apagar
> uma parcela paga apaga uma entrada do caixa e do extrato do clube, e o número
> só volta a fechar com o backup.

### Pendências
- As da revisão de cobrança, ainda abertas: o filtro "só quem já me mandou
  mensagem" é **client-side** (o botão individual não o respeita e o servidor não
  tem gate de WhatsApp); a cobrança de parcelas soma no `{total}` as parcelas
  **que ainda não venceram**; e a linha da cobrança não diz **de qual lançamento**
  a parcela veio (duas iguais ficam indistinguíveis).

---

## 2026-09-17 - Parcelas: o lançamento volta no nome de quem combinou

### Resumo
Bug relatado pelo clube: lançar um parcelamento para um **pai** e ele aparecer na
lista com o nome da **responsável legal** da mesma família.

### O que acontecia
O seletor "para quem" oferece **pai, mãe e responsável legal** como opções
diferentes — quem lança lembra do adulto com quem combinou, e nem sempre é o
responsável legal. Mas as três mandavam o **mesmo** `conta:<id>`:

1. `_resolver_alvo` devolvia só `(usuario, aventureiro)` — **o nome escolhido
   morria no POST**;
2. `pessoa_nome` então **recalculava** o nome pela ficha e caía sempre no
   `resp_nome`.

Ou seja, a escolha nunca chegava ao banco. O nome errado saía em tudo o que lê
`pessoa_nome` — painel de Parcelas, a busca da lista, "📋 Copiar resumo", extrato
do Financeiro, extrato do evento e o próprio toast de confirmação — e, pela mesma
regra dentro de `_nome_da_conta`, também na aba **Cobrar parcelas** e na
**saudação da página pública de pagamento**.

A suíte não pegava porque o único teste do caso escolhia justamente a responsável
legal, o degrau em que as duas regras coincidem.

### A correção
- A opção de Responsáveis passa a carregar o **papel**: `resp:<av_id>:<papel>`.
- `_resolver_alvo` devolve **`(usuario, aventureiro, pessoa)`**, com o nome lido
  **da ficha, no servidor** — um rótulo que o navegador mandasse junto não é
  fonte de verdade.
- O nome é gravado em **`ParcelamentoClube.pessoa`** (migration **0074**) e
  `pessoa_nome` o usa **depois** do aventureiro e **antes** da ficha.
- `_nome_da_conta(usuario, lancamentos)` segue essa pessoa na cobrança e na
  página pública, **só quando todos os lançamentos da conta apontam para ela**.

**O vínculo continua sendo com a CONTA** — mudou só o que a lista mostra.

### De quebra
- Alvo forjado com id não numérico (`av:abc`) estourava `ValueError` dentro do
  `filter` e virava **500 de HTML** numa view cuja recusa é uma mensagem na tela.
  Agora passa por `isdigit` (`_aventureiro_do_alvo`).
- Papel que a ficha não tem preenchido é **recusado**, em vez de gravar um
  lançamento sem nome nenhum na lista.

### Arquivos alterados
- `core/models.py`: campo `pessoa` e a nova ordem do `pessoa_nome`.
- `core/migrations/0074_parcelamentoclube_pessoa.py`: o campo (`AddField`).
- `core/views.py`: `_alvos_responsaveis` (alvo por papel), `_resolver_alvo`
  (3-tupla + validação do id), `_aventureiro_do_alvo`, `CAMPOS_ADULTO_FICHA`,
  `parcelamento_novo_view` (grava `pessoa`) e `_nome_da_conta` (+ as 3 chamadas).
- `core/tests.py`: 3 testes ajustados ao alvo novo e **7** acrescentados.
- `CLAUDE.md`, `docs/REGRAS_CODEX.md`, `docs/ESTADO_ATUAL.md`: a regra e o estado.

### Decisões tomadas
- **`pessoa` é snapshot**, como os outros nomes do sistema: corrigir a ficha
  depois não reescreve o que foi combinado.
- **A conta continua sendo o vínculo.** Guardar o nome é para a tela; trocar o
  vínculo para a pessoa quebraria diretoria sem filho no clube e o link público.
- **Nome divergente entre lançamentos volta ao nome da conta** na cobrança:
  chamar quem recebe a mensagem pelo nome errado é pior do que usar o genérico.
- **Papel do alvo é resolvido no servidor**, nunca aceito do cliente.

### Deploy
Em produção em 17/09/2026, commit `6770e13`: migration **0074** aplicada,
estáticos coletados e healthcheck OK.

**Pendência operacional do leilão.** O deploy trouxe junto o commit `e0d5350`
(leilão — o emoji cedendo a vez para a voz e para o lance), que estava no `main`
e ainda não tinha ido ao ar. Como a pasta é a **mesma** dos dois serviços, o
código novo do leilão **já está no disco**, mas o `pinhaljunior_leilao.service`
**não foi reiniciado** e continua rodando o anterior em memória — é exatamente a
armadilha da §7.1 do `docs/DEPLOY_LEILAO.md`. O passo extra (migrate +
collectstatic com as settings do leilão + restart) **ainda não foi rodado**;
sem ele, os freios de reação novos não estão valendo em produção.

### Pendências
- **Lançamento anterior à migration fica com `pessoa` vazia** e continua
  mostrando o `resp_nome` — a escolha daquele dia não foi gravada e não há como
  recuperá-la. Para corrigir um lançamento já feito, cancelar e lançar de novo.
- Continua valendo a pendência antiga: **editar** um parcelamento já lançado
  (hoje é cancelar e lançar de novo) — é o que resolveria o caso acima sem
  refazer.

---

## 2026-09-16 - Leilão: o emoji cede a vez para a voz e para o lance

### Resumo
Pergunta do clube, e a certa: *no dia não tem só emoji — tem voz ao vivo, lance,
tudo junto.* A rajada de reações estava provada como barata **sozinha**; o que
faltava era garantir, **em código**, que ela não roube o processador do que
importa quando tudo acontece ao mesmo tempo.

### A ordem de importância vira regra
**Voz e lance são o leilão; emoji é enfeite.** Então o enfeite é a primeira
coisa a ser descartada quando aperta — e descartada **calada**: quem tocou já
viu o próprio emoji subir (a tela desenha na hora, sem esperar o servidor),
então ele não perde nada e a tela não tem o que avisar.

Duas travas na **porta de entrada** da reação (`reacoes.aceitar`), fora do
`registrar` — que continua sendo só a regra do balde:

1. **Por pessoa** (0,4 s entre reações). O `reacoes.js` já se segura em 2 por
   segundo, mas o servidor **não pode acreditar no cliente**: um `fetch` num
   console faria 200 por segundo sozinho.
2. **Do processo inteiro** (150 por segundo, somando todo mundo). Passou disso,
   o resto do segundo cai. É o que garante que uma sala eufórica não atrase o
   lance de quem está disputando nem o pacote de voz que sai a cada 20 ms.

A resposta continua **200** quando o freio segura: devolver erro só faria o
celular tentar de novo, que é o oposto do que se quer.

### O que NÃO foi mexido
- **O freio do lance é outro** (`INTERVALO_MIN_LANCE`) e não divide contador com
  o do emoji — há teste provando que encher o teto de reações não atrapalha um
  lance legítimo.
- **O áudio é outro processo** (MediaMTX). O que o leilão faz por ele é não
  gastar CPU à toa — e é isso que este freio garante. A prioridade de CPU
  (`CPUWeight`) e o "parar os outros serviços no dia" continuam em
  `docs/DEPLOY_LEILAO.md`.

### Arquivos alterados
- `leilao/reacoes.py`: `aceitar()`, `limpar_freio()`, `INTERVALO_MIN_POR_PESSOA`,
  `TETO_POR_SEGUNDO`; `limpar()` zera o freio junto.
- `leilao/views.py`: `reagir_view` passa pela porta antes de registrar.
- `leilao/tests.py`: +5 testes (`EmojiNaoAtrapalhaOPregaoTests`).
- `CLAUDE.md`: o módulo de leilão **passou a existir** no arquivo de contexto do
  projeto, com as regras que não se negociam e o passo extra do deploy.

### Decisões tomadas
- **O freio fica na view, não no `registrar`.** `registrar` é a regra do balde e
  é o que os testes exercitam; `aceitar` é proteção de tráfego e vale só para
  quem chega pela rede.
- **Descartar em silêncio.** Erro visível em cima de enfeite gera retentativa —
  mais tráfego exatamente quando há menos CPU.
- **Teto por segundo, não fila.** Reação atrasada não é reação: o excedente é
  jogado fora, nunca guardado para depois.

### Pendências
- As mesmas: Pix real de R$ 1, ensaio de áudio com aparelhos de verdade, trocar
  as senhas `fabiano` e `locutor`, e a data do evento.
- **O teste de carga do dia deve ser combinado**: SSE + lances + `--reacoes` ao
  mesmo tempo, com o MediaMTX no ar — é assim que a noite vai ser.

---

## 2026-09-16 - Leilão: o teto das reações passa a valer para o resumo inteiro

### Resumo
Pergunta do clube depois da rajada: *e se 50 pessoas apertarem o emoji ao mesmo
tempo?* Foi medido, e a medição achou um exagero que estava lá desde o começo.

### O que a medição mostrou (50 pessoas martelando por 10 s)
| | |
|---|---|
| Requisições atendidas | **840** (84/s) |
| Custo de um despejo (o que vai no stream) | **0,06 ms** |
| Despejos por segundo | **2** (fixo, não depende de quanta gente toca) |
| Emojis pedidos num despejo | **240** → agora **42** |

O servidor nunca foi o problema: a view de reação é a mais barata do sistema
(não toca no banco) e o broadcast é **um** resumo a cada meio segundo,
**independente de quantas pessoas tocaram** — é para isso que a agregação existe.

### O exagero: o teto era por emoji, não do resumo
`TETO_POR_DESPEJO` limitava **cada emoji** a 40. Como são seis emojis, um resumo
podia mandar **240** desenhos para um celular que mostra 30. O excedente não ia
para lugar nenhum: só engordava a mensagem e dava trabalho ao aparelho mais
fraco da sala — justamente quem não pode travar.

Agora o teto é do **resumo inteiro**, repartido entre os emojis na proporção em
que foram tocados, com **pelo menos 1 para cada** (a tela precisa mostrar que a
sala mandou seis coisas diferentes, não só a mais votada).

### E o mesmo cuidado no celular
- `soltarVarios` passou a olhar o **espaço livre** (`TETO_NA_TELA - vivos`), não
  o total: sem isso, seis emojis chegando juntos agendavam 30 relógios cada um,
  180 no total, só para descobrir que não havia mais lugar.
- `receber` **reparte o espaço livre** entre os emojis do resumo. Antes o
  primeiro da lista tomava a tela toda e os outros cinco não apareciam.

### Prova antes do evento: `leilao_carga --reacoes`
O comando de carga ganhou a rajada de emoji: todos os `--cookie` martelando ao
mesmo tempo, medindo requisições por segundo e o tempo de resposta. **O lance é
raro** (um por vez, e a pessoa pensa antes); **o emoji é o contrário** — se
alguma coisa vai apertar o servidor no dia, é ela. Rodar de outra máquina,
contra a produção, antes do evento.

    python manage.py leilao_carga --url https://pinhaljunior.com.br/leilao \
        --ouvintes 100 --cookie "leilao_sessionid=..." --cookie "..." --reacoes 20

### Arquivos alterados
- `leilao/reacoes.py`: `drenar()` com teto do resumo inteiro e reparte proporcional.
- `static/leilao/js/reacoes.js`: espaço livre em `soltarVarios`, reparte em `receber`.
- `leilao/management/commands/leilao_carga.py`: `--reacoes` e o `_rajada`.
- `leilao/tests.py`: +3 testes.

### Decisões tomadas
- **Se um dia apertar, o número a mexer NÃO é `EMOJIS_POR_TOQUE`.** Ele não muda
  quantas requisições chegam — muda só o que já viaja dentro do resumo. Quem
  controla a pressão sobre o servidor é o `INTERVALO_ENVIO` do `reacoes.js` (o
  espaçamento dos envios). Está escrito no aviso do próprio comando de carga.
- **Saturar é o comportamento certo**: reação atrasada não é reação, então o
  excedente é descartado, nunca enfileirado.

### Pendências
- As mesmas: Pix real de R$ 1, ensaio de áudio com aparelhos de verdade, trocar
  as senhas `fabiano` e `locutor`, e a data do evento. A rajada de emoji entra
  no mesmo teste de carga.

---

## 2026-09-15 - Leilão: cada toque de emoji vira uma rajada (sem custo novo)

### Resumo
O emoji subia **um por toque** e sumia no meio do pregão. Agora cada toque solta
**4** (`reacoes.EMOJIS_POR_TOQUE`), e isso **não custa uma requisição a mais**:
o que viaja é a **contagem** dentro do resumo que já ia de meio em meio segundo.
A agregação — que é o que segura o módulo em pé com 50 pessoas — continua
exatamente igual.

### De quebra, o em-dobro de quem toca
O resumo é um **broadcast**: ele volta para todo mundo, inclusive para quem
mandou. Como a tela já desenha o próprio emoji na hora (para o toque responder
sem esperar a ida e volta), quem tocava via **duas** vezes o mesmo emoji.

Agora o que sai da tela fica anotado como **crédito** e é descontado do próximo
resumo. Provado no navegador: 1 toque → 4 na tela; o resumo com o meu toque
dentro → continua 4; o resumo de outra pessoa → 8.

O crédito **expira em 4 s**. Se a requisição não chegar (rede ruim), aquele
emoji nunca voltará no resumo — e um crédito pendurado comeria os emojis **dos
outros** pela noite inteira.

### Arquivos alterados
- `leilao/reacoes.py`: `EMOJIS_POR_TOQUE` e a multiplicação dentro do `registrar`.
- `leilao/views.py` + `templates/leilao/leilao.html`: o número vai para a tela
  em `data-rajada`.
- `static/leilao/js/reacoes.js`: rajada local, crédito e desconto.
- `static/leilao/js/leilao.js`: passa o número na ligação.
- `leilao/tests.py`: +6 testes (um antigo ajustado).

### Decisões tomadas
- **A multiplicação é do servidor.** O cliente manda **toques** (no máximo 10
  por requisição) e lê o `data-rajada` só para descontar o que já desenhou.
  Deixar o cliente mandar o total permitiria a um toque forjado encher a tela de
  todo mundo — e o teto por despejo é a última linha, não a primeira.
- **Os dois tetos ficam como estão** (40 por despejo no servidor, 30 na tela).
  Com rajada eles são alcançados mais rápido, e é isso que se quer: em momento
  de euforia a tela satura cheia, em vez de tentar desenhar tudo e travar o
  celular fraco.

### Pendências
- As mesmas: Pix real de R$ 1, ensaio de áudio com aparelhos de verdade, trocar
  as senhas `fabiano` e `locutor`, e a data do evento.

---

## 2026-09-15 - Leilão: revisão de bugs (dinheiro no chão, porta lateral e contagem inflada)

### Resumo
Revisão do módulo inteiro depois das duas rodadas de hoje. Nove correções; três
delas são de dinheiro ou de acesso, e nenhuma aparecia na tela.

### 1. Pagar o Pix ANTIGO não dava baixa (o mais grave)
Refazer a cobrança — que é o que "+15 min" e "vai pagar depois" fazem — troca a
FK `Arremate.pagamento` para o código novo. A cobrança anterior fica **sem
arremate nenhum**, e ela é justamente a que está **na tela da pessoa** no
instante em que o caixa aperta o botão.

Resultado: ela paga aquele código, o webhook chega, o pagamento é aprovado — e
**ninguém é marcado como pago**. O dinheiro entra e o caixa continua cobrando.

Agora o arremate é recuperado da **referência** (`LEILAO-<id>`,
`LEILAO-<id>-R<timestamp>`), que nasce na criação e não muda:

- `_arremates_do_pagamento` fecha o caminho do **webhook**;
- `cobrancas_do_arremate` fecha o da **consulta de reforço** — que vira o único
  caminho do dinheiro quando `site_url` está vazio e **não existe webhook**;
- `marcar_pago` passou a apontar para a cobrança que foi **realmente paga**: é
  dela que sai a taxa, e apontar para a que ninguém pagou mente no extrato.
- O prefixo da referência é conferido pelo id de verdade — `LEILAO-1` não pode
  pescar `LEILAO-12`.

### 2. Dois cliques em "vai pagar depois" = dois Pix vivos
`marcar_combinado` não era idempotente e emitia um código novo a cada chamada. O
botão continua na tela até a página se refazer, então bastava o segundo clique
para existirem dois códigos válidos do mesmo item — e o caixa sem saber qual a
pessoa pagou. Agora ele sai cedo se o arremate já está combinado (ou pago), e o
`caixa.js` tira os botões da linha assim que ela vira "combinado".

### 3. A senha `1234` tinha duas portas laterais
- **Sem freio de tentativas**, dava para varrer `maria/1234` da internet. E quem
  acertasse **primeiro** trocaria a senha, **trancando a voluntária de verdade
  do lado de fora**. Entrou um freio em memória (10 erros por IP em 5 min, zerado
  no acerto). Não é proteção contra ataque distribuído — é o suficiente para o
  que este sistema é.
- **O `/admin/` do leilão aceitava a conta**, porque o Django o abre para
  qualquer `is_staff` — e `is_staff` é exatamente o que toda conta da equipe tem.
  Agora o admin deste serviço é **só de superusuário**.

### 4. O recado prometia a senha `1234` para quem já tinha trocado
"📋 Copiar acesso" mandava sempre `Senha: 1234`. Para quem já escolheu a dela,
isso é entregar uma credencial que não funciona — e fazer a pessoa achar que o
acesso quebrou. A senha só entra no recado **enquanto é a provisória**.

### 5. A contagem de gente incluía a equipe
`HUB.conectados` contava todas as conexões, e as telas da mesa do locutor e do
caixa ficam abertas a noite toda. Três voluntários viravam três pessoas
esperando — justo no número que o locutor usa para decidir **a hora de começar**.
As telas da equipe passam `?equipe=1` e ficam fora da contagem. O **teto** de
conexões continua olhando o total (é limite de recurso, não número sobre gente).

### 6. A frase "já estão aqui" congelava
O evento `online` atualizava só o contador do topo. Na tela de espera — a fase em
que esse número muda o tempo todo — a frase ficava parada no valor de quando a
pessoa conectou.

### 7. A linha filtrada reaparecia sozinha
`pintarLinha` reescrevia `className` inteiro e apagava o `busca-oculto`: quem
tinha filtrado a lista via a linha voltar quando o pagamento dela caía.

### 8. A recarga do caixa jogava fora a aba aberta
As abas são só JS. Com a recarga automática, quem tinha acabado de montar as
rotas de entrega voltava para "Pagamentos" no meio do trabalho. A aba agora fica
no `sessionStorage` (com try/catch — aba anônima pode não ter), e quem pede a
divisão volta direto nela.

### 9. Entradas da internet que viravam 500
`minutos` (esticar prazo) e `quantos` (reação) iam direto para `int()`. Um valor
não numérico devolvia um 500 de HTML numa view cujas recusas são todas JSON — a
tela ficaria muda no meio do evento.

### Arquivos alterados
- `leilao/servicos.py`: `_arremates_do_pagamento`, `cobrancas_do_arremate`,
  `_id_da_referencia`, `conferir_pagamento` reescrito, `marcar_combinado`
  idempotente, `marcar_pago` aponta para a cobrança paga.
- `leilao/hub.py`: `_assinantes` virou dict (fila → é público?), `conectados` e
  `total` separados, `assinar(publico=…)`.
- `leilao/views.py`: `?equipe=1` no stream, teto pelo `total`, `minutos`
  validado, freio de login com `_ip_do`.
- `leilao/equipe.py`: freio de tentativas, recado condicional à senha provisória.
- `leilao/reacoes.py`: `quantos` inválido não estoura.
- `config/urls_leilao.py`: admin só de superusuário.
- `templates/leilao/{locutor,caixa}.html`: `?equipe=1`.
- `static/leilao/js/caixa.js`: aba lembrada, `pintarLinha` preserva o filtro,
  "combinado" limpa os botões e agenda recarga.
- `static/leilao/js/leilao.js`: `online` redesenha as boas-vindas; `arremate_pix`
  reabre o QR quando o código foi refeito; ouvinte de `arremate_prazo`.
- `leilao/tests.py`: +15 testes.

### Decisões tomadas
- **A referência é a âncora do dinheiro**, não a FK. A FK aponta para uma
  cobrança e é trocada quando o Pix é refeito; a referência guarda o id do
  arremate e nunca muda. Cobrança nova que se crie por outro caminho **precisa
  manter esse formato**.
- **O freio de login mora na memória do processo**, como o hub e o cadeado de
  lance — o serviço roda com um worker só. Sem Redis, sem peça nova.
- **O teto de conexões e a contagem de pessoas são números diferentes.** Misturar
  os dois foi o que deixou a equipe entrar na conta.

### Pendências
- As mesmas: Pix real de R$ 1, ensaio de áudio com aparelhos de verdade, trocar
  as senhas `fabiano` e `locutor`, e a data do evento.

---

## 2026-09-15 - Leilão: o caixa vira mesa de trabalho e quem chega é recebido

### Resumo
Rodada vinda de usar a tela no celular. Seis coisas, todas do mesmo tipo: o
sistema estava certo e a **pessoa operando** ficava sem o que precisava na mão.

### 1. Os emojis cobriam o botão de enviar a mensagem
A coluna de reações e o trilho por onde os emojis sobem moram no canto inferior
**direito** — que é exatamente onde fica o **➤** do chat. No celular um cobria o
outro: a pessoa escrevia e o toque de enviar caía num emoji.

Com o chat aberto, os dois **trocam de lado** (`body.chat-aberto`, posta pelo
`desenharChat`). O botão de lance não está na tela nessa hora, então a esquerda
está livre. Não foi preciso esconder nada.

### 2. O caixa só via "Pago" depois do F5
A tela era estática **de propósito** ("tela de conferência, não de pregão"), e na
prática isso virou o caixa recarregando a página para saber se o Pix caiu — ou
pior, não recarregando e cobrando quem já tinha pagado.

Agora ela ouve o **mesmo stream (SSE)** do pregão, com duas regras:

- **a linha muda na hora** (selo, cor, os botões de cobrança somem) — é o retorno
  que o caixa precisa ver no segundo em que acontece, e ela **pisca uma vez**
  para ele saber *onde* mudou numa lista grande;
- **a recarga é adiada** enquanto alguém digita ou está com o Pix aberto. O item
  pago precisa entrar na aba "A entregar" e os totais têm de fechar, mas nada
  disso justifica apagar o "quem recebeu" no meio de uma frase. Não dando, entra
  o botão **🔄 Há novidades — atualizar**.

### 3. Falar com a pessoa: um toque
Botão **💬 WhatsApp** em cada arremate (e ao lado de cada telefone na entrega),
com `wa.me` montado no servidor (`Participante.whatsapp_link`, que acrescenta o
**55** — o cadastro pede só DDD + número). Digitar celular com o leilão rolando é
onde a conversa morre.

### 4. "Vai pagar depois" agora entrega o Pix
O botão existia e resolvia metade: o item não voltava para a fila, mas o caixa
ficava sem nada para **mandar** para a pessoa. Entrou o **📋 Pix**, que abre o
copia e cola do arremate e o botão **💬 Mandar no WhatsApp da pessoa**, com a
mensagem pronta do servidor.

E o código passou a valer **7 dias** (`MINUTOS_PIX_COMBINADO`), não 24 h: "vai
pagar depois" na prática é hoje à noite, amanhã, ou quando a pessoa conseguir.
O **arremate combinado nunca vence** — já era assim, e agora há teste.

### 5. "Me dá mais uns minutos" — botão ⏱️ +15 min
`servicos.estender_prazo` soma o tempo **e refaz o Pix**. Esticar só o `expira_em`
seria meia solução: o código foi criado com a validade do prazo antigo e vence
junto. A pessoa ficaria com mais tempo na tela e um copia e cola que o banco
recusa.

Soma **a partir de agora**, não do prazo antigo: o caso real é o prazo prestes a
vencer (ou vencido há segundos), e somar ao passado daria tempo nenhum.

### 6. Quem chega antes do leilão lê "Intervalo"
E "intervalo" é mentira para quem acabou de entrar: não há intervalo nenhum, o
leilão não começou — a palavra dá a impressão de que ela perdeu o começo.

Agora, antes do primeiro item, a tela mostra **boas-vindas**: título e uma lista
de informações úteis, **escritas pelo clube** e editáveis em
`/preparacao/<id>/editar/` — inclusive **com o leilão no ar** (ao salvar, o estado
é publicado e as telas abertas se redesenham sozinhas). Junto vai a **contagem de
quem já está esperando**, em tempo real: é o número que o locutor usa para
decidir a hora de começar, e para quem espera é o sinal de que o leilão está
vivo. O separador é `Leilao.ja_comecou()`, não "existe último vendido".

### Arquivos criados/alterados
- `leilao/models.py`: `Leilao.boas_vindas_titulo`/`boas_vindas_texto`,
  `Leilao.ja_comecou()`, `Participante.whatsapp_link`.
- `leilao/migrations/0008_…`: os dois campos de boas-vindas.
- `leilao/servicos.py`: `estender_prazo()`, `MINUTOS_PIX_COMBINADO`, evento
  `arremate_prazo`, `situacao` no `arremate_combinado`.
- `leilao/estado.py`: `comecou` e `boas_vindas` no estado público.
- `leilao/views.py`: `caixa_pix_view`, `_texto_pix_whatsapp`, `leilao_editar_view`,
  ação `prazo` no POST da equipe (área **caixa**).
- `leilao/urls.py`: `/caixa/arremate/<pk>/pix/` e `/preparacao/<pk>/editar/`.
- `leilao/forms.py`: os campos de boas-vindas no `LeilaoForm`.
- `templates/leilao/`: `caixa` (botões, modal do Pix, cartão de dividir entregas),
  `leilao` (bloco de boas-vindas), `leilao_form` (novo), `preparacao` (✏️ Editar).
- `static/leilao/js/caixa.js`: SSE, modal do Pix, recarga adiada.
- `static/leilao/js/leilao.js`: `desenharBoasVindas`, `body.chat-aberto`.
- `static/leilao/css/{leilao,locutor}.css`.
- `leilao/tests.py`: +23 testes.

### Decisões tomadas
- **A divisão das entregas continua sendo um botão que alguém aperta**, e a tela
  agora diz por quê: só entra o que **já foi pago**, e no meio do pregão a lista
  ainda está crescendo. Rodar sozinha dividiria uma lista pela metade.
- **Esticar prazo é do caixa**, não do locutor (`ACOES_AREAS`): é conversa de
  quem cuida do dinheiro. Há teste com o locutor levando 403.
- **A mensagem do Pix termina no código.** É assim que a pessoa consegue segurar
  o dedo em cima dele e copiar no celular; qualquer texto depois atrapalha a
  seleção.
- **A tela de boas-vindas é texto do clube, não do sistema.** Quem sabe o que a
  pessoa precisa ler é quem vai conduzir a noite — e ele muda de ideia com o
  evento rolando, por isso a edição funciona com o leilão no ar.
- **"0 pessoa(s)" não vai para a tela.** A frase inteira é montada no cliente,
  com plural certo: é a primeira coisa que a pessoa vê do clube.

### Pendências
- As mesmas: Pix real de R$ 1, ensaio de áudio com aparelhos de verdade, trocar
  as senhas `fabiano` e `locutor`, e a data do evento.
- A recarga do caixa é a página inteira. Funciona e é simples; um endpoint JSON
  só para a lista seria o passo seguinte, se a tela crescer.

---

## 2026-09-15 - Leilão: o diretor cadastra a equipe pela tela (aba Usuários)

### Resumo
Até aqui, dar acesso a um voluntário do leilão só era possível pelo comando
`leilao_papel`, no terminal do servidor — o que significa que **ninguém da
equipe conseguia fazer isso**, e que um ajudante que aparecesse na hora do
evento ficava de fora. Entrou a aba **👤 Usuários** na barra da equipe, visível
só para o **diretor**: nome, função e pronto.

A conta nasce com a senha **`1234`**, igual para todo mundo, e **no primeiro
acesso o sistema exige que a pessoa troque**. Enquanto ela não trocar, a única
tela que abre é a da troca.

### A senha padrão é um bilhete, não um segredo
É o desenho todo em uma frase. `1234` existe para ser **dita em voz alta** numa
mesa de evento ("seu usuário é maria, senha 1234") e digitada no celular em três
segundos. O que a torna segura não é ela — é o fato de **valer uma entrada só**:

- a guarda está em `papeis.exige`, `papeis.exige_diretor` e no `equipe_view`, e
  também **no POST único da equipe** (`/equipe/acao/`), que devolve 403. Esconder
  a tela não protege nada se o botão continuar respondendo por `fetch`;
- a senha nova **pode ser fraca** — `123` passa. Decisão do clube, e ela tem
  motivo: quem digita é um voluntário, no celular, no meio de um evento, numa
  conta que abre telas de leilão. Exigir oito caracteres com número e símbolo ali
  produz senha anotada em papel, que é pior. Os validadores do Django ficam de
  fora **de propósito**;
- a **única** senha recusada é a própria `1234`: aceitá-la faria a troca não
  trocar nada, e a conta seguiria com a senha que a mesa inteira ouviu.

### Por que um model novo (e não `last_login`)
`ContaEquipe.senha_provisoria` responde a pergunta que o `User` do Django não
responde: *esta pessoa ainda está com a senha que o diretor entregou?*

`last_login` parece servir e não serve: o Django o preenche **no momento do
login**, antes da troca. Quem entrasse e fechasse o navegador no meio ficaria com
a senha padrão para sempre, e o sistema acharia que já estava resolvido.

**Quem não tem registro não é cobrado.** As contas que já existiam — e as do
`leilao_papel`, que sorteia senha forte — nunca tiveram senha padrão; forçá-las
a trocar seria inventar um problema no dia do evento.

### O usuário de acesso sai do nome
O diretor digita **nome e função**; o login é gerado (`maria`). Repetiu, vira
`maria.souza`; repetiu de novo, entra o número. O campo de usuário continua lá,
**opcional**, para quem quiser escolher.

Curto porque é **ditado em voz alta**: nessa hora, curto vale mais que único.

### Arquivos criados/alterados
- `leilao/equipe.py` (novo): `SENHA_PADRAO`, `criar_conta`, `definir_papeis`,
  `resetar_senha`, `definir_senha`, `precisa_trocar_senha`, `usuario_sugerido` e
  `recado_de_acesso`. Serviço, como `servicos.py` e `entregas.py` — a view não
  tem regra.
- `leilao/models.py`: `ContaEquipe` (OneToOne com o `User`).
- `leilao/migrations/0007_contaequipe.py`.
- `leilao/papeis.py`: `ITEM_USUARIOS` no menu do diretor, `senha_pendente`,
  `exige_diretor` e a guarda da senha dentro do `exige`.
- `leilao/forms.py`: `UsuarioEquipeForm` e `TrocarSenhaForm`.
- `leilao/views.py`: `usuarios_view`, `usuario_acao_view`, `trocar_senha_view`,
  `_pode_mexer`; guarda no `equipe_view` e no `locutor_acao_view`.
- `leilao/urls.py`: `/equipe/usuarios/`, `/equipe/usuarios/<pk>/`, `/equipe/senha/`.
- `templates/leilao/usuarios.html`, `templates/leilao/trocar_senha.html` (novos);
  `equipe.html` ganhou a descrição do cartão.
- `static/leilao/js/usuarios.js` (novo) e `static/leilao/css/locutor.css`.
- `leilao/tests.py`: +27 testes.

### Decisões tomadas
- **Usuários não é um papel, é o que o diretor faz por ser diretor.** Por isso
  não entrou em `AREAS` (ninguém é "o usuário de usuários") e sim num item de
  menu próprio, com decorator próprio. O template continua iterando o menu —
  nada de `{% if %}` por papel chumbado no HTML.
- **Funções acumulam, e a tela mostra isso** (caixas de seleção, não uma lista
  suspensa): no evento pequeno o mesmo voluntário faz duas coisas, regra que o
  módulo já seguia.
- **Cadastro sem função é recusado.** Conta sem papel entra e não vê tela
  nenhuma — não seria um cadastro, seria uma armadilha para descobrir no dia.
- **Formulários POST comuns, sem `fetch`.** Esta tela não está no pregão; um
  POST com recarga é mais robusto do que JSON no meio de um evento com internet
  ruim. O JS novo só confirma o destrutivo e filtra a lista.
- **Duas travas contra o diretor se trancar fora**: ninguém desliga a própria
  conta, e ninguém tira a própria função de diretor. As duas no servidor.
- **Conta de superusuário só é alterada por superusuário** — um diretor
  voluntário não reseta a senha de quem administra o sistema.
- **O bilhete vem pronto do servidor** (`recado_de_acesso`) numa
  `<textarea class="copiar-fonte">` com o `copiar_texto.js` do clube, como manda
  a convenção. Ele leva **uma** pessoa: usuário, senha e link — nada de terceiro.
- **`update_session_auth_hash` na troca.** Sem ele o Django invalida a sessão e
  a pessoa cai no login logo depois de fazer o que o sistema exigiu. Há teste.

### Pendências
- As mesmas: Pix real de R$ 1, ensaio de áudio com aparelhos de verdade, trocar
  as senhas `fabiano` e `locutor`, e a data do evento.
- A tela **não exclui** conta, só desliga (`is_active`). Desligar é reversível e
  preserva o histórico de quem deu baixa e quem entregou.

---

## 2026-09-14 - Leilão: divide as entregas entre os voluntários

### Resumo
A aba "A entregar" do caixa ganhou um campo **"dividir entre N entregadores"**:
a tela monta uma rota por voluntário, cada uma com seu botão de copiar, pronta
para mandar no WhatsApp dele. E o campo de observação da entrega parou de pedir
**rastreio** — a entrega é na mão, por voluntário, na casa da pessoa: não existe
código nenhum para anotar, e o campo pedindo um só fazia hesitar quem preenchia
com pressa. Ficou "Quem recebeu…".

### O que ele faz — e o que NÃO faz
**Não consulta mapa.** O cadastro guarda rua, número, bairro e cidade, não
coordenada; buscar uma seria dependência externa nova e uma chamada por endereço
na noite do evento. Ele faz o que uma pessoa faria com o mapa aberto: **junta por
bairro** e divide os bairros equilibrando o número de paradas.

**A tela declara esse limite em voz alta**, e isso é parte do recurso: a equipe
vai confiar no resultado numa mesa de evento, e precisão inventada é pior do que
limite declarado. Dois bairros vizinhos podem cair com entregadores diferentes —
quem conhece a cidade ajusta em dez segundos.

### Arquivos criados/alterados
- `leilao/entregas.py` (novo): `dividir()` e `texto_da_rota()`. Funções puras,
  fáceis de testar sem subir tela.
- `leilao/views.py`: `caixa_view` lê `?entregadores=N` e monta as rotas.
- `templates/leilao/caixa.html`: formulário, o aviso do limite, uma seção por
  entregador (`<details>`) e o `<textarea>` de cópia de cada rota. Rastreio saiu
  do campo de observação.
- `static/leilao/css/locutor.css`: `.form-entregadores`, `.rotas`, `.rota*`.
- `docs/MANUAL_LEILAO.md`: subseção "Dividir entre os entregadores".
- `leilao/tests.py`: +16 testes.

### Decisões tomadas
- **A unidade da divisão é a PESSOA, não o item.** Dois itens da mesma casa são
  uma visita só; contar itens faria um entregador parecer sobrecarregado sem
  estar.
- **Bairro nunca é partido.** Dividir um mesmo bairro entre dois entregadores é
  exatamente o que a divisão existe para evitar.
- **A chave da região é normalizada** (sem acento, sem caixa, espaços
  colapsados). Cada pessoa digita o bairro de um jeito, e "Jd. Paulista" versus
  "jardim paulista" faria o entregador percorrer a mesma rua duas vezes.
- **Guloso LPT, não ótimo exato.** A região maior vai para quem está mais leve.
  Fica perto do equilíbrio ideal e — o que importa mais aqui — é conferível a
  olho por quem está na mesa do evento.
- **Determinístico.** O parâmetro vive no GET e o empate desempata pelo índice:
  a equipe recarrega a tela, manda o link para outra pessoa da mesa e vê a mesma
  divisão.
- **Mais entregadores do que bairros deixa alguém sem rota, e a tela mostra.**
  Inventar uma divisão para preencher seria pior.

### Nota
O **CEP** seria o único dado do cadastro com noção geográfica automática (ele
codifica região), e ele saiu do formulário hoje, de propósito — o formulário
curto vale mais. Fica registrado de onde viria uma divisão mais fina, se um dia
importar.

### Pendências
- As mesmas: Pix real de R$ 1, ensaio de áudio com aparelhos de verdade, trocar
  as senhas `fabiano` e `locutor`, e a data do evento.

---

## 2026-09-14 - Leilão: numeração dos itens e fim do cronômetro

### Resumo
Duas coisas, as duas vindas de olhar o sistema com o evento na cabeça.

**Cada item ganhou um número** — a etiqueta que vai colada no objeto físico, o
que liga o que está na tela ao que está na prateleira. Gerado sozinho.

**E o cronômetro foi embora de vez.** Ele já não fechava nada (o locutor é quem
bate o martelo), mas os restos continuavam na tela: campos de configuração
pedindo "tempo por lote" e "tempo extra", o botão +Ns, a opção "reiniciar a cada
lance". Configuração para um recurso que não existe só confunde quem monta o
leilão. **Pausar foi junto**, pelo mesmo raciocínio: para segurar o pregão basta
não abrir o próximo item.

### O número do item
- `Lote.numero`, gerado no `save()` a partir de `Leilao.ultimo_numero_item`.
- **O contador só sobe.** A primeira versão usava `Max("numero")` do que existe
  — e o teste pegou: apagando o último item, o próximo cadastro repetia o número
  dele. Um número que talvez já esteja colado numa caixa. O contador separado é
  o que garante que número usado não volta.
- **Não muda nunca**: item que volta para a fila por falta de pagamento volta
  com a mesma etiqueta, e continua com ela se for arrematado de novo.
- **Não é `ordem`.** A ordem é a fila e muda a cada reorganização da noite.
- **Não vai no broadcast**: "item nº 12" contaria ao público que existem pelo
  menos 12 itens. Chega à mesa pelo `/locutor/dados/`, com a fila.
- Aparece na preparação, na mesa, no caixa e **primeiro na linha** do roteiro de
  entrega — quem separa as caixas procura a etiqueta, não o nome. A busca do
  caixa acha por ele.

### Arquivos criados/alterados
- `leilao/models.py`: `Lote.numero` + `Leilao.ultimo_numero_item` + `save()` +
  `UniqueConstraint(leilao, numero)`. Campos do cronômetro marcados dormentes.
- `leilao/migrations/0006_...`: a ordem das operações importa — o `RunPython` do
  meio numera o que já existe (e acerta o contador) **antes** de a constraint de
  unicidade passar a valer; sem ele, todos ficariam com `numero=0` e a criação
  da constraint quebraria.
- `leilao/servicos.py`: `somar_tempo` e `pausar_lote` removidos; `abrir_lote` não
  liga relógio; `dar_lance` perdeu "tempo esgotado" e a recusa por pausa;
  `verificar_prazos` não olha mais item em pregão.
- `leilao/views.py`: ações `tempo`, `pausar` e `retomar` removidas; a mesa passou
  a receber `numero_atual` e o `numero` de cada item da fila.
- `leilao/estado.py`: saíram `fecha_em`, `total_segundos`, `fechamento_automatico`
  e `pausado`.
- `leilao/forms.py`: os três campos de tempo saíram da configuração do leilão.
- `static/leilao/js/locutor.js`: número na etiqueta e na fila; o desenho da
  contagem regressiva e o botão de pausa saíram.
- `static/leilao/js/leilao.js`: o estado "PAUSADO" do botão de lance e o ouvinte
  de `cronometro` saíram.
- `static/leilao/css/leilao.css`: o anel de cronômetro inteiro.
- `static/leilao/css/locutor.css`: `.item-numero` (pílula) entrou; `.mesa-crono.pausado` saiu.
- `templates/leilao/`: `preparacao`, `locutor`, `lotes`, `caixa`.
- `docs/MANUAL_LEILAO.md`: seção nova "O número do item" (é a equipe que cola as
  etiquetas), a tabela de botões e a seção do cronômetro reescritas.
- `leilao/tests.py`: +19 testes; 8 testes do cronômetro/pausa removidos.

### Decisões tomadas
- **Contador no leilão, não `Max()`.** É a diferença entre "o próximo número
  livre" e "o próximo número nunca usado". Só o segundo serve quando o número
  existe no mundo físico.
- **Numeração por leilão, começando do 1.** A etiqueta é do evento daquela
  noite; começar o de dezembro no item 87 não diria nada a ninguém.
- **A constraint de unicidade fica**, como última linha de defesa: dois itens com
  a mesma etiqueta é o erro que estraga a entrega, e falhar no cadastro é muito
  melhor do que descobrir na porta da casa de alguém.
- **`servidor_em` continua no estado** mesmo sem cronômetro: é por ele que a mesa
  calcula o silêncio pelo relógio do servidor.
- **O relógio da mesa fica, contando para cima.** Nunca foi contagem regressiva
  depois que o martelo virou manual: ele mostra há quanto tempo a sala está
  calada, que é o que ajuda a decidir. Não fecha nada.

### Pendências
- As mesmas: Pix real de R$ 1, ensaio de áudio com aparelhos de verdade, trocar
  as senhas `fabiano` e `locutor`, e a data do evento.

---

## 2026-09-14 - Leilão: tira a música e o desfazer, conserta o chat órfão

### Resumo
Rodada vinda de usar o sistema de verdade. Saíram dois recursos que o clube
olhou prontos e não quis — a **música de fundo** e o **desfazer lance** — e
entrou a correção de um bug que apareceu no teste: **a caixa de conversa ficava
de pé depois de o leilão sair do ar**, e o servidor recusava tudo que fosse
digitado nela.

Os dois recursos removidos foram decisão de ouvido/de mesa, não de código: o
tipo de coisa que só dá para julgar com a tela funcionando. A música chegou a
ser escrita e refeita antes de sair; o trabalho não foi desperdiçado, foi o que
permitiu decidir.

### O bug do chat
`chat_aberto_ate` é só uma hora futura gravada no banco — ela **não sabe que o
leilão acabou**. `Leilao.chat_aberto` olhava só o relógio; a view de envio
perguntava outra coisa (`Leilao.ao_vivo()`). Duas fontes de verdade
discordando: **uma abria a porta e a outra recusava quem passasse por ela**. Na
tela: a pessoa via o campo de conversa, digitava, e levava "nenhum leilão ao
vivo" sem entender por quê.

Corrigido nos dois lados e na mensagem:
- `Leilao.chat_aberto` passou a exigir `status == "ao_vivo"`;
- `mudar_status` fecha o chat ao sair do ar **e** limpa o `chat_aberto_ate` do
  leilão que é encerrado para dar lugar a outro (aquele `update` em massa não
  mexia nisso), publicando `chat_estado` para a caixa sumir da tela em vez de a
  pessoa descobrir no envio;
- no cliente, `desenharChat` também exige `estado.ativo`;
- a recusa passou a dizer **"O leilão foi encerrado."** — "nenhum leilão ao
  vivo" era verdade para o servidor e mentira para quem estava na tela.

### Arquivos criados/alterados
- `static/leilao/js/som.js`: `MusicaLeilao` removida. `SomLeilao` (os efeitos
  de lance, superado, vendido e arremate) **fica** — nunca esteve em questão.
- `static/leilao/js/leilao.js`: `MUSICA_URL`, `aplicarMusica()` e o ouvinte do
  evento `musica` saíram.
- `static/leilao/js/locutor.js`: botão, controle de volume (com o *debounce* de
  300 ms) e o ouvinte saíram.
- `templates/leilao/leilao.html`: `<audio id="audioMusica">` e `data-musica`.
- `templates/leilao/locutor.html`: o bloco 🎵 da mesa.
- `static/leilao/css/locutor.css`: regras `.musica-*`.
- `leilao/views.py`: `_musica_url()`, o contexto `musica_url`, a ação `musica`
  do POST e a linha dela em `ACOES_AREAS`.
- `leilao/servicos.py`: `ajustar_musica()`.
- `leilao/estado.py`: a chave `musica` do estado público.
- `leilao/forms.py`: o campo `musica` da tela de Configuração.
- `leilao/models.py`: campos mantidos, marcados como **dormentes**.
- `leilao/tests.py`: `MusicaTests` deu lugar a `SemMusicaDeFundoTests`.

**Desfazer lance (removido):**
- `templates/leilao/locutor.html`: o botão ↩.
- `static/leilao/js/locutor.js`: a confirmação e o ouvinte de `lance_desfeito`.
- `static/leilao/js/leilao.js`: o ouvinte de `lance_desfeito`.
- `leilao/views.py`: a ação `desfazer` e a linha dela em `ACOES_AREAS`.
- `leilao/servicos.py`: `desfazer_ultimo_lance()`.
- `leilao/tests.py`: 5 testes do desfazer deram lugar a `SemDesfazerLanceTests`.
- `docs/MANUAL_LEILAO.md`: a linha do botão na tabela do locutor.

**Chat órfão (corrigido):**
- `leilao/models.py`: `chat_aberto` exige leilão no ar.
- `leilao/servicos.py`: `mudar_status` fecha o chat e avisa.
- `leilao/views.py`: a recusa explica o que houve.
- `static/leilao/js/leilao.js`: `desenharChat` exige `estado.ativo`.
- `leilao/tests.py`: `ChatNaoSobreviveAoLeilaoTests` (6 testes).

- `docs/ESTADO_ATUAL.md`, `docs/REGRAS_CODEX.md`.

### Decisões tomadas
- **As colunas ficam no banco** (`Leilao.musica_ligada`, `musica_volume`,
  `ConfigLeilao.musica`), sem nada que as leia. Apagar coluna em SQLite é
  reconstruir a tabela, e o ganho seria zero — três colunas em branco não
  custam nada. Estão comentadas como dormentes no model, para ninguém achar
  que são usadas.
- **O campo de arquivo saiu do formulário.** Deixá-lo lá permitiria ao clube
  subir um MP3 que não tocaria em lugar nenhum: pior que não ter o campo.
- **Testes que guardam a ausência.** Nenhum dos dois recursos pode voltar por
  descuido — um `data-acao` copiado, uma chave reposta no estado, um botão
  reaproveitado. `SemMusicaDeFundoTests` e `SemDesfazerLanceTests` cobrem o
  estado, o mapa de ações, a mesa do locutor, o POST forjado (botão escondido
  não protege nada) e o código que sobrou.
- **`Lance.cancelado` fica no banco**, dormente, pelo mesmo motivo das colunas
  de música: apagar coluna em SQLite é reconstruir a tabela e o ganho é zero.
- **Toda porta que a tela abre, o servidor tem de aceitar.** É a lição do bug do
  chat, e virou regra: ao criar controle novo, confira que a condição que o
  EXIBE é a mesma que o servidor usa para ACEITAR. Mostrar um campo que o
  servidor vai recusar é pior do que não mostrar — a pessoa digita, envia e não
  entende.

### Pendências
- As mesmas de ontem: Pix real de R$ 1, ensaio de áudio com aparelhos de
  verdade, trocar as senhas `fabiano` e `locutor`, e a data do evento.

---

## 2026-09-13 - Leilão: música nova, uma porta só, endereço curto e a tela que não apaga

### Resumo
Três acertos que só aparecem com o celular na mão. A música de fundo era lenta
demais para um pregão e virou uma peça instrumental animada. A porta de entrada
perdeu o botão "entrar sem som", que só servia para a pessoa entrar num leilão
mudo achando que o site quebrou. E a tela do celular parou de apagar no meio do
pregão — o economizador de bateria estava a um passo de fazer gente perder item.

### Arquivos criados/alterados
- `static/leilao/js/som.js`: `MusicaLeilao` reescrita. 104 BPM, progressão
  I–V–vi–IV, baixo nos tempos 1 e 3, arpejo em colcheias e pad sustentado —
  **sem melodia**, que disputaria com a voz de quem narra. Agendada por
  lookahead (~120 ms à frente, a cada 25 ms). A API pública não mudou
  (`preparar`/`ligar`/`desligar`/`volume`/`tocando`), incluindo o caminho do
  arquivo enviado pelo clube.
- `static/leilao/js/tela_acesa.js` (novo): Screen Wake Lock + plano B de vídeo
  mudo para iOS anterior ao Safari 16.4.
- `templates/leilao/leilao.html`: só o botão "Entrar com som"; no lugar do
  removido, a frase que diz onde desligar depois. Carrega o módulo novo.
- `templates/leilao/locutor.html`: carrega o módulo novo.
- `static/leilao/js/leilao.js`: pede o bloqueio de tela no toque da porta;
  o listener do botão removido saiu junto.
- `static/leilao/js/locutor.js`: pede o bloqueio ao abrir a mesa e reforça no
  primeiro clique.
- `leilao/forms.py`: **CEP e UF saíram da tela de entrada**. A UF continua no
  formulário como campo **oculto** com `UF_PADRAO = "SP"` (e o `clean` cai nele
  se vier vazia, porque campo oculto é editável por quem quiser); o CEP saiu
  inteiro e fica em branco no model.
- `templates/leilao/entrar.html`, `static/leilao/js/entrar.js`: campos e
  máscaras dos dois removidos.
- `static/leilao/css/leilao.css`: `.btn-porta-mudo` virou `.porta-som-pe`;
  `.col-cep` virou `.col-meia` (ainda usada pelo lance inicial no cadastro de
  item) e `.col-cidade`/`.col-uf` saíram.
- `leilao/tests.py`: +6 testes (147 no total).
- `docs/ESTADO_ATUAL.md`, `docs/REGRAS_CODEX.md`.

### Decisões tomadas
- **Música sem melodia, de propósito.** O que dá energia é o passo do baixo e o
  movimento do arpejo; melodia brigaria com o locutor, que é quem tem de ser
  ouvido. O volume continua sendo dele, para todos juntos.
- **Lookahead em vez de `setInterval` por nota.** O relógio do navegador não é
  preciso; o do WebAudio é. Nota a nota, o ritmo balança de forma audível.
- **Uma porta só.** "Entrar sem som" era uma escolha que a pessoa fazia sem
  saber o que estava escolhendo, e o resultado parecia defeito do site. A saída
  continua existindo no 🔇 do topo, onde ela já sabe o que está desligando.
- **Endereço curto é endereço que a pessoa termina de preencher.** A tela de
  entrada é preenchida com pressa, com o pregão já rolando: campo que não ajuda
  a achar a casa só produz desistência. Rua, número, bairro e cidade acham; CEP
  e UF não acrescentam nada a isso.
- **Mas o dado não some.** A UF vira campo oculto em vez de sumir, porque o
  roteiro de entrega é endereço de verdade; o CEP continua no model, em branco,
  para não apagar o que já estava cadastrado.
- **`visibilitychange` é obrigatório no wake lock**, não refinamento: o sistema
  derruba o bloqueio toda vez que a aba sai da frente e **não o devolve**. Sem
  repor, quem atende uma ligação volta com a tela apagando de novo — e parece
  que a proteção nunca existiu.
- **O vídeo do plano B fica visível** (1px, `opacity: .01`). Com `display:none`
  ou `hidden` o navegador o pausa, e aí ele não segura tela nenhuma.
- Novo teste varre `$("id").metodo` no JS e cobra o `id` no template: `id` que
  não existe é `TypeError` em cima de `null`, o arquivo **inteiro** morre naquela
  linha e nada depois é ligado. Foi o que quase aconteceu ao tirar o botão.

### Pendências
- Pagamento Pix real de R$ 1 (nunca testado ponta a ponta).
- Ensaio de áudio com 10-15 aparelhos de verdade.
- Trocar as senhas `fabiano` e `locutor` antes de divulgar o link.
- iOS anterior ao 16.4 depende do plano B — confirmar no ensaio se algum
  aparelho do grupo está nessa faixa.

---

## 2026-09-13 - Leilão: o martelo é do locutor, a tela do público vira show

### Resumo
Rodada grande de ajustes vinda de ver o sistema com olhos de evento, não de
código: o cronômetro saiu, o público parou de ver o que não devia, entraram
música, reações e a festa do intervalo — e o caixa ganhou o "vai pagar depois".

### O que mudou

**Quem bate o martelo é o locutor.** O tempo não fecha mais nada
(`Leilao.fechamento_automatico`, **desligado por padrão**). O item fica aberto
até o botão VENDIDO. Em troca, a mesa mostra **há quanto tempo a sala está
calada** (`Lote.parado_ha`, contando para CIMA) — é isso que diz a hora do
"dou-lhe uma, dou-lhe duas", não um relógio.

**A tela do público esconde o que muda o jogo.** Saíram do broadcast: a fila
(quantos faltam e quais são) e o histórico de lances. Quem descobre que falta
pouco segura o dinheiro; quem vê 20 itens economiza no primeiro. Vai só a
**foto** do próximo, para a troca de item ser instantânea. A mesa recebe fila e
histórico por caminho **próprio e autenticado** (`/locutor/dados/`).

**Porta do som.** O navegador proíbe tocar áudio sem gesto, e o botão 🔇 no canto
não era achado — era por isso que o sinal sonoro de cada lance nunca tocava. Virou
uma **tela de entrada**: um toque liga narração, música e efeitos.

**Música de fundo**, controlada ao vivo pelo locutor para todos junto (liga,
desliga, volume). Sem arquivo, toca uma **base ambiente sintetizada em WebAudio**
— zero download, zero arquivo no repositório e nenhuma questão de direito
autoral. Com arquivo (`ConfigLeilao.musica`), toca o que o clube subir.

**Reações em emoji.** Sobem na tela de todo mundo. O que segura isto em pé é a
**agregação**: os toques caem num contador em memória e saem num resumo a cada
meio segundo. Sem isso, 50 pessoas martelando emoji dariam dezenas de milhares de
mensagens por segundo e o pregão morreria junto.

**Festa no intervalo.** No lugar de "faltam N itens", o nome de quem acabou de
arrematar, grande e se mexendo, com confete.

**Chat**: agora fica na tela principal do locutor, ao vivo, ao lado do histórico
de lances (a aba sumiu). E cada intervalo abre uma **conversa nova** para os
participantes (`Leilao.chat_aberto_em`) — o locutor continua vendo o fio inteiro.

**Caixa: "📞 Vai pagar depois"** (`Arremate.status="combinado"`). A pessoa foi
contatada e combinou pagar depois: o item **não volta para a fila**, e um **Pix
novo de 24 h** é gerado — o original tinha validade de 15 minutos e já estava
vencido.

### Bug corrigido
**Colocar o leilão no ar não avisava ninguém.** A tela dizia "assim que
iniciarmos, isto acende sozinho" e mentia: só acordava quando o primeiro item
abria. `servicos.mudar_status` agora publica o estado — e tirar do ar também.

### Linguagem
A tela do público não fala mais "pregão" nem "locutor" — é jargão da equipe.
"O leilão ainda não começou", "Assim que iniciarmos…", "Estamos preparando o
próximo item…", "Combine o pagamento com a organização".

### Arquivos
- Models: `fechamento_automatico`, `musica_ligada`/`musica_volume`,
  `chat_aberto_em`, `ConfigLeilao.musica`, `Arremate.combinado_*`, `parado_ha`,
  `em_aberto`. Migrations **0003**, **0004**, **0005**.
- `leilao/reacoes.py` **novo**; `hub.laco_reacoes` (laço próprio de 0,5 s, **sem
  banco**); `servicos.mudar_status`/`ajustar_musica`/`marcar_combinado`.
- `static/leilao/js/reacoes.js` **novo**; música dentro do `som.js`;
  `leilao.js` e `locutor.js` reescritos em boa parte.
- Testes: **137 OK** (+35 nesta rodada).

### Pendências
- Nenhuma nova. Continuam: Pix real de R$ 1, ensaio do áudio, senha do locutor.

---

## 2026-09-13 - Leilão: a trava de auto-lance passa a valer por PESSOA

### Resumo
A trava "ninguém cobre o próprio lance" já existia (servidor + botão travado),
mas tinha um buraco: a entrada cria um `Participante` novo a cada vez, então a
mesma pessoa aberta no **celular e no computador** virava dois registros — e
dava lance contra si mesma, inflando o próprio preço. Agora a comparação é pela
**pessoa** (telefone), não pelo registro. O **bloqueio** ganhou o mesmo
tratamento.

### Arquivos criados/alterados
- `leilao/models.py`: `Participante.telefone_normalizado` e `chave_pessoa`
  (hash do telefone, seguro para o broadcast).
- `leilao/servicos.py`: `_mesma_pessoa` na trava do lance; `pessoa_bloqueada` e
  `bloquear_pessoa`.
- `leilao/views.py`: entrar de novo **não limpa** o bloqueio; bloquear alcança
  todos os cadastros da pessoa.
- `leilao/estado.py` + `templates/leilao/leilao.html` + `static/leilao/js/leilao.js`:
  a `chave` da pessoa vai no estado, então o botão trava também no 2º aparelho.
- `leilao/tests.py`: 9 testes novos (e o auxiliar passou a dar telefone
  **diferente** por pessoa — dava o mesmo para todo mundo, o que é irreal).

### Decisões tomadas
- **Compara pela pessoa, não reaproveita o cadastro.** Reusar o registro de quem
  tem o mesmo telefone resolveria também, mas abriria um buraco pior: qualquer
  um que soubesse o seu número tomaria a sua sessão — e com ela os seus
  arremates e o seu código Pix. Comparar no momento do lance fecha o
  auto-lance **sem** risco nenhum de tomada de conta.
- **O que vai no broadcast é um hash**, nunca o telefone: esse estado é
  transmitido para 100 pessoas.
- **Telefone com e sem DDI é a mesma pessoa** (`5511…` = `11…`): um aparelho
  manda de um jeito, o outro de outro.
- **Consequência aceita:** duas pessoas que dividem um WhatsApp não disputam
  entre si. Num leilão é o lado certo do erro — inflar o próprio preço é
  justamente o que a trava existe para impedir.
- **Bloqueio que se escapa entrando de novo não é bloqueio.** Agora ele segue a
  pessoa nos dois sentidos: o cadastro novo já nasce bloqueado, e bloquear pela
  tela alcança todos os cadastros dela.

### Pendências
- Nenhuma nova.

---

## 2026-09-13 - Leilão: três papéis na equipe, entrega e o item no leilão certo

### Resumo
A área da equipe era uma só, atrás de `is_staff`. Virou **três**: **Preparação** (itens e
configurações), **Locutor** (o pregão) e **Caixa** (pagamentos e **entrega**), com o **Diretor**
enxergando tudo. Junto, duas coisas que a pergunta do usuário expôs: **não havia controle de entrega**
e o cadastro de item **adivinhava** em qual leilão gravar.

### Arquivos criados/alterados
- `leilao/papeis.py`: **novo** — áreas, quem vê o quê, decorator `exige`.
- `leilao/models.py` + migration **0002**: `Arremate.entregue_em`/`entregue_por`/`entrega_obs` e as
  props `entregue`/`a_entregar`.
- `leilao/views.py`: área da equipe reorganizada em três; `caixa_view` nova; `lote_form_view` e
  `lotes_view` passam a receber o leilão pela **URL**; `ACOES_AREAS` gateia o POST único por ação.
- `leilao/urls.py`: uma pasta por área (`/equipe/`, `/locutor/`, `/caixa/`, `/preparacao/`).
- `leilao/management/commands/leilao_papel.py`: **novo** — cria conta e distribui papéis.
- Telas: `equipe.html`, `caixa.html`, `_nav_equipe.html` (novas); `preparacao.html` (era
  `leiloes.html`), `equipe_entrar.html` (era `locutor_entrar.html`); `locutor.html` perdeu a aba de
  pagamentos; `lotes/lote_form/config` ganharam a navegação e o leilão explícito.
- `static/leilao/js/caixa.js` **novo**; `static/leilao/css/locutor.css` com as áreas e a entrega.

### Decisões tomadas
- **`is_staff` sozinho não dá acesso a nada.** Sem papel, a pessoa entra e não vê tela — é o que
  impede uma conta esquecida de virar acesso total no dia do evento.
- **Papéis acumulam.** No evento pequeno o mesmo voluntário faz duas coisas; obrigar troca de login no
  meio do pregão seria pior do que não ter separação. Quem tem **uma** área só pula o hub e cai direto
  no trabalho.
- **O locutor não mexe em dinheiro** (decisão do usuário): `pago` é do Caixa. E isso é conferido **no
  POST, por ação** — esconder o botão no HTML nunca foi proteção. Há teste que prova os dois lados.
- **A entrega é depois, na casa da pessoa** (decisão do usuário): a tela é uma **lista de envio** com
  endereço em destaque e um **roteiro pronto para copiar**, reusando o `copiar_texto.js` do projeto (o
  texto vem pronto do servidor; o JS só copia). O roteiro **leva nome e endereço** — é documento de
  quem entrega, não texto para grupo aberto.
- **Só entra na lista de entrega o que já foi PAGO.** Mandar o item antes de o dinheiro cair é
  exatamente o erro que o prazo de 15 minutos existe para evitar; a regra está no servidor, não na tela.
- **O item vai para o leilão da URL.** Era `Leilao.ao_vivo() or o mais recente`: preparar o leilão de
  dezembro com o de novembro rolando jogava os itens novos **dentro do pregão em andamento**. Agora o
  id vem na rota (`/preparacao/<id>/itens/novo/`), e há teste com os dois leilões.
- **Leilão sem item não vai ao ar** — colocar no ar um leilão vazio encerraria o que estava rolando
  para mostrar uma tela sem nada.

### Pendências
- Distribuir os papéis reais no servidor (`leilao_papel`).
- As mesmas de antes: credenciais do Mercado Pago, ensaio do áudio, data do evento.

---

## 2026-09-13 - Leilão publicado no VPS e medido em produção

### Resumo
O módulo do leilão saiu do "pronto mas não publicado": está **no ar** em
`https://pinhaljunior.com.br/leilao/`, com áudio, e **medido sob carga real**.

### O que foi instalado no servidor
- `/etc/pinhaljunior_leilao.env` — `SECRET_KEY` própria, banco em `data/leilao.sqlite3`, prefixo
  `/leilao`, mídia e estáticos próprios.
- `pinhaljunior_leilao.service` — uvicorn, **1 worker**, porta 8011, `CPUWeight=300`.
- Nginx (site `sitepinhal`, backup antes): `/leilao/static/`, `/leilao/media/`, `/leilao/stream/`
  (com `proxy_buffering off`) e `/leilao/`. **Sem `rewrite`** — o Django tira o prefixo sozinho.
- `mediamtx.service` — MediaMTX v1.21, só WebRTC, sinalização em `/leilao/audio/` e voz em UDP 8189
  (liberada no ufw).
- Usuário `locutor` (`is_staff`) e um leilão de demonstração em **rascunho**, para ensaio.

### Resultado do teste de carga (de outra máquina, pela internet, produção atendendo os 11 sites)
- **100 / 100** conexões SSE mantidas, **zero quedas**; 40 lances, **zero recusados**.
- Atraso do lance: **p50 135 ms · p95 254 ms · máx 261 ms** (alvo era abaixo de 1 s).
- Processo com 65 MB de RSS depois do pico; **zero conexões presas** no hub (confirmado pelo contador
  de `online` e por `ss`).
- Ponta a ponta (login do locutor → abrir lote → participante entra → lance → evento no stream):
  **58 ms** do POST até o evento chegar.

### Decisões e correções durante o deploy
- **A primeira `SECRET_KEY` gerada vazou** na mensagem de erro do shell (tinha `)`, `&`, `$`, que
  quebraram o `source` do arquivo de ambiente). Foi **trocada na hora** por uma `token_urlsafe`, que
  além de não vazar não tem caractere que o shell interprete.
- **O banco nasceu `root:root`** no `migrate` (rodado como root) e o serviço roda como `www-data` —
  `chown` é passo obrigatório, não detalhe.
- **`--cookie` do `leilao_carga` virou repetível**: com um participante só, a própria regra do pregão
  (ninguém cobre o próprio lance) recusava tudo do 2º lance em diante e a medição não saía.
- **MediaMTX v1.x mudou a autenticação**: é `authInternalUsers` global, não `publishUser`/`publishPass`
  por caminho. Com o formato antigo a config **carrega e a proteção não vale** — a documentação foi
  corrigida. Também entrou `moq: false`, senão ele abre 8892/8893 à toa.
- **`socket.send() raised exception.`** aparece no log quando muita gente fecha a página de uma vez —
  é o uvicorn escrevendo em socket já fechado. Conferido que **não** é vazamento.

### Pendências
- **Credenciais do Mercado Pago** em `/leilao/locutor/config/`. Sem elas o leilão funciona e arremata,
  mas não gera Pix — a tela diz "combine o pagamento com o locutor" e a baixa é manual.
- **Ensaio do áudio com aparelhos reais** (a conta de pacotes é linear, mas não substitui o teste).
- **Trocar a senha do `locutor`**, que foi gerada e exibida no terminal durante o deploy.
- Definir a data do evento.

---

## 2026-09-13 - Leilão: refinos para o uso ao vivo

### Resumo
Ajustes saídos de reler o módulo pensando no evento acontecendo, não no código.

### Arquivos criados/alterados
- `static/leilao/js/leilao.js`: estado "te superaram" **permanente**, som próprio de perder a
  liderança, aviso quando não há Pix possível, pré-carga da foto do próximo item.
- `static/leilao/js/locutor.js`: confirmação ao abrir outro item com pregão em disputa; recargas do
  histórico **agrupadas** (era uma consulta por lance).
- `leilao/servicos.py`: lote abandonado volta **limpo** para a fila.
- `leilao/estado.py`: a foto grande do próximo item vai no estado (para a pré-carga).
- `leilao/views.py`: `pix_possivel` na lista de arremates e resposta honesta quando não há credencial.
- `templates/leilao/entrar.html` + `static/leilao/css/leilao.css`: número e complemento na mesma linha.

### Decisões tomadas
- **"Te superaram" não é um piscar.** É a informação mais importante para quem disputa, e a pessoa
  olha o celular de vez em quando — então o estado fica até ela cobrir, e o botão passa a dizer
  "COBRIR O LANCE". Perder a liderança ganhou **som descendente próprio**: dá para entender sem olhar.
- **Sem Mercado Pago configurado o leilão não para** — mas a tela precisa **dizer** isso. Antes
  prometia "Gerando seu Pix…" para sempre; agora diz "combine o pagamento com o locutor", e o Diretor
  dá baixa manual.
- **Abrir outro item no meio de uma disputa** é acidente fácil de cometer falando ao mesmo tempo, e
  caro. Ganhou confirmação nomeando o item, o valor e quem está ganhando. No servidor, o lote
  abandonado volta **limpo** (sem líder nem valor de uma disputa jogada fora) — os lances continuam
  no banco, mas fora da rodada nova.
- **A foto do próximo item é pré-carregada** enquanto o atual está em disputa: a troca de lote é o
  segundo em que todo mundo está olhando, e não pode piscar um quadro vazio.

### Pendências
- As mesmas da entrada anterior (deploy, teste de carga, Pix real, data do evento).

---

## 2026-09-13 - Leilão online ao vivo: módulo implementado (app, serviço e telas)

### Resumo
Implementação do módulo planejado na entrada anterior. App `leilao` **novo e independente**, com
**banco SQLite próprio** e **serviço ASGI próprio**, servindo `/leilao/`: entrada por link (sem senha),
tela do pregão em tempo real por **SSE**, botão de lance de +R$ 5, cronômetro do servidor, fechamento
automático, **Pix com prazo de 15 min** (vencido, o lote volta para a fila), chat entre lotes, mesa do
locutor com voz ao vivo por **WebRTC**, cadastro de item pela câmera do celular e efeitos (som
sintetizado, vibração, confete). Suíte do leilão: **68 testes OK**.

### Arquivos criados/alterados
- `leilao/` (app novo): `models.py` (8 models, migration **0001**), `servicos.py` (regras do pregão),
  `hub.py` (pub/sub em memória + laço central), `estado.py` (estado público), `views.py`, `urls.py`,
  `forms.py`, `sessao.py`, `imagens.py` (Pillow), `context_processors.py`, `admin.py`, `tests.py`,
  comandos `leilao_demo` e `leilao_carga`.
- `config/settings_leilao.py`, `config/urls_leilao.py`, `config/asgi_leilao.py`: o **segundo serviço**.
- `templates/leilao/` (9 telas) e `static/leilao/` (2 CSS + 8 JS).
- `requirements-leilao.txt`: **uvicorn** — a única dependência nova, isolada do ambiente do clube.
- `docs/DEPLOY_LEILAO.md`: serviço, Nginx (com SSE), MediaMTX, firewall e o teste de carga.

### Decisões tomadas
- **Serviço separado com UM worker.** O hub e o relógio vivem na memória do processo: dois workers
  seriam dois leilões paralelos, cada um com o seu cronômetro. E SSE em worker **síncrono** prenderia um
  worker por participante — por isso o leilão não pode morar no serviço do clube.
- **`transaction_mode: IMMEDIATE` no SQLite.** Descoberto rodando o teste de concorrência em banco de
  **arquivo** (o padrão do Django para SQLite é `:memory:` com *shared cache*, que esconde o problema):
  com o `BEGIN DEFERRED` padrão, uma transação que **lê e depois escreve** — que é todo lance — recebe
  `SQLITE_BUSY` na hora, **sem** respeitar o `busy_timeout`. Sem isso, lances se perderiam no meio do
  pregão. "Um escritor só" vale para processos; dentro do processo as views síncronas rodam em threads,
  cada uma com a sua conexão.
- **`ConfigLeilao.get_solo()` não escreve.** Era `get_or_create`, e ele é chamado pelo context processor
  a **cada página** e por uma thread de fundo a cada item vendido — toda leitura virava tentativa de
  escrita, disputando a trava com quem estava dando lance.
- **Lance sem corrida**: cadeado por lote + `UPDATE` conferindo o valor que o cliente viu. Se o preço
  subiu mais de **um** degrau desde que a tela desenhou o botão, o lance é recusado e a pessoa confirma
  de novo — aceitar calado faria alguém pagar mais do que pretendia.
- **O freio de 300 ms vem DEPOIS das recusas com explicação própria.** Antes, quem tocava duas vezes
  ouvia "Calma!" quando a resposta certa era "você já está ganhando".
- **O relógio é do servidor** (`fecha_em` absoluto + `servidor_em` em todo estado): celular com a hora
  errada vê o mesmo cronômetro que os outros.
- **O broadcast só leva o que pode ser dito em voz alta** (nome curto e valor). Código Pix, telefone e
  endereço saem por `GET` autenticado pela sessão. Há teste.
- **Reconexão manda o estado inteiro**, em vez de repetir eventos perdidos: dispensa lógica de replay e
  quem volta está sempre correto.
- **Lances são por rodada** (`Lote.lances_da_rodada`): um item que volta para a fila e é reaberto não
  pode mostrar — nem deixar desfazer — lances da rodada anulada.
- **O Pix é gerado numa thread**, depois de publicar o "vendido": ninguém espera o Mercado Pago com a
  tela parada. Sem credencial configurada o leilão **não para** — o locutor dá baixa manual.
- **`leilao/tests.py` se auto-pula** quando o app não está instalado: o `manage.py test` do clube varre o
  diretório inteiro e, sem isso, o arquivo virava um erro de importação na suíte do clube.
- Áudio por **MediaMTX (WHIP/WHEP)**, com o cliente em `RTCPeerConnection` puro — nenhuma biblioteca JS
  externa entra no projeto. A caixa de áudio é **plugável**: reprovando o teste de carga, aponta para uma
  live externa sem tocar no resto.

### Armadilhas do projeto que morderam de novo (agora com teste)
- **`{# ... #}` é de UMA linha.** O comentário de duas linhas do `_campo.html` continha um `{% include %}`
  de exemplo — que o Django **executou**, fazendo o parcial incluir a si mesmo até estourar a pilha.
  Entrou um teste que varre `templates/` e reprova qualquer `{# #}` multilinha.
- **Bloco `display:flex` não some com `hidden`**: regras explícitas no CSS + teste.
- **A captura do Chrome headless não prova estouro**: o viewport mínimo é ~485px, então pedir 430
  renderiza em 500 e **corta a imagem** — parecia estouro e não era. Quem decide é a sonda
  (`scrollWidth` × `clientWidth`): sem estouro a 500px e a 1280px.

### Pendências
- **Teste de carga com 100 conexões** (`leilao_carga`) e ensaio de áudio com aparelhos reais — a fazer
  **antes** do evento, de outra máquina.
- **Deploy**: serviço, Nginx e MediaMTX ainda não instalados no VPS (passo a passo em `DEPLOY_LEILAO.md`).
- **Pix real do leilão nunca foi cobrado** — o fluxo tem teste, mas o webhook de verdade só se confirma
  com uma cobrança real.
- Definir a **data do evento** e quem será o locutor.

---

## 2026-09-13 - Planejamento do módulo de Leilão online ao vivo

### Resumo
Levantamento e decisões de arquitetura do **leilão online** (`/leilao/`) antes de escrever código: leilão ao
vivo com locutor falando, ~50 participantes simultâneos (teto de 100), **todos remotos**, lance de R$ 5 em
R$ 5, cronômetro de 1 min por lote, chat entre lotes, Pix com **15 min** para pagar (senão o item volta para
a fila) e voz do locutor em tempo real. Nenhum código de produção ainda — esta entrada registra o **plano**.

### Arquivos criados/alterados
- `docs/PLANEJAMENTO_LEILAO.md`: **novo** — o plano completo (arquitetura, protocolo de tempo real, telas,
  dinheiro, áudio, fases, riscos e o que o módulo não faz).
- `docs/ESTADO_ATUAL.md`: item do leilão em "Próximas etapas previstas", apontando para o plano.

### Decisões tomadas
- **Tempo real por SSE num serviço ASGI próprio**, não por polling nem por WebSocket/Channels. O sistema do
  clube roda em **gunicorn síncrono**: uma conexão SSE por participante **ocuparia um worker inteiro** e
  derrubaria o site do clube. Polling foi descartado pelo custo no **1 vCPU compartilhado** (100 celulares
  perguntando a cada segundo ≈ 100 req/s) e Channels+Redis por trazer três peças novas para um VPS sem swap.
- **Um único worker uvicorn, de propósito**: com um processo só, o hub de eventos vive em memória (**sem
  Redis**), há **um escritor só** no SQLite e o cronômetro/expiração rodam num laço `asyncio` único (**sem
  cron**). O preço — não escalar horizontalmente — é aceito e tem saída conhecida (trocar o hub por Redis).
- **Banco próprio** (`leilao.sqlite3`) e **`core` fora do `INSTALLED_APPS`** do serviço do leilão: 50 pessoas
  martelando lance não podem encostar no banco que roda mensalidades/eventos/loja.
- **O pagamento é reaproveitado sem acoplar**: `core/mercadopago.py` é biblioteca pura (só `urllib`, recebe o
  objeto de config de quem chama), então o leilão passa o **seu** `ConfigLeilao`. Custo aceito: as credenciais
  do MP são digitadas de novo na tela do leilão.
- **O relógio é do servidor** (`Lote.fecha_em` absoluto; o cliente só desenha a diferença) e o **cronômetro é a
  autoridade do lance, não a voz** — com público 100% remoto, o áudio sempre chega com algum atraso.
- **Lance sem corrida**: lock por lote no processo + `UPDATE` condicional pelo valor que o cliente viu, para
  dois toques no mesmo milissegundo não virarem dois incrementos sobre o mesmo valor; ninguém cobre o próprio
  lance; 1 lance a cada 300 ms por pessoa.
- **Broadcast único, personalização no cliente**: o servidor serializa o evento **uma vez** e escreve para
  todos; "você está ganhando" é decidido no navegador. Dado privado (código Pix, endereço) **nunca** entra no
  broadcast — sai por `GET` autenticado pela sessão.
- **Áudio no próprio VPS com MediaMTX (WHIP/WHEP)**, não mediasoup/Janus/LiveKit: binário Go único e cliente
  em `RTCPeerConnection` puro, **sem biblioteca JS externa** (a regra do projeto). Contas levantadas: ~40 kbps
  por ouvinte, ~4 Mbps de subida e ~5.000 pacotes/s a 100 ouvintes — banda é irrelevante e a CPU estimada fica
  em 10-20% de um núcleo. **O risco não é a média, é o engasgo**: um dos outros 11 sites segurando o vCPU por
  150 ms faz o som picotar para todos. Mitigação combinada com o usuário: parar os outros serviços no dia e
  dar `CPUWeight` ao processo de áudio.
- **Dependência nova autorizada pelo usuário**: `uvicorn`, isolada num `requirements-leilao.txt` separado.

### Pendências
- Implementação, em 8 fases internas (a entrega ao usuário é única, com o módulo inteiro pronto).
- **Teste de carga obrigatório antes do evento** (comando `leilao_carga` para SSE/lances). O de áudio é
  **estimativa**, não prova: medição com 10-15 aparelhos reais + extrapolação pela conta de pacotes — por isso
  a caixa de áudio da tela nasce **plugável**, para cair numa live externa se reprovar.
- Sugestão feita e **recusada pelo desenho atual** (decisão do usuário): pedir o endereço completo só de quem
  arremata, em vez de na porta de entrada.
- Definir com o usuário a **data do evento** (dita o prazo do ensaio geral) e quem será o locutor.

---

## 2026-09-13 - Parcelas: alinha "Copiar resumo" com "Novo lançamento"

### Resumo
Os dois botões da barra da aba Parcelas estavam desencontrados. Causa: `.btn-acao` nasce com `margin-top:18px`
(foi pensado para fechar um card, não para dividir linha com outro botão) e **sem borda**, enquanto
`.btn-secundario` tem borda de 1.5px — o que dava 18px de desnível e 3px de diferença de altura.

### Arquivos criados/alterados
- `static/css/mensalidades.css`: dentro da barra, o `.btn-acao` perde a margem e ganha uma **borda
  transparente** de 1.5px, igualando a caixa dos dois.

### Decisões tomadas
- **A correção é local à barra** (`.mens-cobranca-barra .copiar-lista-acoes .btn-acao`), não no `.btn-acao`
  global: a margem existe por um motivo em todos os outros lugares onde o botão fecha um card.
- Conferido com **sonda** no Chrome headless (a régua que a documentação recomenda, em vez de confiar no
  olho): mesmo `top` e mesma altura nos dois botões (diferença **0**), sem rolagem horizontal, a 1280px **e**
  a 485px.

### Pendências
- Nenhuma.

---

## 2026-09-13 - Ficha de diretoria na própria conta e card "Minhas parcelas"

### Resumo
Caso real: uma responsável tentou se cadastrar como diretoria e o único caminho existente
(`/cadastro/diretoria/`) **cria uma conta nova** — ela terminaria com dois logins. Agora o **Diretor libera** a
conta em Usuários e a **pessoa preenche a ficha na própria conta**, virando Responsável + Diretoria num login
só. Junto, a segunda falta do mesmo caso: quem é **só diretoria** não tinha onde ver nem pagar o que devia —
entrou o card **💳 Minhas parcelas** em Meus Dados.

### Arquivos criados/alterados
- `core/models.py`: `PerfilUsuario.liberacao_diretoria_em`/`liberacao_diretoria_por` + a propriedade
  `pode_cadastrar_diretoria` (liberado **e** ainda sem ficha). Migration **0073**.
- `core/views.py`: `_gravar_ficha_diretoria` (extraída do cadastro, usada pelos dois caminhos),
  `minha_ficha_diretoria_view`, `usuario_liberar_diretoria_view`, `_minhas_parcelas`; contexto novo em
  `inicio_view` e em `usuarios_view`.
- `core/urls.py`: `/meus-dados/diretoria/` e `usuarios/conta/<id>/liberar-diretoria/`.
- `templates/core/cadastro_diretoria.html`: o passo "Conta de acesso" virou condicional (`{% if conta_form %}`),
  com a numeração dos passos e o ponto ativo acompanhando.
- `templates/core/usuarios.html`: bloco "⛺ Cadastro de diretoria" no modal do responsável (liberar/revogar).
- `templates/core/inicio.html`: convite "Você também é da diretoria?" e o card "💳 Minhas parcelas"
  (+ `{% load formato %}` para o filtro de moeda).
- `static/css/inicio.css`: estilo dos dois cards.
- `core/tests.py`: 18 testes novos (10 da ficha na própria conta, 8 do card).
- `docs/ESTADO_ATUAL.md`, `docs/REGRAS_CODEX.md`, `CLAUDE.md`: documentação.

### Decisões tomadas
- **Quem libera é o Diretor** (escolha do usuário entre três opções). O botão nem aparece para quem não foi
  liberado, e a view confere no GET **e** no POST — esconder no HTML não barra POST forjado.
- **A liberação é consumida** ao preencher a ficha: é autorização para um cadastro, não permissão permanente.
- **Reaproveitar o formulário do cadastro** em vez de duplicar 260 linhas de template. O JS de passos anda por
  **índice**, então bastou não renderizar a seção da conta e marcar a seguinte como ativa.
- **A gravação virou uma função só** (`_gravar_ficha_diretoria`): os dois caminhos precisam gravar exatamente a
  mesma coisa (membro + ficha médica + as 3 assinaturas, com os aceites vindo da assinatura).
- **O papel continua sendo do Diretor**: a pessoa entra na "Diretoria" genérica. Vale lembrar que definir o
  papel **substitui** o grupo genérico — o professor não fica em "Diretoria".
- **O card de parcelas não cria fluxo de pagamento novo**: manda para as mesmas páginas públicas por token que
  a cobrança já usa. Menos código e um caminho só para manter.
- **O card vale para todos os perfis**, não só para a diretoria: o responsável também vê ali as parcelas dele.
  Com isso o perfil **Professor continua com acesso só a "Meus Dados"**, como combinado — o módulo de
  permissões decide o resto depois.

### Deploy e conferência em produção (13/09)
Deploy pelo atalho `pinhaljunior2-deploy`: `cf64c23` → **`c900d2b`**, com backup do SQLite antes, `check` e
`makemigrations --check` limpos (desta vez rodados **antes** do push, depois do incidente de ontem), **migration
`0073` aplicada**, estáticos coletados e healthcheck OK. Serviços: `pinhaljunior2` e `nginx` **active**,
`sitepinhal` **inactive**. Conferido: `/` **200**; `/inicio/`, `/meus-dados/diretoria/` e `/usuarios/` **302**
(pedem login, como esperado).

**O que a conferência NÃO prova:** o caminho completo com gente de verdade — liberar uma conta em Usuários,
a pessoa preencher a ficha e assinar os três documentos no celular, e o card de parcelas com dívida real.

### Pendências
- Módulo de permissões (ligar/desligar telas por perfil) — o encaixe continua sendo `ACESSO_PADRAO`/
  `perfil_efetivo`, sem mexer em menu nem em views.

---

## 2026-09-12 - Parcelas: botão "Copiar resumo" e o evento na cobrança

### Resumo
Dois pedidos do usuário na aba 📆 Parcelas: um **botão "Copiar resumo"** que joga no clipboard um resumo dos
lançamentos, e, na **cobrança de parcelas**, um **marcador/link do evento vinculado** para usar na mensagem e
no prompt da IA.

### Arquivos criados/alterados
- `core/views.py`: `_export_parcelamentos` (texto do resumo) + `parc_resumo` no contexto; `_aplicar_marcadores`
  (marcadores opcionais), `_eventos_da_cobranca` e `_montar_mensagem_cobranca_parcela` com `{evento}` e
  `{link_evento}`.
- `core/models.py`: mensagem e prompt padrão da cobrança de parcelas com as linhas do evento; comentário dos
  marcadores atualizado.
- `static/js/copiar_texto.js` (**novo**): a mecânica do copiar, agora compartilhada; `static/js/evento_painel.js`
  perdeu o bloco duplicado e ambos os templates carregam o arquivo novo.
- `templates/core/mensalidades.html`: botão + `<textarea class="copiar-fonte">` na aba Parcelas e as dicas dos
  marcadores novos; `templates/core/evento_painel.html`: carrega o `copiar_texto.js`.
- `static/css/mensalidades.css`: os dois botões da barra andam juntos à direita.
- `core/tests.py`: 12 testes novos (resumo: totais, bloco por lançamento, parcela vencida, quitado, cancelado
  fora, textarea servida na tela; marcadores: nome+link do evento, linha some sem evento, evento inativo e
  evento simples sem link, e dois testes unitários do `_aplicar_marcadores`).
- `docs/ESTADO_ATUAL.md`, `docs/REGRAS_CODEX.md`, `CLAUDE.md`: documentação.

### Decisões tomadas
- **O texto do resumo vem pronto do servidor**, como o do painel do evento: o JS só copia. Montar no JS seria
  refazer no navegador regras (quitado, vencida, cancelado) que já existem no Python.
- **A mecânica do copiar virou arquivo compartilhado** (`copiar_texto.js`) em vez de um segundo bloco igual:
  mesmo motivo do `mensalidade_cobranca.js`, que já serve duas abas.
- **Cancelado fica fora do resumo** (só contado no fim): os KPIs da aba somam só os ativos, e dois números
  diferentes na mesma tela parecem erro.
- **`{evento}`/`{link_evento}` são marcadores OPCIONAIS**: a linha que usa um deles some inteira quando o
  lançamento não tem evento. Sem isso, o acerto geral do clube receberia "Referente a:" sem nada depois — e,
  no prompt da IA, rótulo sem valor é convite para ela inventar um evento.
- **O link só sai de evento de inscrição e ativo**: a página pública do inativo é bloqueada e o evento simples
  não tem página. O **nome** do evento continua aparecendo nesses casos; só o link é omitido.
- **Com mais de um evento**, o link vira "Nome: URL" por linha — a URL sozinha não diz de qual evento é.

### Deploy e conferência em produção (12/09) — com incidente

**O primeiro deploy falhou e o site ficou 502 por ~2 minutos.** Causa: mudar o **texto padrão** da mensagem e do
prompt da cobrança de parcelas mudou o `default=` desses campos do `ConfigMensalidade` — ou seja, mexeu no
estado do model — e o commit foi sem migration. O atalho roda `makemigrations --check` **antes** de aplicar as
migrations, detectou a pendência e abortou para o rollback. O rollback voltou o código e o banco, mas **não
refaz o `chown root:www-data`** (esse passo vem depois, no caminho feliz), então o Gunicorn ficou sem permissão
de ler o próprio `config/__init__.py`, em `activating (auto-restart)`, e o Nginx devolveu **502**.

Correção: gerar a migration **0072** (só `AlterField` de default — nenhum dado muda, e quem já salvou a própria
mensagem continua com ela), commitar, e rodar o `pinhaljunior2-deploy` de novo. O deploy bem-sucedido refaz as
permissões no fim, então o site voltou sem precisar de conserto manual: `4dfaace` → **`cf64c23`**, migration
`0072` aplicada, 50 estáticos coletados, healthcheck OK. Conferido: `/` **200**, `/mensalidades/` **302**,
`/static/js/copiar_texto.js` **200**; `pinhaljunior2` e `nginx` **active**, `sitepinhal` **inactive**.

Ficou documentado nos dois lugares que evitariam o incidente: a regra "texto padrão é `default` de campo, então
pede migration" (REGRAS_CODEX e CLAUDE.md) e a armadilha do rollback sem permissões (DEPLOY_VPS.md).

**O que a conferência NÃO prova:** o texto copiado com os dados reais e a cobrança com o `{evento}` de fato
enviada (depende da W-API ativa). Vale abrir Mensalidades → 📆 Parcelas, clicar em **📋 Copiar resumo** e colar
numa conversa, e mandar uma cobrança de teste de um lançamento com evento.

### Pendências
- Nenhuma.

---

## 2026-09-12 - Parcelas: o grupo "Responsáveis" traz pai, mãe e responsável legal

### Resumo
Pedido do usuário: "em responsáveis lá puxa todos, tipo pai e mãe". O grupo criado mais cedo hoje listava só o
**responsável legal** (`resp_nome`) de cada ficha — mas quem lança lembra do adulto com quem combinou, que
muitas vezes é o pai ou a mãe que não é o responsável legal. Agora os **três** nomes da ficha
(`pai_nome`/`mae_nome`/`resp_nome`) viram opções, todas apontando para a mesma conta.

### Arquivos criados/alterados
- `core/views.py`: `_alvos_responsaveis` passou a varrer os três campos e a agrupar **por pessoa** (nome
  normalizado) em vez de por nome de responsável.
- `templates/core/mensalidades.html`: rótulo do `<optgroup>` e texto de ajuda dizendo quem aparece ali.
- `core/tests.py`: 3 testes novos (pai/mãe/resp. legal listados, adulto que acumula papéis aparece uma vez só,
  adulto de dois filhos aparece uma vez com os dois).
- `docs/ESTADO_ATUAL.md`, `docs/REGRAS_CODEX.md`, `CLAUDE.md`: documentação.

### Decisões tomadas
- **Agrupar por pessoa, não por campo.** A mãe costuma ser também a responsável legal da mesma ficha: listar
  por campo a faria aparecer duas vezes, com o mesmo efeito. O agrupamento é pelo nome **normalizado**
  (espaços colapsados, sem diferenciar maiúscula) e os papéis se juntam no detalhe ("mãe/resp. legal de
  Fulano").
- **O detalhe ganhou o papel** ("pai de Fulano"), que antes era só "resp. de Fulano". Com três adultos por
  ficha, o papel é o que separa homônimos de famílias diferentes.
- **O alvo continua sendo `conta:<id>`**: nada mudou no POST, em `_resolver_alvo` nem no model.
- **Ficha sem nenhum adulto preenchido** cai no nome da conta, como antes — não some da lista.

### Deploy e conferência em produção (12/09)
Deploy pelo atalho `pinhaljunior2-deploy` (nunca `pinhaljunior-deploy`): `9342913` → **`4dfaace`**, com backup
do SQLite antes, `check` e `makemigrations --check` limpos, **nenhuma migration a aplicar**, estáticos coletados
e healthcheck OK na porta 8010. Serviços: `pinhaljunior2` **active**, `nginx` **active**, `sitepinhal`
**inactive**. Conferido: `/` **200**, `/mensalidades/` **302** (pede login) e, no servidor, o template já com o
rótulo novo do `<optgroup>`.

**O que a conferência NÃO prova:** a lista com os dados reais — o modal é tela de Diretor e não abre de fora.
Vale abrir Mensalidades → 📆 Parcelas → Novo lançamento e ver se pai e mãe aparecem junto do responsável legal,
sem ninguém repetido.

### Pendências
- Nenhuma.

---

## 2026-09-12 - Parcelas: o seletor "para quem" também lista os responsáveis

### Resumo
Pedido do usuário: "em parcelas coloca pra poder selecionar nomes de responsáveis também". O modal de novo
lançamento (Mensalidades → 📆 Parcelas) tinha só **Aventureiros** e **Diretoria**: quando o acerto era do
adulto da família — e não de uma criança específica —, o Diretor precisava escolher um aventureiro qualquer só
para chegar à conta certa. Agora há um terceiro grupo, **Responsáveis (conta da família)**, com a família
listada pelo nome de quem responde por ela e os filhos no detalhe (desempata homônimos).

### Arquivos criados/alterados
- `core/views.py`: `_alvos_parcelamento` passou a devolver também `responsaveis`; nova `_alvos_responsaveis`
  agrupa os aventureiros por conta e monta as opções pelo `resp_nome`.
- `core/models.py`: `ParcelamentoClube.pessoa_nome` ganhou o degrau do responsável antes do username.
- `templates/core/mensalidades.html`: `<optgroup>` "Responsáveis (conta da família)" no seletor + texto de
  ajuda atualizado.
- `core/tests.py`: 5 testes novos em `ParcelamentoClubeTests` (lista o responsável, não repete a conta que já
  está em Diretoria, ignora `demo`, mantém a família cujo aventureiro saiu, e o lançamento na conta da família
  mostra o nome do responsável).
- `docs/ESTADO_ATUAL.md`, `docs/REGRAS_CODEX.md`, `CLAUDE.md`: documentação.

### Decisões tomadas
- **O alvo continua sendo `conta:<id>`** — o mesmo do grupo Diretoria. O grupo novo muda só *como se acha* a
  família, então `_resolver_alvo` e o POST ficaram intactos (nada a migrar, nada a revalidar).
- **A conta que já aparece em Diretoria fica fora do grupo novo**: seria a mesma opção duas vezes, com o mesmo
  efeito.
- **O grupo não filtra `ativo`**, ao contrário do grupo de aventureiros. É a exceção do parcelamento já
  documentada: dívida combinada continua devida depois de a criança sair, e essa família precisa continuar
  alcançável. `demo` fica fora dos três grupos, como em toda contagem do clube.
- **Uma conta com responsáveis diferentes em fichas diferentes** (pai numa, mãe noutra) vira **uma opção por
  nome**, todas apontando para a mesma conta — ajuda a achar pelo nome que o Diretor lembra.
- **`pessoa_nome` precisava do fallback**: antes, um lançamento numa conta de família sem aventureiro aparecia
  na lista de parcelas com o **nome de acesso** (username). Agora mostra o nome do responsável.

### Deploy e conferência em produção (12/09)
Deploy pelo atalho `pinhaljunior2-deploy` (nunca `pinhaljunior-deploy`, que reativaria o sistema antigo):
`60b5c3b` → **`9342913`**, com backup do SQLite antes, `check` e `makemigrations --check` limpos, **nenhuma
migration a aplicar** (a mudança é de seletor e exibição), estáticos coletados e healthcheck OK na porta 8010.
Serviços depois do deploy: `pinhaljunior2` **active**, `nginx` **active**, `sitepinhal` **inactive** (como deve
ficar). Conferido de fora, pelo domínio: `/` **200**, `/mensalidades/` **302** (pede login, como esperado),
`/parcelas/<token inexistente>/` **200** com "Link inválido" e sem vazar nada; no servidor, o template já traz o
`<optgroup>` novo.

**O que a conferência NÃO prova:** a lista de responsáveis **com os dados reais** — de fora não dá para abrir o
modal (é tela de Diretor). Vale abrir Mensalidades → 📆 Parcelas → Novo lançamento e olhar o grupo
**Responsáveis**: os nomes devem ser os dos adultos das famílias, sem repetir quem já está em Diretoria.

### Pendências
- Nenhuma.

---

## 2026-09-07 - Parcelamento lançado pelo clube (lançamento manual de parcelas)

### Resumo
Pedido do usuário: "alguns eventos tiveram o parcelamento habilitado na inscrição, mas outros precisam ser
lançados manual; lá em Mensalidades, ter um botão de fazer lançamento de parcelas pelo clube, digitar os dados,
selecionar um usuário (que é vinculado a um aventureiro, e diretoria também), e gerar como se fosse uma
mensalidade, com vencimento dia 10 de cada mês".

Antes desta alteração o parcelamento existia **em um lugar só**: dentro da inscrição de evento
(`Evento.parcelas_diretoria` + `ParcelaInscricao`), nascendo sozinho quando o evento oferecia a opção e a
pessoa marcava. Não havia **nenhum** caminho manual — quem se inscreveu num evento sem a opção ligada, ou
combinou o acerto depois, ficava fora do sistema.

### O que foi feito
- **Models novos** (migration **0071**): `ParcelamentoClube` (o lançamento: conta, aventureiro opcional,
  evento opcional, descrição, observação, valor total, nº de parcelas, status, token do link público) e
  `ParcelaClube` (número/total/valor/vencimento/situação/forma/valor pago/baixa/`pagamento`), mais
  `CobrancaParcelaEnviada` (histórico da cobrança) e 4 campos em `ConfigMensalidade` (mensagem, assunto,
  alavanca e prompt da cobrança de parcelas). Tipo de pagamento novo: `parcela_clube`.
- **Aba 📆 Parcelas** em Mensalidades: KPIs (lançado, já recebido, a receber, vencido), botão **Novo
  lançamento** (modal com prévia ao vivo das parcelas), lista de lançamentos em `<details>` com baixa manual
  por parcela, cancelamento e o link público de pagamento.
- **Aba 📨 Cobrar parcelas**: mensagem/assunto/prompt próprios, alavanca padrão × IA, canal
  WhatsApp/e-mail/ambos, envio 1-por-request com 10s no front, filtro "só quem não recebeu este mês" por
  canal, termômetro de contato e busca.
- **Página pública** `/parcelas/<token>/`: a pessoa vê o que pagou e o que falta e paga **uma parcela por
  cobrança** (Pix/cartão), com baixa automática pelo webhook (`_finalizar_parcela_clube`, idempotente). O
  token aceita **um lançamento** (link do painel) **ou a conta** (`token_acerto`), e a cobrança manda o da
  conta — a mensagem lista as parcelas de todos os lançamentos, então o link tem de abrir todos.
- **Área do responsável**: bloco "📆 Parcelas combinadas com o clube" na tela de Mensalidades dele.
- **Financeiro**: fonte nova **Parcelamentos** (card, legenda do donut, chip do extrato) para lançamento sem
  evento; com evento, a parcela paga conta na fonte **Eventos**.
- **Painel do evento**: card "Parcelamento do clube" (recebido/a receber/vencido + detalhe por lançamento),
  linha nova em "Por canal" e as parcelas pagas no extrato e nas receitas do evento.
- **Reaproveitamento**: `Evento.dividir_parcelas` virou casca da função de módulo `dividir_em_parcelas`
  (mesma regra: a sobra dos centavos na 1ª parcela); e `mensalidade_cobranca.js` foi **generalizado** para
  servir as duas abas de cobrança em vez de duplicar ~300 linhas de JS.
- **Correção de bônus**: rolagem horizontal **pré-existente** no Financeiro (`.fin-graficos` com `1fr` em vez
  de `minmax(0, 1fr)` — a armadilha que o CLAUDE.md documenta). Conferido com sonda em 485/768/1280px:
  `scrollWidth == clientWidth` em todas as telas novas e nas alteradas.

### Arquivos criados/alterados
- `core/models.py`: models novos, campos em `ConfigMensalidade`, `dividir_em_parcelas` extraída,
  `parcela_clube` em `TIPO_PAGAMENTO_CHOICES`.
- `core/migrations/0071_parcelamento_clube.py`: migration.
- `core/views.py`: seção "Parcelamento lançado PELO CLUBE" (lançar, cancelar, baixa manual, cobrança,
  página pública, finalizador do gateway), contexto das duas abas, bloco do responsável, Financeiro e
  painel do evento.
- `core/urls.py`: 6 rotas internas + 2 públicas. `core/admin.py`: os dois models novos.
- `templates/core/mensalidades.html`: 2 abas + modal. `templates/core/parcelas_clube.html`: página pública.
- `templates/core/mensalidades_responsavel.html`, `templates/core/financeiro.html`,
  `templates/core/evento_painel.html`.
- `static/js/parcelamento.js` (novo: modal + prévia + busca), `static/js/mensalidade_cobranca.js`
  (generalizado), `static/css/mensalidades.css`, `static/css/financeiro.css`, `static/css/eventos.css`.
- `core/tests.py`: 34 testes novos (4 classes). Suíte completa: **396 OK**.

### Decisões tomadas
- **Não reaproveitar `Mensalidade`**: `unique_together (aventureiro, ano, mes)` daria colisão com a
  mensalidade do mês, ela não tem vencimento nem descrição, e é amarrada ao `Aventureiro` — integrante da
  diretoria **sem filho no clube** não teria onde ser lançado. O vínculo do parcelamento é com a **conta**.
- **Não reaproveitar `ParcelaInscricao`**: FK obrigatória de `Inscricao` e o dinheiro dela entra no caixa
  **pelo evento**; misturar arriscaria a contagem dupla que a flag `no_ato` existe para evitar.
- **Escolher o aventureiro resolve os dois vínculos** (criança + conta do responsável), que é o que o
  usuário descreveu; a conta sozinha atende a diretoria.
- **Nada é cobrado no ato**: o lançamento é 100% a receber. Só a parcela **paga** entra no caixa.
- **Vencimento sempre no dia 10** (`DIA_VENCIMENTO_PARCELA`, o mesmo do parcelamento de evento), com o
  **mês** da 1ª parcela escolhido pelo Diretor — data fixa é o que a família guarda.
- **Valor baixo demais para o nº de parcelas é recusado** com aviso, em vez de virar 1 parcela em silêncio
  (`dividir_em_parcelas` cai para à vista, e quem chama confere o tamanho da lista).
- **Aventureiro inativo continua devendo** — diferente da mensalidade. A regra do clube é da cobrança
  recorrente de quem saiu; um acerto combinado é dívida específica, como as parcelas de inscrição.
- **Cobrança em aba e histórico separados** da mensalidade: contar as duas juntas faria "já cobrei este mês"
  de uma silenciar a outra (o mesmo motivo pelo qual o canal faz parte da identidade do registro).
- **Cancelar** cancela só as parcelas em aberto; as pagas continuam no caixa e no extrato.
- O **telefone de cobrança** é o mesmo da mensalidade (responsável financeiro da conta), então a rota de
  trocar o telefone foi reaproveitada em vez de duplicada.

### Deploy e conferência em produção (07/09)
Deploy pelo atalho `pinhaljunior2-deploy` (nunca `pinhaljunior-deploy`, que reativaria o sistema antigo):
`fdc1cf5` → **`60b5c3b`**, com backup do SQLite antes (`db_before_deploy_20260907_210924.sqlite3`),
`check` e `makemigrations --check` limpos, **migration `0071` aplicada**, 5 estáticos coletados e healthcheck
OK na porta 8010. Serviços depois do deploy: `pinhaljunior2` **active**, `nginx` **active**,
`sitepinhal` **inactive** (como deve ficar).

Conferido de fora, pelo domínio: `/` **200**; `/mensalidades/` e `/financeiro/` **302** (pedem login, como
esperado); `/parcelas/<token inexistente>/` **200** mostrando "Link inválido" e **sem vazar nada**;
`/static/js/parcelamento.js` e `/static/css/mensalidades.css` **200**, servindo o conteúdo novo (o JS veio com
o cabeçalho da aba Parcelas, então não é cache de versão antiga).

**O que essa conferência NÃO prova** — e por isso fica registrado:
- o **Pix real de uma parcela**: `_finalizar_parcela_clube` tem teste (inclusive de idempotência, com o aviso
  repetido do MP), mas o **webhook de verdade** nesse tipo novo (`parcela_clube`) só se confirma com uma
  cobrança real. Vale fazer a primeira e olhar a parcela mudar para paga sozinha;
- a **cobrança por WhatsApp** das parcelas: depende da **W-API** estar ativa, e a saúde dela não foi
  conferida neste deploy. Se a cobrança não sair, é o primeiro lugar a olhar (ver DEPLOY_VPS.md,
  "Dependências externas que expiram").

Nada mudou no processo de deploy nem no ambiente: sem dependência nova, sem variável nova em
`/etc/pinhaljunior2.env` e sem cron novo — por isso o `DEPLOY_VPS.md` não precisou de alteração.

### Pendências
- **Cobrança automática** das parcelas (as do clube e as de inscrição) — nada dispara sozinho; hoje o
  Diretor manda pela aba.
- **Editar** um lançamento (valor/nº de parcelas) — hoje é cancelar e lançar de novo.
- **Primeiro pagamento real** de uma parcela ainda não feito (ver a conferência acima).
- Ainda **sem throttle** na recuperação de senha (dívida antiga).

---

## 2026-08-20 - A 1ª parcela do valor da diretoria pode ficar para o mês seguinte

### Resumo
Pedido do usuário: no parcelamento do valor da diretoria, poder **configurar** se a **1ª parcela** é paga na
inscrição (como já era) ou **jogada para o mês seguinte, sempre dia 10** — e, nesse caso, a pessoa **conclui a
inscrição sem precisar pagar** essa parte.

Agora é uma opção **por evento** (`Evento.parcelas_diretoria_primeira`): `ato` (padrão, comportamento de
sempre) ou `proximo_mes`. Com `proximo_mes`, a parte da diretoria **inteira** sai da cobrança do ato: todas as
parcelas nascem **em aberto**, a 1ª vence no **dia 10 do mês que vem** e as seguintes seguem mês a mês daí.
Numa inscrição **só de diretoria** não sobra nada a pagar, então ela é criada na hora e a pessoa nem passa pela
tela de pagamento. Numa inscrição **mista**, o que os outros participantes devem e a lojinha continuam sendo
cobrados normalmente no ato.

### Arquivos alterados
- `core/models.py`: constantes `PRIMEIRA_PARCELA_ATO`/`PRIMEIRA_PARCELA_PROXIMO_MES`/`PRIMEIRA_PARCELA_CHOICES`
  e `DIA_VENCIMENTO_PARCELA` (= 10); campo `Evento.parcelas_diretoria_primeira` + método
  `Evento.primeira_parcela_no_ato()`; campo `ParcelaInscricao.no_ato`; `Inscricao.valor_no_ato` passou a somar
  pela flag `no_ato` (não pelo `numero`).
- `core/migrations/0070_parcela_primeira_proximo_mes.py`: os dois campos + passo de dados marcando
  `no_ato=True` nas parcelas nº 1 que já existem (todas foram cobradas no ato).
- `core/views.py`: novo `_vencimento_diferido(hoje)` (dia 10 do mês seguinte); `_criar_parcelas_inscricao`
  honra o `primeira_no_ato` do payload (status, vencimento, `no_ato`, pagamento); em `evento_inscrever_view` o
  bloco do parcelamento **saiu de dentro** do `if MP configurado`, e a cobrança só acontece quando
  `a_pagar_agora > 0` — senão a inscrição é criada na hora; as duas montagens de **extrato** (evento e clube)
  passaram a pular a parcela por `no_ato`; contexto novo `parcelar_primeira_no_ato`,
  `parcela_vencimento_diferido` e `primeira_parcela_aberta` (tela de sucesso).
- `core/forms.py`: `parcelas_diretoria_primeira` no `EventoInscricaoConfigForm` (não obrigatório; vazio =
  `ato`), com `clean_parcelas_diretoria_primeira` e ajuda explicando as duas opções.
- `templates/core/evento_painel.html`: o campo novo na "Configuração da inscrição".
- `templates/core/evento_inscrever.html`: texto do parcelamento conforme a opção + `data-primeira-ato` e
  `data-primeiro-vencimento` para o JS.
- `templates/core/evento_inscricao_sucesso.html`: aviso "Nada a pagar agora" com a data da 1ª parcela.
- `static/js/evento_insc_cupom.js`: com a 1ª diferida, o diferido é a parte da diretoria **toda**; resumo com a
  data; total ao vivo com o rótulo "(nada a pagar agora)" quando zera.
- `static/css/eventos.css`: `.sucesso-parcelas-aviso`.
- `core/tests.py`: nova classe `PrimeiraParcelaProximoMesTests` (15 testes) + 1 teste novo na
  `ParcelamentoDiretoriaTests` (o padrão do evento) e a asserção da flag `no_ato` no teste que já
  existia. Suíte: **362 testes OK**.
- `CLAUDE.md`, `docs/ESTADO_ATUAL.md`, `docs/REGRAS_CODEX.md`, `docs/README_PROJETO.md`.

### Decisões tomadas
- **Dia fixo, não "30 dias depois"**: o vencimento é o dia 10 do mês seguinte, independente do dia em que a
  pessoa se inscreveu (dia 1º e dia 28 vencem no mesmo dia 10). Data fixa é o que a família consegue guardar, e
  as parcelas seguintes ficam todas no mesmo dia do mês.
- **A flag `no_ato` na parcela, em vez de deduzir pelo número**: com a 1ª podendo ser diferida, "parcela 1" já
  não significa "parcela cobrada no ato". Sem a flag, a 1ª parcela diferida seria contada **duas vezes** no
  extrato (na linha da inscrição e como lançamento próprio). A migration marca as parcelas antigas.
- **Só a parte da diretoria sai da cobrança**: o resto da inscrição e a lojinha continuam integrais no ato —
  mesma regra do parcelamento desde o começo. Por isso a cobrança de hoje pode ir de "tudo" a **zero**.
- **A opção do evento não parcela sozinha**: quem marca "dividir" continua sendo a pessoa, na inscrição. E o
  parcelamento segue **exigindo Mercado Pago configurado** e **não se combinando** com "pago direto ao evento":
  sem cobrança não há o que dividir, e é por ela que a família paga as parcelas depois.
- **Nada de tela nova**: o link público das parcelas (`/inscricao/<token>/parcelas/`) e a baixa manual do
  Diretor já tratavam parcela em aberto — a 1ª diferida entra nos dois sem código novo.
- **`primeira_no_ato` vai no payload** do pagamento, não é relido do evento na hora de criar as parcelas: entre
  o POST e a aprovação do Pix o Diretor pode mexer na configuração, e a inscrição vale pela regra que a pessoa
  viu na tela.

### Pendências
- **Cobrança automática das parcelas** continua não existindo (nem da 1ª diferida): a família paga pelo link e
  o Diretor cobra na mão. Com a 1ª parcela caindo no mês seguinte, isso pesa mais do que antes.
- O **PDV/balcão** continua sem parcelamento (inscrição presencial é à vista).

## 2026-08-19 - Recuperação de senha encontra quem é da diretoria

### Resumo
Relato do usuário: integrante da **diretoria** digita o CPF em "Esqueci minha senha" e o sistema responde que
**não encontrou a conta**. Causa: `_conta_por_cpf_resp` procurava o CPF **só** em `Aventureiro.resp_cpf` — o
responsável legal de uma criança do clube. Quem é da diretoria e **não tem filho no clube** não existia para
esse fluxo; quem tem filho cadastrado no nome do **outro** responsável legal, também não.

Havia um segundo bloqueio logo depois: mesmo achando a conta, o destino do código vinha de `_numeros_conta`,
que lê apenas pai/mãe/responsável **dos aventureiros da conta**. Conta sem aventureiro devolve vazio, e a
pessoa cairia em "Não há WhatsApp cadastrado para enviar o código".

### Arquivos alterados
- `core/views.py`:
  - `_conta_por_cpf_resp` → **`_conta_por_cpf`**, que procura em `Aventureiro.resp_cpf` **e**
    `MembroDiretoria.cpf` (os dois ignorando `demo`) e devolve `(usuario, via_diretoria)`; segue preferindo
    conta ativa.
  - novos **`_whatsapp_diretoria`** (número da ficha, normalizado) e **`_whatsapp_recuperacao(usuario,
    via_diretoria)`**, que decide o destino do código.
  - `recuperar_senha_view` usa os dois; o erro de CPF não encontrado deixou de citar "responsável legal".
- `templates/core/recuperar_cpf.html`: rótulo do campo virou **"CPF"** e a ajuda explica as duas origens.
- `core/tests.py`: nova classe `RecuperarDiretoriaTests` (5 testes). Suíte: **346 testes OK**.
- `CLAUDE.md`, `docs/ESTADO_ATUAL.md`, `docs/REGRAS_CODEX.md`, `docs/README_PROJETO.md`.

### Decisões tomadas
- **Ordem de preferência do destino** (explícita em `_whatsapp_recuperacao`): a **escolha do Diretor**
  (WhatsApp principal da conta) manda sempre; sem escolha, quem foi achado **pelo CPF da ficha de diretoria**
  recebe no número **da própria ficha**; a ficha também é **fallback** quando não há número de responsável.
  O motivo do caso do meio: pedir a recuperação com o próprio CPF e o código cair no celular do cônjuge (o
  responsável legal do aventureiro) deixa a pessoa sem o código.
- **Não mexer em `_numeros_conta`**: ele é usado também pela cobrança de mensalidades e pelo seletor do
  Diretor em "Usuários"; acrescentar ali uma origem "diretoria" mudaria telas que ninguém pediu. A ficha
  entra só no fluxo de recuperação.
- **CPF do responsável legal continua com prioridade** na busca (a ordem de `achados`), para não mudar o
  destino do código de nenhuma família que já usava o fluxo.

### Conferência em produção (19/08, após o deploy)
Rodado contra a base real (só contagens, nenhum dado pessoal): **11** integrantes da diretoria não-demo, dos
quais **3** já eram encontrados pelo próprio CPF (são também responsável legal de um aventureiro) e **8 não
tinham caminho nenhum** de recuperação. Depois da correção, **11 de 11** são encontrados e **11 de 11** têm
WhatsApp para onde mandar o código. Nenhuma ficha ficou de fora por CPF vazio/inválido.

### Integração com o que já estava no GitHub
Ao subir, o `origin/main` tinha **7 commits** de outra máquina (18/08). Rebase por cima deles, com 3 conflitos
resolvidos: `core/context_processors.py` (ficou a versão de lá — ver acima), `docs/ESTADO_ATUAL.md` e
`docs/HISTORICO_ALTERACOES.md` (entradas empilhadas por data). A correção da recuperação de senha não tocava em
nada do que veio de lá. Suíte depois da integração: **346 testes OK**.

### Pendências
- **Throttle continua faltando** na etapa 1 (cada POST válido dispara um WhatsApp real e revela um login) — e
  a dívida ficou maior: agora há mais CPFs que abrem o fluxo. É a próxima coisa a fazer nessa tela.
- Conta **só de diretoria** não tem como escolher o WhatsApp principal: o seletor mora no card do responsável
  da tela "Usuários", que não existe sem aventureiro. Hoje o número sai direto da ficha, o que resolve o caso
  comum; se alguém precisar de um número diferente do da ficha, é ali que entra.

---

## 2026-08-18 - Evento encerrado para a família sai do menu do Responsável

### Resumo
No perfil **Responsável**, o evento só fica no menu lateral **enquanto ele pode se inscrever**. Vencido o prazo
comum, o evento sai — inclusive (e principalmente) na janela extra **"só diretoria"**, que era o caso que
confundia: o pai via "Aventuri" no menu, entrava, preenchia o formulário inteiro e só era recusado **no envio**.
Os perfis da liderança (Diretor, Diretoria, Tesoureiro, Secretário, Professor) continuam vendo, porque são eles
que podem inscrever nessa janela.

O caso real que motivou: o **Aventuri 2026** ficou com prazo comum vencido em **16/08 23:59** e prazo da
diretoria até **18/08 23:59** — dois dias em que a família via um evento em que não podia mais entrar.

### Arquivos alterados
- `core/context_processors.py`: `_eventos_menu(user)` virou `_eventos_menu(user, perfil)` e, no perfil
  `PERFIL_RESPONSAVEL`, filtra por `evento.inscricoes_abertas()` (prazo **comum**). A chamada passa o
  `perfil_ef`, o mesmo do seletor "Ver como" que já manda no resto do menu.
- `core/tests.py`: `EventoNoMenuPorPerfilTests` (6 testes).

### Decisões tomadas
- **A regra é "a inscrição dele fechou", não "está na janela da diretoria"** (escolha do usuário entre as
  opções apresentadas). Com a regra estreita, o evento **reapareceria** no menu no dia seguinte ao fim da
  janela, já todo encerrado — sai e não volta é mais previsível.
- **Só o menu muda; a página e o formulário ficam como estão** (decisão explícita do usuário): quem tem o
  **link direto** abre a página, abre o formulário e se inscreve, sem gating por perfil. Há teste fixando isso
  (`test_pagina_do_evento_continua_abrindo_por_link_direto`) para ninguém "consertar" por engano depois. A
  consequência conhecida é a brecha antiga: quem marca "diretoria" passa, porque o sistema não confere.
- **A regra segue o perfil EFETIVO** (`perfil_efetivo`, o seletor "Ver como"), não os grupos do usuário: sem
  isso o Diretor que também é pai não conseguiria conferir o que a família vê.
- **Prazo comum, não o da diretoria**, no filtro: é o prazo que vale para a família — usar
  `inscricoes_abertas(tem_diretoria=True)` manteria o evento no menu dela durante a janela extra, que é
  exatamente o que se quis tirar.
- **Filtro em Python, não no banco**: `inscricoes_abertas()` compara prazo efetivo com fallback para o fim do
  evento, e reproduzir isso em SQL duplicaria a regra. A lista do menu tem poucos eventos (só os que ainda vão
  acontecer).

### Pendências
- **A família já inscrita também perde o atalho** — chega à página do evento só por link, e ela ainda precisa
  dela (local, mapa, lojinha, informações do dia). A variante "esconde de quem não vai, mantém para quem já tem
  inscrição no evento" foi apresentada e o usuário preferiu a regra simples; se incomodar quando o Aventuri se
  aproximar, é uma condição a mais (`Inscricao.usuario`, que só existe em quem se inscreveu logado).
- Nada muda para **visitante não logado**: o menu não existe para ele, e a página segue pública conforme o
  evento.

## 2026-08-18 - O resumo passa a listar os participantes por faixa de preço

### Resumo
A pedido do usuário, o **📈 Copiar resumo** deixou de ser só números: agora leva **a lista de todos os
participantes agrupada pela faixa de preço** de cada um — incluindo o grupo da **diretoria** (quem paga o valor
fixo, que não tem faixa). Cada grupo tem o **título com a contagem** e os nomes numerados abaixo, em ordem
alfabética.

Como fica:

```
*📊 Resumo — XVIII AVENTURI APO 2026*

*👥 12 inscritos* em 1 inscrição

*Participantes por faixa:*

*Filho de diretoria (0 a 3 anos) — 1*
1. Bento Alves (2)

*Diretoria / Pais / Responsável — 3*
1. Ana Beatriz Cruz (38)
2. Carlos Dias (45)
3. Ítalo Prado (40)

*Aventureiro — 4*
1. Ana Souza (8)
...

*⛺ Diretoria (valor fixo R$ 200,00) — 2*
1. Paulo Diretor (41)
2. Sonia Diretora (39)

*Pagamento:*
💳 Cartão: 12
```

### Arquivos alterados
- `core/views.py`: o laço de `_export_inscritos_evento` passou a guardar `nomes_por_faixa`
  (`faixa_id` / `"_diretoria"` / `"_sem_faixa"` → `[(nome, idade)]`) — no mesmo laço que já existia, sem
  varredura nem query nova. `_resumo_inscritos_txt` monta um grupo por faixa: título com a contagem e os nomes
  numerados, ordenados por `_norm_comparacao` (o mesmo normalizador que a "cobertura do clube" usa).
- `templates/core/evento_painel.html`: o `title` do botão parou de prometer "sem nome de ninguém" e passou a
  avisar que leva nomes; comentário da seção atualizado.
- `core/tests.py`: `CopiarListaInscritosTests` de 35 para **37 testes**. Saíram dois que travavam o
  comportamento antigo (`test_resumo_nao_leva_nome_de_ninguem` e a versão anterior do "fecha no total");
  entraram: os nomes dentro de cada faixa, a ordem alfabética ignorando acento e maiúscula, participante sem
  idade sem `()`, e o "fecha no total" agora conferindo **também** que a quantidade de nomes de cada grupo casa
  com o número do título.

### Decisões tomadas
- **Contagem e nomes no mesmo bloco**, não em dois: o número foi para o título do grupo
  (`*Aventureiro — 4*`). Um bloco de contagens acima e a lista de nomes abaixo repetiria a mesma informação
  numa mensagem que já é longa. (Se pedirem o compacto de volta, é um bloco a mais no topo.)
- **Ordem alfabética dentro do grupo**, ignorando acento e maiúscula: o uso é procurar uma pessoa numa lista de
  35. A ordem de inscrição continua nos outros dois textos.
- **A soma dos grupos = total** segue sendo invariante testada, e ganhou um segundo trava: a contagem do título
  tem de casar com a quantidade de nomes listados.
- **Perda deliberada**: o resumo era o texto sem dados pessoais, o que permitia mandá-lo em qualquer grupo. Com
  nomes de crianças dentro, não é mais. Foi avisado ao usuário; a decisão é dele, é o dado do clube dele. O
  `title` do botão agora carrega o aviso para quem for usar depois.

### Pendências
- Sem **filtro por faixa** na cópia: sai o evento inteiro. Num evento de 300 pessoas o texto fica grande demais
  para uma mensagem só (o `_partir_texto_whatsapp` do aviso interno resolveria, se virar problema).
- A lista não diz **quem já pagou** por pessoa — pagamento é por inscrição, e essa visão está no bloco
  *Pagamento* (em números) e na aba Financeiro.

## 2026-08-18 - Correção: o resumo dizia "Aventureiros" para gente que não é aventureiro

### Resumo
Bug de **rótulo, não de contagem**, encontrado pelo usuário no primeiro uso real (Aventuri 2026): o resumo
mostrava `🧒 Aventureiros: 31` quando os aventureiros do evento são **13**. A linha não era uma contagem, era
uma **subtração** — `total − marcados como diretoria` —, e nesse "resto" cabiam três categorias diferentes:
aventureiro (13), "Diretoria / Pais / Responsável" (15) e filho de diretoria (3). A linha saiu: **quem
categoriza é a faixa de preço**, que é onde o evento cadastra a categoria de verdade, e o bloco "Por faixa"
agora **fecha no total**, servindo de conferência.

Na mesma passada, duas coisas que o usuário estranhou no mesmo texto:

- **"Filho de diretoria" aparecia duas vezes.** O evento tem **três faixas com esse mesmo rótulo** (0-3, 4-5 e
  10-17 anos, preços diferentes); duas tinham gente. Rótulo repetido agora ganha a idade ao lado:
  `Filho de diretoria (0 a 3 anos): 1`.
- **"Diretoria (valor próprio): 4"** não explicava nada ("valor próprio de quê?"). Virou
  `⛺ Diretoria (valor fixo R$ 200,00): 4` — diz o valor que a caixinha "diretoria" faz a pessoa pagar,
  lido do `Evento.valor_diretoria`.

Antes e depois, com os números reais do Aventuri:

```
ANTES                                   DEPOIS
⛺ Diretoria: 4                          *Por faixa:*
🧒 Aventureiros: 31   ← errado           Filho de diretoria (0 a 3 anos): 1
                                        Diretoria / Pais / Responsável: 15
*Por faixa:*                            Filho de diretoria (10 a 17 anos): 2
Filho de diretoria: 1                   Aventureiro: 13
Diretoria / Pais / Responsável: 15       ⛺ Diretoria (valor fixo R$ 200,00): 4
Filho de diretoria: 2                                        (soma = 35 = total)
Aventureiro: 13
Diretoria (valor próprio): 4
```

### Arquivos alterados
- `core/views.py` (`_resumo_inscritos_txt`): saíram as linhas `⛺ Diretoria` / `🧒 Aventureiros` do topo; a
  contagem de diretoria passou para dentro do bloco por faixa (é o que faz o bloco fechar no total); rótulo
  duplicado ganha `(x a y anos)`; a linha da diretoria mostra o `valor_diretoria` do evento quando existe.
- `core/tests.py`: `CopiarListaInscritosTests` de 30 para **35 testes**. Saiu o
  `test_resumo_separa_diretoria_de_aventureiros` (afirmava o comportamento errado) e entraram: não inventa
  categoria de aventureiros, a linha da diretoria diz o valor fixo, evento sem `valor_diretoria` não inventa
  preço, desambiguação de rótulos iguais, rótulo único **não** ganha idade, e o invariante
  **"por faixa fecha no total"**.

### Decisões tomadas
- **Não inventar categoria**: "aventureiros" não é "todo o resto". Nem tentei adivinhar pela faixa (procurar a
  palavra "aventureiro" no rótulo) — o rótulo é texto livre do Diretor, e adivinhar erraria de novo, calado.
- **A soma do bloco por faixa = total** virou invariante com teste. É o que permite bater o olho e confiar:
  se as linhas não somam o total, tem gente numa categoria que ninguém está vendo.
- **A idade só aparece quando o rótulo repete.** Colocar sempre encheria a linha (o WhatsApp quebra por volta
  de 35 caracteres) num evento com faixas bem nomeadas.
- **Nada de renomear as faixas do usuário**: a alternativa era pedir para ele renomear as três "Filho de
  diretoria" no painel. Resolver no resumo é melhor — o sistema deixa de depender de o cadastro estar
  perfeito, e o cadastro dele não está errado (três faixas de preço com o mesmo nome é legítimo).

### Pendências
- A linha `Diretoria / Pais / Responsável: 15` × `⛺ Diretoria (valor fixo): 4` continua podendo confundir:
  são coisas diferentes (a **faixa** de adulto × a **caixinha** que dá o valor fixo). O resumo agora diz o
  valor de cada uma, mas quem lê rápido pode somar errado. Só resolve de verdade quando "diretoria" for um
  vínculo real (participante × cadastro), que é dívida antiga.
- **Vale conferir no evento 67**: 15 pessoas na faixa de adulto (R$ 450) e 4 na diretoria (R$ 200) — se a
  intenção era que os 15 fossem diretoria, quem está pagando R$ 450 deveria estar pagando R$ 200.

## 2026-08-18 - Eventos: botão "Copiar resumo" (números do evento, sem nomes)

### Resumo
Terceiro botão de cópia na aba **Inscrições**: **📈 Copiar resumo** leva só os **números** do evento e **nenhum
nome** — dá para mandar no grupo da diretoria sem expor dados das famílias, e é o que serve para prestar contas
à associação. O pedido do usuário foi explícito num ponto: **"inscritos" é gente, não inscrição** — o resumo
conta **participantes**. Traz: total de pessoas (e em quantas inscrições), **diretoria × aventureiros**,
**quantos por faixa de preço** do evento, **quantos por forma de pagamento**, **quanto falta acertar** de quem
paga por fora e **quantas parcelas em aberto** (com o que venceu).

Como fica:

```
*📊 Resumo — XVIII Aventuri APO 2026*

*👥 8 inscritos* em 6 inscrições
⛺ Diretoria: 2
🧒 Aventureiros: 6

*Por faixa:*
6 a 9 anos: 3
Juvenis: 2
Diretoria (valor próprio): 2
Sem faixa: 1

*Pagamento:*
🌐 Online (site): 3
💵 Dinheiro: 1
💠 Pix: 2
💳 Cartão: 1
🎁 Cortesia: 1
⚠️ Falta acertar (pago por fora): 1 pessoa — R$ 450,00
📆 Parcelas em aberto: 1 inscrição — R$ 337,50
```

### Arquivos alterados
- `core/views.py`: `_export_inscritos_evento` passou a acumular as contagens no **mesmo laço** que já monta a
  planilha e o texto do WhatsApp (nenhuma varredura extra) e devolve a chave **`resumo`**; o texto em si é
  montado pelo novo **`_resumo_inscritos_txt`**. O `prefetch_related` ganhou `participantes__faixa` e
  `pedidos`.
- `templates/core/evento_painel.html`: terceiro botão + a `<textarea id="exportListaResumo">`.
- `core/tests.py`: `CopiarListaInscritosTests` foi de 15 para **30 testes** (15 novos, só do resumo).
- `static/js/evento_painel.js`: **nada** — o módulo já copia qualquer `.btn-copiar-lista`.

### Decisões tomadas
- **Botão separado, não resumo no topo da lista** (escolha do usuário entre as opções apresentadas): o resumo
  sem nomes pode ir para um grupo onde a lista de crianças não pode ir. Um teste garante que nome de
  responsável, de participante e telefone **não aparecem** no resumo.
- **Pagamento contado em pessoas**, não em inscrições: se a família de três pagou no Pix, são três pessoas
  pagas no Pix. A **exceção são as parcelas**, que existem por inscrição — é o valor da diretoria que se
  divide —, e a linha diz "inscrições" para não confundir.
- **Faixas do evento em vez de idade exata** (escolha do usuário): é mais curto e é o que casa com o dinheiro.
  Usa o `rotulo` quando existe, senão a faixa de idades; **faixa sem ninguém não aparece** (ruído).
- **Diretoria fora da contagem por faixa**: quem paga o valor da diretoria não tem faixa (o valor independe da
  idade), então contar nas duas dimensões somaria a mesma pessoa duas vezes. Aparece na própria linha.
- **"Sem faixa" aparece quando existe**: idade fora de todas as faixas (ou sem idade) é quase sempre erro de
  cadastro, e alguém tem de ver.
- **O que falta acertar usa `total_com_loja`** (inscrição + lojinha levada junto), o mesmo número que o painel
  mostra no controle de "pago direto ao evento" — divergir do painel seria pior que não ter o número.
- **Uma informação por linha**, sem juntar com "·": a linha de uma faixa com rótulo longo ou de quatro formas
  de pagamento passaria dos ~35 caracteres em que o WhatsApp quebra no celular, e o corte cairia no meio de um
  número. Um teste trava o tamanho das linhas em 60 caracteres.
- **Linha que não tem número não é escrita**: sem diretoria, sem "⛺ Diretoria: 0"; sem pendência, sem "Falta
  acertar". Resumo que mente por omissão de zero é melhor que resumo cheio de zeros.
- **Nada de nova query**: as contagens saem do laço que já existia, e o que faltava (faixa de cada
  participante, pedidos da lojinha) entrou no `prefetch_related`.

### Pendências
- **Não tem contagem por unidade** (as unidades do clube não estão ligadas ao participante da inscrição — o
  vínculo participante × aventureiro é dívida antiga, a mesma que impede conferir quem é "diretoria" de fato).
- **Check-in não entra** no resumo (existe `ParticipanteInscricao.presente`, e o painel já tem os contadores do
  dia na aba própria).
- Não há contagem de **idade exata** — ficou pela faixa. Se um dia a associação pedir por idade, é o mesmo laço.

## 2026-08-18 - Eventos: a cópia da lista sai formatada para o WhatsApp

### Resumo
Ajuste de rumo no mesmo dia da entrega anterior, a pedido do usuário: **o destino real da lista é o WhatsApp**.
A cópia agrupada saía num desenho de terminal (`1) Nome — telefone — código`, com os participantes indentados)
que **parte no meio** na tela do celular, onde o WhatsApp quebra linha por volta de 35 caracteres. Agora sai
formatada para lá: cabeçalho com o **nome do evento e a contagem**, e **três linhas curtas por família** — nome
em **negrito**, `📱 contato · 🎟️ código`, e os participantes com a idade entre parênteses. Os botões passaram a
dizer o destino: **📊 Copiar para planilha** e **💬 Copiar para o WhatsApp**.

Como fica:

```
*📋 Inscritos — XVIII Aventuri APO 2026*
_4 inscritos · 3 inscrições_

*1. Marcos Souza*
📱 (16) 99999-1111 · 🎟️ MN976R
👤 Ana Souza (12), Bruno Souza (9)

*2. Rita Lima*
📱 (16) 98888-2222 · 🎟️ 2YRP6Z
👤 Carla Lima (10)
```

### Arquivos alterados
- `core/views.py`: em `_export_inscritos_evento`, a chave `grupos` virou **`whatsapp`** e passou a montar o
  cabeçalho (`*📋 Inscritos — evento*` + `_N inscritos · N inscrições_`) e o bloco de três linhas por família.
  Deixou de usar o `_participantes_txt` (que segue servindo o aviso interno, com outro desenho).
- `templates/core/evento_painel.html`: rótulos e `title` dos dois botões, `id` da textarea
  (`exportListaGrupos` → `exportListaWhatsapp`) e o comentário da seção.
- `static/js/evento_painel.js`: só o comentário do módulo (o código não olha o formato, apenas copia).
- `core/tests.py`: `CopiarListaInscritosTests` foi de 11 para **15 testes** — cabeçalho com evento e contagem,
  singular/plural do cabeçalho, as três linhas por família, a linha em branco entre famílias, participante sem
  idade (nada de `()` nem `None`) e a numeração casando entre os dois textos.

### Decisões tomadas
- **Negrito e itálico do WhatsApp** (`*nome*`, `_resumo_`): fora do WhatsApp aparecem como asterisco e
  sublinhado mesmo, e isso é aceitável — este botão **tem um destino declarado**. Quem quer texto cru para
  outro lugar usa o de planilha.
- **Três linhas curtas em vez de uma longa**: foi a escolha do usuário entre os desenhos apresentados. Numa
  lista de 50 inscrições, uma linha por participante encheria a tela de rolagem; juntar os participantes numa
  linha só (`👤 Ana (12), Bruno (9)`) mantém a família legível de um olhar.
- **Cabeçalho com nome do evento e contagem**: quem recebe a lista no WhatsApp não tem o painel na frente
  para saber de que evento se trata, nem se a lista chegou inteira.
- **Idade entre parênteses, sem "anos"**: encurta a linha, que é o recurso escasso no celular.
- **Rótulos dizem o destino** ("para planilha" / "para o WhatsApp") em vez da forma ("lista" / "por
  inscrição"): quem abre o painel escolhe pelo lugar onde vai colar, não pelo formato do texto.
- O botão de **planilha não mudou**: TAB continua sendo o que Excel e Sheets entendem ao colar.

### Pendências
- As mesmas de antes: WhatsApp sai como foi digitado na inscrição, sem coluna de valor/situação e sem filtro
  por faixa ou unidade.
- Lista muito grande **não é partida** em várias mensagens (o WhatsApp aceita bem mais texto colado do que a
  API envia, então isso só apareceria num evento gigante). Se virar problema, o `_partir_texto_whatsapp` do
  aviso interno já resolve o mesmo tipo de caso.

## 2026-08-18 - Eventos: copiar a lista de inscritos (planilha e por inscrição)

### Resumo
A aba **Inscrições** do painel do evento ganhou dois botões de cópia: **📋 Copiar lista** (uma linha por
**pessoa** inscrita, em colunas separadas por TAB — cola direto em planilha) e **📋 Copiar por inscrição**
(agrupada por família, responsável + WhatsApp + código numa linha e os participantes abaixo — o formato que se
lê no WhatsApp). Os dois trazem o **telefone** e o **número (código) da inscrição** de cada inscrito, que era o
que faltava para levar a lista para fora do sistema. Só entra inscrição **confirmada**.

### Arquivos criados/alterados
- `core/views.py`: novo **`_export_inscritos_evento(evento)`**, que devolve `{total, qtd_inscricoes, tabela,
  grupos}` — `tabela` com cabeçalho de colunas e uma linha por participante, `grupos` reaproveitando o
  `_participantes_txt` do aviso interno. Entrou no contexto do `evento_painel_view` como `export_inscritos`.
- `templates/core/evento_painel.html`: os dois botões no cabeçalho da sub-aba "Lista de inscrições", a nota com
  a contagem (inscritos × inscrições confirmadas) e as duas `<textarea class="copiar-fonte">` com o texto
  pronto. Tudo dentro de `{% if export_inscritos.total %}`.
- `static/js/evento_painel.js`: módulo que copia o texto da `textarea` correspondente ao botão
  (`data-fonte`), com toast padrão do sistema e "✅ Copiado!" no próprio botão.
- `static/css/eventos.css`: `.copiar-lista-acoes`, `.copiar-lista-nota` e `.copiar-fonte`.
- `core/tests.py`: `CopiarListaInscritosTests` (11 testes).

### Decisões tomadas
- **Copiar, não exportar arquivo**: pedido do usuário. Evita rota nova, download e a dúvida de "onde foi salvo
  o arquivo" no celular — e o destino real da lista é colar no WhatsApp ou na planilha.
- **Texto montado no servidor, não no JS a partir do DOM**: a lista da tela tem selos, pills e detalhes em
  `<details>`; raspar o HTML daria um texto frágil, que quebraria no próximo ajuste visual. O JS só copia.
- **TAB como separador** (e não vírgula ou ponto e vírgula): Excel e Google Sheets quebram em colunas ao colar
  texto tabulado, sem passar por importação de CSV. Colado num lugar que não é planilha, ainda se lê.
- **O WhatsApp repete em cada participante da mesma inscrição** na versão em colunas: na planilha cada linha
  tem de se sustentar sozinha — célula vazia estragaria filtro e ordenação. Um teste garante isso.
- **`<textarea>` fora da tela em vez de `hidden`**: a cópia de reserva (navegador antigo, ou `clipboard` negado
  pelo navegador) precisa de `select()` num campo que exista de fato; `display:none` impede a seleção.
- **Cancelada fica fora**, confirmada entra — inclusive a que vai **pagar por fora**: para contato, o que
  importa é que a pessoa está inscrita. Quem quer a lista de pendência de pagamento tem o aviso interno.
- **Numeração igual à do aviso interno** (ordem de `criado_em`): o "nº 3" da planilha e o "3)" do texto
  agrupado falam da mesma gente.
- A lógica de cópia ficou **repetida** em relação ao `evento_pagamento.js` (código Pix). Extrair um utilitário
  comum mexeria em pagamento, loja e WhatsApp de uma vez — ficou anotado como dívida, não foi feito agora.

### Pendências
- A lista sai com o WhatsApp **como foi digitado** na inscrição (o painel mostra igual); não há normalização de
  formato entre uma inscrição e outra.
- Sem coluna de valor, forma de pagamento ou situação — a lista é de **contato**. Se precisar do financeiro em
  planilha, é outro formato (e aí um CSV de verdade compensa).
- Não há filtro por faixa/unidade na cópia: sai a lista inteira do evento.

---

## 2026-08-17 - Eventos: a janela da diretoria fica discreta (e some do menu do Responsável)

### Resumo
Ajuste do prazo de inscrição da diretoria (feito mais cedo no mesmo dia), a pedido do usuário: **nenhuma tela
pública conta que a diretoria tem prazo diferente**, e **o Responsável deixa de ver o evento assim que o prazo
do aventureiro vence**.

Passado o **prazo comum**, a página do evento volta ao estado de sempre — "⛔ Inscrições encerradas", **sem o
botão de inscrever, para todo mundo** (inclusive a própria diretoria e o visitante não logado). A diretoria
entra pelo **link direto** de `/eventos/<id>/inscrever/`, que a view continua abrindo pelo prazo mais generoso;
quem decide continua sendo a **validação do POST** pela composição real da inscrição, com a trava no model.

No **menu**, o evento sai da lista do **Responsável** junto com o prazo comum, mesmo faltando dias para
acontecer. Os demais perfis (Diretor, Diretoria, Professor…) continuam vendo o evento até ele terminar — é por
ali que a diretoria chega ao link na janela extra.

### Arquivos alterados
- `templates/core/evento_pagina.html`: some o terceiro estado visual (`.parcial` / "só diretoria"), o parágrafo
  "Inscrição com diretoria vai até…" e a dica "A inscrição precisa incluir alguém da diretoria". O status e o
  botão passam a seguir o **prazo comum**.
- `templates/core/evento_inscrever.html`: some o bloco `insc-aviso-prazo` que explicava a janela extra.
- `core/views.py`: `evento_pagina_view` publica `inscricoes_abertas` = `evento.inscricoes_abertas()` (prazo
  comum) e não passa mais `so_diretoria`/`prazo_diretoria`/`tem_prazo_diretoria`; `evento_inscrever_view` perde
  as mesmas chaves do contexto e o **erro de POST fora do prazo virou genérico** nos dois casos.
- `core/context_processors.py`: **descartado** na integração de 19/08 — esta parte foi feita, em paralelo e
  melhor, pelo commit `f24d3a9` de 18/08 ("Esconde do responsavel o evento cuja inscricao ja encerrou para
  ele"), que usa o **perfil efetivo** (`_eventos_menu(user, perfil)`) em vez de `atua_como_responsavel`. Os 3
  testes de menu escritos aqui ficaram e passam contra aquela implementação. Vale a versão de 18/08.
- `static/css/eventos.css`: removidas `.evento-publico-status.parcial` e `.insc-aviso-prazo` (sem uso).
- `core/models.py`: docstring de `so_diretoria_pode_inscrever` (agora é estado **interno**).
- `core/tests.py`: 3 testes novos de menu; 3 reescritos (a página esconde o botão, a tela não avisa, o erro é
  genérico). Suíte: **298 testes OK** (295 + 3).
- `CLAUDE.md`, `docs/ESTADO_ATUAL.md`, `docs/REGRAS_CODEX.md`.

### Decisões tomadas
- **O botão some para todos, não só para o Responsável** (escolha do usuário): esconder por perfil exigiria a
  diretoria estar logada e com o perfil ativo certo — quem estivesse "vendo como Responsável" não acharia o
  caminho. Com o link direto, o acesso não depende de perfil, e a validação de servidor continua a mesma.
- **Erro de POST genérico**: manter a mensagem antiga ("só a diretoria ainda pode se inscrever, até…")
  anularia o efeito — era a instrução mais explícita de todas.
- **O painel do Diretor não mudou**: lá o selo ⛺ Só diretoria e a data da janela continuam à mostra, porque é
  a tela de quem configura o prazo.

### Pendências
- Sem o item de menu, o Responsável perde também o caminho para a **lojinha** daquele evento depois do prazo de
  inscrição (o link direto continua valendo). Consequência aceita na decisão; se incomodar, o desenho natural é
  manter no menu só os eventos com lojinha aberta, com um rótulo que não prometa inscrição.
- Quem já se inscreveu também deixa de ver o evento no menu depois do prazo — hoje o menu não sabe quem está
  inscrito. Uma futura seção "Minhas inscrições" resolveria isso melhor que o menu de eventos.


## 2026-08-17 - Eventos: prazo de inscrição próprio da diretoria

### Resumo
O evento passa a ter um **segundo prazo de inscrição, só para a diretoria**
(`Evento.inscricao_limite_diretoria`, migration **0069**), normalmente mais longo — a diretoria fecha a lista
depois das famílias. A regra combinada: **uma inscrição que inclua alguém da diretoria vale por esse prazo
INTEIRA**, então o aventureiro que entra na mesma inscrição aproveita a janela extra, mesmo com o prazo comum
já vencido. É o caso que motivou o pedido.

O prazo da diretoria **só estende, nunca restringe**: o prazo de uma inscrição com diretoria é sempre o **mais
generoso** entre os dois. Assim ninguém perde uma janela que já tinha — se o prazo da diretoria vencer antes do
comum, a diretoria continua se inscrevendo no prazo comum.

### Arquivos alterados
- `core/models.py`: campo `inscricao_limite_diretoria`; `prazo_inscricao_diretoria()` (o máximo entre os dois),
  `prazo_inscricao_efetivo(tem_diretoria)`, a property `tem_prazo_diretoria` (só True quando de fato estende) e
  `so_diretoria_pode_inscrever`. **`inscricoes_abertas()` ganhou o parâmetro `tem_diretoria=False`** —
  compatível com todas as chamadas antigas.
- `core/migrations/0069_prazo_inscricao_diretoria.py`.
- `core/forms.py`: o campo no `EventoInscricaoConfigForm` (com `input_formats` do `datetime-local`, como o
  prazo comum) e a explicação de que ele só estende.
- `core/views.py`: `evento_inscrever_view` abre a tela pelo prazo **mais generoso** e valida o POST pela
  **composição real** da inscrição; `evento_pagina_view` e `evento_painel_view` publicam o estado da janela.
- `templates/core/evento_pagina.html`, `evento_inscrever.html`, `evento_painel.html`; `static/css/eventos.css`.
- `core/tests.py`: 15 testes novos (`PrazoDiretoriaTests`). Suíte: **295 testes OK** (280 + 15).

### Decisões tomadas
- **"Só estende, nunca restringe"** (escolha do usuário, entre as duas regras possíveis): o prazo da diretoria
  é sempre comparado com o comum e vale o maior. A alternativa — "o prazo da diretoria manda, para bem ou para
  mal" — recusaria uma inscrição com diretoria depois do prazo dela, mesmo que o aventureiro ainda estivesse no
  prazo próprio; é mais simples de explicar, mas barra inscrição que seria válida.
- **A tela abre pelo prazo mais generoso; o POST valida pela composição real.** Se a tela fechasse pelo prazo
  comum, a diretoria nunca chegaria ao formulário na janela extra. A regra de verdade está na validação do POST
  (`any(l["diretoria"] for l in linhas)`), e a trava final no model — POST forjado com `part_diretoria_1`
  depois dos **dois** prazos não cria nada (há teste).
- **Basta marcar a caixinha "diretoria"** (decisão do usuário), como já vale para o **valor** da diretoria: o
  sistema não confere se a pessoa consta na diretoria do clube. Consistente com o que existe, e a inscrição
  aceita nome livre até de quem não tem conta. Fica a brecha conhecida: alguém marcar "diretoria" para se
  inscrever fora do prazo — hoje ela já existe para pagar o valor da diretoria.
- **Terceiro estado visual na página do evento** (classe `.parcial`, âmbar): a faixa verde dizia "aberto" e a
  vermelha "encerrado", e nenhuma das duas descreve "encerrado para as famílias, aberto para a diretoria".
  Achado na verificação visual — a faixa saía **verde** com o texto "Inscrições encerradas".
- **O PDV/balcão continua sem checar prazo** (só se o evento terminou): é inscrição presencial feita pela
  própria diretoria, e travá-la por prazo atrapalharia o atendimento no dia.

### Pendências
- A brecha do "marcar diretoria sem ser": fechar exigiria casar a pessoa com o `MembroDiretoria` cadastrado, o
  que hoje não dá (a inscrição guarda **nome livre** e nem exige login). Vale junto do vínculo exato de
  participante × aventureiro, que já é dívida antiga.
- O prazo da diretoria **não afeta a lojinha** do evento (que segue aberta até o evento terminar) nem o
  cancelamento de inscrição — cancelar continua sendo ação só do Diretor, sem prazo.

## 2026-08-17 - Eventos: valor da diretoria parcelado (estilo mensalidade)

### Resumo
A parte da inscrição que **a diretoria** paga passa a poder ser dividida em parcelas cobradas **pelo clube**
(não é parcelamento de cartão): a **1ª parcela é cobrada no ato** da inscrição e as seguintes vencem **mês a
mês**, pagas por um link próprio da inscrição. Quantas parcelas é **configurável por evento**
(`Evento.parcelas_diretoria`, 1 = à vista). Motivação: eventos regionais caros (Aventuri) em que o valor da
diretoria pesa de uma vez só.

**Só a parte da diretoria é parcelada.** Numa inscrição mista (um integrante da diretoria + os filhos), no ato
a família paga **1ª parcela da diretoria + o valor integral dos outros participantes + a lojinha**; as parcelas
restantes cobrem apenas o valor da diretoria.

### Arquivos criados/alterados
- `core/models.py`: `Evento.parcelas_diretoria` + `permite_parcelar_diretoria()` e `dividir_parcelas()`
  (a sobra dos centavos vai na 1ª parcela, então as seguintes ficam iguais e redondas); model novo
  **`ParcelaInscricao`** (número/total, valor, vencimento, situação, forma, baixa e FK do `Pagamento`);
  em `Inscricao`, o `token_parcelas` (link público, mesmo mecanismo do `token_acerto` da família) e as
  propriedades **`valor_no_ato`** e **`valor_no_caixa`**; `parcela_inscricao` entra em
  `TIPO_PAGAMENTO_CHOICES`.
- `core/migrations/0068_parcelamento_diretoria_evento.py`.
- `core/forms.py`: `parcelas_diretoria` no `EventoInscricaoConfigForm`, campo vazio = à vista, teto de 12, e
  validação cruzada — parcelar exige um `valor_diretoria` definido.
- `core/views.py`: na inscrição, o total da diretoria é separado e, se a pessoa marcar parcelar, a cobrança do
  ato passa a ser `total − parcelas futuras`; `_criar_parcelas_inscricao` (1ª paga, as outras abertas) e
  `_somar_meses`; `_finalizar_parcela_inscricao` no dispatch do pagamento; página pública
  `inscricao_parcelas_view` + `inscricao_parcela_pagar_view` (uma parcela por cobrança); baixa manual do
  Diretor em `evento_parcela_pago_view`; e as somas de caixa passando a usar `valor_no_caixa`.
- `core/urls.py`: `/eventos/<id>/parcelas/<id>/pago/`, `/inscricao/<token>/parcelas/` e `.../pagar/`.
- `templates/core/inscricao_parcelas.html` (nova, pública), `evento_inscrever.html` (opção de parcelar),
  `evento_inscricao_sucesso.html` (parcelas + link para guardar) e `evento_painel.html` (config, parcelas por
  inscrição com baixa manual e o card "Parcelas da diretoria" no Financeiro).
- `static/js/evento_insc_cupom.js`: prévia do parcelamento (mostra a opção só quando há participante de
  diretoria; o total passa a exibir "a pagar agora").
- `static/css/eventos.css`: blocos do parcelamento, das parcelas e do card do financeiro.
- `core/tests.py`: 27 testes novos (`ParcelamentoDiretoriaTests`). Suíte: **280 testes OK** (253 + 27).

### Decisões tomadas
- **É o clube que parcela, não o cartão.** O checkout do Mercado Pago já oferecia até 12x no cartão (juros do
  titular, clube recebe tudo na hora); isso é outra coisa — aqui o clube **recebe em 3 vezes**, como as
  mensalidades. As duas coisas convivem: a 1ª parcela ainda pode ser paga no cartão em 12x.
- **A inscrição é confirmada com a 1ª parcela paga**, não depois de quitar tudo — a pessoa fica inscrita e o
  Diretor vê o que falta. Mantém a regra do sistema de que a inscrição só existe após um pagamento aprovar.
- **Numa inscrição mista, uma única cobrança no ato** (1ª parcela + os outros participantes + lojinha), não
  duas. Dois pagamentos deixariam a inscrição confirmada pela metade se um falhasse.
- **Caixa só conta o que entrou.** `Inscricao.valor_total` continua sendo o valor da inscrição, mas **toda soma
  de caixa passou a usar `valor_no_caixa`** (total − parcelas em aberto). Sem isso a arrecadação do evento e o
  Financeiro do clube mostrariam dinheiro que não chegou. No **extrato**, a linha da inscrição vale o
  `valor_no_ato` e cada parcela paga depois é um lançamento próprio, na data em que caiu — assim o extrato soma
  exatamente a arrecadação, sem contar a mesma parcela duas vezes (há teste que compara os dois).
- **Uma cobrança por parcela**, e não uma que quita várias: a baixa fica individual e a taxa do gateway cai na
  parcela certa.
- **Link público por token**, como o acerto de mensalidades: quem se inscreve pode não ter conta no sistema.
- **Parcelar não se combina com "pago direto ao evento"**: naquele fluxo o dinheiro nunca passa pelo clube, e
  já existe o controle de pendência próprio. Sem Mercado Pago configurado também não há parcelamento (não há
  cobrança nenhuma).
- A trava é no **servidor**: `permite_parcelar_diretoria()` é reavaliado no POST, então esconder o campo (ou
  forjar `parcelar_diretoria=1`) não parcela nada — há teste.
- A **baixa manual** do Diretor (parcela acertada em dinheiro) **entra** no caixa, ao contrário da baixa do
  "pago direto ao evento". Reabrir uma parcela solta o vínculo com o `Pagamento`, para a taxa não ficar somada
  a uma parcela que voltou a contar como em aberto.
- Na página pública, **um seletor de forma de pagamento só** e **um botão por parcela** (o `name="parcela_id"`
  vai no próprio botão). A primeira versão repetia o seletor inteiro por parcela — legível em 3x, ilegível em
  12x. A cobrança continua sendo **uma parcela por vez**.
- Achado na verificação visual: o bloco do parcelamento é `display:flex` e nasce com `hidden`, e **`[hidden]`
  não esconde flex** — ele aparecia (80px de altura) em toda inscrição sem diretoria. Corrigido com
  `.insc-parcelar[hidden] { display: none; }`. É o mesmo tropeço da lista de busca; a regra foi
  **generalizada** no `REGRAS_CODEX.md`, porque nenhum teste Python pega isso.

### Pendências
- **Não há cobrança automática das parcelas.** Nada avisa a família quando a parcela 2 vence — o Diretor
  manda o link na mão. O gancho natural é o `_notificar` com um template novo, no padrão da cobrança de
  mensalidades (respeitando os gates e o 1-por-request com 10s).
- O **PDV/balcão não parcela**: o parcelamento existe só na inscrição pelo site.
- O parcelamento não é oferecido em inscrição **gratuita** nem quando o valor da diretoria é 0 (não há o que
  dividir).
- Os vencimentos são mês a mês a partir da inscrição, **sem travar na data do evento**: quem parcela em 3x num
  evento que acontece em 30 dias fica com parcelas vencendo depois do evento. É escolha do Diretor ao definir
  o número de parcelas.

## 2026-08-15 - Doc: listas canônicas de rotas e models atualizadas

### Resumo
Passagem de documentação depois das duas entregas do dia. Os resumos do topo do `ESTADO_ATUAL.md` já tinham
sido escritos, mas as **listas canônicas** do fim do arquivo (rotas e models) e o `README_PROJETO.md` ainda
descreviam o estado anterior. Sem código.

### Arquivos alterados
- `docs/ESTADO_ATUAL.md`: no model `Evento`, os campos que faltavam (`ativo`, `formas_pagamento_fora`/
  `instrucoes_pagamento_fora`, `notificar_inscricoes`/`notificar_inscricoes_para`) e as migrations até
  **0067**; nas rotas, `/eventos/avisar-inscritos/` e `/eventos/<id>/inscricoes/<id>/pago/`; na etapa 2 da
  recuperação, o usuário de acesso; e a dívida técnica do throttle, que ficou mais séria com essa exibição.
- `docs/README_PROJETO.md`: mesma coisa no nível de resumo — model `Evento`, rota do aviso de inscritos e o
  item de recuperação de senha.

## 2026-08-15 - Aviso de inscrição: lista completa, enviada em partes

### Resumo
Correção de rumo logo após a entrega anterior. O aviso tinha um **teto de texto** que aparava as inscrições
mais antigas quando a mensagem crescia — ou seja, **inscrito sumia da lista**. A regra é o contrário:
**quem se inscreveu nunca sai da lista de inscritos**, tenha pago na hora ou por fora. O teto saiu; quando o
texto não cabe numa mensagem do WhatsApp, ele agora é **enviado em partes numeradas**.

### Arquivos alterados
- `core/views.py`: removido o `LIMITE_TEXTO_LISTA` e o aparo em `_texto_inscritos_evento`. Novo
  **`_partir_texto_whatsapp`** (corta só em quebra de linha, numera "(i de N)", parte à força linha que
  sozinha não caberia) e `_notificar_whatsapp` passou a enviar as partes em ordem, parando na primeira falha
  e devolvendo a posição dela.
- `core/tests.py`: o teste do aparo virou **`test_evento_grande_nao_perde_ninguem_da_lista`** (o mais antigo e
  o mais novo continuam na lista), mais 3 testes novos (envio em partes numeradas com todo mundo presente,
  corte respeitando as linhas, texto curto que não vira parte).

### Decisões tomadas
- **Partir em vez de cortar**: numa lista de pessoas, o que "não cabe" é gente — resumir seria perder a
  informação que motivou o aviso. Dividir mantém tudo e é transparente para quem recebe.
- **A divisão mora no `_notificar_whatsapp`**, não no aviso de inscrição: qualquer notificação longa passa a
  ser tratada igual, e o extrato 📨 Envios grava uma linha por parte (é o que de fato saiu).
- Limite de **3500 caracteres** por mensagem, com folga sob o limite da API.

### Validação
- **253 testes OK** (237 + 16 do aviso).

## 2026-08-15 - Eventos: aviso interno de inscrição para a diretoria

### Resumo
Por evento, dá para ligar **"Avisar a diretoria a cada inscrição"** e escolher **um integrante** que passa a
receber, a cada nova inscrição, a **lista de inscritos** pelo WhatsApp — agrupada por inscrição (responsável +
WhatsApp, e abaixo cada participante com nome e idade), com **separação de quem vai pagar por fora** e ainda
precisa ser cobrado. Tem também **envio manual** da lista atual.

### Arquivos criados/alterados
- `core/models.py`: `Evento.notificar_inscricoes` + `notificar_inscricoes_para` (FK User); novo tipo de
  notificação **`NOTIF_INSCRICAO_INTERNA`** em `TEMPLATES_NOTIFICACAO` (texto padrão + prompt de IA que manda
  reproduzir a lista sem resumir).
- `core/migrations/0067_aviso_inscricao_evento.py`: os dois campos (padrão desligado/nulo — nenhum evento
  existente muda).
- `core/views.py`: `_texto_inscritos_evento` (monta lista + bloco de pendências), `_resumo_novo_inscrito`,
  `_notificar_inscricao_interna`, `_agendar_aviso_inscricao` (gancho único), `_usuarios_diretoria_aviso`,
  `_eventos_com_aviso_inscricao`, `_nome_destinatario_aviso` e a view **`evento_avisar_inscritos_view`**
  (envio manual). Ganchos em `_criar_inscricao_de_payload` (site) e no PDV de inscrição (balcão).
- `core/urls.py`: rota `eventos/avisar-inscritos/` — **sem pk**, porque o mesmo botão é usado no painel do
  evento e na aba Templates (com seletor de evento).
- `core/forms.py`: os dois campos em `EventoInscricaoConfigForm`; o seletor lista **só** integrantes da
  diretoria ativos/não-demo e mostra o **nome da ficha**, não o login.
- `templates/core/evento_painel.html`, `templates/core/whatsapp.html`, `static/css/eventos.css`,
  `static/css/whatsapp.css`: liga/desliga + seletor + botões de envio manual (`.config-aviso`,
  `.wa-lista-form`), e `<select>` entrou no estilo dos campos do `wa-form`.
- `core/tests.py`: `AvisoInscricaoEventoTests` (13 testes).

### Decisões tomadas
- **Destinatário no evento, texto no template**: cada evento costuma ter um responsável diferente, então o
  checklist global da aba Templates não serviria. Consequência: este é o único aviso interno em que o POST da
  aba Templates **não** mexe na M2M `avisos_internos_para` (mexer zeraria a lista de outro aviso).
- **Gancho nos dois caminhos de inscrição** (site e balcão): o PDV cria a inscrição fora do payload; sem isso
  a lista enviada divergiria da lista do painel.
- **Teto de 2800 caracteres na lista** (`LIMITE_TEXTO_LISTA`): a mensagem cresce a cada inscrição e a W-API
  recusa texto muito longo. As inscrições mais antigas saem (com aviso); o bloco de pagamento por fora fica
  **sempre inteiro** — é o que exige ação.
- **Envio manual independe do automático**: quem deixou o gatilho desligado ainda consegue mandar a lista.

### Validação
- **250 testes OK** (237 + 13), incluindo: agrupamento por inscrição com idade, separação/limpeza do bloco
  "por fora", disparo pelo site, disparo pelo balcão, evento sem aviso não incomoda ninguém, botão manual,
  erro sem destinatário, exigência de Diretor e o aparo da lista gigante.
- Conferido em 520/1400px com sonda de overflow (zero) e pela mensagem renderizada de ponta a ponta.

### Pendências
- O aviso sai **por WhatsApp**; o canal de e-mail funciona pelo mesmo template, mas o texto é pensado para o
  WhatsApp (a lista fica longa num e-mail).
- Não há histórico de "quando avisei pela última vez" — se for útil, dá para gravar como no `CobrancaEnviada`.

## 2026-08-15 - Recuperação de senha mostra o usuário de acesso

### Resumo
Quem clica em "Esqueci minha senha" muitas vezes esqueceu **o login**, não a senha — e o fluxo não dizia qual
era em lugar nenhum. Depois de digitar o CPF do responsável legal, a **tela do código** passa a mostrar o
**usuário de acesso** da conta, e a **mensagem do WhatsApp** leva o usuário junto do código.

### Arquivos alterados
- `core/views.py`: `_recup_gerar_e_enviar` acrescenta "Seu usuário de acesso é: …" na mensagem e grava
  `usuario` na sessão do fluxo; `recuperar_senha_codigo_view` passa `usuario_login` ao contexto.
- `templates/core/recuperar_codigo.html`: card com o usuário em destaque (`.recup-usuario`), copiável
  (`.selecionavel`, já que o `base.css` desliga a seleção do texto de interface).
- `templates/core/recuperar_cpf.html`: o texto de ajuda avisa que o usuário será mostrado.
- `static/css/recuperar.css`: `.recup-usuario` / `-rotulo` / `-nome`, com `overflow-wrap: anywhere` para
  login comprido não esticar o card.
- `core/tests.py`: `RecuperarUsuarioTests` (4 testes) — o fluxo de recuperação não tinha **nenhum** teste.

### Decisões tomadas
- **Mostrar na tela, não só no WhatsApp** (escolha do usuário, com o custo explicado): quem souber o CPF de
  um responsável passa a descobrir o login sem ter o celular da família. Aceito porque o caso real é a pessoa
  que não lembra o próprio usuário e precisa da resposta na hora; o CPF continua sendo a chave de entrada e
  **CPF desconhecido não abre a etapa do código** (há teste).
- **O login vai na sessão** (`recup["usuario"]`), gravado onde o código é gerado — assim o **reenvio** repete
  o usuário sem consulta extra. Sessão em andamento criada antes do deploy simplesmente não mostra o card
  (expira em 10 min).
- Sem migration: nada de novo no banco.

### Validação
- **237 testes OK** (233 + 4). Sonda de overflow em 485/800/1400px, com login normal e comprido:
  `scrollWidth == clientWidth` em todas.

### Pendências
- **Throttle** na etapa 1 (dívida técnica já conhecida): cada POST válido dispara um WhatsApp real e agora
  também revela um login. Vale limitar por IP/CPF antes de divulgar o recurso.
- O link da tela de login continua dizendo só "Esqueci minha senha" — se quiser, virar "Esqueci minha senha
  ou meu usuário" para quem procura o login achar o caminho.

## 2026-08-13 - Pagamento por fora passa a ser POR FORMA de pagamento

### Resumo
Ajuste pedido logo após o deploy da versão anterior: o "pago direto ao evento" era uma **chave do evento
inteiro** (ligou, todas as formas confirmavam sem cobrar). Passou a ser **por forma de pagamento** — dá para
**cobrar o cartão pelo site e deixar só o Pix por fora** no mesmo evento.

### Arquivos alterados
- `core/models.py`: `Evento.pagamento_por_fora` (bool) → **`formas_pagamento_fora`** (`nenhuma`/`pix`/`cartao`/
  `ambos`, padrão `nenhuma`), com `FORMAS_FORA_CHOICES`; métodos **`formas_fora()`**,
  **`forma_paga_por_fora(forma)`** e a propriedade **`tem_pagamento_por_fora`**.
- `core/migrations/0066_formas_pagamento_fora.py`: cria o campo novo, **converte** quem tinha a chave ligada
  (`ambos` = o que a chave significava) e só então remove a antiga. Reversível.
- `core/forms.py`: o campo novo no lugar do checkbox, com o texto de ajuda reescrito.
- `core/views.py`: a forma escolhida é validada **uma vez** e decide o caminho —
  `evento.forma_paga_por_fora(forma)` manda para a criação imediata, o resto segue para o Mercado Pago.
  Contexto novo para a tela: `formas_fora`, `rotulo_fora` e `todas_por_fora`.
- `templates/core/evento_inscrever.html`: **cada opção** sai marcada conforme o seu caminho — "(pago direto ao
  evento…)" ou "(até 12x…)" —, e a orientação diz de qual forma se trata ("Escolhendo Pix, …").
- `templates/core/evento_painel.html`: o checkbox virou o seletor (`_campo.html`).
- `core/tests.py`: `PagamentoPorForaTests` adaptada + 4 testes novos (caso misto nos dois caminhos, marcação por
  opção na tela, forma marcada que o evento não oferece, padrão do evento novo).

### Decisões tomadas
- **Um campo com 4 opções**, espelhando o `formas_pagamento_online` que já existe, em vez de um checkbox por
  forma: fica igual ao seletor vizinho e cabe numa linha do formulário.
- **`formas_fora()` interseta com `formas_online()`**: se o evento é "somente Pix" e alguém marcar o cartão como
  por fora, não acontece nada — não há cartão para escolher. Evita configuração que parece ligada e não é.
- **A lojinha avulsa do evento não muda**: lá a compra é fechada na hora e não há acerto posterior; só o item
  levado *dentro* de uma inscrição por fora herda a marca.

### Validação
- **233 testes OK** (229 + 4). Conferido o caso misto por captura: Pix marcado como "pago direto ao evento" e
  cartão com o texto de parcelamento, na mesma tela.

## 2026-08-13 - Eventos: inscrição paga direto ao evento (fora do caixa)

### Resumo
Alguns eventos (caso do **Aventuri**) são pagos **direto para a organização do evento**, não para o clube — mas
a inscrição é feita e controlada aqui. O evento ganhou uma chave: **o pagamento é acertado direto com o evento**.
Com ela ligada, quem se inscreve **não passa pela tela de fatura** — a inscrição é confirmada na hora, com
**pagamento pendente**, e vê a **orientação cadastrada**. O Diretor dá a **baixa manual** na lista de inscrições.
Esse dinheiro **não entra em nenhum financeiro** — nem no resultado do evento, nem no do clube.

### Arquivos criados/alterados
- `core/models.py`: `Evento` += `pagamento_por_fora` e `instrucoes_pagamento_fora`; `Inscricao` +=
  `pagamento_externo`, `pago_externo_em`, `pago_externo_por` e as propriedades `pagamento_pendente`/
  `situacao_pagamento`; `PedidoLoja` += `pagamento_externo`.
- `core/migrations/0065_evento_instrucoes_pagamento_fora_and_more.py`: migration.
- `core/forms.py`: os dois campos novos no `EventoInscricaoConfigForm` (mesmo formulário do seletor de formas).
- `core/views.py`: `evento_inscrever_view` desvia para a criação imediata quando `pagamento_por_fora`;
  `_criar_inscricao_de_payload` aceita `forma_pagamento=`/`pagamento_externo=`; nova view
  `evento_inscricao_pago_view` (baixa manual, liga/desliga); `evento_painel_view`, `_montar_financeiro`,
  `_montar_dashboard` e `financeiro_view` passaram a excluir o pago por fora dos totais de caixa.
- `core/urls.py`: `eventos/<id>/inscricoes/<id>/pago/`.
- `templates/core/evento_painel.html`: os dois campos na aba Configuração, selo de situação + botão "Marcar como
  pago" na lista, card "Fora do caixa" no Financeiro e selo no extrato.
- `templates/core/evento_inscrever.html` e `evento_inscricao_sucesso.html`: aviso + orientação.
- `static/css/eventos.css`: `.insc-forma-*` (que **não tinham CSS**), `.sucesso-pendente*`, `.fin-card-fora`,
  `.fin-card-acao`, `.lanc-fora`, `.lanc-selo-fora`, `.inscrito-acoes`, `.btn-marcar-pago`, `.pill-pendente`.
- `core/tests.py`: nova classe `PagamentoPorForaTests` (11 testes).
- `CLAUDE.md`, `docs/README_PROJETO.md`, `docs/ESTADO_ATUAL.md`.

### Decisões tomadas
- **Aproveita o `formas_pagamento_online` de 12/08 em vez de criar outro seletor.** A primeira versão desta
  feature (branch `backup/pagamento-por-fora-v1`) foi escrita sobre uma base desatualizada e criou um model
  `FormaPagamentoEvento` com a sua própria lista de formas — dois seletores de pagamento na mesma aba. Foi
  refeita: a escolha das formas continua sendo a que já existia e o "por fora" é **uma chave do evento**.
- **Fora dos dois financeiros** (escolha do usuário): o dinheiro nunca passou pelo clube, então somá-lo no
  resultado do evento faria o evento mostrar um lucro que não existe. A **baixa manual não joga valor no
  caixa** — ela só registra que a pessoa acertou com o evento. O controle vira um card à parte.
- **Status continua `confirmada`**: a pessoa **está inscrita**; a pendência é do pagamento, não da inscrição.
  Por isso a situação é campo separado, e não um novo valor de `status` (que tiraria a pessoa das contagens).
- **A lojinha levada junto herda o `pagamento_externo`**: sem isso uma camiseta comprada numa inscrição por fora
  entraria no caixa sem nunca ter sido cobrada.

### Validação
- **229 testes OK** (218 + 11). Os novos cobrem: confirma sem fatura, orientação nas duas telas, exclusão dos
  dois financeiros, baixa manual (liga/desliga) sem mexer no caixa, recusa de baixa em inscrição normal, lojinha
  herdando a flag, forma forjada, evento sem a chave (regressão), grátis não vira pendente, campos na
  configuração e **classes novas presentes no CSS**.
- Chrome headless em 1400/520/380px com sonda de overflow: **zero overflow de página**.

### Pendências
- A orientação aparece nas telas, não na notificação de WhatsApp/e-mail. Se for útil mandar a chave Pix junto,
  dá para criar um marcador `{pagamento}` no template `inscricao_evento`.
- O branch `backup/pagamento-por-fora-v1` guarda a versão descartada; pode ser apagado quando não for mais útil.

## 2026-08-12 - WhatsApp: extrato de envios + webhook de entrega (quem recebeu e quem não)

### Resumo
A resposta do `POST /message/send-text` só diz que a **W-API aceitou** a mensagem. Número sem WhatsApp, número
digitado errado ou pessoa que bloqueou o clube devolvem sucesso e a mensagem nunca chega — e nas notificações
automáticas, que rodam em thread, a falha **sumia em silêncio** (ninguém lia o retorno do `_notificar`). Agora
existe o extrato de saída (o par do `LogEmail`, que o e-mail já tinha) e o **webhook de entrega** da W-API
alimenta a situação real de cada mensagem: entregue, lida ou não entregue.

### Arquivos criados/alterados
- `core/models.py`: model **`MensagemWhatsapp`** (+ constantes `MSG_WA_*`), com `registrar` e
  `atualizar_status`.
- `core/migrations/0064_mensagemwhatsapp.py`.
- `core/wapi_parser.py`: **`extrair_status`** + tabela de sinônimos de status.
- `core/wapi.py`: **`configurar_webhook_entrega`** (tenta os nomes candidatos do endpoint).
- `core/views.py`: `_enviar_whatsapp` virou casca de `_wapi_post_texto` e grava o extrato; helper
  `_registrar_status_whatsapp` no webhook; `_envios_whatsapp_ctx`; view `whatsapp_webhook_entrega_view`; os 7
  pontos de envio passaram a informar a `origem`.
- `core/urls.py`: `whatsapp/webhook/entrega/`.
- `templates/core/whatsapp.html`: aba **📨 Envios** + bloco do webhook de entrega na aba 🔔 Webhook.
- `static/css/whatsapp.css`, `static/js/whatsapp.js`.
- `core/tests.py`: `ExtratoWhatsappTests` (16 testes). Suíte: **212 testes OK**.

### Decisões tomadas
- **O status é tratado ANTES de tudo no webhook.** Se um aviso de entrega entrasse pelo caminho de "mensagem
  recebida", o sistema marcaria contato e até **autorização** de quem não escreveu nada — termômetro verde
  falso e gate anti-bloqueio liberado indevidamente. Tem teste de regressão nos dois sentidos (status não vira
  conversa; conversa não vira status).
- **Reconhecimento de status largo de propósito.** O formato não está na doc pública e o WhatsApp tem vários
  nomes para a mesma coisa: `SENT`/`SERVER_ACK`, `RECEIVED`/`DELIVERY_ACK`/`DELIVERED`, `READ`/`PLAYED`,
  `FAILED`, mais os ACKs numéricos 1..5. Exige **status reconhecido + ao menos um id** para classificar como
  aviso — sem os dois, segue o fluxo normal.
- **O status não retrocede**, porque os avisos chegam fora de ordem e "lida" virar "entregue" apagaria a
  informação melhor. A exceção é o **FAILED**, que sempre vale: é o que o Diretor precisa ver.
- **Registro no ponto único.** `_enviar_whatsapp` passou a ser uma casca que grava o extrato e delega o POST
  para `_wapi_post_texto`. Assim não existe caminho de envio que escape — foi a lição do `LogEmail`.
- **O texto enviado não é gravado** (só destino, origem e resultado), mesma regra do `LogEmail`: não acumular
  dado pessoal à toa. Há teste.
- **A tela avisa quando o webhook de entrega não está confirmando nada**, senão a coluna toda em "sem
  confirmação" pareceria que ninguém recebeu.

### O formato real da W-API (medido, não documentado)
Ligado o webhook em produção e feito um envio de teste para o próprio número do clube, o que chega é:

- **Dois endpoints de configuração**, ambos válidos e com papéis diferentes:
  `/webhook/update-webhook-delivery` → *"Webhook de envio atualizado"*; e
  `/webhook/update-webhook-message-status` → *"Webhook de status atualizado"*. O sistema registra **os dois**.
- **`webhookDelivery`**: chega **sem campo `status`** — é o eco da mensagem que saiu (`fromMe: true`, com
  `messageId`). Mapeado para **enviada**, nunca para "entregue": ele confirma a saída, não a chegada.
- **`webhookStatus`**: traz `status` com o vocabulário **`SERVER` / `DELIVERY` / `READ`** — e não
  `SENT`/`RECEIVED`, que era o que a doc sugeria. Os dois conjuntos ficam como sinônimo no parser.
- **Método:** *sondar por GET não descobre rota na W-API* — ela responde `Cannot GET /v1/webhook/<qualquer
  coisa>` mesmo para as rotas que existem com PUT. Só o PUT distingue.

Trava importante: o evento **sem** campo de status só é aceito como aviso de entrega quando tem `fromMe=true`.
Sem isso, um evento de conversa com nome parecido seria engolido como status e o clube **perderia a mensagem
recebida** — junto com a autorização que ela pode carregar. Há teste.

### Pendências
- Casar o extrato com a família/aventureiro (hoje guarda o nome como texto), para o Diretor filtrar por pessoa.

---

## 2026-08-12 - Mensalidades: Top 10 de quem está devendo mais

### Resumo
A aba **Resumo** só mostrava totais e o mês a mês — para saber **quem** deve era preciso abrir a lista de
aventureiros e somar a olho. Agora há um bloco **"Top 10 — quem está devendo mais"**, entre o gráfico e o
detalhe por mês: posição (3 primeiros em vermelho), nome, responsável, meses em aberto, barra proporcional e
o valor devido.

### Arquivos criados/alterados
- `core/views.py`: helper **`_top_devedores(ano, limite=10)`** + `top_devedores` no contexto de
  `mensalidades_view`.
- `templates/core/mensalidades.html`: bloco na aba Resumo (com estado vazio "🎉 Ninguém com mensalidade em
  aberto").
- `static/css/mensalidades.css`: `.mens-devedores`/`.mdev-*` e a correção do `.mens-resumo-topo`.
- `core/tests.py`: `TopDevedoresTests` (8 testes). Suíte: **196 testes OK**.

### Decisões tomadas
- **O ranking soma toda a dívida em aberto, de qualquer ano.** "Quem deve mais" olhando só o ano selecionado
  daria ordem errada (quem arrastou meses do ano anterior apareceria abaixo de quem deve pouco). Para o número
  não brigar com os KPIs — que são do ano da tela —, cada linha mostra **quanto vem de outros anos**.
- **Uma consulta só**: `values(...).annotate(Sum, Count, Sum(filter=Q(ano=ano)))`, ordenada no banco e cortada
  em 10. Nada de somar em Python por aventureiro.
- **Regras do clube aplicadas**: `aventureiro__ativo=True` (inativo não é cobrado, nem aparece devendo) e
  `demo=False`; isento e pago fora. Há teste para cada uma — é o tipo de filtro que se esquece.
- **Por aventureiro, não por família.** A aba é por aventureiro; a cobrança é que vai por família, e o bloco
  aponta para a aba 📣 Cobranças em vez de duplicar o botão de cobrar.

### Bug pré-existente corrigido de passagem
A tela de Mensalidades tinha **rolagem horizontal na página inteira** em telas estreitas (sonda: `scrollWidth`
572 × `clientWidth` 489). Causa: `.mens-resumo-topo` com `grid-template-columns: 1fr` — `1fr` tem
`min-width: auto` e **não encolhe abaixo do conteúdo**, então o gráfico de 12 meses esticava a grade e o
wrapper `.mens-grafico-scroll` (que existe justamente para rolar por dentro) nunca entrava em ação. Virou
`minmax(0, 1fr)` nas duas media queries. É o **mesmo defeito** já visto em Aniversários — vale como regra:
coluna de grade que recebe conteúdo largo usa `minmax(0, 1fr)`.

### Verificação visual
Chrome headless em 380/520/800/1400px: `scrollWidth == clientWidth` em todas, e o gráfico agora rola dentro do
próprio card (com a legenda inteira visível no celular).

---

## 2026-08-12 - Inativar um evento (liga/desliga para o público)

### Resumo
Faltava um jeito de **suspender** um evento já criado: dentro da data ele aparecia no menu de todos os perfis
e aceitava inscrição/compra, e excluir só é possível em evento vazio (por regra, evento com inscrição, pedido
ou presença nunca é apagado). Agora o Diretor **inativa** o evento: ele sai do menu, e a página, a inscrição,
a lojinha e a tela de pagamento param de abrir para responsáveis e público — **mesmo dentro da data**.
Reativar devolve tudo. Nada do que já aconteceu é apagado ou escondido.

### Arquivos criados/alterados
- `core/models.py`: campo **`Evento.ativo`** (padrão `True`); `inscricoes_abertas()` e `loja_aberta()` passam
  a devolver `False` quando o evento está inativo.
- `core/migrations/0063_evento_ativo.py`.
- `core/context_processors.py`: `_eventos_menu` filtra `ativo=True`.
- `core/views.py`: helper **`_evento_inativo_bloqueio`** (usado em `evento_pagina`, `evento_inscrever`,
  `evento_loja` e `evento_pagamento`) e a view **`evento_ativar_view`** (POST, Diretor, alterna).
- `core/urls.py`: rota `eventos/<int:pk>/ativar/` (`core:evento_ativar`).
- `templates/core/eventos.html`: selo "⏸️ Inativo", botão **Inativar/Reativar** e a linha "Situação" no modal.
- `templates/core/evento_painel.html`: selo no cabeçalho, botão **Inativar evento** e faixa de aviso.
- `static/css/eventos.css`: `.evento-selo-inativo`, `.evento-card-inativo`, `.btn-acao-neutro`,
  `.aviso-inativo` e o `.painel-cabecalho` (que era usado no HTML **sem regra em CSS nenhum**).
- `static/js/evento_painel.js`: handler genérico de `data-confirmar` (o painel não carrega o `eventos.js`).
- `core/tests.py`: `EventoInativoTests` (13 testes). Suíte: **186 testes OK**.

### Decisões tomadas
- **Três camadas, não uma.** Menu (filtra `ativo=True`) + views públicas (bloqueio na entrada) + **model**
  (`inscricoes_abertas`/`loja_aberta` em `False`). A terceira é a que importa: esconder o botão no HTML não é
  validação — mesmo erro que já apareceu nas formas de pagamento, e há teste de POST forjado nos dois fluxos.
- **404 para visitante anônimo, `/inicio/` com aviso para quem está logado.** Para quem tem o link público, o
  evento inativo simplesmente não existe; para o responsável logado, um 404 seco seria confuso.
- **O Diretor não perde nada.** Painel, balcão/PDV, presença, operadores e financeiro continuam idênticos —
  inativar é sobre a **porta pública**, não sobre os dados. Inscrições, pedidos e dinheiro seguem contando.
- **O PDV/balcão fica de fora do bloqueio** de propósito: é ferramenta do Diretor/operador, não o canal que se
  quer fechar. Se um dia for preciso travar o balcão também, é uma decisão separada.
- **Não é `demo`.** `demo` marca dado fictício e sai de tudo (contagens, menu, financeiro); `ativo=False` é um
  evento real, desligado só para o público.
- **Padrão `True`** e alternância por POST: nenhum evento existente muda de comportamento, e um GET (link ou
  prefetch do navegador) nunca desliga um evento — há teste para o 405.

### Ajuste 2 (mesmo dia, a pedido): o inativo tem de se ver de longe
O card do evento inativo ficou **cinza de verdade**, não só translúcido: fundo `#eef1f5`, borda cinza, sem
sombra, título/data/local em tons de cinza e `filter: grayscale(1)` no topo e na linha de meta (apaga a cor dos
emojis). O selo virou **pílula cinza-escura com texto branco em caixa alta** ("INATIVO"), que se lê batendo o
olho. Duas decisões: (1) saiu o `opacity: 0.72` do card inteiro — ele apagava também os **botões**, que
precisam continuar legíveis e clicáveis, então o cinza é aplicado peça por peça e as ações ficam com a cor
normal; (2) o **emoji ⏸️ saiu do selo** — dentro da pílula escura ele desaparecia (continua nos botões e na
faixa de aviso, onde o fundo é claro). Conferido em 380/520/1400px: zero overflow.

### Ajuste (mesmo dia, a pedido)
O botão **não aparece em evento que já terminou**: ele já saiu do menu sozinho e não aceita mais inscrição, e a
lojinha fecha por `ja_terminou()` — "Inativar" ali seria um botão que não faz nada. Condição nos dois
templates: `{% if not evento.ja_terminou or not evento.ativo %}`. O **"Reativar" continua** em evento passado
que esteja inativo, senão o selo "Inativo" ficaria preso sem forma de desfazer. A **view não passou a recusar**
esse POST de propósito: inativar evento passado é inócuo (não há nada a proteger), e travar por travar só
criaria um caminho para erro. Mais 2 testes (**188 no total**).

### Verificação visual
Chrome headless em 380/520/1400px nas duas telas, com sonda de overflow: **zero overflow** em todas
(`scrollWidth == clientWidth`). **Um defeito achado e corrigido na captura:** o selo "Inativo" tinha nascido
dentro de `.evento-topo` — um flex de 3 itens — e **espremia o nome do evento** ("Festa Junina do Clube
(adiada)" virava "Festa Juni…", porque `.evento-nome` tem `line-clamp: 2`). O selo foi para `.evento-meta`,
que já quebra linha, igual ao que o painel faz com o `.painel-meta`.

### Pendências
- Avaliar se o **evento simples** inativo deve sair também da tela de **Presença** do Diretor (hoje continua,
  porque presença é registro interno e histórico).
- Avaliar travar o **balcão/PDV** de evento inativo, se algum dia a intenção for fechar o evento por completo.

---

## 2026-08-12 - Cookies de sessão e CSRF só por HTTPS em produção

### Resumo
`SESSION_COOKIE_SECURE` e `CSRF_COOKIE_SECURE` não estavam definidos — o navegador mandava o cookie em
**texto puro** numa requisição `http://`. Confirmado em produção com `curl`:

```
Set-Cookie: pinhaljunior2_csrftoken=...; Path=/; SameSite=Lax     ← sem Secure
```

O 301 do Nginx **não protege**: quando o redirecionamento chega, o cookie **já foi transmitido**. Bastava
alguém digitar o endereço sem `https://` numa rede pública para o token vazar. Agora ambos seguem `not DEBUG`.

### Arquivos criados/alterados
- `config/settings.py`: `SESSION_COOKIE_SECURE` e `CSRF_COOKIE_SECURE` = `not DEBUG`, com o porquê no
  comentário; e uma nota explicando que `SECURE_SSL_REDIRECT` fica **de propósito** com o Nginx.
- `core/tests.py`: `SegurancaCookiesTests` (4 testes).

### Decisões tomadas
- **Amarrado ao `DEBUG`, não fixo em `True`.** Em `http://127.0.0.1` o navegador não guarda cookie `Secure`
  e o login local pararia de funcionar. Há teste para os dois lados (produção exige, desenvolvimento não).
- **`SECURE_SSL_REDIRECT` continua desligado.** Quem redireciona HTTP→HTTPS é o Nginx (`return 301`), antes
  de chegar ao Django; ligar aqui duplicaria e arriscaria laço. O aviso `security.W008` do `check --deploy`
  é **esperado** — o teste `test_ssl_redirect_fica_com_o_nginx` documenta isso para ninguém "consertar" depois.
- O teste também trava o `SECURE_PROXY_SSL_HEADER`: sem ele o Django não reconhece a requisição como HTTPS
  e não mandaria o cookie `Secure` — as duas configurações só funcionam juntas.

### Pendências
- `SECURE_HSTS_SECONDS` continua sem valor. HSTS mal configurado é **irreversível por meses** no navegador
  de quem já visitou; se for ligar, começar com valor baixo e **sem** `includeSubDomains`.
- Divergência de ambiente: produção roda **Django 5.2.15 / Python 3.12.3**, a máquina de desenvolvimento
  **6.0.5 / 3.14.3**. No VPS **cada app tem venv própria** (rodam de 5.2.11 a 6.1 lado a lado, sem Django no
  Python do sistema), então o certo é **igualar o local**, não mexer no servidor.

---

## 2026-08-12 - Formas de pagamento online por evento (Pix, cartão ou os dois)

### Resumo
O Diretor passa a escolher, **por evento**, o que o site aceita: **só Pix**, **só cartão** ou **os dois**
(padrão). Vale para a **inscrição** e para a **lojinha** daquele evento. O **PDV/balcão não muda** — lá o
operador continua com dinheiro, cortesia e o resto, porque quem cobra presencialmente é o clube.

Novo campo `Evento.formas_pagamento_online` (`ambos`/`pix`/`cartao`, padrão `ambos`) + migration **0062**.
Como o padrão é `ambos`, **os eventos existentes continuam exatamente como estavam**.

### Arquivos criados/alterados
- `core/models.py`: constantes `FORMAS_PAGAMENTO_ONLINE` (movida da `views.py`, agora fonte única) e
  `FORMAS_ONLINE_EVENTO_CHOICES`; campo `Evento.formas_pagamento_online`; métodos `Evento.formas_online()`
  (lista `(valor, rótulo)` filtrada) e `Evento.aceita_forma_online(forma)` (validação).
- `core/migrations/0062_evento_formas_pagamento_online.py`: campo novo, com default.
- `core/forms.py`: `EventoInscricaoConfigForm` ganha o campo + texto de ajuda.
- `core/views.py`: `FORMAS_PAGAMENTO_ONLINE` agora vem do models (sem duplicar); `evento_loja_view` valida
  por `aceita_forma_online` e manda `evento.formas_online()` ao template; `evento_inscrever_view` idem, com
  fallback para a 1ª forma permitida; helper `_erro_forma_pagamento` para a mensagem citar só o que o evento
  aceita.
- `templates/core/evento_inscrever.html`: os rádios eram **chumbados** (Pix + cartão fixos); agora iteram
  `formas_pagamento`.
- `templates/core/evento_painel.html`: o campo novo na aba de configuração da inscrição.
- `core/tests.py`: `FormasPagamentoEventoTests` (8 testes).

### Decisões tomadas
- **Validar no servidor, não só esconder o rádio.** Esconder a opção no HTML não impede um POST forjado —
  `aceita_forma_online` é chamada no POST da lojinha e da inscrição. Há teste de regressão para isso.
- **Na inscrição, forma inválida cai na 1ª permitida** em vez de derrubar o formulário: o padrão antigo do
  código era `or "pix"` fixo, que num evento só-cartão cobraria pelo caminho que o Diretor desligou.
- **A lista canônica saiu da `views.py` para a `models.py`** — o model precisa dela para filtrar, e duas
  cópias iam divergir. As telas fora de evento (Loja do Clube, mensalidades) seguem importando o mesmo nome.
- **PDV intocado de propósito**: usa a variável `formas` (outra lista, com dinheiro/cortesia).
- Mensagem de erro citando só as formas do evento — "escolha Pix ou cartão" numa tela que só mostra Pix é
  confuso.

### Pendências
- A escolha vale para **evento**. Loja do Clube e mensalidades continuam com as duas formas fixas; se for
  preciso o mesmo controle lá, o caminho é repetir o padrão (campo + `formas_online()`).

---

## 2026-08-02 - Aniversários: abas com o padrão visual do projeto

### Resumo
As abas da tela eram **links sublinhados soltos**. Motivo: nasceram com as classes `abas`/`aba`/`aba-ativa`,
que **não existiam em CSS nenhum** do projeto — inventadas na criação da tela. Agora seguem o mesmo padrão de
`loja.css`/`mensalidades.css`.

### Arquivos alterados
- `static/css/aniversarios.css`: `.aniv-abas` (trilho com fundo suave, borda e cantos arredondados),
  `.aniv-aba` (pílula, 44px de alvo de toque, sem sublinhado), `.aniv-aba.ativa` (gradiente azul + sombra) e
  `.aniv-aba-badge` (contador verde, translúcido na ativa).
- `templates/core/aniversarios.html`: abas remarcadas, com `aria-current="page"` na ativa e badges —
  total de aniversariantes, quantas mensagens estão ligadas (`n/3`) e envios do ano.
  O link da aba da lista **preserva o mês selecionado**.
- `core/views.py`: `ativos_qtd` e `envios_qtd` no contexto (as badges).
- `core/tests.py`: dois testes novos.

### Decisões tomadas
- **Reusar o padrão existente** em vez de criar um visual novo: a tela passa a ser indistinguível das outras.
- **No celular (≤480px) o rótulo some** e fica só o ícone + badge — três abas com texto completo não cabem
  lado a lado. A **ativa mantém o nome**, para não virar adivinhação de ícone.
- Badge de mensagens como `n/3` em vez de só o número: "1" sozinho não diz se falta ligar as outras.

### Validação
- Teste que confere que **toda classe usada no HTML existe no CSS** — é exatamente o defeito que passou:
  classe inventada, sem estilo, sem nenhum teste reclamando.
- Teste de que só a aba ativa tem `aria-current`.
- Suíte: **161 testes OK**. Conferido em 1400px e 520px.

## 2026-08-02 - Aniversários: cards com larguras diferentes no desktop

### Resumo
No desktop os cards da tela tinham **larguras diferentes** — "É hoje!" ia até a borda e "Agosto" e "Faltando
data" paravam em 640px, deixando a coluna visivelmente desalinhada. Reportado pelo usuário com print.

### Causa
`.wa-card { max-width: 640px }`, herdado da tela do WhatsApp (onde os cards são formulários e a largura menor
é proposital). O card "É hoje!" usa `card aniv-hoje`, **sem** `wa-card`, então era o único sem o limite — daí
a diferença. Medido com sonda: `CARD[1] maxw=none w=980` × `CARD[2] maxw=640px w=640`.

### Arquivos alterados
- `static/css/aniversarios.css`: nova classe `.aniv-largo { max-width: none }`, com o porquê no comentário.
- `templates/core/aniversarios.html`: `aniv-largo` nos três cards de lista/tabela (mês, faltando data e
  envios). Os formulários da aba ✏️ **continuam em 640px** — texto longo é mais legível em coluna estreita.

### Decisões tomadas
- Modificador explícito em vez de `.wa-card { max-width: none }` no CSS da tela: o override global também
  esticaria os formulários da aba de mensagens, que ficam melhores estreitos.

### Validação
- Sonda no desktop (1400px): os dois cards agora em **980px**, iguais. Suíte: **159 testes OK**.

### Nota de método
- Este defeito estava na captura que eu havia revisado na véspera e passou batido a olho. Comparar **números**
  (largura de cada card) em vez de confiar na impressão visual é o que o pega.

## 2026-08-01 - Aniversários: responsividade e 3 correções achadas na verificação visual

### Resumo
Revisão de responsividade da tela de Aniversariantes em 8 larguras. A verificação visual encontrou três
defeitos que os testes não pegavam — um deles afetando também uma tela feita ontem.

### Arquivos alterados
- `static/css/aniversarios.css`: reescrito com **3 faixas** (≥760 / 560–760 / <560) + ajuste ≤380px.
  `minmax(0, 1fr)` e `overflow-wrap:anywhere` no nome e no detalhe; botão com `min-height:40px`; pílulas de
  mês com `flex:1 1 auto` no celular.
- `templates/core/_aniv_acoes.html`: `{# ... #}` trocado por `{% comment %}`.
- `templates/core/mensalidades.html`: mesmo erro no comentário do seletor de canal (de 31/07).
- `templates/core/aniversarios.html`: include das ações **também** na lista do mês.
- `core/views.py`: `tambem_em` passa a guardar o **rótulo** do perfil, não a chave.
- `core/tests.py`: teste de regressão de comentário vazando; ajuste do teste de perfil duplicado.

### Os três defeitos
1. **Comentário de template renderizado como texto.** O `{# ... #}` do Django é de **uma linha só**; escrito
   em várias, o conteúdo vaza para a tela. Aparecia em cada pessoa da lista e também na aba Cobranças, no
   comentário que eu havia escrito ontem. Agora ambos usam `{% comment %}` e um teste varre `{#`/`#}` no HTML
   renderizado de 3 telas.
2. **A lista do mês não tinha botão de envio.** O `replace_all` que inseriu o include casou só com o markup da
   lista "É hoje" — a do mês tem o bloco de detalhe diferente (por causa do "também é"). Ou seja, a lista
   principal ficou sem a ação.
3. **Nota de perfil duplicado mostrava a chave técnica** ("responsavel", sem acento) em vez do rótulo.

### Método
- Chrome headless (`--headless=new`) com HTML gerado pelo test client e caminhos de estático reescritos para
  `file:///`. Cenários que estressam o layout: nome de 48 caracteres, nome de 2 letras, pessoa com dois perfis
  e aniversariante do dia.
- **Sonda de overflow** injetada na página: compara `documentElement.scrollWidth` com `clientWidth` e lista os
  elementos cujo `right` passa da viewport. Mede também a altura do botão e conta os botões renderizados —
  foi assim que o defeito 2 apareceu (`QTD_BOTOES` menor que o esperado).
- **Nota sobre o método:** o viewport mínimo do headless é **~485px**, então uma captura pedida em 360px é
  renderizada em 485 e reduzida — o que *parece* corte de layout e não é. Vale medir com a sonda antes de
  concluir que há overflow (foi o que evitou uma "correção" de um problema inexistente).

### Validação
- 485, 560, 640, 768, 900, 1024, 1440 e 1920px: **`OVERFLOW=nao`** em todas; botão 40px; 6 botões renderizados.
- Suíte: **159 testes OK**.

## 2026-08-01 - Aniversários: disparo automático, envio manual e controle de duplicidade

### Resumo
Fecha o módulo de Aniversariantes: as mensagens passam a sair de verdade, por WhatsApp e/ou e-mail, com as
mesmas regras anti-spam do resto do sistema, botão de envio manual por pessoa e trava de "já enviei este ano".

### Arquivos criados/alterados
- `core/models.py`:
  - `TemplateAniversario` += `enviar_whatsapp` / `enviar_email` (ambos nascem ligados — o `ativo`, que nasce
    desligado, já é a trava principal).
  - Novo **`EnvioAniversario`**: `chave`/`nome`/`perfil`/`ano`/`canal`/`destino`/`ok`/`detalhe`/`manual`/
    `enviado_por`. `UniqueConstraint(chave, ano, canal)` **com `condition=Q(ok=True)`** e o helper
    `ja_enviado(chave, ano)`.
  - As constantes `CANAL_*` subiram no arquivo (agora servem cobrança **e** aniversário).
- `core/views.py`: `_render_aniversario`, **`_enviar_aniversario`**, `_anotar_envios`, `_MOTIVO_ANIV` e
  `aniversario_enviar_view`. `_aniversariantes` passou a expor a `chave` de cada pessoa.
- `core/management/commands/enviar_aniversarios.py` **(novo)**: cron diário, `--dry-run`, `--pausa` (10s).
- `templates/core/aniversarios.html` (painel de status, aba 📬 Envios, canais na aba de mensagens),
  `templates/core/_aniv_acoes.html` **(novo)**, `static/js/aniversarios.js` **(novo)**,
  `static/css/aniversarios.css` (selos, botão, 4ª coluna).
- `core/urls.py`: `aniversarios/enviar/`. `core/migrations/0061_...py` **(novo)**.
- `docs/DEPLOY_VPS.md`: seção do cron. `core/tests.py`: `EnvioAniversarioTests` (20 testes).

### Decisões tomadas
- **A trava é no banco, não só na consulta.** `UniqueConstraint` condicionada a `ok=True` protege contra a
  corrida real: o cron rodando enquanto alguém clica no botão manual.
- **Falha não ocupa a trava.** Se ocupasse, um timeout de rede queimaria o aniversário da pessoa até o ano
  seguinte. Falhas ficam como log e podem ser retentadas.
- **Reenvio forçado usa `update_or_create`**, não `create`: a constraint só permite uma linha de sucesso por
  pessoa/ano/canal, então o reenvio atualiza a existente (data e autor do último envio).
- **Aniversário não é transacional.** A pessoa não fez nada — é o clube que resolve escrever. Passa pelos dois
  gates, como cobrança. `forcar` reenvia mas **não** fura consentimento; forçar não pode virar atalho.
- **Um canal barrado não impede o outro**: descadastrado do e-mail ainda recebe no WhatsApp, e vice-versa.
- **A criança recebe no contato do responsável** — é o único que existe, e está correto.

### Validação
- Suíte: **158 testes OK** (138 + 20), cobrindo trava anual, retry após falha, gates, `forcar`, botão manual,
  idempotência do comando e `--dry-run`.
- Renderização conferida com dados reais (destaque "É hoje!", botão, selos, aba de envios).

### Pendências
- **Operacional**: agendar o cron `enviar_aniversarios` no VPS e ligar as mensagens na aba ✏️ (nascem
  desligadas). Preencher a data de nascimento dos responsáveis segue pendente.

## 2026-08-01 - Novo módulo: Aniversariantes (lista + mensagens por perfil)

### Resumo
Módulo novo (só Diretor) que junta aventureiros, responsáveis e diretoria numa lista de aniversários, mais uma
aba para cadastrar a mensagem de cada perfil. **O disparo automático não faz parte desta etapa** — fica para a
próxima, como combinado.

### Arquivos criados/alterados
- `core/models.py`:
  - `Aventureiro` += `pai_data_nascimento`, `mae_data_nascimento`, `resp_data_nascimento` (opcionais).
  - Novo **`TemplateAniversario`** (um registro por perfil) + `TEMPLATES_ANIVERSARIO` com rótulo, ícone,
    marcadores, mensagem e assunto padrão. `get_tipo` cria com os padrões e preenche assunto faltante.
- `core/views.py`: `_idade_em`, `_chave_pessoa`, `_PRIORIDADE_ANIV`, **`_aniversariantes`**,
  `_aniversarios_faltando`, `aniversarios_view` e `aniversario_template_view`.
- `core/urls.py`: `aniversarios/` e `aniversarios/mensagem/`. `core/menus.py`: item 🎂.
- `templates/core/aniversarios.html` **(novo)** e `static/css/aniversarios.css` **(novo)**.
- `core/forms.py`: `ResponsavelLegalForm` += `resp_data_nascimento` (opcional, `<input type=date>`);
  `editar_responsavel_view` grava e recarrega o campo.
- `core/migrations/0060_...py` **(novo)**.
- `core/tests.py`: `AniversariantesTests` (20 testes).

### Decisões tomadas
- **Deduplicação por pessoa, com prioridade.** O mesmo adulto costuma ser diretoria **e** responsável e
  receberia duas mensagens. Chave: CPF (≥11 dígitos) → WhatsApp → nome normalizado. Prioridade
  **diretoria > responsável > aventureiro**; os perfis descartados viram a nota "também é ...".
- **Aventureiro tem chave própria (`av:<id>`), fora da deduplicação de pessoas.** A criança não tem telefone
  nem e-mail próprios — usa os do responsável — e colidia com o pai/mãe, sumindo da lista. Pego na verificação
  visual (a criança aparecia só como texto no detalhe da mãe), com teste de regressão. Deduplicar criança com
  adulto também não faz sentido conceitual.
- **29/02 é tratado como 28/02**: senão o aniversariante some do calendário em ano não bissexto.
- **Template separado do `TemplateNotificacao`**: aniversário não é reação a uma ação da pessoa (é data de
  calendário) e o texto muda muito por perfil — não se escreve para uma criança como para um voluntário.
- **Campos de data do responsável criados, mesmo nascendo vazios.** Sem eles o perfil "responsável" seria
  decorativo. A tela é honesta sobre isso com o card "⚠️ Faltando data de nascimento".

### Cobertura em produção (consultada antes de construir)
- Aventureiros ativos: **35/35** com data. Diretoria ativa: **10/10** com data.
- Responsáveis: **66 nomes distintos, nenhum com data** — o campo não existia. Começam todos no card de
  pendência até serem preenchidos.

### Validação
- Suíte: **138 testes OK** (118 + 20). `check` e `makemigrations --check` limpos.
- Renderização conferida com dados reais: lista ordenada por dia, ícone por perfil, idade correta.

### Pendências
- **Disparo automático** da mensagem de aniversário (próxima etapa): decidir gatilho (cron diário),
  canal (WhatsApp/e-mail, reusando `_notificar`/`_enviar_email`) e registro de "já enviei este ano".
- Preencher a data de nascimento dos responsáveis (dado operacional, não código).

## 2026-08-01 - Acerto público deixa de cobrar aventureiro inativo

### Resumo
A regra do clube é **aventureiro inativo não é cobrado**, mesmo tendo mês em aberto. A cobrança, o painel do
Diretor, a área do responsável e o Financeiro já respeitavam; a **página pública de acerto** (o link que vai no
WhatsApp de cobrança) não — ela listava e pedia pagamento da dívida de quem já saiu do clube.

### Arquivos alterados
- `core/views.py`: `_mensalidades_abertas_familia` ganhou `aventureiro__ativo=True`, com comentário
  explicando por que o filtro não é detalhe.
- `core/tests.py`: dois testes em `AcertoPublicoTests` — um garantindo que o inativo não aparece (e o ativo
  continua), outro que uma família só com inativo vê "Tudo em dia".
- `CLAUDE.md`: a regra virou convenção explícita, com a lista dos pontos onde o filtro precisa existir.

### Contexto (dados de produção)
- 4 aventureiros inativos, dos quais **1 com 8 mensalidades em aberto (R$ 240,00)**. Ela já estava fora da
  cobrança e dos totais, mas apareceria no acerto se a família abrisse o link antigo (o token é permanente).
- Nenhuma conta tem aventureiro ativo e inativo ao mesmo tempo hoje, então o efeito prático era limitado —
  mas o teste cobre o caso misto, que é o que dá errado de forma silenciosa.

### Decisões tomadas
- **Filtrar em vez de marcar isento.** Marcar as mensalidades do inativo como isentas também sumiria com elas,
  mas exigiria ação manual a cada desligamento e reescreveria dado histórico. O filtro aplica a regra sozinho.
- **Pagas continuam contando.** Só o "em aberto" de inativo é ignorado; o que a pessoa pagou enquanto era
  ativa permanece no histórico e nos relatórios.

### Validação
- Suíte: **118 testes OK** (116 + 2). Sem migration.

## 2026-08-01 - WhatsApp: resposta da autorização com log e retry idempotente

### Resumo
Fecha a pendência aberta em 2026-07-14. A confirmação automática da autorização era disparo único dentro de
`try/except: pass`, ignorando o retorno do envio: uma falha transitória da W-API se perdia sem log e sem nova
tentativa, deixando a pessoa autorizada e sem resposta.

### Arquivos alterados
- `core/models.py`: `PerfilUsuario.confirmacao_autorizacao_em` — data em que a confirmação **saiu com
  sucesso**. Autorizado + campo vazio = pendente.
- `core/views.py`:
  - `_registrar_contato_whatsapp` deixou de enviar direto; agora delega a **`_confirmar_autorizacao`** e é
    chamado em **toda** mensagem, não só na que autoriza — é isso que dá o retry.
  - Novo **`_confirmar_autorizacao(perfil, numero, cfg=None)`**: sai só se ainda não confirmada; confere o
    retorno de `_enviar_whatsapp`; marca `confirmacao_autorizacao_em` **apenas** no sucesso; loga
    (`logger.warning`) na falha e deixa pendente; nunca levanta exceção. Devolve `(enviou, motivo)`.
  - `whatsapp_liberar_view` passa a preencher também `confirmacao_autorizacao_em`.
- `core/migrations/0059_...py` **(novo)**: `AddField` + **`RunPython` de backfill**.
- `core/tests.py`: `ConfirmacaoAutorizacaoTests` (9 testes).

### Decisões tomadas
- **Retry na próxima mensagem**, não em fila/cron: a pessoa escrevendo de novo é o gatilho natural e mantém a
  resposta contextual. Sem infraestrutura nova.
- **Marca só no sucesso.** É o que transforma "disparo único" em "entrega garantida na próxima chance".
- **Backfill obrigatório na migration.** Sem ele o campo nasceria vazio para todos os já autorizados, e a
  próxima mensagem de cada um dispararia uma segunda confirmação — quem recebeu semanas atrás levaria outra.
  O passado fica fechado; o retry vale só daqui em diante.
- **Marcação manual fecha a pendência.** Quem foi liberado à mão autorizou por fora (ligação, presencial);
  receberia a confirmação do nada na próxima mensagem. Preserva o comportamento de hoje.
- **`logger.warning`, não `exception`**: falha de terceiro em webhook é esperada, não é bug nosso — não polui
  o log com stack trace.

### Validação
- Suíte: **116 testes OK** (107 + 9), incluindo o caso que motivou a mudança (falha → fica pendente → retry na
  mensagem seguinte) e a garantia de que a marcação manual não gera resposta posterior.
- `check` e `makemigrations --check` limpos; migration aplicada localmente com o backfill.

### Pendências
- Nenhuma para esta correção. **A lista de pendências técnicas do WhatsApp fica zerada.**
- Segue em aberto (decisão do usuário): nomes reais de pessoas no histórico do Git — ver a entrada de 31/07.

## 2026-07-31 - DEPLOY_VPS: registra o conhecimento operacional do servidor

### Resumo
Só documentação. Registra no `docs/DEPLOY_VPS.md` o que foi descoberto operando o servidor nesta sessão e que
não estava escrito em lugar nenhum — informação que, sem registro, seria rediagnosticada do zero.

### Arquivos alterados
- `docs/DEPLOY_VPS.md`:
  - Aviso sobre os **dois atalhos de deploy** (`pinhaljunior2-deploy` × `pinhaljunior-deploy`), com tabela de
    projeto/caminho/porta e como distinguir pela saída. Rodar o errado reativa o `sitepinhal.service`.
  - Nova seção **"O VPS é compartilhado com outros projetos"**: as 11 aplicações Django ativas, os recursos
    (1 vCPU, 3,8 GB, **sem swap**, ~38 gunicorn) e as implicações.
  - Nova seção **"Dependências externas que expiram"**: W-API (403 = assinatura, 401 = QR), certificado,
    senha de app do Gmail — com o comando de diagnóstico da W-API que envia ao próprio número do clube.
  - Nova seção **"Acesso bloqueado em redes corporativas (FortiGate)"**: causa provável (domínio novo, não
    classificado), conserto (reclassificação no FortiGuard) e o paliativo correto (*Web Rating Overrides*,
    que vale para todos os perfis — a lista de URLs vale só para o perfil amarrado).
  - Cuidado novo: deploy só traz o que está no GitHub; `Commit anterior == Commit atual` = faltou o push.

### Decisões tomadas
- Documentar no `DEPLOY_VPS.md` e não no `ESTADO_ATUAL.md`: é conhecimento de **operação**, não estado do
  sistema, e quem for mexer no servidor abre esse arquivo.
- Não versionar a chave SSH de automação nem credenciais — só o caminho de diagnóstico.

### Validação
- Sem código; suíte segue em **107 testes OK**. Deploy `cba3830` confirmado no ar.

## 2026-07-31 - Cobrança: opção "Ambos" (WhatsApp + e-mail no mesmo clique)

### Resumo
O seletor de canal da aba Cobranças ganhou **💬+✉️ Ambos**: um clique envia pelos dois canais, cada um com as
suas próprias regras anti-bloqueio/anti-spam, sem duplicar quem já recebeu.

### Arquivos alterados
- `core/models.py`: `CANAL_AMBOS` — opção de **envio**, deliberadamente **fora** de `CANAL_COBRANCA_CHOICES`
  (o campo `CobrancaEnviada.canal` guarda só o canal que realmente saiu).
- `core/views.py` (`mensalidade_cobranca_enviar_view`): aceita `canal=ambos`; monta `pedidos` e, **por família**,
  calcula os `destinos` que faltam; a mensagem é gerada **uma vez** e reusada; um `CobrancaEnviada` por envio;
  resposta com `por_canal`. O filtro `so_nao_enviados` saiu do pré-filtro da lista e passou a ser avaliado
  por canal dentro do laço.
- `templates/core/mensalidades.html`: `<option value="ambos">`.
- `static/js/mensalidade_cobranca.js`: `canaisDoEnvio`, `campoDoCanal`, `temDestinoNoCanal`, `faltaAlgumCanal`;
  `marcaEnviado(li, porCanal)` atualiza os dois contadores e mostra `💬 n · ✉️ n`; `alvosLote` e o toast de
  troca de canal cobrindo "ambos".
- `core/tests.py`: 8 testes do modo "ambos".

### Decisões tomadas
- **Uma geração de mensagem por família**, não por canal: com o modo IA ligado seriam duas chamadas ao GPT e
  dois textos diferentes para a mesma pessoa. Há teste garantindo `call_count == 1`.
- **Filtro por canal dentro do laço**: é o que permite "quem já recebeu por WhatsApp leva só o e-mail".
- **Um canal desconfigurado não aborta o lote** — em "ambos" segue pelo outro; só recusa (400) se nenhum
  estiver configurado. Antes, qualquer canal faltando derrubava a requisição inteira.
- **Gate de e-mail não bloqueia o WhatsApp**: se a pessoa se descadastrou do e-mail, o WhatsApp ainda sai e a
  falha aparece na lista com o motivo.
- **"Só quem já me mandou mensagem" não exclui a família em "ambos"** — é o gate do WhatsApp; excluir a linha
  barraria também o e-mail, que tem gate próprio no servidor.

### Validação
- Suíte: **107 testes OK** (99 + 8). Sem migration.

## 2026-07-31 - Corrige o seletor de canal da cobrança disparando a troca de telefone

### Resumo
O seletor "Enviar por" (canal da cobrança) nasceu com a classe `mens-cob-tel-sel`, que é o gancho do handler
que **troca o telefone de cobrança da família**. Resultado: só de mudar o canal, o front disparava um POST
indevido para `mensalidade_cobranca_telefone_view` (com `usuario_id=undefined`) e mostrava um toast de erro,
sem o Diretor ter clicado em nada de envio.

### Arquivos alterados
- `templates/core/mensalidades.html`: o `#cobrancaCanal` passou a usar a classe própria
  `mens-cob-canal-sel` (+ comentário explicando por que não reusar a outra).
- `static/js/mensalidade_cobranca.js`: o handler de troca de telefone agora exige `data-usuario` na origem do
  evento — guarda contra outro `<select>` herdar a classe por engano.
- `static/css/mensalidades.css`: `.mens-cob-canal-sel` herda o estilo do seletor e ganha destaque (é o que
  decide por onde o lote sai).
- `core/tests.py`: teste de regressão conferindo que a tag do `#cobrancaCanal` **não** tem a classe do
  seletor de telefone.

### Decisões tomadas
- Corrigido nos **dois** lados: classe própria no template (causa) e exigência de `data-usuario` no handler
  (proteção). Só a primeira já resolveria, mas a segunda impede a repetição do mesmo engano.

### Validação
- Suíte: **99 testes OK** (98 + 1 de regressão).

### Nota de diagnóstico (não é código)
- No mesmo período a instância da W-API estava com a **assinatura vencida** (403) e depois **desconectada**
  (401), o que fazia toda cobrança por WhatsApp falhar. Após a renovação e o pareamento, envio real validado
  (`ok=True`, 218 grupos). O 403 que aparecia na tela vinha daí, não do código.

## 2026-07-31 - E-mail: extrato dos últimos envios

### Resumo
A tela `/email/` passou a mostrar os últimos e-mails que o sistema tentou enviar — sucesso, falha e o que foi
barrado pelo gate. Antes só havia o contador agregado, insuficiente para acompanhar a ligação das notificações.

### Arquivos criados/alterados
- `core/models.py`: novo **`LogEmail`** (`para`, `assunto`, `origem`, `ok`, `detalhe`, `criado_em`), com
  `LIMITE = 200`, `registrar()` (nunca levanta exceção; apara em lote quando passa de `LIMITE + 50`) e a
  propriedade `rotulo_origem`, que reusa o rótulo do `TEMPLATES_NOTIFICACAO`.
- `core/email_envio.py`: `enviar(..., origem="")` + `_registrar_log`; grava sucesso e falha.
- `core/views.py`: `_enviar_email(..., origem="")` — e o que é **barrado pelo gate** também vira linha, com o
  motivo já traduzido por `_MOTIVO_EMAIL`. `origem` propagada: tipo da notificação em `_notificar_email`,
  `"cobranca"` no envio em lote e `"teste"` no botão de teste. `email_view` passa `log_emails` (60 mais recentes).
- `templates/core/email.html`: card **📬 Últimos envios** (tabela com `tabela-scroll`, botão Atualizar e aviso
  quando vazio).
- `core/migrations/0058_logemail.py` **(novo)**.
- `core/tests.py`: `LogEmailTests` (8 testes).

### Decisões tomadas
- **O corpo não é gravado.** Só destinatário, assunto e resultado — o extrato serve para diagnóstico, não para
  arquivar mensagens, e o projeto evita acumular dado pessoal. Há teste garantindo.
- **Barrado pelo gate também vira linha.** Sem isso, um descadastro pareceria "sumiço" da notificação.
- **Apara em lote** (`LIMITE + 50`), não a cada envio: evita um DELETE por e-mail enviado.
- **`rotulo_origem` no model**, não no contexto da view: template Django não faz lookup de dicionário por chave
  variável, e a informação pertence ao registro.

### Dúvidas do usuário respondidas (sem mudança de código)
- **`Reply-To` deve ficar vazio** para as respostas caírem na conta de envio: sem ele, a resposta vai para o
  `From`, que já é a conta configurada. O campo existe para desviar as respostas a *outro* endereço.
- **A cobrança já tem pausa nos dois canais**: 1 por requisição com 10s entre cada, barra e cancelar — o pacing
  está no JS (`mensalidade_cobranca.js`), então independe do canal.

### Validação
- Suíte: **98 testes OK** (90 + 8). `check` e `makemigrations --check` limpos.

### Pendências
- Ligar cada notificação no canal de e-mail pela aba 🧩 Templates (todas nascem desligadas).
- Robustez da resposta automática de autorização do WhatsApp segue pendente.

## 2026-07-31 - Notificações por e-mail (Etapas 3 e 4: fan-out dos gatilhos + cobrança)

### Resumo
Fecha a feature: o e-mail passou a sair de verdade. As 5 notificações transacionais despacham para os canais
marcados no template, e a cobrança de mensalidades ganhou seletor de canal com contagem por canal.

### Arquivos criados/alterados
- `core/views.py`:
  - **`_notificar(tipo, numero, contexto, *, forcar=False, email="")`** virou despachante. Renderiza o texto
    **uma vez** e chama `_notificar_whatsapp` e/ou `_notificar_email` conforme `enviar_whatsapp`/`enviar_email`.
    Retorna o resultado por canal. Curto-circuito `sem_canal` antes de renderizar (não gasta chamada de IA).
  - **`texto_para_email`** (+ `_RX_NEGRITO_WA`): remove o `*negrito*` do WhatsApp.
  - **`_email_familia`** (par do `_whatsapp_familia`) e `_MOTIVO_EMAIL` (motivos do gate em português).
  - Gatilhos com e-mail: `_notificar_cadastro` (resp_email / e-mail da diretoria),
    `_notificar_mensalidade_paga`, `_criar_inscricao_de_payload` (`responsavel_email`),
    `_notificar_compra_loja` (`comprador_email` + e-mail dos membros no aviso interno).
  - `_cobrancas_familias`: `email`/`tem_email` e contagem por canal
    (`cobrado_mes_whatsapp`/`cobrado_mes_email`; `cobrado_mes` continua sendo o total).
  - `mensalidade_cobranca_enviar_view`: parâmetro `canal`, envio por `_enviar_email` com
    `transacional=False`, filtro por canal e `CobrancaEnviada(canal=...)`.
  - `mensalidade_cobranca_config_view` salva o assunto; `mensalidades_view` expõe `email_configurado`.
- `core/models.py`: `CobrancaEnviada.canal` (+ `CANAL_WHATSAPP`/`CANAL_EMAIL`/`CANAL_COBRANCA_CHOICES`),
  `ConfigMensalidade.assunto_cobranca_email` e `ASSUNTO_COBRANCA_PADRAO`.
- `core/migrations/0057_cobrancaenviada_canal_and_more.py` **(novo)**.
- `templates/core/mensalidades.html`: seletor `#cobrancaCanal`, campo de assunto e os `data-*` por canal.
- `static/js/mensalidade_cobranca.js`: `canalAtual`/`campoCobrado`/`temDestino`, `canal` no POST, badge por
  canal e revalidação dos botões ao trocar o canal.
- `core/tests.py`: `FanOutNotificacaoTests` (10) e `CobrancaPorEmailTests` (8).

### Decisões tomadas
- **Texto renderizado uma vez** para os dois canais: com a IA ligada, renderizar por canal dobraria o custo e
  poderia mandar textos diferentes para a mesma pessoa. Há teste garantindo `render.call_count == 1`.
- **`canal` no `CobrancaEnviada` com default `whatsapp`**: todo o histórico anterior é de WhatsApp, então a
  contagem antiga continua correta sem data migration.
- **Cobrança vai como não-transacional.** É o clube que inicia; respeita descadastro, leva
  `List-Unsubscribe` e é barrada por bounce — ao contrário dos comprovantes.
- **Só `*...*` é limpo** do texto: `_` e `~` aparecem em endereços de e-mail e nomes de arquivo.
- **O filtro "só quem já me mandou mensagem" não se aplica ao e-mail** — é o gate do WhatsApp; o do e-mail
  (descadastro/bounce) roda no servidor.
- Assunto padrão da cobrança sem caixa alta, "!" ou "URGENTE": linguagem agressiva é gatilho de spam.

### Validação
- Suíte: **90 testes OK** (72 + 18).
- `check` e `makemigrations --check` limpos; aba Cobranças renderiza o seletor e os `data-*` por canal.
- Corrigido em produção o único e-mail inválido da base: um `pai_email` cujo domínio estava digitado pela
  metade. Revalidação: **0 e-mails com formato inválido**. (Identificação do registro fora do versionamento —
  ver a regra de dados pessoais no `.gitignore`.)

### Pendências
- Ligar cada notificação no canal de e-mail pela aba 🧩 Templates (todas nascem desligadas) e preencher o
  `Reply-To` na tela `/email/`.
- Por decisão do usuário: os 2 aventureiros de `teste_responsavel` **ficam** com `demo=False`, e a senha de app
  do Gmail **não** será rotacionada.
- Robustez da resposta automática de autorização do WhatsApp segue pendente.

## 2026-07-31 - Notificações por e-mail (Etapa 2: canal por notificação + camada anti-spam)

### Resumo
Cada notificação passou a escolher por qual canal sai (WhatsApp e/ou e-mail), e o canal de e-mail ganhou a
camada de **consentimento** que faltava: descadastro, supressão por bounce, `List-Unsubscribe`, `Reply-To` e
rodapé de identificação. **Nada dispara por e-mail ainda** — a Etapa 3 liga os gatilhos.

### Motivação
Pergunta do usuário sobre risco de spam ao mandar cobrança/lembrete. Cobrança **não é transacional**: o clube
inicia, não o usuário. Para filtro de spam isso é outra categoria, e sem opt-out o dano vai além da cobrança —
quem marca "é spam" derruba a reputação da conta para todos os envios, inclusive os comprovantes.

### Arquivos criados/alterados
- `core/models.py`:
  - `TemplateNotificacao` += `enviar_whatsapp` (default `True`), `enviar_email` (default `False`), `assunto`.
    `TEMPLATES_NOTIFICACAO` ganhou um 6º item por tipo (assunto padrão) e o novo `assunto_padrao(tipo)`;
    `get_tipo` passa a preencher o assunto também em templates já existentes que estejam sem.
  - Novo **`ContatoEmail`**: `endereco` (único), `nome`, `descadastrado_em`, `bounce_em`/`bounce_motivo`,
    contador, `token`. `para()` normaliza e cria; `pode_receber(transacional)`, `registrar_bounce`,
    `descadastrar`/`reinscrever` (idempotentes). Índices em `descadastrado_em` e `bounce_em`.
  - `EmailConfig` += `reply_to`, `site_url`, `rodape`.
- `core/email_envio.py`: `enviar(..., contato=None, transacional=False)` — cabeçalhos `List-Unsubscribe` e
  `List-Unsubscribe-Post` (RFC 8058), `Reply-To`, rodapé via `_montar_corpo`, `link_descadastro` e
  `_eh_recusa_definitiva` (só 5xx/`SMTPRecipientsRefused` marcam bounce).
- `core/views.py`: `_pode_enviar_email` (gate), `_enviar_email` (ponto único), `descadastrar_view` (pública,
  `@csrf_exempt`), canais em `whatsapp_templates_view`, `enviar_*`/`assunto` em `_notif_templates_ctx`,
  `email_configurado` no contexto do WhatsApp e painel de contatos em `email_view`.
- `core/urls.py`: `descadastrar/<str:token>/`.
- `templates/core/descadastrar.html` **(novo)**; `templates/core/email.html` (card "🛡️ Proteção contra spam" +
  `Reply-To`); `templates/core/whatsapp.html` (bloco "Por onde enviar" + assunto).
- `core/migrations/0056_...py` **(novo)**.
- `core/tests.py`: nova `ConsentimentoEmailTests` com 16 testes.

### Decisões tomadas
- **Bounce bloqueia tudo; descadastro bloqueia só o não-transacional.** Quem se descadastrou de avisos ainda
  recebe o comprovante do que ele mesmo fez — espelha a lógica de `NOTIF_TRANSACIONAIS` do WhatsApp.
- **`forcar=True` não fura bounce.** Insistir em endereço morto é o que mais machuca reputação; o `forcar`
  existe para aviso interno à diretoria, não para contornar recusa do servidor.
- **Falha 4xx ou de conexão não marca bounce** — é problema nosso (rede, senha, greylisting), não do endereço.
- **`site_url` no model em vez de `build_absolute_uri`**: as notificações saem em thread de fundo (`_em_thread`
  dentro de `on_commit`), onde não existe `request`.
- **`@csrf_exempt` no descadastro**: Gmail/Outlook fazem POST direto no link (One-Click) sem passar pela nossa
  página. O token é a credencial e a ação é reversível.
- **Transacional não leva convite de descadastro** — não faz sentido oferecer saída de um comprovante.
- Sequência escolhida: transacionais primeiro (constroem reputação com destinatários engajados), cobrança só
  depois. Começar por cobrança em massa faria o contrário.

### Validação
- Suíte: **72 testes OK** (45 + 11 da Etapa 1 + 16 desta).
- `check` e `makemigrations --check` limpos; as 3 telas renderizam (5 blocos de canal na aba Templates).
- **Base de e-mails checada por DNS, sem enviar nada**: 62 endereços distintos, 59 em domínios saudáveis.
  Problemas: um `pai_email` com o domínio digitado pela metade e 2× um endereço `@example.com`
  (null MX — RFC 7505 — dos registros de teste `teste_responsavel`).
- Autenticação de remetente já OK sem trabalho: com `From` `@gmail.com`, SPF/DKIM/DMARC passam pelo Google.

### Pendências
- **Etapa 3**: `_notificar` vira fan-out entre os canais + `_email_familia`; limpar a marcação `*negrito*` do
  WhatsApp no caminho do e-mail.
- **Etapa 4**: cobrança/lembrete por e-mail — exige campo `canal` no `CobrancaEnviada` (hoje ele não distingue
  canal, então ligar e-mail faria a família contar como cobrada e o WhatsApp deixaria de sair) e pacing.
- Corrigir o `resp/pai_email` com digitação (`@gmai`) — dado pessoal em produção, aguarda confirmação.
- Marcar os 2 aventureiros de teste (`teste_responsavel`) como `demo=True`; hoje estão `demo=False`.
- Robustez da resposta automática de autorização do WhatsApp segue pendente.

## 2026-07-30 - Notificações por e-mail (Etapa 1: base + tela)

### Resumo
Início do **segundo canal de notificação**: e-mail, ao lado do WhatsApp. Esta etapa entrega só a
infraestrutura — configuração da conta SMTP, cliente de envio e tela com teste. **Nenhuma notificação sai por
e-mail ainda**; o canal por notificação entra na Etapa 2.

### Arquivos criados/alterados
- `core/models.py`: novo **`EmailConfig`** (singleton `get_solo`) — `host`/`porta`/`seguranca`
  (STARTTLS/SSL/nenhuma)/`usuario`/`senha`/`remetente_nome` + contador `enviados`/`falhas`/`ultimo_envio_em`/
  `ultimo_erro`. Propriedades `configurado`, `senha_mascarada` (reusa `_mascarar_segredo`) e `remetente`
  (`formataddr`); métodos `registrar_envio`/`registrar_falha` (com `F()`, seguros entre threads) e
  `zerar_contador`. Novo import `from email.utils import formataddr`.
- `core/email_envio.py` **(novo)**: cliente de envio. Usa `django.core.mail` (`get_connection` + `EmailMessage`)
  montando a conexão SMTP a partir do `EmailConfig`, não do settings. `enviar(config, destino, assunto, corpo)`
  → `(ok, detalhe)`; `_amigavel` traduz `SMTPAuthenticationError`/recusa de destinatário/timeout etc.
- `core/migrations/0055_emailconfig.py` **(novo)**.
- `core/views.py`: bloco novo "E-mail (SMTP)" com `email_view`, `email_config_view`, `email_testar_view` (JSON) e
  `email_zerar_view`, todas `@diretor_required`. Helper **`_email_do_usuario`** (conta de login → ficha da
  diretoria → `resp_email` do aventureiro). Imports `email_envio` e `EmailConfig`.
- `core/urls.py`: rotas `email/`, `email/config/`, `email/testar/`, `email/zerar/`.
- `core/menus.py`: item **✉️ E-mail** em `ITENS_MENU`, logo após WhatsApp (o Diretor já recebe todos os itens
  por `ACESSO_PADRAO`, então não foi preciso mexer no acesso).
- `templates/core/email.html` **(novo)** e `static/js/email.js` **(novo)**: espelham `ia.html`/`ia.js`
  (mostrar/ocultar segredo, teste via AJAX com toast, contador atualizado sem recarregar). Reusam `whatsapp.css`.
- `core/tests.py`: nova `EmailConfigTests` com 11 testes.

### Decisões tomadas
- **Sem dependência nova**: as outras integrações falam HTTP por `urllib`, mas para e-mail o Django já traz o
  `django.core.mail`. A conexão é montada a partir do model (não das variáveis `EMAIL_*` do settings), para a
  configuração ficar na tela como nos demais módulos.
- **Senha de app com espaços é normalizada** ao salvar e no cliente: o Gmail exibe em grupos de 4 e o usuário
  cola assim, mas o servidor SMTP não aceita.
- **`_email_do_usuario` desce até o `resp_email`**: a conta de login quase nunca tem e-mail (1 de 43 no banco de
  produção), enquanto o `resp_email` do aventureiro está preenchido em 100% das famílias.
- **Sem gate no e-mail**: o `_pode_notificar` existe pelo risco de bloqueio da W-API, específico do WhatsApp.
  E-mail transacional para quem forneceu o próprio endereço não tem esse risco.
- Módulo próprio em vez de aba dentro do WhatsApp: é outro canal e o padrão de `ITENS_MENU` já suporta.

### Validação
- Suíte completa: **56 testes OK** (45 anteriores + 11 novos).
- `manage.py check` e `makemigrations --check` limpos.
- SMTP do Gmail: autenticação e envio reais confirmados pelo código novo (`email_envio.enviar`), incluindo a
  falha proposital com senha errada (mensagem amigável + contador de falhas).
- No VPS de produção: saída para `smtp.gmail.com` liberada nas portas 587, 465 e 25.

### Pendências
- **Etapa 2**: campos `enviar_whatsapp`/`enviar_email`/`assunto` no `TemplateNotificacao` + os controles na aba
  🧩 Templates.
- **Etapa 3**: `_notificar` vira fan-out entre os dois canais + `_email_familia`; limpar a marcação `*negrito*`
  do WhatsApp no caminho do e-mail.
- Robustez da resposta automática de autorização do WhatsApp (log + retry idempotente) segue pendente.

## 2026-07-14 - WhatsApp/Liberação: marcar autorizado manualmente

### Resumo
Botão por linha na aba 🚦 Liberação para marcar um contato como autorizado à mão (autorização por fora ou
mensagem que não chegou ao webhook), já liberando as notificações automáticas para ele.

### Arquivos criados/alterados
- `core/views.py`: `whatsapp_liberar_view` (POST, `@diretor_required`) — seta `autorizacao_recebida_em` e
  `ultima_msg_whatsapp_em` no `PerfilUsuario` e `autorizou_em`/`ultima_msg_em` no `ContatoWhatsapp` (só quando
  vazios; não sobrescreve contato real). Resolve o número com `_numero_do_contato`.
- `core/urls.py`: rota `whatsapp/liberar/` (`whatsapp_liberar`).
- `templates/core/whatsapp.html`: `data-liberar-url` no painel + botão `.wa-lib-liberar` (só se `not p.autorizou`
  e há `p.usuario_id`).
- `static/js/whatsapp.js`: handler por delegação — confirma, POST AJAX, e na resposta ok deixa a pill verde
  ("✅ Autorizado" + "há instantes") e remove o botão.
- `static/css/whatsapp.css`: `.wa-lib-liberar` (+ hover/disabled); `.wa-lib-status` com `flex-wrap`.

### Decisões tomadas
- Marcar também o `ContatoWhatsapp` (não só o perfil) é o que importa: o gate `_pode_notificar` consulta o
  ContatoWhatsapp por número — sem isso, ficaria verde no termômetro mas as notificações continuariam barradas.
- Só preenche datas vazias (idempotente; não clobbera uma última mensagem real mais recente).
- Botão só para linhas com conta (`usuario_id`); diretoria sem User não tem perfil a marcar.

### Pendências
- Robustez da resposta automática de autorização (log + retry idempotente, migration `0055`) segue pendente.

## 2026-07-14 - WhatsApp/Liberação: busca inteligente + diagnóstico da resposta de autorização

### Resumo
Adicionado um campo de busca ao vivo na aba 🚦 Liberação (filtra a lista de responsáveis/diretoria enquanto
digita, por nome ou número). Trabalho originado de um diagnóstico: por que a resposta automática de autorização
não estava sendo enviada em alguns casos.

### Arquivos criados/alterados
- `templates/core/whatsapp.html`: campo `#waLibBusca` (input `type=search`) + contador `#waLibConta` acima da
  lista e aviso `#waLibSemResultado` ("nenhum contato encontrado") abaixo dela.
- `static/js/whatsapp.js`: bloco de busca da Liberação — pré-computa por linha um índice de nome (sem acento/caixa,
  via `normalize("NFD")`) e os dígitos do número; handler `input` filtra escondendo `.wa-lib-item`; `Esc` limpa.
- `static/css/whatsapp.css`: `.wa-lib-busca`, `.wa-lib-busca-input` (+ `:focus`), `.wa-lib-busca-conta`,
  `.wa-lib-vazio-busca` — na paleta existente. **Fix:** `.wa-lib-item[hidden] { display:none }` — o `display:flex`
  do item sobrescrevia o `[hidden]` (contava "1 de 11" mas não escondia os demais); a regra por atributo vence.

### Diagnóstico (resposta automática de autorização)
> Identificação das pessoas envolvidas fora do versionamento — o repositório é público (ver a regra de dados
> pessoais no `.gitignore`). Os casos ficam descritos pelo padrão de falha, que é o que importa tecnicamente.

- **Caso 1 — mensagem chegou, confirmação não saiu**: a mensagem casou com o perfil e a autorização foi
  marcada, mas a resposta de confirmação não foi entregue. Causa: `_registrar_contato_whatsapp` envia a
  confirmação em `try/except: pass` **ignorando o retorno** de `_enviar_whatsapp`, e a confirmação é disparo
  único — uma falha transitória da W-API se perde sem log nem retry. A instância estava OK (listou 216 grupos);
  o envio manual depois deu `ok:True` (a pessoa recebeu a confirmação com atraso).
- **Caso 2 — a mensagem nunca chegou**: `autorizacao_recebida_em=None`, `ultima_msg_whatsapp_em=None`,
  **nenhum** evento de webhook e **nenhum** `ContatoWhatsapp` (que é permanente) em qualquer variante do DDD.
  Conclusão: a mensagem de autorização **nunca chegou ao webhook do clube** — não é bug de código.

### Decisões tomadas
- Busca 100% no front (sobre a lista já renderizada) — sem novo endpoint, coerente com o tamanho da base.
- Match "inteligente": letras filtram por nome (sem acento), dígitos filtram por número.

### Pendências
- **Robustez da resposta de autorização (não feita)**: logar a falha do envio (parar de engolir) e tornar a
  confirmação **idempotente com retry** na próxima mensagem (campo novo, migration `0055`). Combinado com o
  usuário, fica para uma próxima etapa.

## 2026-07-12 - Revisão geral (parte 4): responsividade mobile

### Resumo
Ajustes de responsividade a partir da auditoria: alvos de toque, tabelas roláveis e salvaguarda de imagem.

### Arquivos criados/alterados
- `static/css/eventos.css`: `.ordem-btn` (40×34) e `.entrega-btn` (40×40) — antes 28×22 / 26×26.
- `static/css/loja.css`: `.loja-kit-remover` (40×40); media ≤560px colapsa `.loja-var-valor/.loja-var-estoque`.
- `static/css/base.css`: `img { max-width: 100% }` global.
- `templates/core/loja.html`: as 3 tabelas da aba Vendas envoltas em `.tabela-scroll`.

### Decisões tomadas
- Reaproveita `.tabela-scroll` (já em eventos.css, linkado na loja) em vez de criar classe nova.
- Alvos de toque ~40px (padrão recomendado); vale uma conferência final no dispositivo real.

### Pendências
- Nenhuma para esta revisão. Recomendações operacionais em aberto: otimizar `logo.png`/remover
  `logo_original_backup.png` (binários, exige ok); confirmar `DJANGO_SECRET_KEY` no VPS.

## 2026-07-12 - Revisão geral (parte 3): performance

### Resumo
Elimina N+1 e trabalho redundante nas telas mais pesadas; adiciona índices de banco.

### Arquivos criados/alterados
- `core/views.py`: `_foto_valida` só checa o campo (sem `storage.exists()`); `presenca_view` usa
  `annotate(Count("presencas"))`; `_inativos_para_reengajar` aceita `liberacao` pronta e `whatsapp_view`
  reusa a lista (antes 2×); `mensalidades_view` chama `ConfigMensalidade.get_solo()` 1× (antes 5×);
  `_loja_relatorio` materializa os itens (queryset separado só para o `.filter` dos pendentes).
- `templates/core/inicio.html`: `onerror` na foto da diretoria (degrada pro placeholder).
- `core/models.py` + `core/migrations/0054_*`: `db_index` em `Aventureiro.ativo/demo`,
  `Pagamento.status/tipo`, `Mensalidade.ano/status`.

### Decisões tomadas
- Confiar no campo de foto + `onerror` no template (padrão já usado) em vez do stat de disco em loop.
- Índices nos campos mais filtrados; ganho cresce com a base (hoje pequena).

### Pendências
- Recomendação (não feita, exige confirmação — são binários): otimizar `static/img/logo.png` (448 KB,
  servido em toda página) e remover/mover `static/img/logo_original_backup.png` (1,7 MB, backup morto
  em `static/`).
- Mobile (próxima parte).

## 2026-07-12 - Revisão geral (parte 2): robustez das notificações WhatsApp

### Resumo
Envio das notificações não bloqueia mais o request/webhook, e o reconhecimento da autorização ficou exato.

### Arquivos criados/alterados
- `core/views.py`: helper `_em_thread` (thread daemon fire-and-forget que fecha a conexão de banco e
  loga erros); os 4 `on_commit` de notificação passam a chamar `_em_thread(...)`; match de autorização
  em `_registrar_contato_bruto` e `_registrar_contato_whatsapp` virou igualdade normalizada exata;
  `import threading`.

### Decisões tomadas
- Thread daemon (sem dependência nova, sem fila) para as notificações transacionais — HTTP de até ~20s
  não segura a resposta nem o webhook do MP.
- Match exato: o link `/autorizar` já envia o texto exato; substring abria o gate indevidamente.
- Cobrança/reengajamento em lote não mudaram (já são 1-por-request com pausa de 10s no front).

### Pendências
- Performance e responsividade mobile (próximas partes da revisão).

## 2026-07-12 - Revisão geral (parte 1): gate transacional + críticos de produção

### Resumo
A partir de uma auditoria geral (responsividade, performance, correção). Esta parte fecha o
comportamento do gate das notificações e endurece pontos críticos de produção.

### Arquivos criados/alterados
- `core/views.py`: `NOTIF_TRANSACIONAIS` + `_notificar` aplica o gate só a notificações não
  transacionais; `_aprovar_pagamento` com claim atômico de idempotência; `mercadopago_webhook` com
  `try/except` de topo (loga via `logger` e responde 500 sem traceback); `cadastro_aventureiro_view`
  envolta em `transaction.atomic`; `import logging` + `logger`.
- `templates/core/evento_inscrever.html`: texto do bloco de autorização reescrito (a confirmação já vem
  sempre; o convite passa a ser para avisos futuros).
- `config/settings.py`: `DEBUG` com padrão seguro (liga só sem `ALLOWED_HOSTS`; env explícita manda).

### Decisões tomadas
- Notificações transacionais furam o gate (resposta a uma ação da própria pessoa; baixo risco de bloqueio).
- Idempotência por claim atômico (`UPDATE ... WHERE finalizado=False`) — funciona no SQLite (sem lock de
  linha) e no Postgres; rollback reverte o claim em falha, deixando o MP reprocessar.
- Webhook do MP responde 500 (sem traceback) em erro de finalização, para o MP reenviar — seguro por ser
  idempotente.

### Pendências
- Robustez WhatsApp (envio em lote em background, match de autorização estrito), performance, mobile.
- Operacional: confirmar `DJANGO_SECRET_KEY` no `/etc/pinhaljunior2.env` do VPS.

## 2026-07-12 - Notificações automáticas por WhatsApp (Etapa 5: inscrição + autorização pré-checkout)

### Resumo
Fecha a feature: confirmação de inscrição em evento + bloco "Autorizar no WhatsApp" antes do checkout
nos eventos abertos ao público (para o inscrito desconhecido se liberar e receber a confirmação).

### Arquivos criados/alterados
- `core/views.py`: `_criar_inscricao_de_payload` agenda a confirmação (`inscricao_evento`) via `on_commit`;
  `evento_inscrever_view` passa `mostrar_autorizar`/`link_autorizar` ao contexto.
- `templates/core/evento_inscrever.html`: bloco de autorização (só evento aberto + WhatsApp configurado
  + notificação ativa), usando o link curto `/autorizar/`.
- `static/css/eventos.css`: estilos `.notif-autorizar*`.

### Decisões tomadas
- O bloco só aparece quando faz sentido (evento aberto, WhatsApp configurado, notificação de inscrição ativa).
- Confirmação respeita o gate; o bloco pré-checkout é o caminho para o desconhecido se tornar "liberado".

### Pendências
- Nenhuma para esta feature. (Operacional no VPS: manter o Mercado Pago em modo teste até liberar produção.)

## 2026-07-12 - Notificações automáticas por WhatsApp (Etapa 4: novo cadastro)

### Resumo
Cadastros que criam conta nova (aventureiro e diretoria) enviam boas-vindas com o usuário de acesso.

### Arquivos criados/alterados
- `core/views.py`: helper `_notificar_cadastro` (via `on_commit`); ligado em `cadastro_aventureiro_view`
  (usa nome/WhatsApp do responsável) e `cadastro_diretoria_view` (nome/WhatsApp do integrante, exceto
  quando `com_aventureiro`, que já cai no cadastro de aventureiro).

### Decisões tomadas
- Novo aventureiro em conta já existente NÃO notifica (não é conta/usuário novo).
- Gate anti-bloqueio aplicado: a boas-vindas chega a quem já escreveu ao clube.

### Pendências
- Etapa 5: inscrição em evento + autorização pré-checkout no evento aberto.

## 2026-07-12 - Notificações automáticas por WhatsApp (Etapa 3: Mensalidade paga)

### Resumo
Todo pagamento de mensalidade (online ou baixa manual do Diretor) dispara um agradecimento ao
responsável, respeitando o gate anti-bloqueio.

### Arquivos criados/alterados
- `core/views.py`: helpers `_whatsapp_familia` (número do responsável financeiro), `_rotulo_mensalidade`
  e `_notificar_mensalidade_paga` (agenda via `on_commit`); ligados em `_finalizar_mensalidade`
  (coleta as pagas + notifica) e em `mensalidade_pagar_view` (baixa manual, só quando marca pago).

### Decisões tomadas
- Número da família = responsável financeiro (`cobranca_whatsapp_origem` + `_resolver_origem_numero`),
  mesma lógica das Cobranças.
- Notifica também na baixa manual do Diretor (é um pagamento recebido); o gate evita spam a não-liberados.

### Pendências
- Etapas 4–5: novo cadastro, inscrição + autorização pré-checkout.

## 2026-07-12 - Notificações automáticas por WhatsApp (Etapa 2: Loja)

### Resumo
Ligado o 1º gatilho: toda compra da Loja do Clube dispara confirmação ao comprador + aviso interno à
diretoria escolhida (para comprar os materiais).

### Arquivos criados/alterados
- `core/views.py`: helpers `_whatsapp_membro_diretoria` e `_notificar_compra_loja`; `_criar_compra_loja`
  monta o texto dos itens e agenda as notificações via `transaction.on_commit` (vale para o fluxo pago
  via Mercado Pago e o simulado).

### Decisões tomadas
- **`on_commit`**: a chamada HTTP do WhatsApp roda só após o commit, para não segurar/derrubar a
  transação atômica do webhook do Mercado Pago.
- Confirmação ao comprador respeita o gate `_pode_notificar`; o aviso interno usa `forcar=True`
  (diretoria sempre recebe, independe de ter mandado msg).

### Pendências
- Etapas 3–5: Mensalidade paga, novo cadastro, inscrição + autorização pré-checkout.

## 2026-07-12 - Notificações automáticas por WhatsApp (Etapa 1: base + aba Templates)

### Resumo
Início do sistema de **notificações automáticas por WhatsApp** disparadas por eventos do sistema
(compra na loja, mensalidade paga, novo cadastro, inscrição em evento). Esta etapa entrega a
**infraestrutura** (sem disparar nada ainda): registro de todo número que escreve ao clube, salvaguarda
anti-bloqueio e a **aba Templates** (🧩) para configurar cada notificação (liga/desliga, texto do sistema
ou IA com prompt, e — no aviso interno — quais integrantes da diretoria recebem).

### Arquivos criados/alterados
- `core/models.py`: novos models **`ContatoWhatsapp`** (todo número que escreve ao clube: nome,
  primeira/última mensagem, contagem, autorizou_em) e **`TemplateNotificacao`** (1 linha por tipo:
  ativo, usar_ia, mensagem, prompt_ia, M2M `avisos_internos_para`); dict `TEMPLATES_NOTIFICACAO` com os
  5 tipos e textos/prompts padrão; campo `WhatsappConfig.notificar_janela_dias` (default 60).
- `core/migrations/0053_contatowhatsapp_whatsappconfig_notificar_janela_dias_and_more.py`.
- `core/views.py`: webhook passa a chamar `_registrar_contato_bruto` (grava TODO número recebido);
  helpers `_pode_notificar` (gate: autorizou OU mandou msg dentro da janela), `_render_notificacao`
  (texto do sistema OU IA com prompt, reusa `openai_ia`+`registrar_uso`), `_notificar` (ponto único de
  envio com o gate) e `_MarcadorDict`; contexto/`_notif_templates_ctx`/`_diretoria_membros` na
  `whatsapp_view`; view `whatsapp_templates_view` (salva 1 template ou a janela global).
- `core/urls.py`: rota `whatsapp/templates/salvar/` (`core:whatsapp_templates`).
- `templates/core/whatsapp.html`: nova aba/painel **🧩 Templates**.
- `static/css/whatsapp.css`: estilos `.wa-check`/`.wa-membros`/`.wa-notif-form`/`.wa-janela-form`.
- `core/admin.py`: registro de `ContatoWhatsapp` e `TemplateNotificacao`.

### Decisões tomadas
- **Filtro anti-bloqueio SEMPRE aplicado** (`_pode_notificar`): número desconhecido só chega em evento
  aberto; nesse caso a autorização pré-checkout (Etapa 5) o libera. `forcar=True` só para avisos internos.
- **Fonte da verdade de "quem escreveu"** = `ContatoWhatsapp` (grava todo número, cadastrado ou não),
  separado do rastreio por `PerfilUsuario` (mantido para o termômetro dos cadastrados).
- Aba Templates cobre **só as 5 notificações novas**; cobrança/reengajamento/autorização ficam onde estão.
- Cada notificação: liga/desliga + alavanca IA (com prompt) OU texto do sistema; se a IA falhar, cai no texto.

### Pendências
- Ligar os gatilhos (Etapas 2–5): Loja, Mensalidade, Cadastro, Inscrição + bloco de autorização
  pré-checkout no evento aberto.

## 2026-07-12 - Doc: consolidação das fontes da verdade (IA + WhatsApp/liberação)

### Resumo
Atualização das fontes da verdade que ainda não refletiam tudo o que foi construído (módulo **Configurações IA**,
**cobrança por IA/telefone** e toda a evolução do **WhatsApp**: grupos, webhook, autorização, liberação,
reengajamento, link `/autorizar`). `ESTADO_ATUAL`/`HISTORICO` já vinham em dia a cada mudança; esta leva alinha o
contexto principal.

### Arquivos alterados
- `CLAUDE.md`: intro (IA + WhatsApp liberação), **Rotas** (WhatsApp com abas + webhook + `/autorizar` + reengajar;
  Configurações IA; Cobranças `modo`/`telefone`/`enviar`), **Models** (`WhatsappConfig` novo, `GrupoWhatsapp`,
  `WhatsappWebhookEvent`, `OpenAIConfig`, `ConfigMensalidade` com IA, `PerfilUsuario` de cobrança/rastreio),
  migrations até **0052**, e nova **convenção** de integrações externas (clients urllib, webhooks públicos,
  envio em lote com 10s).
- `docs/README_PROJETO.md`: parágrafo de módulos atualizado (Presença/Mensalidades/Loja/Financeiro/MP/WhatsApp/IA).

---

## 2026-07-11 - Autorização: resposta automática de confirmação

### Resumo
Quando alguém manda a **mensagem de autorização**, o sistema agora **responde automaticamente** com uma
confirmação curta (uma vez só). Como é uma resposta a quem acabou de escrever, é seguro (não é o clube iniciando
conversa). O texto é **configurável** na aba Autorização (vazio = não responde).

### Arquivos alterados
- `core/models.py`: `WhatsappConfig.resposta_autorizacao` (com default).
- `core/views.py`: `_registrar_contato_whatsapp` envia a resposta só na **1ª** vez que a autorização é
  reconhecida (guardas: WhatsApp configurado + resposta não-vazia; try/except pra nunca derrubar o webhook);
  `whatsapp_autorizacao_config_view` salva o campo; contexto da tela.
- `templates/core/whatsapp.html`: campo "Resposta automática ao autorizar" na aba Autorização.
- Migration **0052**.

### Verificação
Msg comum → não responde; autorização → responde 1x ao número certo; 2ª autorização → não repete; resposta
vazia → não responde.

---

## 2026-07-11 - Reengajamento: manda UMA vez por silêncio (não insiste)

### Resumo
Ajuste no critério de quem entra no reengajamento. Antes era **por tempo** (quem foi reengajado voltava a ser
elegível depois de `reengajar_dias`, ou seja, **reenviava a cada 30 dias mesmo sem resposta**). Agora é **por
mensagem**: reengaja **uma vez só** por período de silêncio e **não insiste** se a pessoa não responder. Só volta
a ser elegível se ela **mandar mensagem de novo** e depois ficar calada outra vez.

### Como controla
Regra em `_inativos_para_reengajar`: elegível se (a) já interagiu alguma vez, (b) está calado há ≥
`reengajar_dias` e (c) **`reengajado_em` é anterior à última mensagem** (`reengajado_em < ultima_msg_em`) — ou
nunca foi reengajado. Assim o reengajamento "trava" após o envio e só "destrava" quando a última mensagem da
pessoa passa a ser mais recente que o reengajamento (ela respondeu).

### Arquivos alterados
- `core/views.py`: `_inativos_para_reengajar` (critério por mensagem em vez de por janela de tempo).
- Sem migration (usa os campos existentes `ultima_msg_whatsapp_em`/`reengajado_em`).

### Verificação
6 cenários testados (nunca reengajado → envia; já reengajado → não insiste; 200 dias depois ainda sem resposta →
não reenvia; respondeu e calou de novo → envia; ativo → não; cold → não).

---

## 2026-07-11 - Doc: cron do reengajamento (automático no servidor)

### Resumo
Decidido rodar o reengajamento **automático via cron no servidor** (opção do usuário). Nenhuma mudança de
código: o comando `reengajar_inativos` já existe, já **pausa 10s** entre envios e já lê o **nº de dias**
configurável na tela (WhatsApp → Liberação). Só faltava documentar a linha do cron.

### Arquivos alterados
- `docs/DEPLOY_VPS.md`: seção "Cron — reengajamento do WhatsApp" com a linha pronta do crontab (caminhos reais do
  VPS: `/var/www/pinhaljunior2/current`, venv `.venv/bin/python`, env `/etc/pinhaljunior2.env`), como pausar e testar.

### Decisão
- Frequência da verificação = no **crontab (servidor)**; **quantos dias sem resposta** = na **tela** (configurável).
  Roda independente de acesso ao site.

---

## 2026-07-11 - WhatsApp: reengajamento com pausa entre envios (10s)

### Resumo
O "Reengajar inativos agora" mandava **tudo de uma vez** (um request só, sem intervalo) — arriscado (parece
spam). Agora tem o **mesmo pacing da cobrança**: envia **um a um, com 10s entre cada**, barra de progresso e
**cancelar**. O comando de cron (`reengajar_inativos`) também pausa 10s entre envios (server-side `time.sleep`,
sem risco de timeout).

### Arquivos alterados
- `core/views.py`: `import time`; constante `DELAY_ENVIO_LOTE_S=10`; helpers `_numero_do_contato` e
  `_reengajar_um(config, usuario_id)` (envia a 1 conta + marca `reengajado_em`); `_reengajar_inativos` agora
  pausa entre envios (usado pelo comando); `whatsapp_reengajar_view` passou a enviar **1 por request**
  (`usuario_id`); `whatsapp_view` embute a lista de alvos.
- `templates/core/whatsapp.html`: alvos via `json_script` + barra de progresso/cancelar no card de reengajamento.
- `static/js/whatsapp.js`: loop paced (10s, barra, cancelar), um envio por vez — espelha o "Enviar a todos".
- `static/css/whatsapp.css`: barra de progresso.
- Sem migration.

---

## 2026-07-11 - WhatsApp: responsividade das abas (mobile)

### Resumo
Com 5 abas (Configurações/Grupos/Webhook/Autorização/Liberação), a barra de abas **estourava e cortava** no
celular. Agora a barra **quebra em várias linhas** (`flex-wrap`), com padding/fonte menores abaixo de 520px —
todas as abas ficam visíveis, sem corte nem scroll horizontal da página. Revisão mobile das últimas telas
(Grupos, Webhook, Autorização, Liberação, Reengajamento e a aba Cobranças com termômetro/seletor de
telefone/alavanca) confirmada por screenshot a 484px.

### Arquivos alterados
- `static/css/whatsapp.css`: `.wa-abas` com `flex-wrap:wrap` + media query (≤520px) reduzindo `.wa-aba`;
  `.wa-grupo-item` com `flex-wrap` (ID longo não espreme).

---

## 2026-07-11 - WhatsApp: reengajamento de contatos inativos

### Resumo
Mesmo quem autorizou "esfria" se ficar muito tempo sem responder (só o clube manda). Agora, na aba **🚦
Liberação**, dá para configurar um **reengajamento**: se um contato que **já interagiu** fica `reengajar_dias`
(padrão 30) sem mandar mensagem, o clube envia uma **mensagem curta** perguntando se ele quer continuar recebendo
— reativando a conversa. Só vai para **quem já mandou mensagem alguma vez** (nunca para cold, que causaria
bloqueio) e **não reenvia** dentro da janela (idempotente).

### Como usar
- Config na aba Liberação: **dias sem resposta** + **mensagem de reengajamento**.
- Botão **"Reengajar inativos agora"** (mostra quantos inativos há) — dispara na hora.
- Comando **`python manage.py reengajar_inativos`** (mesma lógica) para agendar no **cron** (rodar sozinho).

### Arquivos alterados
- `core/models.py`: `WhatsappConfig.reengajar_dias`/`mensagem_reengajamento`; `PerfilUsuario.reengajado_em`.
- `core/views.py`: `_inativos_para_reengajar` (seleção: já interagiu + parado há X dias + não reengajado na
  janela; dedup responsável/diretoria) e `_reengajar_inativos` (envia + grava `reengajado_em`);
  `_liberacao_lista` inclui `usuario_id`/`reengajado_em`; views `whatsapp_reengajar_config_view`/
  `whatsapp_reengajar_view`; contexto com contagem de inativos.
- `core/management/commands/reengajar_inativos.py` (novo): para cron.
- `core/urls.py`: `whatsapp/reengajar/config/` e `whatsapp/reengajar/`.
- `templates/core/whatsapp.html`: card de reengajamento (config + botão) na aba Liberação.
- `static/js/whatsapp.js`: botão reengajar (confirma + AJAX + toast).
- `static/css/whatsapp.css`: separador.
- Migration **0051**.

---

## 2026-07-11 - WhatsApp: rastreio inclui diretoria + painel Liberação

### Resumo
O rastreio de contato/autorização passou a valer **também para a diretoria** (antes era só responsáveis). Agora,
uma mensagem recebida é casada com o número de **pai/mãe/resp. legal de aventureiro** OU de **membro da diretoria**
(`MembroDiretoria.whatsapp`). E a tela WhatsApp ganhou uma aba **🚦 Liberação**: um painel único que lista
**responsáveis + diretoria** com o termômetro (🟢 autorizado / 🟡 mandou msg / 🔴 nunca) + "há X" e um resumo
"N de M já mandaram msg".

### Arquivos alterados
- `core/views.py`: `_familia_por_whatsapp` → **`_perfil_por_whatsapp`** (casa responsáveis **e** diretoria);
  helper `_liberacao_lista` (responsáveis por conta + diretoria); `whatsapp_view` passa a lista + resumo.
- `templates/core/whatsapp.html`: 5ª aba **Liberação** com a lista e o resumo.
- `static/css/whatsapp.css`: estilos do painel + pills do termômetro (self-contained).
- Sem migration (rastreio já ficava em `PerfilUsuario`, que existe para qualquer conta).

### Nota
Quem é responsável **e** diretor aparece nas duas seções (status é por conta, então idêntico). O termômetro nas
Cobranças continua só para responsáveis (mensalidade); a visão completa (com diretoria) é o painel Liberação.

---

## 2026-07-11 - Cobranças: enviar em lote só para quem já mandou mensagem

### Resumo
No "Enviar a todos" (aba Cobranças) faltava filtrar por quem é seguro cobrar. Adicionado o checkbox
**"Só quem já me mandou mensagem (evita bloqueio)"** — quando ligado (padrão), o envio em lote mira **apenas**
famílias que já **autorizaram** ou já **mandaram alguma mensagem** (dado do rastreio via webhook). Assim não se
inicia conversa com quem só visualiza (o que causa o bloqueio por spam).

### Arquivos alterados
- `templates/core/mensalidades.html`: `data-liberado` por família (autorizou OU tem última msg) + checkbox
  "Só quem já me mandou mensagem" (padrão marcado).
- `static/js/mensalidade_cobranca.js`: `alvosLote()` respeita o novo filtro (além de "não recebeu este mês" e
  "tem número").
- `static/css/mensalidades.css`: dica do checkbox.
- Sem migration.

### Nota
É filtro do **envio em lote**; o envio **individual** continua manual (você decide por pessoa). "Liberado" =
autorizou OU já mandou qualquer mensagem (via webhook de recebidas).

---

## 2026-07-11 - WhatsApp: link curto de autorização (/autorizar/ → wa.me)

### Resumo
O link de autorização ficava longo (wa.me + texto grande). Agora há um **link curto e com a marca do clube**:
`https://pinhaljunior.com.br/autorizar` (rota pública `/autorizar/`) que **redireciona** (302) para o wa.me
montado a partir da config (número do clube + mensagem de autorização). É o link **curto** que se compartilha; o
wa.me fica "escondido" atrás dele. A aba Autorização passa a mostrar o link curto como principal (Copiar) e o
wa.me num `<details>` "Ver o link direto".

### Arquivos alterados
- `core/views.py`: helper `_wa_link_autorizacao(config)` (reaproveitado); `autorizar_view` (pública, redireciona;
  503 amigável se não configurado); `whatsapp_view` passa `link_autorizar_curto`. Import de `HttpResponse`.
- `core/urls.py`: rota `autorizar/`.
- `templates/core/whatsapp.html`: link curto (Copiar) + wa.me em `<details>` + Abrir.
- Sem migration.

### Nota
Sob o domínio raiz (produção) o link fica `pinhaljunior.com.br/autorizar`. Sem `numero_clube`/mensagem, a rota
responde 503 (configurar primeiro na aba Configurações/Autorização).

---

## 2026-07-11 - WhatsApp: link wa.me de autorização (avulso, copiável)

### Resumo
Fecha o ciclo do rastreio de autorização: a aba **✍️ Autorização** agora gera um **link wa.me avulso** com a
mensagem de autorização **pronta**. O responsável clica → abre o WhatsApp dele numa conversa com o clube com o
texto preenchido → só enviar. Ao enviar, cai no webhook, casa o número e marca a família como **autorizada**
(termômetro verde) — sem o clube iniciar conversa (não dispara o antspam do WhatsApp). O link tem botão
**Copiar** (para colar no grupo/cartaz/reunião) e um **Abrir no WhatsApp** para teste.

### Arquivos alterados
- `core/models.py`: `WhatsappConfig.numero_clube` (número da instância = destino do wa.me).
- `core/views.py`: `whatsapp_config_view` salva `numero_clube`; `whatsapp_view` monta `wa_link_autorizacao`
  (`https://wa.me/<numero normalizado>?text=<msg URL-encoded>`).
- `templates/core/whatsapp.html`: campo "Número do WhatsApp do clube" (aba Configurações) + card do link (aba
  Autorização, com Copiar e Abrir).
- `static/js/whatsapp.js`: handler de "Copiar" genérico (qualquer botão com `data-target`).
- Migration **0050**.

### Decisões / pendências
- **Disparo no grupo listando "quem falta": CANCELADO** (decisão do usuário) — não será feito.
- **QR code** do link: não feito agora (exigiria dependência nova; combinar depois se quiser).

---

## 2026-07-11 - WhatsApp: rastreio de contato + autorização (termômetro nas Cobranças)

### Resumo
Mecanismo de **visibilidade** de quem responde no WhatsApp (o que faltava, mais do que o disparo no grupo).
Agora, **toda mensagem recebida pelo webhook** (direta, não de grupo) é casada com o telefone de um responsável
(pai/mãe/resp. legal de aventureiro ativo não-demo). Ao casar, o sistema registra **a data da última mensagem**
daquela família e, se o texto bater com a **mensagem de autorização** configurada, marca a **autorização como
recebida**. Em **Mensalidades → Cobranças**, cada família ganhou um **termômetro visual** (verde = autorizado;
amarelo = já mandou msg, sem autorização; vermelho = nunca mandou) + "última mensagem há X".

### Onde configurar
Nova aba **✍️ Autorização** na tela WhatsApp: o Diretor define o **texto que o responsável deve enviar** para
contar como autorizado. A comparação ignora maiúsculas/minúsculas e acentos (equale ou contém).

### Arquivos alterados
- `core/models.py`: `PerfilUsuario.ultima_msg_whatsapp_em`/`autorizacao_recebida_em`;
  `WhatsappConfig.mensagem_autorizacao`.
- `core/views.py`: helpers `_familia_por_whatsapp` (casa telefone→família), `_registrar_contato_whatsapp`
  (grava última msg/autorização) e `_norm_comparacao`; o webhook chama o registro para mensagem direta;
  `_cobrancas_familias` expõe `ultima_msg_em`/`autorizou`; `whatsapp_autorizacao_config_view`; contexto da tela.
- `core/urls.py`: rota `whatsapp/autorizacao/`.
- `templates/core/whatsapp.html`: 4ª aba **Autorização** (texto padrão).
- `templates/core/mensalidades.html`: termômetro por família na aba Cobranças.
- `static/css/mensalidades.css`: estilo do termômetro.
- Migration **0049**.

### Decisões
- **Não** troca o número de destino automaticamente ao receber msg (o usuário ficou em dúvida) — só rastreia/
  mostra; a troca de telefone segue manual (seletor da aba Cobranças).
- Casamento por telefone normalizado (`normalizar_telefone`) contra os 3 números da família.

### Pendências / futuro
- Link/botão "enviar autorização" fácil (wa.me com texto pronto) para o responsável — combinado para depois.
- Disparo no grupo listando "quem falta" (a antiga Fase 3) — despriorizado pelo usuário.

---

## 2026-07-11 - WhatsApp: webhook de mensagens recebidas + últimas 5 (Fase 2)

### Resumo
**Fase 2** do módulo de liberação de números: nova aba **🔔 Webhook** na tela WhatsApp com (a) a **URL do webhook**
para cadastrar na W-API + botão **"Configurar webhook na W-API"** (chama `PUT /webhook/update-webhook-received`);
e (b) o painel **"Últimas 5 mensagens recebidas"** (atualiza sozinho a cada 5s), para **testar** que o webhook
está chegando. Endpoint público recebe as mensagens, faz parsing robusto e guarda o evento (com payload cru).

### Base (parser portado do BEEZAP)
- `core/wapi_parser.py` (novo): `parse_webhook_payload` extrai remetente/nome/texto/tipo/`fromMe`/`is_group`/
  `chat_id` de forma **muito defensiva** (vários caminhos + busca recursiva), pois o payload da W-API varia
  (W-API Lite/Baileys/grupos). Portado do projeto **BEEZAP** (testado em produção), com detecção de grupo e de
  status/transmissão (ignora Status/stories). Remetente vem de `sender.id`; texto de `message.conversation` etc.

### Arquivos criados/alterados
- `core/wapi_parser.py` (novo): parser do webhook.
- `core/models.py`: model **`WhatsappWebhookEvent`** (campos extraídos + `raw_payload` JSON + `recebido_em`).
- `core/views.py`: `whatsapp_webhook_view` (público, csrf_exempt, ignora status, guarda os 100 últimos),
  `whatsapp_webhook_eventos_view` (JSON dos últimos 5), `whatsapp_webhook_config_view` (registra a URL na W-API);
  `whatsapp_view` passa `webhook_url`.
- `core/urls.py`: `webhooks/whatsapp/` (público), `whatsapp/webhook/configurar/`, `whatsapp/webhook/eventos/`.
- `templates/core/whatsapp.html`: 3ª aba **Webhook** (URL + configurar + últimas 5).
- `static/js/whatsapp.js`: configurar webhook, copiar URL, polling das últimas 5 (5s enquanto a aba está aberta).
- `static/css/whatsapp.css`: lista de eventos.
- Migration **0048**.

### Pendências
- Confirmar o payload real com uma mensagem de verdade (é o objetivo do painel "últimas 5").
- **Fase 3**: usar o `phone` recebido para marcar o responsável como "liberado" (whitelist) e a campanha no grupo.

---

## 2026-07-11 - WhatsApp: abas Configurações/Grupos + listagem de grupos (Fase 1 do módulo de liberação)

### Resumo
Início do **módulo de liberação de números** do WhatsApp (resolver bloqueio por "spam" quando o clube inicia
conversa com quem só visualiza). **Fase 1**: a tela WhatsApp agora tem **duas abas** — **Configurações**
(instância + teste, como antes) e **Grupos**. Na aba Grupos, o botão "Atualizar lista" busca os grupos da conta
na W-API (`GET /v1/group/get-all-groups`) e mostra **nome + ID**, persistindo o vínculo (trabalha-se com o ID).

### Arquivos criados/alterados
- `core/wapi.py` (novo): cliente W-API via `urllib` — `listar_grupos` (parsing defensivo do payload),
  `dados_grupo` (group-metadata), `configurar_webhook_recebido` (para a Fase 2) e `enviar_texto` (número ou
  grupo `...@g.us`, para a Fase 3).
- `core/models.py`: model **`GrupoWhatsapp`** (group_id único ↔ nome/subject, tamanho, `usar_liberacao`).
- `core/views.py`: `whatsapp_view` com abas (`aba`); nova `whatsapp_grupos_sync_view` (upsert dos grupos, JSON).
- `core/urls.py`: rota `whatsapp/grupos/sincronizar/`.
- `templates/core/whatsapp.html`: abas Configurações/Grupos + lista de grupos.
- `static/js/whatsapp.js`: troca de abas + sincronização via AJAX.
- `static/css/whatsapp.css`: abas e lista de grupos.
- Migration **0047**.

### Notas / pendências
- A doc da W-API é SPA; o **formato exato do item de grupo** e o **payload do webhook de recebidas** não vieram
  100% autoritativos. O parser dos grupos é defensivo (aceita `id`/`groupId`/`jid`, `subject`/`name`, string pura).
  Testar na instância real (não há como testar a W-API localmente).
- **Fase 2** (próxima): webhook de mensagens recebidas — registrar o payload cru, confirmar o formato com uma
  mensagem real, e marcar o número do responsável como "liberado" (whitelist).
- **Fase 3**: campanha no grupo dos pais listando "quem falta" (postagem **manual + resumo**, escolha do usuário).

---

## 2026-07-11 - Cobranças: escolher o telefone do responsável financeiro por família

### Resumo
Na aba **Cobranças**, cada família com **2+ telefones** cadastrados (pai/mãe/responsável legal) agora tem um
**seletor** de para qual WhatsApp a cobrança vai — o do **responsável financeiro**. A escolha **persiste** (fica
como padrão até trocar de novo) e, ao trocar, aparece um **aviso** (toast "Telefone de cobrança alterado ✅"). Se
a família só tinha número em um responsável e nenhuma escolha definida, escolher aqui **habilita** o envio
(individual e em lote).

### Como funciona
- Campo **próprio e independente**: `PerfilUsuario.cobranca_whatsapp_origem` (pai/mãe/resp). É **separado** do
  `whatsapp_principal_origem` (usado no código de recuperação de senha), porque **quem tem o login pode não ser
  quem paga** — o responsável financeiro pode ter outro WhatsApp. Sem escolha → cai no responsável legal (padrão
  antigo preservado).
- Endpoint AJAX `mensalidades/cobrancas/telefone/` grava a origem; o envio resolve o número no servidor na hora.

### Arquivos alterados
- `core/models.py`: `PerfilUsuario.cobranca_whatsapp_origem` (novo campo).
- `core/views.py`: helper genérico `_resolver_origem_numero(numeros, escolhido)` (usado pela cobrança e pelo
  `_whatsapp_principal` da recuperação, cada um com o SEU campo); `_cobrancas_familias` expõe `numeros`/
  `origem_atual` a partir do campo de cobrança; nova view `mensalidade_cobranca_telefone_view`.
- `core/urls.py`: rota `mensalidades/cobrancas/telefone/`.
- `templates/core/mensalidades.html`: seletor de telefone no item da cobrança (quando há 2+ números).
- `static/js/mensalidade_cobranca.js`: troca via AJAX, toast de "alterado", habilita o envio, desfaz em erro.
- `static/css/mensalidades.css`: estilo do seletor.
- Migration **0046**.

### Decisões tomadas
- Telefone de cobrança em **campo próprio** (responsável financeiro), independente do WhatsApp principal/
  recuperação — o login e o pagador podem ser pessoas diferentes.

---

## 2026-07-11 - Cobrança pela IA: prompt padrão pede quebras de linha

### Resumo
A cobrança gerada pela IA chegava no WhatsApp como um **parágrafo único, sem quebras de linha**. Diagnóstico:
**não é bug do programa** — o texto do GPT passa só por `.strip()`, vai por JSON (que preserva `\n`) e o WhatsApp
renderiza `\n`; tanto que a mensagem padrão (com quebras no template) chega formatada. O problema é o **prompt**:
pedia mensagem "curta e objetiva" sem instruir estrutura, e o `gpt-4.1-nano` devolvia tudo em bloco. O prompt
padrão (`PROMPT_COBRANCA_IA_PADRAO`) passou a **instruir explicitamente as quebras de linha** (saudação, lista,
total, link e agradecimento em blocos separados por linha em branco).

### Observação
Prompts **já salvos** (`ConfigMensalidade.prompt_cobranca_ia`) não mudam com isso — é preciso reescrever/colar o
prompt atualizado na aba Cobranças para o efeito valer.

### Arquivos alterados
- `core/models.py`: `PROMPT_COBRANCA_IA_PADRAO` com bloco "FORMATO" pedindo quebras de linha reais.

---

## 2026-07-11 - VPS: sistema novo vira a raiz do domínio

### Resumo
Foi feita a virada do VPS para que **`https://pinhaljunior.com.br/`** passe a servir o **PINHALJUNIOR2.0**
(sistema novo). Antes, a raiz do domínio apontava para o sistema antigo (`sitepinhal`, porta 8000) e o novo
ficava só em **`/sistema-novo/`**. A troca foi feita no Nginx e no env de produção do novo, sem trocar código
do GitHub nesse passo. O sistema antigo foi **compactado, parado e desabilitado**; a rota legada
**`/sistema-novo/`** foi mantida temporariamente por compatibilidade.

### Arquivos e infraestrutura alterados
- `docs/DEPLOY_VPS.md`: atualizado para refletir a publicação na raiz do domínio e o arquivamento do sistema antigo.
- `docs/ESTADO_ATUAL.md`: registra a virada da raiz, o estado dos serviços e as validações do VPS.
- VPS `/etc/nginx/sites-available/sitepinhal`: raiz `/`, `/static/` e `/media/` passam a apontar para o sistema novo (`127.0.0.1:8010`).
- VPS `/etc/pinhaljunior2.env`: removido `DJANGO_FORCE_SCRIPT_NAME`; `DJANGO_STATIC_URL` e `DJANGO_MEDIA_URL` passaram para `/static/` e `/media/`.
- VPS `/srv/sitepinhal-archive/sitepinhal_20260711_221836.tar.gz`: arquivo compactado do sistema antigo.

### Decisões tomadas
- Manter `https://pinhaljunior.com.br/sistema-novo/` funcionando por enquanto, com rewrite para a raiz antes do proxy, para reduzir risco de link antigo quebrado.
- Não subir `origin/main` junto com a virada: a troca de domínio foi feita sobre o build do sistema novo já publicado no VPS, para diminuir risco operacional.
- Parar e desabilitar `sitepinhal.service` em vez de apagar diretórios, deixando rollback mais simples.

### Validações
- `manage.py check` no VPS: OK.
- `collectstatic --noinput`: OK.
- `nginx -t`: OK.
- HTTP 200 em `https://pinhaljunior.com.br/`, `/cadastro/`, `/recuperar-senha/`, `/static/css/login.css` e `/sistema-novo/`.
- `pinhaljunior2.service`: ativo.
- `sitepinhal.service`: inativo e desabilitado.

### Pendências
- Revisar depois se ainda vale manter a rota legada `/sistema-novo/` ou se já pode redirecionar/remover.
- Mercado Pago no VPS continua em **modo teste**; antes de cobrança real, virar para produção e validar webhook/credenciais.

## 2026-07-11 - Cobrança de mensalidades pela IA (1º uso do GPT no sistema)

### Resumo
Primeiro ponto de uso do módulo **Configurações IA**: na aba **Cobranças** de Mensalidades, o Diretor/Tesoureiro
agora pode escolher **como** a cobrança é enviada por WhatsApp — pela **mensagem padrão** (template de sempre) ou
**pela IA** (o GPT redige uma mensagem personalizada por família). Uma **alavanca** (switch) na barra de cobranças
alterna os dois modos e persiste na hora; abaixo há um **prompt editável** que é enviado ao GPT. Ao enviar
(individual ou em lote), quando o modo IA está ligado, o sistema monta o prompt com os dados da família, pede a
mensagem ao GPT e envia o texto retornado. Os tokens consumidos entram no contador de Configurações IA.

### Como funciona
- O prompt usa os **mesmos marcadores** da mensagem padrão (`{nome}`/`{itens}`/`{total}`/`{link}`), já
  preenchidos por família antes de ir ao GPT (reaproveita `_montar_mensagem_cobranca`).
- Se o modo IA estiver **ligado mas a IA não configurada**, o envio é barrado com aviso claro (configurar em
  Configurações IA ou voltar ao padrão) — e a tela já mostra um alerta preventivo.
- Se a IA **falhar** para uma família específica no lote, ela entra em "falhas" (não é enviada) — o Tesoureiro vê.

### Arquivos alterados
- `core/models.py`: `ConfigMensalidade` ganhou `cobranca_via_ia` (bool, a alavanca) e `prompt_cobranca_ia`
  (texto); constante `PROMPT_COBRANCA_IA_PADRAO` (prompt padrão: tesoureiro educado, mensagem curta e objetiva).
- `core/views.py`: `mensalidade_cobranca_config_view` salva o prompt; nova `mensalidade_cobranca_modo_view`
  (liga/desliga a alavanca via AJAX); helper `_gerar_cobranca_ia` (monta o prompt + chama o GPT + conta tokens);
  `mensalidade_cobranca_enviar_view` ramifica padrão × IA; contexto da tela passa prompt/flag/`ia_configurada`.
- `core/urls.py`: rota `mensalidades/cobrancas/modo/`.
- `templates/core/mensalidades.html`: prompt da IA no form de mensagens + card da alavanca (switch) + aviso.
- `static/js/mensalidade_cobranca.js`: alavanca persiste ao trocar e atualiza o texto/aviso.
- `static/css/mensalidades.css`: switch e card de modo.
- Migration **0045**.

### Decisões tomadas
- A alavanca é uma configuração persistida (`ConfigMensalidade.cobranca_via_ia`), lida no servidor no ato do envio.
- IA por família = 1 chamada ao GPT por envio (mais lento que o padrão, mas personalizado); tokens contabilizados.

### Pendências
- Próximos pontos de uso da IA no sistema (a definir).

---

## 2026-07-11 - Configurações IA: modelo fixo + contador de tokens + sem URL base

### Resumo
Ajustes na tela **Configurações IA**: (1) o **modelo agora é fixo** — `gpt-4.1-nano` (o mais barato) —, sem
campo para trocar; (2) a **URL base deixou de ser configurável** (constante no cliente); (3) novo card
**"Consumo de tokens"** que acumula o gasto de todas as chamadas à IA: nº de chamadas, tokens de **entrada**
(total), destes **em cache** e **fora do cache**, tokens de **saída** e **total**, com botão **"Zerar contador"**.
O contador atualiza ao vivo após cada teste (sem recarregar).

### Arquivos alterados
- `core/openai_ia.py`: `MODELO`/`BASE_URL` viraram **constantes** (modelo `gpt-4.1-nano`); `conversar`/
  `enviar_prompt` passam a devolver `(ok, texto, uso)` — `uso` traz `prompt`/`cache`/`completion`/`total`
  (cache lido de `usage.prompt_tokens_details.cached_tokens`).
- `core/models.py` (`OpenAIConfig`): removidos os campos `modelo` e `base_url`; adicionados os contadores
  `chamadas`/`tokens_prompt`/`tokens_cache`/`tokens_completion`; props `tokens_prompt_sem_cache`/`tokens_total`;
  métodos `registrar_uso(uso)` (acumula com `F()`, seguro em concorrência) e `zerar_uso()`.
- `core/views.py`: `ia_config_view` salva só a chave; `ia_testar_view` contabiliza o uso e devolve o acumulado;
  `ia_view` passa o modelo fixo; nova `ia_zerar_view`.
- `core/urls.py`: rota `ia/zerar/`.
- `templates/core/ia.html`: modelo mostrado como fixo, campos de modelo/URL base removidos, card "Consumo de
  tokens" + botão zerar.
- `static/js/ia.js`: atualiza o contador ao vivo após cada teste.
- `static/css/whatsapp.css`: grade `.ia-tokens`.
- Migration **0044** (remove `modelo`/`base_url`, adiciona os contadores).

### Decisões tomadas
- Modelo fixo **`gpt-4.1-nano`** (escolhido pelo usuário como o mais barato); mudar é trocar a constante `MODELO`.
- Contagem de cache = subconjunto da entrada (`cached_tokens`), exibida separada de "fora do cache".

---

## 2026-07-11 - Módulo "Configurações IA" (API do GPT / OpenAI)

### Resumo
Novo módulo **Configurações IA** (🤖, só Diretor) no mesmo padrão do WhatsApp/Mercado Pago: um singleton de
configuração + tela para guardar a **chave da API do GPT** (OpenAI), escolher o **modelo** e a URL base, mais um
campo para **enviar um teste** e ver a resposta da IA na própria tela. A chave é exibida só com os últimos
dígitos (mascarada) e só é trocada se uma nova for digitada. Cliente HTTP via `urllib` (sem dependência nova).
Esta é a **base** — onde a IA vai ser aplicada dentro do sistema será definido depois.

### Arquivos criados/alterados
- `core/models.py`: model **`OpenAIConfig`** (singleton `get_solo`: `api_key`, `modelo` [padrão `gpt-4o-mini`],
  `base_url` [padrão `https://api.openai.com/v1`], `atualizado_por/_em`); props `configurado`, `modelo_efetivo`,
  `api_key_mascarada`.
- `core/openai_ia.py` (novo): cliente da API de Chat Completions via `urllib` — `conversar(config, mensagens)`
  (reaproveitável) e o atalho `enviar_prompt(config, prompt)`; devolve `(ok, texto|erro)` com erros amigáveis.
- `core/views.py`: `ia_view` (tela), `ia_config_view` (POST salvar), `ia_testar_view` (POST → JSON com a
  resposta); import de `OpenAIConfig` e do módulo `openai_ia`.
- `core/urls.py`: rotas `ia/`, `ia/config/`, `ia/testar/`.
- `core/menus.py`: item de menu `ia` ("Configurações IA", 🤖) — Diretor vê tudo, então já aparece só pra ele.
- `templates/core/ia.html` (novo): card de configuração (badge ✓ Configurado/Não configurado + chave mascarada)
  + card de teste com a caixa de resposta.
- `static/js/ia.js` (novo): mostrar/ocultar chave + envio de teste via AJAX com toast e resposta na tela.
- `static/css/whatsapp.css`: estilos da caixa `.ia-resposta` (reaproveita a folha, já carregada pela tela).
- Migration **0043** (`OpenAIConfig`).

### Decisões tomadas
- Mesmo molde dos gateways existentes (singleton + `urllib`, sem dependência nova) — regra do projeto.
- `modelo` é um campo **editável** (padrão `gpt-4o-mini`) para o Diretor apontar o modelo que tiver acesso.
- Chave nunca reenviada ao navegador; exibida só mascarada.

### Pendências
- Definir **onde** a IA será usada no sistema (o usuário vai explicar) — este módulo é só a configuração base.

---

## 2026-07-11 - Mercado Pago: sinal visível de "credenciais salvas"

### Resumo
Na tela `/mercadopago/` (só Diretor), cada par de credenciais — **Teste** e **Produção** — ganhou um
**badge no cabeçalho** ("✓ Configurado" / "Não configurado"), no mesmo padrão do card de Modo. Além disso, os
campos que guardam segredo (Access Token e Assinatura do webhook, de teste e de produção) agora mostram os
**últimos 4 dígitos** do valor salvo (ex.: `••••••1234`), como já fazia a assinatura do webhook de teste.
Assim dá pra confirmar, batendo o olho, que as credenciais estão gravadas — sem precisar colar de novo. Nada
é exposto por inteiro e nenhum segredo é reenviado ao navegador.

### Arquivos alterados
- `core/models.py` (`MercadoPagoConfig`): propriedades novas `teste_configurado`/`prod_configurado` (bool pelo
  access token do par) e mascaradas `access_token_teste_mascarado`/`access_token_prod_mascarado`/
  `webhook_secret_teste_mascarado`/`webhook_secret_prod_mascarado` (reusam `_mascarar_segredo`).
- `templates/core/mercadopago.html`: badge de status em cada card (Teste/Produção) e troca do texto "Salvo
  (oculto por segurança)" por "Atual: **••••••1234** (salvo)" nos campos de segredo.

### Decisões tomadas
- Sinal de "configurado" = ter o **Access Token** do par (é a credencial obrigatória para cobrar).
- Sem migration: só propriedades derivadas, nenhum campo novo no banco.

### Pendências
- Operacionais (inalteradas): cadastrar a URL do webhook + secret no painel do MP e confirmar a taxa real em
  produção com um pagamento de verdade.

---

## 2026-07-11 - Revisão geral dos pagamentos (cartão) + fix do pagamento recusado

### Resumo
Revisão dos pagamentos (Pix e **cartão/Checkout Pro**) nas 3 áreas — **loja**, **mensalidades** e **eventos**.
Conclusão: a engine está consistente (cartão disponível nos 6 pontos: lojinha de evento, inscrição, Loja do
Clube, mensalidades do Diretor, mensalidades do responsável e acerto público; gross-up da taxa correto;
webhook valida assinatura e usa o MP como fonte da verdade; página genérica trata cartão com "confirmando +
polling"). **Corrigido um problema:** quando o cartão (ou Pix) era **recusado/cancelado**, a página de
pagamento ficava **girando para sempre** — o polling só reagia a "aprovado". Agora, em `rejeitado`/`cancelado`,
a tela para o spinner, mostra um aviso de **recusa** e um botão **"Voltar e tentar de novo"** (destino por tipo:
mensalidades/loja/página do evento/início).

### Arquivos alterados
- `static/js/pagamento_mp.js`: trata `rejeitado`/`cancelado` no polling (mostra recusa, para o spinner, toast).
- `templates/core/pagamento.html`: bloco `#pixRejeitado` (aviso de recusa + voltar).
- `core/views.py` (`pagamento_view`): novo `voltar_url` por tipo de pagamento.
- `core/tests.py`: teste `test_pagamento_rejeitado_mostra_recusa_sem_redirecionar`.

### Pendências (operacionais — do lado do usuário, não código)
- Cadastrar a **URL do webhook** + a **secret** no painel do Mercado Pago (produção) e confirmar a **taxa real**
  do cartão com uma venda de produção (ajustar `taxa_cartao_pct` se o "termômetro" na tela do MP ficar > 0).
- Deixar o parcelamento como **"Parcelado comprador"** no painel do MP (juros por conta do comprador).

---

## 2026-07-11 - Validação do cadastro usa o toast padrão do sistema

### Resumo
Ao clicar "Próximo"/"Finalizar" com campos obrigatórios vazios, o aviso agora é o **toast clássico** do
sistema (`window.mostrarToast`), com **uma notificação só** listando o(s) campo(s) que faltam (ex.:
"Preencha os campos obrigatórios: Usuário, Senha, Confirmar senha"; acima de 4, resume com "e mais N").
Removida a caixa `#avisoValidacao`.

### Arquivos alterados
- `static/js/wizard_validacao.js`: `mostrarAviso` monta uma mensagem e chama `window.mostrarToast(msg, "error")`.
- `templates/core/cadastro.html` e `cadastro_diretoria.html`: carregam `inicio.js` (expõe `mostrarToast`;
  CSS do toast já está em `base.css`) e removem a caixa de aviso.

---

## 2026-07-11 - Ajustes na ficha médica e no visual do Sim/Não

### Resumo
Refinamentos após revisão:
- **Doenças e Deficiência física:** a lista agora fica **sempre visível** (antes só aparecia depois do "Sim",
  e a pessoa não via as opções). Viraram o padrão das classes: mostra a lista + opção **"Nenhuma"** e exige
  ao menos uma marcação (doença/deficiência OU "Nenhuma"). Removidos os gates `teve_doencas`/`tem_deficiencia`.
- **Número da Carteira do SUS:** agora **obrigatório**.
- **Sim/Não:** deixado **menor** (padrão de todos os cadastros), sem o "quadrado azul" de foco ao clicar do
  mouse (mantido no teclado via `:focus-visible`), com destaque discreto da opção escolhida (`:has(input:checked)`).
- **Tipo sanguíneo:** confirmado que "Não sabe" já é uma das opções.

### Arquivos alterados
- `core/forms.py`: `FichaMedicaCamposMixin` — `sem_doencas`/`sem_deficiencia` (em vez dos gates), `cartao_sus`
  obrigatório, `clean()` exige ao menos uma marcação.
- `templates/core/_ficha_medica_campos.html`: listas visíveis + "Nenhuma".
- `static/css/cadastro.css`: `.simnao-opcao` menor + foco/checked ajustados.

---

## 2026-07-11 - Cadastros: obrigatoriedade dos campos + Sim/Não + validação com aviso

### Resumo
Revisão da obrigatoriedade dos campos nos dois cadastros (diretoria e aventureiro), com asterisco automático,
perguntas **Sim/Não obrigatórias** e **aviso listando os campos que faltam** ao tentar avançar/finalizar.
- **Ficha médica (ambos):** cada pergunta virou **Sim/Não obrigatório**; o detalhe ("qual/medicamentos") só é
  exigido quando "Sim". As listas de doenças e de deficiência ganharam um Sim/Não obrigatório na frente
  (`teve_doencas`/`tem_deficiencia`); se "Sim", exige marcar ao menos um; tipo sanguíneo obrigatório.
- **Diretoria:** obrigatórios foto, nacionalidade, data nasc., igreja, distrito, RG, estado civil, e-mail,
  endereço completo e escolaridade; "Tem filhos?" Sim/Não (+ qtd se Sim); cônjuge obrigatório se casado/união.
- **Aventureiro:** obrigatórios foto, sexo, data nasc., colégio/série/ano, tamanho da camiseta, endereço
  completo, grau de parentesco e e-mail do responsável; **Bolsa Família** vira Sim/Não; **classes** com opção
  **"Nenhuma"** (exige ao menos uma marcação); **pai/mãe** com "Tem os dados? Sim/Não" (se Sim, todos os campos
  daquele responsável obrigatórios); termo de imagem exige nacionalidade do menor e nacionalidade/estado civil/
  RG do responsável. Cidade da inscrição segue opcional.
- **Reaproveitamento:** o termo de imagem agora é **pré-preenchido** com os dados já digitados (nome do menor,
  nome/CPF/endereço do responsável) — sem redigitar.

### Arquivos criados/alterados
- `core/forms.py`: helper `campo_sim_nao` + `FichaMedicaCamposMixin` (compartilhado pelas duas fichas);
  obrigatórios e `clean()` condicionais em `MembroDiretoriaForm`, `AventureiroForm`, `AutorizacaoImagemForm`.
- Templates: `_campo_simnao.html` (novo), `_ficha_medica_campos.html` (novo, corpo da ficha compartilhado),
  ajustes em `cadastro.html` e `cadastro_diretoria.html` (caixa `#avisoValidacao`, Sim/Não, classes, pai/mãe).
- Estáticos: `static/js/wizard_validacao.js` (novo, valida e lista faltantes), `cadastro.js` e
  `cadastro_diretoria.js` (condicionais por grupo de radios `data-depende-nome`, validação por etapa/envio,
  reaproveitamento do termo de imagem); estilos `.campo-simnao`/`.simnao-*` em `cadastro.css`.
- Removido `_campo_check_livre.html` (não usado). **Sem migration** (obrigatoriedade é no form).

### Decisões (confirmadas com o Fabiano)
- Ficha médica "tudo com Sim/Não"; pai/mãe "todos os campos" quando tem os dados; "endereço completo";
  classes com opção "Nenhuma". Foto obrigatória (atenção: em erro de servidor o arquivo precisa ser
  reanexado — a validação no cliente evita isso na maioria dos casos).

---

## 2026-07-11 - Comandos de migração: diretoria + assinaturas antigas

### Resumo
Dois comandos de importação (rodam **localmente**, lendo o ZIP de exportação git-ignored; depois db/media
sincronizam para o VPS). Ambos idempotentes e com `--dry-run`.
- **`importar_diretoria`**: cria `MembroDiretoria` (+ `FichaMedicaDiretoria` + foto) por integrante, vincula ao
  perfil **Diretoria** e trata as **mesclagens** (quem tem diretoria e responsável em logins diferentes é
  anexado ao login que tem o aventureiro → 1 login com 2 perfis). Cria o `User` (preservando username + hash da
  senha) para os só-diretoria que ainda não existiam. Pula teste e Fabiano.
- **`importar_assinaturas`**: importa as assinaturas desenhadas antigas casando **por CPF**:
  `aventureiroficha` → `AssinaturaDocumento` (inscrição/declaração médica/imagem);
  `diretoriaficha` → `AssinaturaDocumentoDiretoria` (compromisso/imagem + **declaração médica = cópia do
  compromisso**, pois o antigo não tinha). As imagens vêm dos arquivos de assinatura do ZIP.

### Resultado local (validado)
- Diretoria: **10 membros** (6 logins novos criados; 3 mesclagens; Lediani no login dela); 10 fotos, 10 fichas.
- Assinaturas: **96** de aventureiro (32 fichas × 3) e **21** de diretoria (7 × 3). Cobertura: 32/46
  aventureiros e 7/10 membros (os demais não tinham ficha assinada no antigo).

### Arquivos criados/alterados
- `core/management/commands/importar_diretoria.py`, `core/management/commands/importar_assinaturas.py`.
- `.gitignore`: ignora `migracao_mesclagem.json` (config local com logins reais — não versionar).

### Decisões
- A config de **skip/mesclagem** (com logins/nomes reais) fica em `migracao_mesclagem.json` **local**
  (git-ignored); o comando é genérico. Sem o arquivo, só pula o registro de teste e não faz mesclagens.
- Migração roda local; o db/media resultantes é que vão para o VPS (padrão já usado no projeto).

---

## 2026-07-11 - Levantamento da migração da diretoria (doc local)

### Resumo
Análise **somente leitura** dos dados do sistema antigo (zip de exportação) para planejar a migração da
diretoria: quem é diretoria, quem é só-diretoria e quem tem duas contas (diretoria + responsável) e precisa
de **mesclagem** (um login com 2 perfis). Resultado registrado em `docs/MIGRACAO_DIRETORIA.md`.

### Arquivos alterados
- `docs/MIGRACAO_DIRETORIA.md`: **novo, mantido LOCAL** (contém nomes/logins reais da diretoria).
- `.gitignore`: ignora `docs/MIGRACAO_DIRETORIA.md` (não versionar dados pessoais).

### Decisões
- Não versionar o levantamento (privacidade). Nenhum dado/código alterado — só análise + doc local.

### Atualização (mesmo dia)
- Investigado o **formato das assinaturas antigas** (só leitura): NÃO foram migradas; existem no export como
  base64 por documento em `aventureiroficha`/`diretoriaficha` (batem 1:1 com o novo) + arquivos PNG únicos.
  Mapeamento para `AssinaturaDocumento`/`AssinaturaDocumentoDiretoria` registrado no doc local.
- Decisão: aventureiro tem 3 assinaturas (inscrição, declaração médica, imagem) — a ficha médica entra sob a
  declaração médica. Diretoria (antigo) só tinha 2 (compromisso + imagem) → na migração, a declaração médica
  da diretoria recebe uma **cópia** da assinatura do compromisso, para ficar com as 3.

---

## 2026-07-11 - Diretor atribui o papel dos integrantes da diretoria

### Resumo
Nova tela (Diretor) para **atribuir o papel** de cada integrante da diretoria: Diretor, Secretário,
Tesoureiro, Professor ou "Diretoria (sem papel definido)". A atribuição ajusta os **grupos** do usuário
(remove os demais papéis e aplica o escolhido), então o perfil/menu passa a refletir o papel. Acessível por
um botão **"Gerenciar diretoria (papéis)"** na tela Usuários.

### Arquivos alterados
- `core/views.py`: `diretoria_equipe_view` (lista) e `diretoria_papel_view` (POST); constantes
  `PAPEIS_DIRETORIA_OPCOES`/`GRUPOS_PAPEL_DIRETORIA` e helper `_papel_atual_diretoria`.
- `core/urls.py`: `usuarios/diretoria/` e `usuarios/diretoria/<id>/papel/`.
- `templates/core/diretoria_equipe.html`: nova tela (lista + seletor de papel por integrante).
- `templates/core/usuarios.html`: botão "Gerenciar diretoria (papéis)".

### Decisões tomadas
- O papel é guardado como **grupo** do Django (fonte da verdade dos perfis). Atribuir um papel específico
  **remove** o grupo genérico "Diretoria" e os demais papéis, deixando só o escolhido.
- Atenção: atribuir "Diretor" concede acesso total (é o propósito do controle).

### Pendências
- Módulo de permissões por botão (fino) segue como futuro; hoje o acesso é por perfil.

---

## 2026-07-11 - "Meus Dados" mostra os dados do membro da diretoria

### Resumo
Quando um voluntário/integrante da diretoria (ex.: Secretário) acessa "Meus Dados", agora aparece um
**card "Diretoria"** com os dados do cadastro dele: identificação (nome, nacionalidade, CPF, RG, nascimento,
estado civil, cônjuge, filhos, igreja, distrito, escolaridade), contato, endereço e um resumo da ficha
médica. Mostra também o **papel** (Diretor/Secretário/Tesoureiro/Professor ou "Diretoria (papel a definir)").

### Arquivos alterados
- `core/views.py`: `inicio_view` carrega o `MembroDiretoria` do usuário (foto/idade/iniciais + `_preparar_ficha`)
  e o papel via novo helper `_papel_diretoria`; contexto `membro_diretoria`.
- `templates/core/inicio.html`: card "Diretoria" (painel expansível), entre o card do responsável e a lista
  de aventureiros.
- `static/css/inicio.css`: `.resp-avatar-img` (foto redonda) e `.painel-corpo .bloco-rotulo`.

### Pendências
- Próximo: UI do Diretor para atribuir o papel específico da diretoria.

---

## 2026-07-11 - Diretoria: assinatura desenhada dos 3 documentos (substitui os checkboxes)

### Resumo
No cadastro de diretoria, os aceites por checkbox (compromisso de voluntário, declaração médica e
autorização de imagem) viraram **assinatura desenhada** (dedo/mouse), no mesmo padrão do cadastro de
aventureiro. Cada documento tem a sua assinatura própria, gravada como imagem PNG + snapshot do texto do
termo preenchido. Responsividade mobile verificada (Chrome headless, 490px): etapa de Termos e modal de
assinatura OK. Corrigido, de quebra, um bug cosmético do preview de assinatura (imagem quebrada no estado
vazio) que afetava também o cadastro de aventureiro.

### Arquivos alterados
- `core/models.py`: `AssinaturaDocumentoBase` (molde abstrato) + `AssinaturaDocumento` (aventureiro, refatorado
  para herdar da base, tabela inalterada) + novo `AssinaturaDocumentoDiretoria` (membro + documento).
- `core/migrations/0042_...`: cria AssinaturaDocumentoDiretoria.
- `core/termos.py`: textos dos 3 documentos da diretoria (`montar_texto_diretoria`) — compromisso, declaração
  médica e autorização de imagem do adulto.
- `core/views.py`: `cadastro_diretoria_view` valida e grava as 3 assinaturas (`_validar_aceites_diretoria`
  agora exige assinatura; `_salvar_assinaturas_diretoria`); reusa `_decode_signature`.
- `core/admin.py`: registra `AssinaturaDocumentoDiretoria`.
- `templates/core/cadastro_diretoria.html`: blocos `_assinatura_doc.html` + modal de assinatura + `assinatura.js`.
- `static/js/cadastro_diretoria.js`: validação por assinatura (não mais checkbox) + revisão "Assinado".
- `static/css/cadastro.css`: `.assinatura-doc-preview img[hidden] { display:none }` (fix da imagem quebrada).
- Removido `templates/core/_campo_check_livre.html` (não é mais usado).

### Pendências
- Próximos: exibir o membro da diretoria em "Meus Dados"/"Usuários" e a UI do Diretor para atribuir o papel.

---

## 2026-07-11 - .gitignore: ignora PDFs soltos na raiz

### Resumo
Adiciona `/*.pdf` ao `.gitignore` para não versionar documentos de referência escaneados soltos na raiz
(ex.: `Fichas-Secretaria-Padrão (1).pdf`), seguindo a regra de "arquivos soltos na raiz não são versionados".

### Arquivos alterados
- `.gitignore`: novo padrão `/*.pdf` (PDFs no diretório-raiz).

---

## 2026-07-11 - Cadastro de Diretoria (Compromisso para Voluntários) + tela de escolha + 2 perfis

### Resumo
Implementado o **cadastro de diretoria** (voluntários), o novo ponto de entrada do "Cadastre-se"
(escolha de tipo) e a **alternância de 2 perfis** (Diretoria + Responsável). Fluxos:
- **Tela "Cadastre-se"** (`/cadastro/`) agora oferece **3 opções**: Aventureiro, Diretoria,
  Diretoria + Aventureiro. (Antes ia direto ao cadastro de aventureiro.)
- **Cadastro de diretoria** (`/cadastro/diretoria/`): wizard com Conta, Identificação (com cônjuge
  condicional ao estado civil e qtd. de filhos), Contato/Endereço, **ficha médica completa** (igual à do
  aventureiro), Escolaridade e **3 termos** (compromisso de voluntário, declaração médica e **autorização
  de imagem do adulto**, adaptada da versão do menor). Cria a conta + `MembroDiretoria` + `FichaMedicaDiretoria`,
  adiciona ao perfil **Diretoria** e loga.
- **Diretoria + Aventureiro** (`?com_aventureiro=1`): após a diretoria, emenda no cadastro de aventureiro
  (pré-preenchendo o responsável com os dados da diretoria) → 1 login com **2 perfis**.

### Arquivos criados/alterados
- `core/models.py`: `FichaMedicaBase` (abstract, campos médicos compartilhados); `FichaMedica` passa a herdar
  dela (tabela inalterada); novos `MembroDiretoria` e `FichaMedicaDiretoria`; choices `ESTADO_CIVIL`/`ESCOLARIDADE`.
- `core/migrations/0041_...`: cria MembroDiretoria e FichaMedicaDiretoria (FichaMedica intacta).
- `core/menus.py`: novo perfil **Diretoria** (ORDEM/ícone/acesso); `perfil_do_usuario`/`perfis_do_usuario`
  ajustados — "Responsável" é **implícito** (quem tem aventureiro não-demo) e convive com "Diretoria"
  (habilita a alternância). `configurar_perfis` cria o grupo "Diretoria".
- `core/forms.py`: `MembroDiretoriaForm` e `FichaMedicaDiretoriaForm`.
- `core/views.py`: `cadastro_view` vira a **tela de escolha**; `cadastro_aventureiro_view` (fluxo antigo);
  `cadastro_diretoria_view` (+ `_validar_aceites_diretoria`); prefill do responsável a partir da diretoria
  (`_dados_diretoria_para_responsavel`/`_dados_anteriores_ou_diretoria`); `cadastro_sucesso_view` com `tipo`.
- `core/urls.py`: rotas `cadastro_aventureiro` e `cadastro_diretoria`.
- `core/admin.py`: registra `MembroDiretoria` e `FichaMedicaDiretoria`.
- Templates: `cadastro_escolha.html`, `cadastro_diretoria.html`, `_campo_check_livre.html`,
  `cadastro_sucesso.html` (variante diretoria). Estáticos: `static/js/cadastro_diretoria.js`,
  estilos `.escolha-*` em `static/css/cadastro.css`.

### Decisões tomadas
- Ficha médica da diretoria = **completa** (reusa o molde abstrato, sem duplicar campos).
- Papel específico (Diretor/Secretário/Tesoureiro/Professor) **não** é escolhido no cadastro — a pessoa entra
  como "Diretoria" genérica e o Diretor define depois (a UI de atribuição fica para o próximo passo).
- Assinatura desenhada dos termos fica para depois; por ora, **aceite por checkbox** com o texto do termo.
- Textos dos termos = fiéis ao PDF oficial DSA: o "Compromisso para Voluntários" é o formulário + um aceite
  curto; a autorização de imagem é a da pág. 5 adaptada para maior de idade.

### Pendências
- **Próximo passo:** exibir os dados do membro da diretoria em "Meus Dados"/"Usuários" e a **UI do Diretor
  para atribuir o papel** específico. Assinatura desenhada dos termos da diretoria. Substituir o texto do
  compromisso pelo oficial, se/quando o clube fornecer um texto de juramento formal.

---

## 2026-07-11 - Ficha médica: 6 doenças e bloco de deficiência física (alinha ao formulário oficial DSA)

### Resumo
Completa a **Ficha Médica** para bater com o formulário oficial da DSA (PDF `Fichas-Secretaria-Padrão`).
Adicionadas as **6 doenças** que faltavam na lista "Já teve ou tem" — **Varíola, Coqueluche, Difteria,
Caxumba, Rinite e Bronquite** — e um **bloco novo "Deficiência física"** (Cadeirante, Visual, Auditiva e
Fala/mudez), que não existia. O telefone fixo de pai/mãe do formulário oficial foi deliberadamente deixado
de fora (decisão do Fabiano).

### Arquivos criados/alterados
- `core/models.py`: `FichaMedica` ganhou 6 BooleanField de doença (após `tetano`) e 4 BooleanField de
  deficiência física (`deficiente_cadeirante/_visual/_auditivo/_fala`, após as alergias).
- `core/migrations/0040_...`: migration dos 10 campos novos (todos `default=False`).
- `core/views.py` (`_preparar_ficha`): as 6 doenças entram em `doencas_lista`; nova `deficiencias_lista`
  para exibição.
- `templates/core/cadastro.html`: 6 checkboxes novos na etapa da ficha médica + bloco "Deficiência física".
- `templates/core/_aventureiro_detalhe.html`: linha "Deficiência física" na seção Ficha médica
  (usada em "Meus Dados" e no modal de Usuários).

### Decisões tomadas
- `FichaMedicaForm` usa `exclude=["aventureiro"]`, então os campos novos entram no form automaticamente
  (sem alterar o form). Admin idem (só `list_display`).
- Campos `default=False` → `criar_dados_teste`/`importar_migracao` não precisam mudar.
- Telefone fixo de pai/mãe **não** foi adicionado (fora do escopo pedido).

### Pendências
- Próximo passo combinado: iniciar o **cadastro de diretoria** (ficha "Compromisso para Voluntários",
  pág. 7 do PDF oficial). Especialidades (págs. 8-10) seguem sem módulo.

---

## 2026-07-07 - Perfil Responsável: Loja, Mensalidades e Presença próprias + registro central de menu

### Resumo
Início do trabalho nos **perfis**. Criado o **registro central de menu/acesso por perfil**
(`core/menus.py`) — fonte única da verdade de "quem vê/acessa o quê", pronta para o futuro módulo de
permissões encaixar sem reescrever menu nem views. O menu (`_menu.html`) deixou de ser chumbado
(`{% if is_diretor %}`) e passa a **iterar `menu_itens`** (vindo do context processor). O **perfil
Responsável** ganhou telas próprias, separadas das do Diretor, na **mesma URL** (a view ramifica por
perfil):
- **Loja** (`loja_view`): só a **vitrine** (comprar) + aba **"Meus pedidos"** (acompanhar). Sem
  Gerenciar/Vendas. Vitrine extraída para o parcial `_loja_vitrine.html` (reusado pelo Diretor e pelo
  responsável). Pagamento igual (Pix/cartão).
- **Mensalidades** (`mensalidades_view`): **resumo** (pago no ano × em aberto), lista das **em aberto
  vencidas** (mês atual + atrasados) para **selecionar e pagar** (uma cobrança Pix/cartão via
  `minhas_mensalidades_pagar`), botão **"adiantar meses"** (`?frente=1` mostra os futuros) e **texto de
  apelo** configurável pelo Diretor.
- **Presença** (`presenca_view`): **relatório só-leitura** dos próprios filhos — por criança, em quantos
  eventos com chamada esteve/faltou e em quais (o responsável **não marca** presença).

O Diretor ganhou, na aba **Cobranças**, um 2º campo: a **mensagem de apelo** (`ConfigMensalidade.mensagem_apelo`,
migration **0038**), exibida ao responsável na tela de Mensalidades dele.

### Arquivos criados/alterados
- `core/menus.py` (novo): `ITENS_MENU`, `ACESSO_PADRAO`, `perfil_do_usuario`, `itens_menu_para`,
  `pode_acessar`. Comentário marca o "encaixe" do futuro módulo de permissões (`_ids_liberados`).
- `core/context_processors.py`: expõe `menu_itens` e `perfil_atual`.
- `templates/core/_menu.html`: itera `menu_itens` (mantém o caso do operador externo e "Operar (PDV)").
- `core/models.py`: `ConfigMensalidade.mensagem_apelo` + `MENSAGEM_APELO_PADRAO`.
- `core/migrations/0038_configmensalidade_mensagem_apelo.py` (novo).
- `core/views.py`: `loja_view`/`mensalidades_view`/`presenca_view` passam a `@login_required` e ramificam
  por perfil; helpers `_loja_responsavel`, `_mensalidades_responsavel`, `_mensalidades_familia_abertas`,
  `_presenca_responsavel`; view `minhas_mensalidades_pagar_view`; `mensalidade_cobranca_config_view`
  salva também a mensagem de apelo.
- `core/urls.py`: rota `mensalidades/pagar-selecionadas/` (`minhas_mensalidades_pagar`).
- Templates novos: `_loja_vitrine.html`, `loja_responsavel.html`, `mensalidades_responsavel.html`,
  `presenca_responsavel.html`. `mensalidades.html`: 2ª textarea (apelo) na aba Cobranças.
- CSS: blocos do responsável em `static/css/mensalidades.css` e `static/css/presenca.css`.
- `core/tests.py`: `PerfilResponsavelTests` (menu por perfil, loja/mensalidades/presença do responsável,
  pagamento escopo-família e bloqueio de família alheia, responsável não marca presença) + apelo salvo.

### Decisões tomadas
- **Mesma URL, view ramifica por perfil** (uma entrada de menu por item), em vez de URLs separadas —
  menu simples e consistente.
- Gating por perfil resolvido em **um único lugar** (`core/menus.py`); o Diretor continua vendo tudo.
- Segurança do pagamento: `minhas_mensalidades_pagar` filtra por `aventureiro__usuario=request.user` —
  ninguém paga mensalidade de outra família.
- Presença do responsável é **só-leitura** (a tela do Diretor, que marca qualquer criança, segue só dele).

### Pendências
- Módulo de permissões (liga/desliga por perfil/usuário) — encaixa em `core/menus.py` sem reescrever.
- Demais perfis (Professor, Tesoureiro, Secretário) ainda sem telas.

---

## 2026-07-07 - Seletor de perfil vira cartão do usuário no topo do menu

### Resumo
A pedido, o seletor de perfil saiu da lista do menu e virou o **cartão do usuário no topo** (logo abaixo do
título "Clube de Aventureiros Pinhal Júnior"): mostra o **nome** + o **perfil selecionado** (chip verde) e,
quando o usuário tem 2+ perfis, é um **dropdown** (`<details>` nativo) que abre a lista para trocar de perfil.
O **nome do usuário foi removido do rodapé** (lá ficou só o botão Sair + copyright). Ocupa menos espaço no menu
e deixa claro "em que perfil estou".

### Arquivos alterados
- `templates/core/_menu.html`: cartão `perfil-box` (dropdown `<details>` quando `perfis_disponiveis`, senão
  estático) no topo; removida a seção "Ver como" que ficava no fim.
- `templates/core/*.html` (26 arquivos): removido o bloco `barra-usuario` do rodapé (nome subiu para o menu).
- `static/css/inicio.css`: estilos `.perfil-box`/`.perfil-atual`/`.perfil-lista`/`.perfil-opcao` (substituem
  os antigos `.menu-perfil*`).

### Decisões
- Dropdown com `<details>` nativo (sem JS): o auto-fechar do `inicio.js` é escopado a `.conteudo-interno`, então
  não interfere no menu; clicar num perfil já navega (fecha sozinho).

---

## 2026-07-07 - Seletor de perfil ("Ver como") + dados fictícios (demo) do Fabiano

### Resumo
Generaliza o preview do Diretor para um **seletor de perfil** de verdade e permite o Fabiano testar o perfil
Responsável **com dados**, sem poluir o clube.
- **Seletor "Ver como"** no menu: lista os perfis que o usuário **possui de fato** (grupos nativos) e troca a
  visão (menu + telas) ao clicar. Só aparece com 2+ perfis. Substitui o botão binário "Ver como responsável".
- **Fabiano ganha os 5 perfis** (Diretor, Responsável, Professor, Tesoureiro, Secretário). Professor/Tesoureiro/
  Secretário ainda **sem telas** → por ora só "Meus Dados" (placeholder no `ACESSO_PADRAO`).
- **Dados fictícios isolados:** flag **`demo`** em `Aventureiro` e `Evento` (migration **0039**). Tudo `demo=True`
  fica **fora de todas as contagens do clube** (Usuários, Mensalidades e Presença do Diretor, Financeiro, menu de
  eventos). A presença do responsável **casa a demo-ness** (família fictícia só enxerga eventos fictícios; a real,
  só reais — os demos não viram "falta" para ninguém).
- **Comando `dados_demo_fabiano`** (idempotente): dá os perfis ao Fabiano e cria **2 aventureiros fictícios**
  (foto/ficha/autorização), suas **mensalidades** (2 pagas + o resto em aberto/atrasado) e **2 eventos fictícios**
  com **presença** — para as telas do responsável aparecerem cheias.

### Arquivos alterados
- `core/menus.py`: perfis Professor/Tesoureiro/Secretário + `ORDEM_PERFIS`/`ICONE_PERFIL`; `PERFIL_ATIVO_KEY`,
  `perfis_do_usuario`, `perfil_efetivo` (via seletor), `pode_trocar_perfil`.
- `core/context_processors.py`: `perfis_disponiveis` (seletor) + menu do perfil efetivo; `_eventos_menu` exclui demo.
- `core/views.py`: `preview_responsavel_view` → `trocar_perfil_view`; **exclusão de `demo`** em usuarios,
  mensalidades (lista/totais/taxa), reajustar, gerar, cobranças, financeiro, presença (marcar/selecionar),
  recuperação por CPF, eventos e `_presenca_responsavel` (casa demo-ness).
- `core/models.py`: `Aventureiro.demo`, `Evento.demo`. `core/migrations/0039_*`.
- `core/urls.py`: `trocar-perfil/` (era `preview-responsavel/`). `templates/core/_menu.html`: seletor.
- `static/css/inicio.css`: estilo `.menu-perfil`. `core/management/commands/dados_demo_fabiano.py` (novo).
- `core/tests.py`: `DemoIsolamentoTests` + testes do seletor (substituem os de preview).

### Como usar
`python manage.py dados_demo_fabiano` → entrar como Fabiano → menu **"Ver como" → Responsável**.

---

## 2026-07-07 - Preview do Diretor: "Ver como responsável" (substituído pelo seletor de perfil)

### Resumo
Para o Diretor testar/conferir a visão do responsável sem outra conta, o menu do Diretor ganhou o botão
**"Ver como responsável"** (e **"Voltar ao Diretor"**). Liga/desliga uma flag na sessão (`PREVIEW_KEY`);
enquanto ligada, o menu e as telas Loja/Mensalidades/Presença se comportam como responsável.

### Arquivos alterados
- `core/menus.py`: `PREVIEW_KEY`, `perfil_efetivo(request)`, `atua_como_responsavel(request)`,
  `itens_menu_do_perfil(perfil)`.
- `core/context_processors.py`: menu usa `perfil_efetivo`; expõe `preview_responsavel`.
- `core/views.py`: `loja_view`/`mensalidades_view`/`presenca_view` passam a ramificar por
  `atua_como_responsavel`; nova `preview_responsavel_view` (só Diretor, POST).
- `core/urls.py`: rota `preview-responsavel/`. `templates/core/_menu.html`: botão (form POST).
- `static/css/inicio.css`: estilo `.menu-preview`. `core/tests.py`: 2 testes de preview.

### Observação
A conta do Diretor (Fabiano) não tem aventureiros, então em preview as telas aparecem **vazias**. Para ver
**com dados**, logar como um responsável real (ex.: `teste_responsavel` / `123456`).

---

## 2026-07-07 - Cobranças: busca também por aventureiro

### Resumo
A busca da aba Cobranças (que só achava por responsável) agora acha **também pelo nome do aventureiro**: o
`data-busca` de cada família passou a incluir o nome do responsável **e** os nomes das crianças. Placeholder
atualizado para "Buscar por responsável ou aventureiro…".

### Arquivos alterados
- `templates/core/mensalidades.html`: `data-busca` inclui `{{ f.resp_nome }}` + os `c.nome` das crianças;
  placeholder do campo de busca.

---

## 2026-07-07 - Cobranças: detalhe por criança + só cobra meses já vencidos

### Resumo
Dois ajustes: **(1)** cada família na aba Cobranças (e no cálculo) agora mostra o **detalhe por criança** —
nome do aventureiro, **valor em aberto dele** e os **meses**; **(2)** a cobrança e a página de acerto passam a
considerar **apenas meses já vencidos** (competência ≤ mês atual): cobra o **mês atual e os anteriores** em
aberto, **nunca meses à frente** (as mensalidades do ano inteiro já nascem geradas).

### Arquivos alterados
- `core/views.py`: `_cobrancas_familias` monta `criancas` (nome/total/meses por aventureiro); novo
  `_q_mens_vencidas()` (competência ≤ hoje) aplicado em `_mensalidades_abertas_familia` (acerto) e em
  `_cobrancas_familias` (aba Cobranças). A cobrança por aventureiro do Diretor (modal) segue manual (ele escolhe).
- `templates/core/mensalidades.html`: bloco por criança em cada família. `static/css/mensalidades.css`: estilos.
- `core/tests.py`: render com 2 crianças; `test_acerto_ignora_meses_futuros`; setups usam o mês atual.

---

## 2026-07-07 - Cobranças: busca, envio em lote com delay/progresso/cancelar, aviso como toast

### Resumo
Refinos na aba Cobranças, a pedido: **(1)** campo de **busca** por responsável (filtra ao digitar); **(2)**
**"Enviar a todos"** agora é **sequencial pelo navegador**, com **10s entre cada envio**, **barra de progresso**
e **botão cancelar** (evita bloqueio por spam do WhatsApp); **(3)** o aviso "configure o WhatsApp" **deixou de
ser um banner fixo** e passa a aparecer como **toast** (notificação lateral) só **quando se tenta enviar** (vem
da resposta do endpoint).

### Detalhes
- O lote envia **uma família por vez** (POST individual), atualiza a barra e o status inline, e respeita o filtro
  "só quem não recebeu este mês". Cancelar interrompe entre um envio e outro; se o WhatsApp não estiver
  configurado, o lote aborta no 1º retorno com o toast.
- Botões não ficam mais desabilitados por "WhatsApp não configurado" (só por família sem número) — o toast
  orienta ao tentar.

### Arquivos alterados
- `templates/core/mensalidades.html`: campo de busca, bloco de progresso (barra + cancelar), `data-*` nos itens
  (busca/cobrado/tem-numero); removido o banner fixo.
- `static/js/mensalidade_cobranca.js`: busca ao vivo; envio individual (atualiza inline); **lote com 10s +
  progresso + cancelar** (estado compartilhado, sem duplo encerramento).
- `static/css/mensalidades.css`: estilos da busca e da barra de progresso.

---

## 2026-07-07 - Cobrança de mensalidades (parte 2): aba "Cobranças" (WhatsApp)

### Resumo
Nova aba **"Cobranças"** no módulo Mensalidades (ao lado de Resumo/Aventureiros): dispara a **cobrança das
mensalidades por WhatsApp** (reusa a W-API), com **mensagem personalizável**, **envio a um ou a todos**,
**histórico do mês** e **filtro "só quem não recebeu este mês"**. A mensagem leva o **link de acerto** (parte 1).

### Como funciona
- **Mensagem configurável** (`ConfigMensalidade.mensagem_cobranca`) com marcadores `{nome}`, `{itens}`, `{total}`,
  `{link}` — interpolados por família no envio. Padrão em `MENSAGEM_COBRANCA_PADRAO`.
- **Agrupada por família** (conta): lista as famílias com mensalidade em aberto, com responsável, total, WhatsApp
  principal (reusa `_whatsapp_principal`), status do mês (📤 cobrado Nx / ⏳ não) e o link (`token_acerto`).
- **Envio**: `mensalidade_cobranca_enviar_view` (JSON) manda a um (`usuario_id`) ou a todos, com filtro
  `so_nao_enviados`; cada envio grava um `CobrancaEnviada` (mês/ano/quem) para o histórico e o filtro.
- Sem WhatsApp configurado (W-API) ou sem número da família → o envio avisa/pula.

### Arquivos criados/alterados
- `core/models.py`: `ConfigMensalidade.mensagem_cobranca` + `MENSAGEM_COBRANCA_PADRAO`; model `CobrancaEnviada`
  (histórico do mês). Migration **0037**.
- `core/views.py`: `_cobrancas_familias`, `_montar_mensagem_cobranca`, `_moeda_txt`,
  `mensalidade_cobranca_config_view` e `mensalidade_cobranca_enviar_view`; contexto da aba em `mensalidades_view`.
- `core/urls.py`: `mensalidades/cobrancas/config/` e `.../enviar/`.
- `templates/core/mensalidades.html`: aba/painel **Cobranças** (editor da mensagem + lista + enviar a um/todos +
  filtro). `static/js/mensalidade_cobranca.js` (envio AJAX). `static/css/mensalidades.css` (estilos).
- `core/tests.py`: `CobrancaWhatsappTests` (envio registra histórico; render da aba).

### Observações
- Envio "a todos" é síncrono (um POST por família na W-API); para o porte do clube, ok.
- Fecha a feature de cobrança (parte 1 = página de acerto; parte 2 = aba Cobranças).

---

## 2026-07-07 - Cobrança de mensalidades (parte 1): página pública de acerto (link do WhatsApp)

### Resumo
Primeira parte do sistema de cobrança de mensalidades: a **página pública de acerto** — o destino do link que
vai na mensagem de cobrança. Sem login: um **token fixo e secreto por família** (conta) abre uma página que
mostra as **mensalidades em aberto de todos os aventureiros da família** e permite **pagar na hora** (Pix ou
cartão), reusando a engine. O **Pix é gerado só no clique** (nada "vence" se a pessoa demorar a abrir o link) e a
página sempre reflete o que está em aberto **no momento**. É, na prática, a "visualização do responsável" numa
versão enxuta e pública.

### Arquivos criados/alterados
- `core/models.py`: `PerfilUsuario.token_acerto` (+ `get_token_acerto()`; uuid fixo). Migration **0036**.
- `core/views.py`: `acerto_view` (pública, por token) e `acerto_cobrar_view` (pública; cobra TODAS as
  mensalidades em aberto da família, Pix/cartão) + helpers `_mensalidades_abertas_familia`/`_responsavel_da_familia`.
- `core/urls.py`: `/acerto/<token>/` e `/acerto/<token>/cobrar/`.
- `templates/core/acerto.html`: **nova** página pública (em aberto + total + pagar; "tudo em dia"/"link inválido").
- `core/tests.py`: `AcertoPublicoTests` (mostra em aberto, token inválido, cobrar Pix → simular → quita a família).

### Próximo (parte 2)
- Aba **"Cobranças"** no Mensalidades: template de mensagem configurável (com `{nome}`/`{itens}`/`{total}`/`{link}`),
  envio pelo WhatsApp (todos/um a um), **histórico por mês** de quem já recebeu e **filtro** "só quem não recebeu".

---

## 2026-07-07 - Pagamentos Mercado Pago (Etapa 6, parte 2): cartão nos 4 pontos

### Resumo
O cartão (Checkout Pro + gross-up da taxa + parcelado-comprador) foi replicado nos demais pontos: **Loja do
Clube**, **Inscrição de evento** e **Mensalidades**. Agora os quatro pontos aceitam **Pix e cartão**.

### Como ficou por ponto
- **Loja do Clube** (`loja_pagamento_view`): ramo de cartão espelhando o do Pix (já tinha o seletor Pix/Cartão).
- **Inscrição** (`evento_inscrever_view` + `evento_inscrever.html`): novo **seletor Pix/Cartão** no formulário
  (só quando o MP está configurado); cartão → Checkout Pro. Grátis segue criando na hora.
- **Mensalidades** (`mensalidade_cobrar_view` + modal em `mensalidades.html`): **seletor Pix/Cartão** no modal de
  cobrança; cartão → Checkout Pro (baixa múltipla no webhook, igual ao Pix).

### Arquivos alterados
- `core/views.py`: ramos de cartão em `loja_pagamento_view`, `evento_inscrever_view` e `mensalidade_cobrar_view`
  (+ `mp_configurado` no contexto da inscrição).
- `templates/core/`: seletor de forma em `evento_inscrever.html` e no modal de `mensalidades.html`.
- `core/tests.py`: cartão gera preferência em mensalidade e inscrição (sem criar/quitar antes de aprovar).

### Pendências
- No painel do MP, deixar o parcelamento como **"Parcelado comprador"** (config da conta).
- (Opcional) checkout transparente no site, se um dia não quiserem o redirecionamento.

---

## 2026-07-07 - Pagamentos Mercado Pago (Etapa 6, parte 1): cartão via Checkout Pro (lojinha de evento)

### Resumo
Início do **cartão de crédito**, reusando a engine. Modelo: **Checkout Pro** (redireciona ao MP; sem SDK, sem
dado de cartão no servidor, sem dependência nova). **Todas as taxas vão pro cliente**: o **juro do parcelamento**
é do comprador (config "Parcelado comprador" na conta MP, até 12x) e a **taxa de intermediação** (fixa) é
**embutida no preço** do cartão via *gross-up* (`cobrado = venda ÷ (1 − taxa%)`). Ligado 1º na **lojinha de
evento** para validar; os outros pontos vêm em seguida.

### Como funciona
- Config nova: **`MercadoPagoConfig.taxa_cartao_pct`** (padrão 4,98% = crédito na hora) + **termômetro** na tela
  (mostra a taxa residual média que o clube arcou nas vendas de cartão; ideal ≈ 0, senão aumentar o %).
- `mercadopago.criar_preferencia` (Checkout Pro, via `urllib`): cria a preferência (só cartão, `installments=12`,
  `back_urls`, `notification_url`) e devolve o `init_point` para redirecionar.
- `_criar_pagamento_cartao`: gross-up + cria `Pagamento(forma="cartao", valor_bruto=venda)` + preferência.
- **Taxa unificada**: `_aprovar_pagamento` calcula `taxa = valor_bruto − líquido` (o que o clube arcou). No Pix o
  clube absorve → taxa ≈ 1%; no cartão o repasse cobre → **líquido volta a bater com a venda → taxa ≈ 0**.
- Webhook e finalização já existentes servem; a forma (pix/cartão) do pedido/compra/mensalidade/inscrição passou
  a vir do `pagamento.forma` (antes fixava "pix").
- Página de pagamento genérica trata cartão (tela "confirmando pagamento" + polling, sem QR).

### Arquivos alterados
- `core/models.py`: `taxa_cartao_pct` (migration **0035**).
- `core/mercadopago.py`: `criar_preferencia`.
- `core/views.py`: `_grossar_cartao`, `_criar_pagamento_cartao`, `_aprovar_pagamento` (taxa = bruto − líquido),
  ramo de cartão na `evento_pagamento_view`, termômetro na `mercadopago_view`, `taxa_cartao_pct` no salvar, e as
  finalizações usando `pagamento.forma`.
- `templates/core/mercadopago.html` (config do cartão + termômetro), `pagamento.html` (modo cartão).
- `core/tests.py`: cartão gera preferência + webhook confirma com taxa repassada (≈ 0); teste do gross-up.

### Pendências
- Replicar o cartão em **Loja do Clube**, **Inscrição** e **Mensalidades**.
- No painel do MP, deixar o parcelamento como **"Parcelado comprador"** (config da conta, não do sistema).

---

## 2026-07-07 - Loja/Vendas: Custos, Taxa e Resultado como cards no Resumo

### Resumo
No Resumo da aba Vendas da Loja, **Custos**, **Taxa Mercado Pago** e **Resultado líquido** viraram **KPIs
próprios** (cards), ao lado de **Arrecadado** (que já era card). Removidos o card "Resultado da loja" (com a
linha Vendas/Custos/Taxa/Resultado) e a nota explicativa — a informação agora está nos cards. Ordem dos KPIs:
Arrecadado · Custos · Taxa Mercado Pago · Resultado líquido · Compras · Média por compra · Itens a entregar.

### Arquivos alterados
- `templates/core/loja.html`: KPIs de Custos/Taxa/Resultado no Resumo; remove o card "Resultado da loja".

---

## 2026-07-07 - Financeiro: remove "Onde está o dinheiro" e ajusta resultado do caixa

### Resumo
Removido da tela Financeiro o card/modal **"Onde está o dinheiro"** (banco + espécie), a pedido do usuário.
Também foi ajustado o banco local para o resultado líquido do Financeiro bater com o valor informado da conta do
clube: **R$ 3.353,00**.

### Arquivos alterados
- `templates/core/financeiro.html`: remove o card "Onde está o dinheiro" e o modal de edição do caixa.
- `docs/ESTADO_ATUAL.md` e `docs/HISTORICO_ALTERACOES.md`: documentação atualizada.

### Dados ajustados
- Mensalidades reabertas: IDs `744`, `675`, `611`, `610`, `695` (R$ 30,00 cada) e `482` (R$ 27,00).
- Mensalidade mantida paga com ajuste fino: ID `581`, `valor_pago` de R$ 30,00 para R$ 28,00.
- Resultado financeiro recalculado: **R$ 3.353,00**.

### Validação
- `python manage.py check` OK.
- Busca no template confirma que `Onde está o dinheiro`, `modalCaixa`, `btnEditarCaixa`, `caixa.saldo_banco` e
  `caixa_especie` não aparecem mais em `templates/core/financeiro.html`.
- Recalculo local do Financeiro: mensalidades recebidas R$ 2.995,00 e resultado R$ 3.353,00.
- Deploy no VPS com `pinhaljunior2-deploy` OK; banco online substituído pelo `db.sqlite3` local ajustado.
- Backup do banco online anterior: `/var/www/pinhaljunior2/backup/db_before_caixa_mensalidades_20260707_003251.sqlite3`.
- Recalculo no VPS: mensalidades recebidas R$ 2.995,00, resultado R$ 3.353,00, 100 pagas e 288 abertas.
- `https://pinhaljunior.com.br/sistema-novo/` respondeu `200`; serviços `pinhaljunior2`, `nginx` e `sitepinhal`
  ativos.

### Pendências
- Sem novas pendências.

---

## 2026-07-07 - Restaura banco local no VPS

### Resumo
Após testes manuais no ambiente online sujarem o banco do VPS, o banco da instalação nova (`pinhaljunior2`) foi
restaurado a partir do `db.sqlite3` local. A mídia do VPS foi mantida, pois a solicitação era restaurar o banco.
O sistema antigo (`sitepinhal`) não foi alterado.

### Arquivos/configurações envolvidos
- Local: `db.sqlite3` enviado temporariamente para `/tmp/pinhaljunior2-db-local.sqlite3`.
- VPS: `/var/www/pinhaljunior2/data/db.sqlite3` substituído pelo banco local.
- Backup criado antes da troca: `/var/www/pinhaljunior2/backup/db_before_local_restore_20260707_002006.sqlite3`.
- `docs/DEPLOY_VPS.md`, `docs/ESTADO_ATUAL.md` e `docs/HISTORICO_ALTERACOES.md`: documentação atualizada.

### Validação
- `manage.py check` OK no VPS.
- `migrate --noinput` sem pendências.
- Serviço `pinhaljunior2.service` ativo.
- `https://pinhaljunior.com.br/sistema-novo/` respondeu `200`.
- Contagem do banco restaurado: 37 usuários, 39 aventureiros, 36 ativos e 0 pagamentos.
- Serviços `pinhaljunior2.service`, `nginx` e `sitepinhal.service` ativos.

### Decisões tomadas
- Parar apenas `pinhaljunior2.service` durante a troca.
- Remover o arquivo temporário `/tmp/pinhaljunior2-db-local.sqlite3` após restaurar.
- Manter a pasta `media/` do VPS, que já continha os uploads.

### Pendências
- Sem novas pendências.

---

## 2026-07-06 - Loja/Vendas: resumo financeiro no Resumo; Custos só com a lista

### Resumo
Ajuste de organização: o resumo financeiro (Vendas − Custos − Taxa MP = Resultado) saiu da sub-aba **Custos** e
virou um card **"💰 Resultado da loja"** na sub-aba **Resumo** (junto do Arrecadado) — é onde a taxa e o
resultado líquido fazem sentido. A sub-aba **Custos** ficou só com a **lista de custos** ("Custos da loja") +
um **Total de custos**.

### Arquivos alterados
- `templates/core/loja.html`: card "Resultado da loja" no Resumo; Custos retitulada ("Custos da loja"), sem a
  linha de resultado, com total ao final.
- `static/css/loja.css`: `.loja-custos-total`.

---

## 2026-07-06 - Loja/Vendas dividida em sub-abas

### Resumo
A aba **Vendas** da Loja (que estava com tudo empilhado) foi dividida em **4 sub-abas** para facilitar a
visualização: **Resumo** (KPIs + mais vendidos + por forma de pagamento), **Custos** (resultado líquido +
custos/pagamentos da loja), **Pedido ao fornecedor** (o que falta entregar) e **Todas as compras** (lista
buscável com entrega). Mesmo padrão visual das abas principais da Loja.

### Arquivos alterados
- `templates/core/loja.html`: barra de sub-abas + cada seção envolvida numa `.loja-subsecao` (Resumo visível
  por padrão; demais `hidden`).
- `static/js/loja.js`: alterna as sub-abas (`.loja-subaba` → `.loja-subsecao`).
- `static/css/loja.css`: estilo das sub-abas.

### Nota
- Fecha a pendência adiada da revisão anterior.

---

## 2026-07-06 - Taxa sempre visível na Loja/Vendas + nota na lojinha do evento

### Resumo
Ajuste de visibilidade da taxa (o cálculo já estava certo desde a Etapa 5). Na **Loja → Vendas**, a linha da
**taxa do Mercado Pago** só aparecia quando havia taxa > 0, dando a impressão de que o resultado "não refletia" a
taxa. Agora a linha **aparece sempre** (mesmo R$ 0,00) e há uma nota explicando que o Resultado já é líquido
(sem custos e sem taxa). Na **aba Lojinha do painel do evento**, uma nota esclarece que os valores dos pedidos
são brutos e que a taxa/resultado líquido ficam na aba **Financeiro**.

### Arquivos alterados
- `templates/core/loja.html`: linha de taxa sempre visível no resultado da aba Vendas + nota.
- `templates/core/evento_painel.html`: nota na sub-aba Pedidos da Lojinha.
- `core/tests.py`: `test_vendas_loja_resultado_reflete_taxa` (resultado da loja desconta a taxa).

### Pendências
- **Adiado (a pedido)**: dividir a aba **Vendas** da Loja em sub-abas (Custos / Pedido ao fornecedor / Todas as
  compras) para facilitar a visualização.

---

## 2026-07-06 - Correção: 500 no Financeiro (extrato com data+hora × custo do clube)

### Resumo
Após passar o extrato a exibir **data+hora** (`|date:"d/m/y H:i"`), a página `/financeiro/` dava **erro 500** em
produção: o lançamento de **custo do clube** usava `cc.data` (um `date`, sem hora) e o filtro `|date` com `H`
**quebra em objetos `date`** (`TypeError: ...may not contain time-related format specifiers`). Os testes não
tinham custo do clube, por isso não pegou.

### Correção
- `core/views.py`: o lançamento de custo do clube no extrato agora carrega um **datetime** (`cc.data` combinado
  com meia-noite) em vez de um `date`. Todos os itens do extrato passam a ser datetime → o `H:i` não quebra.
- `core/tests.py`: `test_financeiro_desconta_taxa_do_liquido` cria um `CustoClube` (exercita o render do extrato)
  — regressão coberta.

---

## 2026-07-06 - Financeiro: extrato ordenado por data E hora (com hora na tela)

### Resumo
O extrato consolidado do Financeiro ordenava só por **data** (`_dt_data` truncava o horário), então lançamentos
do mesmo dia ficavam na ordem de inserção, não do mais recente. Agora ordena por **data + hora** (mais recente
no topo) e a tela mostra o **horário** de cada lançamento. Isso também deixa a linha **"Taxa Mercado Pago"**
adjacente à venda que a gerou.

### Arquivos alterados
- `core/views.py`: `_dt_data` preserva o datetime; novo `_ordem_extrato` (chave aware date+hora, normaliza
  date/datetime/None); `extrato.sort` usa essa chave.
- `templates/core/financeiro.html`: data do extrato exibida como `d/m/y H:i`.
- `core/tests.py`: confirma a linha "Taxa Mercado Pago" no extrato.

### Nota
- A taxa (1%) aparece como linha própria no extrato **a partir da Etapa 5** — se não apareceu, faltou o deploy.

---

## 2026-07-06 - Pagamentos Mercado Pago (Etapa 5): taxa/líquido nos relatórios

### Resumo
Os relatórios financeiros passaram a mostrar o **valor líquido que caiu no banco** (bruto − custos − **taxa do
Mercado Pago**). O clube absorve a taxa (não repassa ao cliente), mas ela agora aparece descontada em **todos os
relatórios**: **Financeiro geral**, **painel financeiro do evento**, **Mensalidades** e **Loja (Vendas)**. Usa a
`taxa` real gravada em cada `Pagamento` aprovado (fallback 1% já vem da engine).

### Como a taxa é somada (sem contagem dupla)
- **Geral**: soma `Pagamento.taxa` por **tipo** aprovado (mensalidade / loja_clube / loja_evento+inscricao) —
  cada Pagamento tem uma taxa e é contado uma vez.
- **Evento**: soma sobre os **Pagamentos distintos** ligados às inscrições/pedidos confirmados do evento (uma
  inscrição e o pedido de lojinha que veio junto **compartilham** o mesmo Pagamento → `set` evita duplicar).
- **Mensalidades/Loja**: soma a taxa dos Pagamentos das mensalidades do ano / das compras da loja.

### Arquivos alterados
- `core/views.py`:
  - `financeiro_view`: taxa por fonte (`resumo.*.taxa`), líquido de cada fonte já **sem taxa**, `saidas` e
    `resultado` incluem a taxa, `disponivel`/`reservado_loja` recalculados, e **linhas de "Taxa Mercado Pago"**
    no extrato consolidado.
  - `_montar_financeiro` (evento): `taxa` + `saidas_total` (custos + taxa), `resultado` líquido, taxa no extrato;
    `evento_painel_view` reflete no `resumo`.
  - `loja_view`: `taxa_loja` e `loja_resultado` já sem taxa.
  - `mensalidades_view`: `totais.taxa_gateway` e `totais.liquido`.
- Templates: `financeiro.html` (cards por fonte com linha de taxa + textos), `evento_painel.html` (Saídas =
  custos + taxa), `loja.html` (linha de taxa nas Vendas), `mensalidades.html` (líquido no KPI Recebido).
- `core/tests.py`: taxa refletida no geral (`test_financeiro_desconta_taxa_do_liquido`) e no painel do evento
  (`test_painel_evento_desconta_taxa_no_resultado`).

### Pendências
- Próxima: **cartão de crédito** (Etapa 6). Pagamentos manuais/dinheiro/importados têm taxa zero (líquido = bruto).

---

## 2026-07-06 - Pagamentos Mercado Pago (Etapa 4): Inscrição de evento via Pix

### Resumo
Quarta etapa: a **inscrição online** de evento passou a cobrar por **Pix real** quando há valor a pagar. Antes a
inscrição nascia **confirmada sem pagar**; agora, com MP configurado e total &gt; 0, os dados validados são
**serializados** e a inscrição só é criada **na aprovação** do Pix (webhook/simular). Inscrição **gratuita**
(total 0 — diretoria/faixa sem valor) ou **sem MP** continua criando na hora. O **balcão/PDV** não muda.

### Como funciona
- `evento_inscrever_view`: valida como antes (responsável + participantes com preço/cupom + campos + lojinha) e
  monta um **payload serializável** (responsável; participantes com `valor` já calculado/descontado, `faixa_id`,
  respostas e cupom; campos extra; itens da lojinha). Se MP configurado e total &gt; 0 → cria `Pagamento`
  (`tipo="inscricao"`) e vai à página de pagamento genérica; senão → cria na hora.
- `_criar_inscricao_de_payload` (usado pela criação imediata **e** pela finalização): cria a Inscrição
  confirmada + participantes + respostas + pedido de lojinha vinculado; **marca os cupons** (uso único revalidado
  no ato — no Pix, isso acontece só no pagamento). Preços vêm prontos do payload (o desconto do cupom foi fixado
  na cobrança), evitando divergência de valor após pagar. `_finalizar_inscricao` chama esse helper na aprovação.
- Inscrição paga por Pix fica `forma_pagamento="pix"` e com FK `pagamento` (idem o pedido de lojinha junto).

### Arquivos alterados
- `core/models.py`: FK `Inscricao.pagamento`. Migration **0034**.
- `core/views.py`: `_criar_inscricao_de_payload` + `_finalizar_inscricao` + dispatch; `_sucesso_url_e_sessao`
  trata `inscricao`; bloco de criação da `evento_inscrever_view` reescrito (payload + branch Pix/imediato).
- `core/tests.py`: `InscricaoPixTests` (paga → Pix → simular → inscrição confirmada + taxa + FK; grátis cria na hora).

### Decisões tomadas
- Preço fixado na cobrança (payload) e cupom marcado só na aprovação (best-effort): se o cupom for usado por
  outro entre a geração do Pix e o pagamento, a pessoa mantém o preço que pagou (não falha após o pagamento).
- Balcão/PDV de inscrição inalterado (pagamento presencial).

### Pendências
- Próximas: **taxa/líquido nos relatórios** (Etapa 5) e **cartão** (Etapa 6).

---

## 2026-07-06 - Pagamentos Mercado Pago (Etapa 3): Loja do Clube via Pix

### Resumo
Terceira etapa: a **Loja do Clube** passou a cobrar por **Pix real** (Mercado Pago), reaproveitando a engine e a
**página de pagamento genérica** da Etapa 2. Sem MP configurado, mantém o fluxo simulado antigo. A **compra só
nasce na aprovação** (o carrinho fica na sessão/no payload até lá). De quebra, o "Marcar pago/Desfazer" das
mensalidades agora mostra **toast de sucesso**.

### Como funciona
- `loja_pagamento_view`: com MP configurado + Pix, cria um `Pagamento` (`tipo="loja_clube"`, `payload` com o
  **carrinho** serializado + comprador) e **redireciona para a página genérica** de pagamento (`/pagamento/<ref>/`).
- Na aprovação, `_finalizar_loja_clube` reconstrói os itens do carrinho (`_loja_resolver_kits`, extraído de
  `_loja_cart_detalhado`) e cria a `CompraLoja` (forma Pix, FK `pagamento`, baixa de estoque). O sucesso volta
  para `loja_sucesso` (limpa carrinho/checkout da sessão).

### Arquivos alterados
- `core/models.py`: FK `CompraLoja.pagamento`. Migration **0033**.
- `core/views.py`: `_loja_resolver_kits` (resolvedor puro do carrinho) + `_loja_cart_detalhado` refatorado;
  `_finalizar_loja_clube` + dispatch; `_sucesso_url_e_sessao` trata `loja_clube`; `loja_pagamento_view` usa o Pix
  real quando configurado.
- `static/js/mensalidades.js`: toast de sucesso no marcar pago/desfazer.
- `core/tests.py`: `LojaClubePixTests` (carrinho → Pix → simular → compra criada + taxa + FK).

### Pendências
- Próximas: **Inscrição de evento** (Etapa 4), **taxa/líquido nos relatórios** (Etapa 5), **cartão** (Etapa 6).

---

## 2026-07-06 - Cache-busting dos estáticos (JS/CSS antigo preso no navegador)

### Resumo
**Causa-raiz** de "corrigi e não resolveu": as correções de JavaScript (caminho do fetch, leitura do cookie de
CSRF) eram entregues ao servidor, mas o **navegador continuava usando o `mensalidades.js`/`loja.js` antigos em
cache** — então o "Desfazer"/"Marcar pago" seguia batendo no endereço errado (raiz = sistema antigo), que não
devolve JSON → "não foi possível atualizar". Correções **server-side** (deslogar) pegavam na hora; as que
dependiam de JS novo ficavam mascaradas pelo cache. Confirmado por teste automatizado: o Desfazer no servidor
funciona (`MensalidadePixTests.test_desfazer_mensalidade_paga_via_pix`).

### Solução
Ativado **cache-busting** em produção: `STORAGES` usa `core.storages.CacheBustingStaticFilesStorage`
(subclasse de `ManifestStaticFilesStorage`, `manifest_strict=False`), que renomeia cada estático com um hash do
conteúdo (`mensalidades.<hash>.js`). Quando o arquivo muda, a URL muda e o navegador **sempre** baixa a versão
nova; arquivos inalterados mantêm o hash (seguem em cache). Em `DEBUG` continua o storage simples.

### Arquivos criados/alterados
- `config/settings.py`: `STORAGES` com o storage de cache-busting quando `DEBUG=False`.
- `core/storages.py`: **novo** — `CacheBustingStaticFilesStorage` (`manifest_strict=False`, para não quebrar
  testes/páginas quando falta o manifesto ou uma entrada).

### Notas
- `collectstatic --noinput` (roda no deploy) valida e gera o manifesto; testado localmente (168 arquivos, ok).
- Depois do deploy, basta **recarregar a página** — o HTML passa a apontar para o JS com hash novo; não precisa
  mais de "atualização forçada" (Ctrl+F5) a cada correção.

---

## 2026-07-06 - Correção: "deslogou sozinho" — cookies compartilhados com o sistema antigo

### Resumo
No VPS o sistema novo e o antigo estão no **mesmo domínio** (`pinhaljunior.com.br`) e os dois são Django usando
o **mesmo nome de cookie** de sessão (`sessionid`) e de CSRF (`csrftoken`). Cookie é do domínio inteiro → **um
sobrescreve o do outro**, derrubando o login do sistema novo ("deslogou ao clicar em Mercado Pago"). Como efeito,
o **Desfazer** das mensalidades (AJAX) recebia o redirecionamento para o login em vez de JSON → "não foi possível
atualizar". Resolvido dando **cookies com nome próprio** ao sistema novo.

### Arquivos alterados
- `config/settings.py`: `SESSION_COOKIE_NAME=pinhaljunior2_sessionid` e `CSRF_COOKIE_NAME=pinhaljunior2_csrftoken`
  (ambos via env: `DJANGO_SESSION_COOKIE_NAME` / `DJANGO_CSRF_COOKIE_NAME`).
- `static/js/mensalidades.js` e `static/js/loja.js`: o leitor de CSRF passa a ler o novo nome de cookie (com
  fallback para o token do formulário `csrfmiddlewaretoken`, que independe do nome).

### Efeito colateral esperado
- Ao subir, todas as sessões atuais do sistema novo caem uma vez (o cookie antigo `sessionid` é ignorado); é só
  logar de novo. Depois disso o login do sistema novo não briga mais com o do antigo.

---

## 2026-07-06 - Correção: fetch com caminho absoluto quebrava sob o prefixo do VPS

### Resumo
Bug **pré-existente** exposto pelo deploy no VPS (app sob `/sistema-novo/`): dois JS faziam `fetch` com
**caminho absoluto fixo**, que no VPS resolvia para a raiz do domínio (sistema antigo) e falhava. Sintoma
relatado: em Mensalidades, **"Desfazer"** (e o "Marcar pago") não funcionava. Também afetava a **marcação de
entrega** da Loja do Clube (mesmo bug, ainda não percebido).

### Arquivos alterados
- `static/js/mensalidades.js`: usa a URL de `#mensLista[data-pagar-url]` (via `{% url %}`, que inclui o prefixo)
  em vez de `"/mensalidades/pagar/"` fixo. `templates/core/mensalidades.html`: adiciona `data-pagar-url`.
- `static/js/loja.js`: usa `#lojaComprasLista[data-entrega-url|data-entrega-compra-url]` em vez de
  `"/loja/entrega/..."` fixo. `templates/core/loja.html`: adiciona os dois `data-`.

### Decisões tomadas
- Padrão a seguir dali em diante: **toda URL usada em JS vem do template via `{% url %}`** (num `data-`), nunca
  caminho absoluto fixo — senão quebra sob `FORCE_SCRIPT_NAME`. O código novo dos pagamentos já seguia isso.
- Mantido um fallback para o caminho local. Varredura confirmou que não há outros `fetch` absolutos.

---

## 2026-07-06 - Pagamentos Mercado Pago (Etapa 2): Mensalidades online + admin do Pagamento

### Resumo
Segunda etapa da integração. **(1)** `Pagamento` agora aparece no **/admin/** (lista só-leitura, para auditoria).
**(2)** **Mensalidades online via Pix**: o Diretor seleciona os meses em aberto de um aventureiro e gera **uma
única cobrança Pix**; quando o pagamento é aprovado (webhook ou "Simular" no teste), **todos os meses escolhidos
são quitados automaticamente**. Reaproveita a engine da Etapa 1 e já fica pronto para a futura tela do
responsável (mesmo fluxo: selecionar em aberto → pagar → baixa tudo). Criada também uma **página de pagamento
genérica** (QR + polling + simular) e uma **tela de sucesso genérica**, reaproveitáveis pelas próximas etapas.

### Como funciona
- Na aba **Aventureiros** das Mensalidades, cada aventureiro com valor em aberto ganha o botão **"💳 Cobrar em
  aberto via Pix"** → abre um modal com os meses em aberto (checkbox, total ao vivo) → **"Gerar cobrança Pix"**.
- `mensalidade_cobrar_view` cria um `Pagamento` (`tipo="mensalidade"`, `payload` com os ids dos meses) + o Pix, e
  leva à página de pagamento genérica.
- Na aprovação, `_finalizar_mensalidade` marca cada mensalidade do payload como **paga** (forma Pix, `valor_pago`,
  `pago_em`, `registrado_por`, FK `pagamento`). Idempotente (só mexe nas que ainda estão em aberto). O webhook
  "sabe quem pagou e o quê" pelo `payload`.

### Arquivos criados/alterados
- `core/admin.py`: `PagamentoAdmin` (só-leitura: sem add/change/delete).
- `core/models.py`: FK `Mensalidade.pagamento`. Migration **0032**.
- `core/views.py`: `_finalizar_mensalidade` + dispatch; `_sucesso_url_e_sessao` para os tipos genéricos;
  `pagamento_view` (página genérica), `pagamento_sucesso_view` (sucesso genérico), `mensalidade_cobrar_view`.
- `core/urls.py`: `mensalidades/cobrar/`, `pagamento/<ref>/` e `pagamento/<ref>/sucesso/`.
- `templates/core/pagamento.html` e `pagamento_sucesso.html`: **novas** (genéricas, reaproveitáveis).
  `templates/core/mensalidades.html`: botão + modal de cobrança; `data-valor`/`data-nome` nos meses.
- `static/js/mensalidade_pix.js`: **novo** (monta o modal com os meses em aberto + total ao vivo).
  `static/css/mensalidades.css`: estilos do modal de cobrança.
- `core/tests.py`: `MensalidadePixTests` (renderização da tela; cobrança → simular → baixa múltipla + taxa + FK).

### Decisões tomadas
- Uma cobrança Pix por **aventureiro** (a view garante que todas as mensalidades são do mesmo).
- Por ora quem dispara é o **Diretor** (para testar); a engine já serve a futura tela do responsável.
- Páginas de pagamento/sucesso **genéricas** (por `referencia` do pagamento) para reuso nas Etapas 3 e 4.

### Pendências
- Próximas: **Loja do Clube** (Etapa 3), **Inscrição de evento** (Etapa 4), **taxa/líquido nos relatórios**
  (Etapa 5) e **cartão** (Etapa 6). Tela do responsável para pagar as próprias mensalidades: futura.

---

## 2026-07-06 - Pagamentos Mercado Pago (Etapa 1): engine Pix + webhook + lojinha de evento

### Resumo
Início da integração real de pagamentos (Mercado Pago), começando **só por Pix**. Criada uma **engine única
reaproveitável** para os 4 pontos de venda (lojinha de evento, Loja do Clube, mensalidades e inscrição) e
**ligada primeiro na lojinha de evento**, substituindo o QR simulado pela cobrança Pix real. O clube **absorve a
taxa** (não repassa), mas o sistema grava a **taxa real** informada pelo Mercado Pago e o **líquido** que caiu no
banco (fallback de 1% quando o dado não vier) — base para os relatórios financeiros mostrarem o líquido (Etapa 5).

### Componentes
- **Config** `MercadoPagoConfig` (singleton, só Diretor, tela `/mercadopago/`): guarda **dois pares** de
  credenciais — teste e produção — + `modo` ativo. Segredos mascarados; trocam só se um novo for digitado
  (espelha o `WhatsappConfig`). Mostra a **URL do webhook** para cadastrar no painel do MP.
- **Cliente** `core/mercadopago.py` (só `urllib`, sem dependência nova): `criar_pix`, `consultar_pagamento`
  (extrai **taxa real** de `fee_details` e o **líquido** de `net_received_amount`), `validar_assinatura`
  (HMAC-SHA256 do `x-signature`) e `mapear_status`. Usa a API clássica `/v1/payments`.
- **Model** `Pagamento` (genérico): `tipo`, `forma`, `referencia` (external_reference), `mp_payment_id`,
  `status`, `valor_bruto`/`taxa`/`valor_liquido`, `payload` (JSON = o que está sendo pago), dados do Pix (QR),
  `finalizado` (idempotência). FK `PedidoLoja.pagamento` (nulo em balcão/dinheiro/importados → taxa zero).
- **Webhook** `/webhooks/mercadopago/` (público, `csrf_exempt`, idempotente): valida a assinatura, **consulta o
  pagamento no MP (fonte da verdade)**, e ao aprovar grava taxa/líquido e **finaliza** (cria o objeto pago
  conforme o `tipo`). Despacho por tipo — só `loja_evento` implementado nesta etapa.
- **Fluxo na lojinha**: `evento_pagamento_view` usa Pix real quando o MP está configurado (QR do MP +
  **polling** de status + botão **"Simular aprovação" só no modo teste**); sem config, mantém o simulado antigo.
  O `PedidoLoja` só nasce na aprovação (webhook/simulação), preservando "sem estoque reservado por carrinho
  abandonado".

### Arquivos criados/alterados
- `core/models.py`: `MercadoPagoConfig`, `Pagamento`, `STATUS_PAGAMENTO_CHOICES`/`TIPO_PAGAMENTO_CHOICES`,
  `PedidoLoja.pagamento`; import `uuid`. Migration **0031**.
- `core/mercadopago.py`: **novo** cliente do gateway (urllib).
- `core/views.py`: engine (`_criar_pagamento_pix`, `_aprovar_pagamento`, `_finalizar_pagamento`/
  `_finalizar_loja_evento`, `_sucesso_url_e_sessao`), views de config, webhook, status (polling) e simulação;
  `evento_pagamento_view` passa a usar o MP quando configurado (`_evento_pagamento_pix_mp`).
- `core/urls.py`: rotas `mercadopago`, `mercadopago_config`, `mercadopago_webhook`, `pagamento_status`,
  `pagamento_simular`.
- `templates/core/mercadopago.html`: **nova** tela de config. `templates/core/evento_pagamento.html`: modo Pix
  real (QR base64 + copia e cola + polling + simular) com fallback ao simulado. `templates/core/_menu.html`:
  item "Mercado Pago" (💳, Diretor).
- `static/js/pagamento_mp.js`: **novo** (polling + botão simular + copiar). `static/css/eventos.css`: estilos do
  Pix (spinner/aguardando/erro/teste).
- `core/tests.py`: `MercadoPagoClienteTests` (assinatura + extração de taxa) e `PagamentoLojinhaTests` (fluxo
  pendente→aprovado, simulação só em teste, webhook com **taxa real**, assinatura inválida, retrocompat sem MP).

### Decisões tomadas
- **Taxa real do MP** (não 1% fixo), com fallback de 1% no Pix quando o dado não vier — bate com o extrato do banco.
- **Dois pares de credenciais** (teste/produção) num só singleton: valida no teste e vira a chave sem redigitar.
- **Engine genérica com `payload`**: o webhook sabe "quem pagou e o quê" sem depender da sessão do navegador.
- **Sem dependência nova**: cliente via `urllib`, como a W-API.
- Objeto pago só nasce na aprovação (mantém o padrão "não reserva estoque de carrinho abandonado").

### Pendências
- **Confirmar a taxa real com um pagamento de verdade**: no sandbox não dá para "pagar" um Pix de teste; o botão
  "Simular" usa 1% estimado. O caminho da taxa real (webhook → `fee_details`) já está testado com dado mockado;
  confirmar o **valor real** exige um Pix pequeno em produção (ou o fluxo de cartão de teste, na fase de cartão).
- Cadastrar a **URL do webhook** e a **assinatura secreta** no painel do MP e colar a secret na tela de config.
- Próximas etapas: **Mensalidades online** (seleção múltipla → uma cobrança → baixa automática), **Loja do
  Clube**, **Inscrição de evento**, **taxa/líquido nos relatórios financeiros** e, por fim, **cartão de crédito**.

---

## 2026-07-06 - Documentação dedicada de deploy no VPS

### Resumo
Criado um documento específico para o deploy no VPS, reunindo em um só lugar a URL temporária, estrutura do
servidor, atalho global, variáveis de ambiente, dados importados, validações e cuidados para não afetar o sistema
antigo.

### Arquivos criados/alterados
- `docs/DEPLOY_VPS.md`: novo guia de deploy e operação do VPS.
- `README.md`: adiciona link para o guia de deploy.
- `docs/README_PROJETO.md`: aponta para o guia dedicado na seção "Deploy no VPS".
- `docs/ESTADO_ATUAL.md`: referencia `docs/DEPLOY_VPS.md` no resumo do deploy.
- `docs/HISTORICO_ALTERACOES.md`: esta entrada.

### Decisões tomadas
- Manter o guia operacional separado do histórico para facilitar continuidade.
- Registrar explicitamente que código vai por GitHub + `pinhaljunior2-deploy`, e que o sistema antigo não deve
  ser alterado sem pedido.

### Pendências
- Sem novas pendências.

---

## 2026-07-06 - Preparação para deploy no VPS

### Resumo
Preparado o projeto para rodar em produção no VPS sem alterar o comportamento local. As configurações sensíveis
e específicas do servidor agora podem vir de variáveis de ambiente, permitindo usar SQLite persistente fora do
repositório, `DEBUG=False`, hosts/CSRF corretos, arquivos estáticos coletados e publicação em subcaminho com
`DJANGO_FORCE_SCRIPT_NAME`.

### Arquivos criados/alterados
- `config/settings.py`: lê `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`,
  `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_SQLITE_PATH`, `DJANGO_FORCE_SCRIPT_NAME`, `DJANGO_STATIC_URL`,
  `DJANGO_STATIC_ROOT`, `DJANGO_MEDIA_URL` e `DJANGO_MEDIA_ROOT`; adiciona `STATIC_ROOT` e proxy HTTPS.
- `requirements.txt`: adiciona `gunicorn` para execução via systemd/Gunicorn no VPS.
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md` e `docs/README_PROJETO.md`: documentação atualizada.

### Decisões tomadas
- Manter os padrões locais quando as variáveis não existem, para não atrapalhar o desenvolvimento.
- Usar configuração por ambiente no VPS, sem versionar segredo, banco ou uploads.

### Pendências
- Concluir a configuração no VPS: clone via GitHub, env file, serviço systemd, Nginx no subcaminho temporário e
  atalho global de deploy.

---

## 2026-07-06 - WhatsApp: preserva ID e token salvos

### Resumo
Reforçada a persistência da configuração do WhatsApp/W-API. A configuração já ficava no banco via
`WhatsappConfig`, mas o ID da instância podia ser apagado se o formulário fosse enviado com o campo vazio. Agora
ID da instância e token seguem a mesma regra: só são substituídos quando um novo valor é digitado.

### Arquivos criados/alterados
- `core/views.py`: `whatsapp_config_view` preserva `instance_id` quando o POST vem vazio, assim como já fazia
  com o token.
- `templates/core/whatsapp.html`: texto da tela deixa claro que novo ID/token só devem ser digitados para troca.
- `core/tests.py`: teste automatizado garantindo que campos vazios não apagam ID/token salvos, chamando a view
  diretamente para não depender do prefixo `/sistema-novo` do ambiente de produção.
- `docs/ESTADO_ATUAL.md` e `docs/HISTORICO_ALTERACOES.md`: documentação atualizada.

### Validação
- `python manage.py test core.tests.WhatsappConfigTests` OK.
- `python manage.py check` OK.

### Pendências
- Sem novas pendências.

---

## 2026-07-06 - Importação inicial do banco e mídias locais no VPS

### Resumo
Enviado para o novo sistema online o banco SQLite local e todos os arquivos da pasta `media/`, já que esses dados
não passam pelo GitHub. A importação foi feita apenas na instalação nova (`pinhaljunior2`), sem tocar no sistema
antigo do domínio raiz.

### Arquivos/configurações envolvidos
- Local: `db.sqlite3` e `media/` empacotados temporariamente para transferência.
- VPS: `/var/www/pinhaljunior2/data/db.sqlite3` substituído pelo banco local.
- VPS: `/var/www/pinhaljunior2/media` substituída pela pasta `media/` local.
- VPS: backup prévio salvo em `/var/www/pinhaljunior2/backup/local_before_import_<timestamp>/`.

### Validação
- `manage.py check` OK no VPS.
- `migrate --noinput` sem migrations pendentes.
- Serviço `pinhaljunior2.service` reiniciado e ativo.
- Contagem validada no banco importado: 37 usuários, 39 aventureiros e 36 aventureiros ativos.
- Arquivo de mídia validado com HTTP 200 em `/sistema-novo/media/`.

### Decisões tomadas
- Remover os pacotes temporários com dados sensíveis após a importação.
- Manter backup do banco/media anteriores do VPS, mesmo sendo a instalação nova.

### Pendências
- Sem novas pendências.

---

## 2026-07-06 - Deploy inicial no VPS em /sistema-novo

### Resumo
Publicado o sistema novo no VPS, sem substituir o sistema antigo do domínio principal. A nova versão responde em
`https://pinhaljunior.com.br/sistema-novo/`, usando serviço, banco, media, staticfiles e comando de deploy próprios.
O sistema antigo continua no domínio raiz e no serviço `sitepinhal.service`.

### Arquivos/configurações criados ou alterados no VPS
- `/var/www/pinhaljunior2/current`: clone do repositório GitHub.
- `/var/www/pinhaljunior2/.venv`: ambiente virtual Python do novo sistema.
- `/var/www/pinhaljunior2/data/db.sqlite3`: banco SQLite persistente da nova versão.
- `/var/www/pinhaljunior2/media` e `/var/www/pinhaljunior2/staticfiles`: uploads e estáticos coletados.
- `/etc/pinhaljunior2.env`: variáveis de produção, incluindo prefixo `/sistema-novo`.
- `/etc/systemd/system/pinhaljunior2.service`: Gunicorn em `127.0.0.1:8010`.
- `/usr/local/bin/pinhaljunior2-deploy`: deploy global via GitHub, com backup do SQLite, migrations,
  collectstatic, restart e healthcheck.
- `/etc/nginx/sites-available/sitepinhal`: adicionadas apenas as rotas `/sistema-novo/`,
  `/sistema-novo/static/` e `/sistema-novo/media/`; backup criado antes da alteração.

### Validação
- `pinhaljunior2-deploy` concluiu com healthcheck OK.
- `nginx -t` OK e reload aplicado.
- `https://pinhaljunior.com.br/sistema-novo/` respondeu `200`.
- `https://pinhaljunior.com.br/sistema-novo/static/css/login.css` respondeu `200`.
- Login real com `Fabiano` retornou `302` para `/sistema-novo/inicio/`.
- Serviços `pinhaljunior2.service`, `nginx` e `sitepinhal.service` ficaram ativos.

### Pendências
- Trocar a senha inicial do usuário diretor `Fabiano`.
- Configurar dados reais de produção e integrações de pagamento quando a etapa de gateway começar.

---

## 2026-07-06 - Cadastro: assinatura desenhada dos 3 documentos da inscrição

### Resumo
Voltou (do sistema antigo) a **assinatura desenhada** (dedo/mouse, estilo Canva) na inscrição do aventureiro.
O responsável assina **3 documentos** — ficha de inscrição, declaração médica e termo de autorização de imagem
— e a **assinatura substitui o checkbox de aceite** (assinar = aceitar). Cada assinatura vira um **documento de
assinatura** guardado (imagem PNG + **texto do termo preenchido no momento**), para que o **Diretor** consiga
depois gerar/imprimir o **termo assinado** de cada pessoa. O responsável **não** vê a própria assinatura depois
(só o status "assinado em ..."); a imagem/termo assinado é acessível **só pelo Diretor**.

### Arquivos criados/alterados
- `core/termos.py` (novo): textos canônicos dos 3 termos, já preenchidos com os dados (fonte única).
- `core/models.py`: model **`AssinaturaDocumento`** (aventureiro, documento, imagem, titulo/texto snapshot,
  assinante_nome/cpf, assinado_em; único por aventureiro+documento). Migration `0030_assinaturadocumento`.
- `core/views.py`: `_decode_signature` (base64→PNG), `_validar_aceites` agora exige as 3 assinaturas,
  `_salvar_aventureiro`/`_salvar_assinaturas` criam os 3 registros; `_preparar_assinaturas` anota status;
  nova view `aventureiro_termos_view` (Diretor) para o termo assinado; `prefetch_related("assinaturas")`.
- `core/urls.py`: rota `usuarios/aventureiro/<pk>/termos/`.
- `core/forms.py`: `mensalidade_isento`/`mensalidade_desconto_pct` deixam de ser obrigatórios no cadastro
  público (Diretor define depois em Mensalidades) — **corrige** um travamento pré-existente do cadastro.
- `core/admin.py`: registro de `AssinaturaDocumento`.
- Templates: `_assinatura_doc.html` (novo, bloco reutilizável), `aventureiro_termos.html` (novo, pág. de
  impressão do Diretor), `cadastro.html` (blocos de assinatura nas etapas 5, 6 e revisão; termo de imagem
  interpolado com os dados), `_aventureiro_detalhe.html` (status assinado + link só Diretor),
  `usuarios.html` (passa `pode_ver_termos=True`).
- Estáticos: `static/js/assinatura.js` (novo, pad em canvas com pointer events, sem lib),
  `static/js/cadastro.js` (validação por assinatura + revisão + interpolação do termo), `static/css/cadastro.css`
  (pad/modal/preview), `static/css/inicio.css` (link "Ver termos assinados").

### Decisões tomadas
- **Sem biblioteca**: canvas + pointer events (dedo e mouse), como no sistema antigo.
- Snapshot do texto do termo no ato da assinatura → o termo assinado é reconstruível mesmo se o cadastro mudar.
- Imagens em `media/assinaturas/` (git-ignored, dado pessoal) — nunca versionar.
- Página do Diretor pronta para impressão (`@media print`) — salva PDF pelo navegador, sem lib de PDF.

### Pendências
- Assinatura na diretoria (quando o cadastro de diretoria for implementado) pode reusar o mesmo padrão.

---

## 2026-07-06 - Loja/Vendas: relatório "Pedido para o fornecedor" (só o que falta entregar)

### Resumo
Nova seção na aba **Vendas** da Loja: **"📦 Pedido para o fornecedor"** — por **produto → variação**
(tamanho/item), mostra **só o que falta entregar** (= exatamente o que pedir ao fornecedor). Variações e
produtos **já 100% entregues não aparecem**; quando não há nada pendente, mostra "✅ Tudo entregue — nada a
pedir". (Primeira versão trazia colunas Vendido/Entregue + toggle; a pedido do usuário ficou só "A entregar",
sem dados desnecessários.) Ex.: Camiseta por tamanho, Uniforme de Gala por item, Laço.

### Arquivos alterados
- `core/views.py`: `_loja_relatorio` agrega `fornecedor` só com itens `falta_entregar > 0` (por produto/variação).
- `templates/core/loja.html`: seção "Pedido para o fornecedor" (antes de "Todas as compras"), coluna única
  "A entregar" + estado vazio.
- `static/css/loja.css`: estilos `.loja-forn-*`.

### Validação
- `manage.py check` OK. Render (test client): tudo entregue → mostra "Tudo entregue"; ao desmarcar 1 item, o
  relatório lista só aquela variação com a quantidade a entregar.

---

## 2026-07-06 - Financeiro: fim do "rateio" + contas Disponível × Reservado (loja)

### Resumo
A pedido do usuário, **removido o "rateio"** dos custos gerais (era confuso). Os **4 cards** do topo voltaram a
mostrar o **líquido de cada fonte** (Mensalidades, Loja, Eventos, Custos gerais) — visão de "quem gera mais
lucro/prejuízo". E entrou o modelo de **duas contas** que o usuário descreveu:
- **💚 Disponível pra gastar** = Mensalidades + **lucro dos eventos** − Custos gerais do clube (dinheiro livre).
- **🔒 Reservado da loja** = Vendas − pagamento a fornecedores (travado; não é lucro do clube).
As duas somam o resultado líquido. Custo **geral** sai do disponível; custo com destino **loja** sai do
reservado (usa o `destino` que já existe — sem rateio).

### Arquivos alterados
- `core/views.py`: `financeiro_view` remove o cálculo de contribuição/rateio; calcula `disponivel`,
  `reservado_loja` e `lucro_eventos`.
- `templates/core/financeiro.html`: 4 cards voltam ao líquido; novo bloco `.fin-contas` (Disponível × Reservado).
- `static/css/financeiro.css`: estilos `.fin-contas`/`.fin-conta*` (borda verde = livre, âmbar = travado).

### Validação
- `manage.py check` OK. Render (test client): cards Mensalidades R$ 3.174,00 · Loja R$ 808,50 · Eventos
  R$ 3.392,29 · Custos gerais −R$ 2.834,79; **Disponível R$ 3.731,50** + **Reservado (loja) R$ 808,50** =
  Resultado R$ 4.540,00.

### Pendências
- Filtro por período (hoje tudo é acumulado desde o início do clube).

---

## 2026-07-06 - Financeiro: "Onde está o dinheiro" simplificado (só banco + espécie)

### Resumo
A pedido do usuário, o card "Onde está o dinheiro" ficou com **duas linhas**: **na conta (banco)** e **em
espécie (caixa físico)**. Removida a linha **"a receber (empréstimos)"** — o valor do empréstimo entra **somado
no saldo do banco** (ex.: banco 2.808,00 + empréstimo 1.276,98 = **4.084,98** informado como banco), e a
**espécie** continua sendo o restante calculado (resultado − banco = **455,02**). O modal de edição passou a ter
só o campo do saldo do banco.

### Arquivos alterados
- `core/models.py`: remove `CaixaClube.a_receber` (migration **0029**). `core/forms.py`: `CaixaClubeForm` só com
  `saldo_banco`. `core/views.py`: `caixa_especie = resultado − saldo_banco`.
- `templates/core/financeiro.html`: card e modal sem a linha/campo "a receber".

### Validação
- `manage.py check` OK; `migrate` (0029). Render (test client): card com Banco R$ 4.084,98 + Espécie R$ 455,02
  = Resultado R$ 4.540,00; modal só com o saldo do banco; POST salva.

---

## 2026-07-06 - Financeiro: cards por contribuição + card "Onde está o dinheiro"

### Resumo
Reorganização do Resumo do Financeiro a pedido do usuário:
- **Cards do topo** (Mensalidades, Loja, Eventos) agora mostram **quanto cada fonte contribui no resultado**
  (o líquido **já com o rateio dos custos gerais**), com **% do resultado**, em vez do total de vendas/receita.
  As três **somam exatamente** o resultado líquido (resolve a confusão de "os cards não batem"). O card solto
  **"Custos gerais do clube"** saiu do topo (já entra rateado nas fontes e segue no quadro "Como o resultado se
  forma").
- **Removido** o card separado "Quanto cada fonte contribui no resultado" (o conteúdo virou os cards do topo);
  **mantido** o quadro "Como o resultado líquido se forma".
- **Novo card "Onde está o dinheiro"**: mostra **na conta (banco)** + **a receber (empréstimos/pendências)** +
  **em espécie (caixa físico)** = resultado líquido. O Diretor informa banco e a receber (modal ✏️ com máscara
  de moeda); a **espécie é calculada** (resultado − banco − a receber). Se ficar negativa, avisa pra conferir.

### Arquivos criados/alterados
- `core/models.py`: modelo **`CaixaClube`** (singleton `get_solo`: `saldo_banco`, `a_receber`). Migration **0028**.
- `core/forms.py`: `CaixaClubeForm` (banco/a_receber com `data-moeda`).
- `core/views.py`: `financeiro_view` agrega `contrib`/`rateio`/`pct` em cada fonte do `resumo` e calcula
  `caixa`/`caixa_especie`; nova `caixa_editar_view` (POST). `core/urls.py`: rota `financeiro/caixa/`.
- `templates/core/financeiro.html`: cards do topo por contribuição (3, sem o de custos gerais); remove o card
  de contribuição; card "Onde está o dinheiro" + modal de edição.
- `static/js/financeiro.js`: `ligarModal` genérico (custo + caixa). `static/css/financeiro.css`: `.fin-caixa*`
  e `.fin-fontes-intro` (remove `.fin-contrib*`).

### Validação
- `manage.py check` OK; `migrate` (0028). Render (test client, Diretor): cards mostram contribuição
  (Mensalidades R$ 1.953,95 · 43,0%, Loja R$ 497,72 · 11,0%, Eventos R$ 2.088,33 · 46,0%); card "Onde está o
  dinheiro" com Banco R$ 2.808,00 + A receber R$ 1.276,98 + Espécie R$ 455,02 = Resultado R$ 4.540,00. POST de
  edição do caixa salva (valores restaurados após o teste).

### Pendências
- Sem novas. (Rateio dos custos gerais é proporcional ao líquido; ajustável se quiserem outro critério.)

---

## 2026-07-06 - Financeiro: quadro "Quanto cada fonte contribui no resultado"

### Resumo
Os cards de "líquido por fonte" **não somavam** o resultado, porque os **custos gerais do clube** ficam num
balde à parte (não pertencem a nenhuma fonte) — então Mensalidades + Loja + Eventos dava mais que o resultado
líquido. Novo quadro na aba **Resumo** que **rateia os custos gerais** entre as fontes (proporcional ao líquido
de cada uma) e mostra, por fonte, **quanto ela contribui no resultado** (valor + **% do resultado** com barra),
de modo que as três **somam exatamente** o resultado líquido. O rateio é uma **escolha** (custo geral não é
"causado" por uma fonte); usei o critério proporcional, o mais comum.

### Arquivos alterados
- `core/views.py` (`financeiro_view`): calcula `contribuicao` (líquido de cada fonte − rateio dos custos gerais,
  contribuição, % e largura da barra) e `custos_gerais_total`; adiciona ao contexto.
- `templates/core/financeiro.html`: card `.fin-contrib` (3 fontes + barra de % + linha de total) após o quadro
  "Como o resultado líquido se forma".
- `static/css/financeiro.css`: estilos do card (barras nas cores das fontes: azul/verde/amarelo).

### Validação
- `manage.py check` OK. Render (test client, Diretor): quadro presente com Mensalidades **R$ 1.941,97 (47,5%)**,
  Loja **R$ 494,67 (12,1%)**, Eventos **R$ 1.648,34 (40,4%)**, somando **R$ 4.084,98**; barras 48/12/40%.

### Pendências
- Sem novas. (Critério de rateio dos custos gerais é ajustável se o clube preferir outro.)

---

## 2026-07-06 - Máscara de moeda pt-BR no "valor recebido" do PDV (troco corrigido)

### Resumo
Estende a máscara de moeda pt-BR ao campo **"Valor recebido (dinheiro)"** dos dois balcões — **PDV de venda**
(`evento_pdv.html`) e **PDV de inscrição** (`evento_pdv_inscricao.html`). Como o campo agora mostra
`1.234,56`, o **cálculo de troco ao vivo** foi ajustado: em vez de `parseFloat(value.replace(",","."))` — que
**quebraria** com o separador de milhar (`"1.234,56"` → `1.234`) — o JS passou a ler **os dígitos como
centavos** (`value.replace(/\D/g,"")/100`), batendo exatamente com o valor exibido. Back-end inalterado (já
fazia `replace(",",".")` e trata vazio/ inválido).

### Arquivos alterados
- `templates/core/evento_pdv.html` e `evento_pdv_inscricao.html`: `valor_recebido` vira `type=text data-moeda`;
  ambos carregam `moeda_br.js`.
- `static/js/evento_pdv.js` e `evento_insc_cupom.js`: leitura do recebido por dígitos/centavos (não `parseFloat`).

### Validação
- `manage.py check` OK. Render (test client, evento futuro temporário): ambos os PDVs carregam `moeda_br.js` e o
  recebido vem `type=text data-moeda`. Simulação do parse: `"1.234,56"` → `1234.56` (o antigo dava `1.234`).
  POST de venda em dinheiro (item R$ 35,00, recebido `50.00`): pedido criado com **total 35,00 · recebido 50,00
  · troco 15,00**. (Evento/produto temporários removidos após o teste.)

### Pendências
- Sem novas.

---

## 2026-07-06 - Máscara de moeda pt-BR nos preços de produto e custos de evento (fecha a pendência)

### Resumo
Fecha a pendência recorrente "aplicar a **máscara de moeda pt-BR** também aos **preços de produto da loja**
e aos **custos de evento** (ainda `type=number`)". Agora **todos** os campos de valor R$ do sistema usam o
padrão `moeda_br.js` (mostram `1.234,56` ao digitar e enviam o valor limpo `1234.56`). Migrados:
- **Loja do Clube** — preço da variação (`_loja_var_linha.html`).
- **Lojinha de evento** — preço da variação (`_variacao_linha.html`).
- **Evento** — **custo** (modal, `CustoEventoForm.valor`), **faixa etária** (`FaixaEtariaPrecoForm.valor`) e
  **valor da diretoria** (`EventoInscricaoConfigForm.valor_diretoria`).

Para cobrir os campos renderizados pelo Django e as **linhas de variação adicionadas por JS**, o
`moeda_br.js` ganhou um **modo inline**: um único `input[type=text] data-moeda` (sem campo oculto) formata
enquanto digita e é **normalizado para o valor limpo pouco antes do `submit`** (listener global em captura,
que ignora os campos do modo par visível+oculto, com `data-moeda-alvo`). Assim o back-end **não muda**
(continua recebendo `1234.56`; o parser das variações já fazia `replace(",", ".")`).

### Arquivos alterados
- `static/js/moeda_br.js`: modo inline (normalização no `submit`, em captura) + doc dos dois modos.
- `core/forms.py`: `CustoEventoForm.valor`, `FaixaEtariaPrecoForm.valor` e `EventoInscricaoConfigForm.valor_diretoria`
  passam de `NumberInput` para `TextInput` com `data-moeda`/`inputmode=decimal`/`placeholder=0,00`.
- `templates/core/_loja_var_linha.html` e `_variacao_linha.html`: preço vira `type=text data-moeda` (o
  `<template>` de clonagem usa os mesmos parciais, então linhas novas já nascem com a máscara).
- `templates/core/evento_painel.html`, `loja_produto_form.html`, `evento_produto_form.html`: carregam
  `moeda_br.js`.

### Decisões tomadas
- **Modo inline** em vez de par visível+oculto para os campos de formulário Django e as linhas repetíveis —
  evita ter de gerar um `<input hidden>` por linha e mantém a renderização padrão do Django (com erros do
  form). O modo par (com `data-moeda-alvo`) continua para os modais de custo do Financeiro/Loja.
- `valor_recebido` do PDV (troco ao vivo) e campos de **percentual/idade/estoque/quantidade** ficam como
  estão (não são preço em R$).

### Validação
- `manage.py check` OK. Render (test client, Diretor): as 3 telas carregam `moeda_br.js`; preço da loja e da
  lojinha de evento com `type=text data-moeda` (sem `type=number` sobrando); painel do evento com 3 campos
  `data-moeda` e nenhum `type=number step=0.01`. Forms validam com valor limpo: custo `1234.56`, faixa
  `40.00`, diretoria `25.50` (POST do custo gravou `1234.56`).

### Pendências
- Sem novas. (Todos os campos de valor R$ agora usam a máscara.)

---

## 2026-07-06 - Financeiro: quadro "Como o resultado líquido se forma" (esclarece a soma)

### Resumo
> Registro retroativo (o commit `d0fc5d8` foi feito sem atualizar os docs).

Os líquidos das 3 fontes não somavam sozinhos o resultado porque há os **custos gerais do clube** (que saem
do caixa comum). Adiciona um **quadro de composição** explícito na aba Resumo do Financeiro:
`mensalidades + loja + eventos − custos gerais = resultado líquido`, com nota explicativa. O rótulo dos cards
de fonte muda de "líquido no caixa" para **"líquido da fonte"**.

### Arquivos alterados
- `templates/core/financeiro.html`: quadro `.fin-composicao` (lista dos líquidos por fonte − custos gerais =
  resultado) + nota; rótulo dos cards → "líquido da fonte".
- `static/css/financeiro.css`: estilos do quadro de composição.

---

## 2026-07-06 - Financeiro: líquido por fonte + custos da loja + reclassificação + fluxo ao fundo

### Resumo
O clube tem **uma conta só**, então os cards de resumo agora mostram o **líquido de cada fonte** (quanto do
dinheiro no caixa é de cada uma): **Mensalidades** (recebido), **Loja** (vendas − custos da loja),
**Eventos** (entradas − custos de evento) e **Custos gerais do clube** (gastos que não são de loja/eventos).
Os líquidos **somam o Resultado líquido** total. Para isso, o **custo do clube ganhou `destino`** (Geral do
clube / Loja): custo com destino "loja" abate no líquido da loja. A **loja** ganhou, na aba Vendas, uma seção
**"Custos / pagamentos da loja"** (pagamento de fornecedores, ex.: uniformes) com o **resultado da loja** e um
botão **"Lançar custo da loja"** (modal, valor com máscara, comprovantes). **Reclassificados** os custos
importados: *Pagamento Uniformes de Gala* → **loja**; *Aluguel Decoração Acampamento* → **custo do evento**
Acampamento (movido para `CustoEvento`); os demais seguem como **gerais**. Ajuste visual: o gráfico de **fluxo
mensal** foi empurrado para a **base do card** (sem espaço em branco embaixo).

### Arquivos alterados
- `core/models.py`: `CustoClube.destino` (geral/loja; mig. **0027**). `core/forms.py`: campo `destino`.
- `core/views.py`: `financeiro_view` (líquido por fonte usando destino), `custo_clube_novo_view` (volta à
  loja quando destino/`de`=loja), `loja_view` (custos da loja + resultado).
- `templates/core/financeiro.html`: cards com líquido + tag; destino no modal de custo.
- `templates/core/loja.html`: seção "Custos/pagamentos da loja" + modal (máscara + comprovantes) na aba Vendas.
- `static/css/financeiro.css` (líquido/fluxo ao fundo) e `static/css/loja.css` (custos da loja).

### Decisões tomadas
- Custo de **evento** vira `CustoEvento` (aparece no painel do evento e no Financeiro); custo de **loja** é
  `CustoClube` com destino=loja; o resto é `CustoClube` geral. Os líquidos por fonte somam o resultado total.

### Pendências
- Máscara pt-BR nos **preços de produto da loja** e **custos de evento** (ainda `type=number`).

---

## 2026-07-06 - Financeiro: ajustes (custos importados, KPI, cards, custo em modal, máscara R$, extrato)

### Resumo
Vários ajustes no Financeiro: (1) KPI "Resultado" → **"Resultado líquido"**. (2) **Importados os custos do
clube** do sistema antigo (`financeirocomprovante`: 14 lançamentos, R$ 5.066,60, com comprovantes) — antes
estava zerado. (3) **Donut** de entradas por fonte **centralizado** no card e os dois cards de gráfico com a
**mesma altura**; nos cards de resumo por fonte, os botões "Ver …" ficam **fixos no rodapé**. (4) **Custos do
clube**: a aba agora tem só o botão **"➕ Lançar custo"** que abre um **modal**; sem campo de data (usa a data
do lançamento); permite **vários comprovantes** por custo (novo modelo `ComprovanteCustoClube`). (5) **Máscara
de moeda pt-BR** (`moeda_br.js`): campos de valor formatam `1.234,56` ao digitar e enviam o valor limpo —
aplicada ao custo do clube e aos valores de mensalidade (padrão documentado no CLAUDE.md). (6) **Corrigido o
extrato**: os **filtros por fonte** (chips) e a **busca** não escondiam nada — `.fin-lanc` tinha `display:flex`
sobrepondo o atributo `hidden`; corrigido com `.fin-lanc[hidden]{display:none}`.

### Arquivos criados/alterados
- `core/models.py`: `ComprovanteCustoClube` (mig. **0026**). `core/forms.py`: `CustoClubeForm` sem data/
  comprovante único. `core/admin.py`: inline de comprovantes.
- `core/views.py`: `custo_clube_novo_view` (data automática + múltiplos comprovantes); extrato usa 1º
  comprovante.
- `templates/core/financeiro.html`: KPI, custos via modal, comprovantes múltiplos; `mensalidades.html`: valores
  com máscara. `static/js/moeda_br.js` (novo); `financeiro.js` (abre modal); `financeiro.css` (donut/alturas/
  rodapé/`[hidden]`).

### Pendências
- Aplicar a máscara pt-BR também aos **preços de produto da loja** e **custos de evento** (ainda `type=number`).

---

## 2026-07-05 - Módulo Financeiro geral (mensalidades + loja + eventos + custos do clube)

### Resumo
Novo item **"Financeiro"** (📈, só Diretor) que **consolida as três frentes** — mensalidades, loja e eventos —
num só lugar. Tem **KPIs** (Entradas, Saídas, Resultado com selo positivo/negativo), **3 abas**:
- **Resumo**: **resumo por fonte** (cards de Mensalidades, Loja, Eventos com inscrições/lojinha/custos/
  resultado, e Custos do clube), **donut** de entradas por fonte e **gráfico de fluxo mensal** (entradas ×
  saídas por mês, CSS puro).
- **Extrato**: **extrato consolidado único** (mensalidades pagas, compras da loja, inscrições e lojinha de
  eventos como entradas; custos de evento e do clube como saídas), **cronológico**, com **filtro por fonte**
  (chips) + busca; cada lançamento com data, badge da fonte, valor (+verde/−vermelho) e link do comprovante.
- **Custos do clube**: **lançar** gastos gerais do clube (descrição, valor, data, **comprovante** anexo) e
  listar/remover — igual aos custos de evento, mas do clube.
Tudo responsivo (mobile/desktop). Números batem com cada módulo (entrada por lá para detalhes finos).

### Arquivos criados/alterados
- `core/models.py`: modelo **`CustoClube`** (nome, valor, data, comprovante). Migration **0025**.
- `core/forms.py`: `CustoClubeForm`. `core/admin.py`: `CustoClube`.
- `core/views.py`: `financeiro_view` (agrega as 3 fontes + custos, monta resumo/extrato/fluxo/donut),
  `custo_clube_novo_view`, `custo_clube_excluir_view`, helper `_dt_data`.
- `core/urls.py`: rotas `financeiro/…`. `templates/core/_menu.html`: item "Financeiro" (📈, Diretor).
- `templates/core/financeiro.html`; `static/js/financeiro.js`; `static/css/financeiro.css`.

### Decisões tomadas
- **Um extrato único** com filtro por fonte (em vez de extratos separados) — mais fácil de ver o todo e
  segmentar quando quiser. Entradas = mensalidades pagas + loja + (inscrições + lojinha de eventos); Saídas =
  custos de evento + custos do clube. Cancelados não entram. Custos do clube ficam em `media/` (git-ignored).

### Pendências
- Filtro por período/ano no extrato; exportar; gráficos por evento. Financeiro é consolidação — o detalhe fino
  fica em cada módulo.

---

## 2026-07-05 - Mensalidades: aventureiro inativo não interfere nos totais (mantém só dados anteriores)

### Resumo
Aventureiro **inativo** deixou de interferir no resumo/relatório de mensalidades — ficam só os **dados de
antes** de ele ficar inativo. Regra: **Recebido** conta **todas as cobranças pagas** (histórico, mesmo de
quem depois saiu); **Em aberto/Previsto** contam **só de aventureiros ativos**. Antes, os totais ignoravam os
pagamentos de inativos (some da lista) e o dashboard ainda somava as cobranças em aberto deles — agora está
consistente. O **reajuste em massa** também **pula inativos**. (Loja e eventos já respeitavam: a loja usa
registros históricos das compras; a cobertura/presença de eventos contam só ativos.) Os aventureiros da conta
de **teste** foram marcados **inativos** (a conta `teste_responsavel` segue ativa para os testes).

### Arquivos alterados
- `core/views.py`: `mensalidades_view` (totais: recebido = todos os pagos; em aberto = só ativos),
  `_mensalidades_dashboard` (idem por mês) e `mensalidade_reajustar_view` (só `aventureiro__ativo=True`).

---

## 2026-07-05 - Mensalidades: valores/reajuste viram botões+modais; oculta meses sem cobrança

### Resumo
A barra ficava poluída com os formulários de "Valores padrão" e "Reajustar" inline. Agora são **dois botões**
claros — **"💲 Valores da mensalidade"** e **"🔁 Reajustar mensalidades"** — que abrem **janelas (modais)**
com o respectivo formulário e um texto explicando o que faz (fechamento seguro mousedown+click). No dashboard,
os **cards de "Detalhe por mês"** deixam de mostrar os meses **sem cobrança** (ex.: Janeiro não aparece mais).

### Arquivos alterados
- `templates/core/mensalidades.html`: barra com 2 botões + modais "Valores"/"Reajustar"; cards só de meses
  com cobrança.
- `static/js/mensalidades.js`: `ligarModalBotao` (abre/fecha os modais por botão, com fechamento seguro).
- `static/css/mensalidades.css`: barra de ações e formulários dos modais.

---

## 2026-07-05 - Mensalidades: "Detalhe por mês" vira cards didáticos (corrige tabela sem estilo)

### Resumo
No dashboard, o "Detalhe por mês" era uma **tabela sem estilo** (usava classe da loja não carregada aqui).
Trocado por **cards mês a mês** mais didáticos: cada mês mostra a **% paga** com **barra de progresso
colorida** (verde ≥80%, amarelo ≥40%, vermelho abaixo), **nº de pagas / em aberto / isentos** e os valores
**recebido / a receber**. Meses sem cobrança aparecem esmaecidos ("Sem cobranças"). Nota deixando claro que o
resumo **conta inscrições + mensalidades**.

### Arquivos alterados
- `core/views.py`: `_mensalidades_dashboard` inclui `cor` (faixa de desempenho) por mês.
- `templates/core/mensalidades.html`: tabela → grade de cards mês a mês.
- `static/css/mensalidades.css`: estilos dos cards (barra de progresso colorida, contagens, valores).

---

## 2026-07-05 - Mensalidades: reajuste em massa a partir de um mês + modais não fecham ao arrastar

### Resumo
Dois pontos: (1) **Reajuste em massa** — na barra de valores há agora "🔁 Aplicar os valores atuais às
cobranças **em aberto** a partir de [mês]" + **Reajustar**: recalcula todas as cobranças **em aberto** do ano,
do mês escolhido em diante, com o **valor atual da configuração** (respeitando isenção/desconto de cada
aventureiro; **pagas não mudam**). Assim dá para "a partir do próximo mês a mensalidade passa a ser R$ X para
todos". (2) **Correção de modais**: o modal de editar mês (mensalidades) e os modais da loja (aviso de
obrigatórios e lightbox) fechavam ao **arrastar uma seleção de dentro para fora**; agora só fecham se o clique
**começar e terminar no fundo** (padrão `mousedown`+`click`, [[modais-fechamento-seguro]]).

### Arquivos alterados
- `core/views.py`: `mensalidade_reajustar_view`; contexto ganha `meses`/`mes_atual`. `core/urls.py`: rota.
- `templates/core/mensalidades.html`: form de reajuste na barra. `static/css/mensalidades.css`: estilo.
- `static/js/mensalidades.js` e `static/js/loja_produto.js`: fechamento seguro dos modais (mousedown+click).

---

## 2026-07-05 - Mensalidades: dashboard mês a mês (abas Resumo / Aventureiros)

### Resumo
A tela de Mensalidades ganhou **abas**: **Resumo** (dashboard) e **Aventureiros** (a lista operacional que já
existia). O **Resumo** mostra a visão geral do ano: um **donut de taxa de pagamento** (recebido ÷ previsto)
com a legenda recebido × em aberto, um **gráfico de barras mês a mês** (recebido em verde, em aberto em
amarelo, empilhados; CSS puro, sem libs; rolagem horizontal no celular) e uma **tabela "Detalhe por mês"**
(pagas, em aberto, recebido, a receber, % pago, com linha de total). Tudo respeita o **ano** selecionado.

### Arquivos alterados
- `core/views.py`: `_mensalidades_dashboard(mens)` (agrupa por mês: recebido/aberto/% + alturas das barras);
  `mensalidades_view` passa `dashboard`, `taxa` e `aba`.
- `templates/core/mensalidades.html`: abas + painel Resumo (donut, gráfico, tabela); lista vira painel
  "Aventureiros".
- `static/js/mensalidades.js`: alternância das abas (com `?aba=`). `static/css/mensalidades.css`: abas,
  donut (conic-gradient), gráfico de barras, tabela.

---

## 2026-07-05 - Mensalidades: edição por mês vira desconto % (com valor ao vivo) + remove "Gerar cobranças"

### Resumo
Refinos a pedido do usuário: (1) no modal de edição por mês, em vez de digitar o valor, agora se informa a
**% de desconto** e o **valor resultante aparece ao vivo** ("Ficará: R$ X — valor cheio: R$ Y"); "Isentar
este mês" = 100%. O servidor calcula o valor a partir do **valor cheio** (config) × (1 − %). (2) **Removido o
botão "Gerar cobranças <ano>"** do topo — desnecessário, pois o cadastro do aventureiro já gera as cobranças
do mês atual até dezembro automaticamente. (A geração por aventureiro sem cobranças continua disponível.)

### Arquivos alterados
- `core/views.py`: `mensalidade_editar_view` passa a receber `desconto_pct` e calcular o valor a partir da base.
- `templates/core/mensalidades.html`: modal com "% de desconto" + preview; `data-base` no botão ✏️; remove
  a barra "Gerar cobranças".
- `static/js/mensalidades.js`: preview ao vivo (base × desconto). `static/css/mensalidades.css`: preview.

---

## 2026-07-05 - Mensalidades: import do histórico + isenção/desconto por mês + valores visíveis

### Resumo
Três ajustes: (1) **Importado o histórico** de mensalidades do sistema antigo (352 cobranças de 2026, **104
pagas**, R$ 3.120 recebido; casadas pelo **nome** do aventureiro — pulou só 1 registro "teste"). As
cobranças respeitam os meses reais (ex.: quem entrou em fevereiro tem Fev=inscrição em diante). (2) **Isenção/
desconto por mês específico**: cada mês em aberto tem um botão **✏️** que abre um modal para **mudar o valor
daquele mês** (desconto pontual) ou **isentar só aquele mês** (endpoint `mensalidade_editar`). Continua
existindo a isenção/desconto do aventureiro inteiro. (3) **Valores padrão** agora aparecem preenchidos
(R$ 30,00) — antes o `<input type=number>` rejeitava o decimal localizado e ficava vazio; corrigido com
`stringformat`.

### Arquivos alterados
- `core/views.py`: `mensalidade_editar_view` (edita/isenta um mês; não mexe em pagas). `core/urls.py`: rota.
- `templates/core/mensalidades.html`: botão ✏️ por mês + modal de edição; inputs de valores padrão com
  `stringformat:'.2f'` (mostram o valor).
- `static/js/mensalidades.js`: abrir/preencher o modal de edição. `static/css/mensalidades.css`: botão e modal.

### Decisões tomadas
- Import é **fonte da verdade** de 2026 (apaga as cobranças e recria a partir do antigo). Dados ficam no
  banco local (não versionados). Edição por mês não altera cobranças **pagas** (desfazer o pagamento antes).

---

## 2026-07-05 - Módulo Mensalidades

### Resumo
Novo módulo **"Mensalidades"** (💰, só Diretor), separado do financeiro. Cada aventureiro tem, por mês do
ano, uma **cobrança**: o mês em que se inscreve nasce como **"inscrição"** e os meses seguintes como
**"mensalidade"** (gerado **automaticamente** no cadastro). **Valores configuráveis** (padrão R$ 30 cada, em
`ConfigMensalidade`). Aventureiros podem ser **isentos** ou ter **desconto %** — aplicável às cobranças em
aberto. Tela com **KPIs** (previsto/recebido/em aberto/isentos do ano), **seletor de ano**, botão **"Gerar
cobranças <ano>"** (todos ou um), e por aventureiro (card expansível) os **12 meses** com **marcar pago/
desfazer** (forma de pagamento, sem recarregar) + controle de isenção/desconto. **Busca** e filtro **"Só quem
deve"**. Contas de mensalidade ficam no banco local (não versionadas).

### Arquivos criados/alterados
- `core/models.py`: `ConfigMensalidade` (singleton) e `Mensalidade` (aventureiro, ano, mês, tipo, valor,
  isento, status, forma/valor_pago/pago_em); campos `Aventureiro.mensalidade_isento` e
  `mensalidade_desconto_pct`; constantes `MESES_PT`. Migration **0024**.
- `core/views.py`: `_gerar_mensalidades`/`_valor_mensalidade`/`_resumo_mensalidades`/`_fmt_moeda`;
  `mensalidades_view`, `mensalidade_config_view`, `mensalidades_gerar_view`, `mensalidade_pagar_view` (JSON),
  `mensalidade_isencao_view`; geração automática no `_salvar_aventureiro` (cadastro).
- `core/urls.py`: rotas `mensalidades/…`. `core/admin.py`: `Mensalidade`/`ConfigMensalidade`.
- `templates/core/_menu.html`: item "Mensalidades" (💰, Diretor).
- `templates/core/mensalidades.html`; `static/js/mensalidades.js`; `static/css/mensalidades.css`.

### Decisões tomadas
- Uma `Mensalidade` por (aventureiro, ano, mês) — controle simples de pago/aberto (sem agregador de
  pagamento por ora). Isenção/desconto ficam no aventureiro e são reaplicados às cobranças **em aberto**
  (as **pagas** não mudam). Geração é **idempotente**.

### Pendências
- Importar o **histórico de mensalidades** do sistema antigo (360 cobranças + pagamentos) — precisa mapear
  aventureiro antigo→novo. Cobrança/lembrete por WhatsApp. Financeiro geral consolidando as 3 áreas.

---

## 2026-07-05 - Loja/Vendas: remove os chips por produto (redundantes com a busca)

### Resumo
A pedido do usuário, os **chips por produto** em "Todas as compras" foram **removidos** — davam o mesmo
resultado de digitar o nome do produto na busca. Ficaram só o **campo de busca** e o **"Só a entregar"**.
Removidos a marcação `data-produtos`, o JS e o CSS dos chips. (As demais mudanças do relatório — "mais
vendidos" por pedido/unidade e "Média por compra" — foram mantidas.)

### Arquivos alterados
- `templates/core/loja.html`: remove a barra de chips e o `data-produtos`.
- `static/js/loja.js`: remove o filtro por chip (mantém busca + "só a entregar").
- `static/css/loja.css`: remove os estilos `.loja-chips`/`.loja-chip`.

---

## 2026-07-05 - Loja/Vendas: "Mais vendidos" por pedido (composto) + chips por produto + rótulo do ticket

### Resumo
Ajustes no relatório da aba Vendas: (1) **"Mais vendidos"** — produto **composto** (Uniforme de Gala) agora
conta **por pedido** (cada pedido que levou o produto = 1), pois tem vários itens obrigatórios; produtos
**simples** (Camiseta, Laço) seguem contando por **quantidade** de unidades (ex.: 2 tamanhos no mesmo pedido
= 2). A coluna mostra a **unidade** ("9 pedido(s)" / "14 un."). (2) **Chips por produto** ("Todos · <produto>…")
acima de "Todas as compras": clicar mostra só os pedidos que contêm aquele produto (um pedido misto aparece
em mais de um) — jeito leve de segmentar sem formulário de filtro. (3) O KPI "Ticket médio" virou **"Média por
compra"** com dica (arrecadado ÷ nº de compras).

### Arquivos criados/alterados
- `core/views.py`: `_loja_relatorio` recalcula "mais vendidos" (composto = por pedido; simples = por unidade),
  ordenado por total.
- `templates/core/loja.html`: coluna "Vendidos" com unidade; KPI "Média por compra" + dica; chips de produto
  (`#lojaChips`) e `data-produtos` em cada compra.
- `static/js/loja.js`: filtro por chip integrado à busca/"só a entregar".
- `static/css/loja.css`: estilos dos chips.

### Decisões tomadas
- Composto conta **por pedido** (via distintas compras que contêm o produto) — robusto mesmo com os pedidos
  importados; simples conta por unidade. Ordenação por **total (R$)** por serem unidades diferentes.

---

## 2026-07-05 - Loja/Vendas: entrega por pedido ("Entregar tudo") + filtro "Só a entregar"

### Resumo
Refino da entrega na aba **Vendas**, a pedido do usuário: a seção separada **"A entregar"** (que virava uma
lista enorme) foi **removida**. Agora tudo acontece dentro de **"Todas as compras"** (ordenadas por data):
cada compra mostra o **selo** de entrega e, ao expandir, tem os **toggles por item** e um botão **"Entregar
tudo"** (entrega/desfaz todas as variações do pedido de uma vez — ideal para o Uniforme de Gala). Adicionado
o filtro **"Só a entregar"** ao lado da busca, para achar rápido os pedidos pendentes. Os KPIs e o "Mais
vendidos"/"Por forma" continuam.

### Arquivos criados/alterados
- `core/views.py`: `loja_entrega_compra_view` (marca/desmarca todos os itens de uma compra; JSON).
- `core/urls.py`: rota `loja/entrega/compra/`.
- `templates/core/loja.html`: remove a seção "A entregar"; adiciona botão "Entregar tudo" por compra,
  `data-pendente` no card e o filtro "Só a entregar".
- `static/js/loja.js`: handler do "Entregar tudo" (atualiza selo, botão e todos os toggles) + filtro
  combinado (busca + só pendentes).
- `static/css/loja.css`: estilos do filtro e do botão "Entregar tudo" (verde quando há o que entregar).

### Decisões tomadas
- Entrega segue por **item** (toggle) **ou por pedido inteiro** ("Entregar tudo"); nada de lista global —
  o Diretor abre o pedido marcado como "A entregar" e resolve ali.

---

## 2026-07-05 - Loja: aba "Vendas" (relatório + entrega) + importação dos pedidos pagos do sistema antigo

### Resumo
Nova aba **"Vendas"** (📊, Diretor) na tela da Loja, com **relatório** e controle de entregas: **KPIs**
(arrecadado, nº de compras, ticket médio, itens a entregar), **Mais vendidos** (por produto: qtd + total),
**Por forma de pagamento**, uma seção **"A entregar"** (itens pendentes, com botão de entregar) e **Todas as
compras** — lista detalhada e **buscável** (nome/código/produto) com todos os dados (comprador, WhatsApp,
e-mail, login, data, forma) e **marcar entrega por item** (toggle sem recarregar, via JSON). As "compras
recentes" saíram do Gerenciar (que ficou só com produtos). Adicionado **controle de entrega** ao
`ItemCompraLoja` (`quantidade_entregue`/`entregue_em`/`entregue_por` + props; mig. **0023**) e ao
`CompraLoja` (props `status_entrega`/`falta_entregar_total`). Endpoint `loja_entrega` (POST/JSON, Diretor).

Também **importados os pedidos pagos** da loja oficial do sistema antigo (21 compras, R$ 3.083,50, todas Pix;
19 vinculadas a um login), com comprador, forma, **data original** e o **status de entrega** preservados
(código `LM<id>`, idempotente). Só pedidos **pagos**, **não-teste**, da **loja oficial** (evento=None) e com
produto do clube.

### Arquivos criados/alterados
- `core/models.py`: `ItemCompraLoja` ganha `quantidade_entregue`/`entregue_em`/`entregue_por` + props
  (`entregue`/`entrega_parcial`/`status_entrega`/`falta_entregar`); `CompraLoja` ganha `status_entrega` e
  `falta_entregar_total`. Migration **0023**.
- `core/views.py`: `_loja_relatorio()` (KPIs + mais vendidos + por forma + pendentes), `loja_entrega_view`
  (toggle JSON) e `loja_view` passa `relatorio`.
- `core/urls.py`: rota `loja/entrega/`.
- `templates/core/loja.html`: aba "Vendas" (KPIs, tabelas, "A entregar", "Todas as compras" com busca e
  entrega por item); Gerenciar sem a lista de compras.
- `static/js/loja.js`: toggle de entrega (fetch + `X-CSRFToken`, atualiza selo) e busca nas compras.
- `static/css/loja.css`: KPIs, tabelas do relatório, lista "a entregar", selos/botões de entrega, busca.

### Decisões tomadas
- Entrega por **item** com toggle total (entregar tudo/desfazer); parcial fica para depois (o histórico
  importado preserva a quantidade entregue original).
- Pedidos importados usam código **`LM<id>`** (idempotente) e status `confirmado`; **cancelados/pendentes**
  do antigo **não** entram. Fotos/produtos/pedidos são dados locais (`media/`+banco), não versionados.

### Pendências
- Entrega **parcial** pela tela (stepper), se necessário.
- Vincular item importado ao aventureiro/variação exatos (hoje é snapshot + produto por título).

---

## 2026-07-05 - Loja: galeria de fotos (com lightbox) + correção do estilo dos campos do carrinho

### Resumo
Dois ajustes na Loja do Clube: (1) **galeria de fotos por produto** — um produto pode ter **várias fotos**
(ex.: como fica o uniforme, tabela de tamanhos), com **miniaturas** e **ampliação em tela cheia (lightbox)**
no celular e no PC (setas/teclado/toque, fecha no X/fundo/Esc). No cadastro, **upload múltiplo** e remoção de
fotos; a 1ª é a capa (vitrine/gerenciar). (2) **Correção**: os campos "Dados do comprador" (nome/WhatsApp/
e-mail) no carrinho estavam **sem estilo** porque o CSS de campo é escopado em `.evento-form` e o form do
carrinho não tinha essa classe — adicionada nele e no form de configuração do produto.

Também foi **importado o "Uniforme de Gala - Aventureiro (Completo)"** do sistema antigo (produto 7): **61
variações** em 3 grupos (Camiseta escolha única/obrigatório; Calça/Saia escolha única/obrigatório — calça
meninos, saia meninas; Acessórios em itens, cada um obrigatório) + as **5 fotos** da galeria. Preços exatos.
As fotos ficam **só em `media/`** (git-ignored), como as fotos dos membros.

### Arquivos criados/alterados
- `core/models.py`: modelo **`FotoProdutoLoja`** (galeria) + property **`ProdutoLoja.capa`** (1ª foto/legado).
  Migration **0022**.
- `core/forms.py`: `ProdutoLojaForm` deixa de ter o campo único `foto` (galeria via upload múltiplo na view).
- `core/views.py`: `_produto_loja_form` trata upload/remoção de fotos (`_salvar_fotos_loja`); `loja_produto_view`
  e `loja_view` passam/prefetch as fotos.
- `core/admin.py`: inline `FotoProdutoLojaInline` em `ProdutoLoja`.
- `templates/core/loja_produto.html`: galeria (principal + miniaturas) + **lightbox**; form de config com `evento-form`.
- `templates/core/loja_produto_form.html`: seção "Fotos do produto" (existentes + remover + upload múltiplo).
- `templates/core/loja.html`: cards usam `capa`; badge "📷 N" na vitrine; form do carrinho com `evento-form` (fix).
- `static/js/loja_produto.js`: galeria + lightbox (miniaturas, setas, teclado, fechar).
- `static/css/loja.css`: galeria, miniaturas, lightbox, gerenciador de fotos e badge.

### Decisões tomadas
- Galeria em modelo próprio (`FotoProdutoLoja`), sem foto por variação por ora (as fotos do antigo eram
  `todas_variacoes=True`). A capa é a 1ª foto (ou o antigo `foto`, mantido só como fallback).
- Fotos reais do uniforme/tabelas ficam **apenas em `media/`** (git-ignored), nunca versionadas.

### Pendências
- Fotos por variação (se um dia quiserem foto por tamanho/cor) — hoje é galeria do produto.

---

## 2026-07-05 - Loja do Clube (loja oficial): cadastro, vitrine com carrinho e pagamento simulado

### Resumo
Novo módulo **Loja do Clube** (loja oficial — uniformes, lenços etc.), **independente** da lojinha de
evento e primeira das 3 áreas financeiras do clube (eventos ✅, mensalidades ⏳, loja ▶). Item novo
**"Loja"** (🛍️) no menu, **só Diretor** por ora. Tela com **2 abas**: **Gerenciar** (cadastro de produtos +
compras recentes) e **Loja** (vitrine com carrinho). Estrutura de produto em 3 níveis **Produto → Grupos →
Variações**: produto **simples** (uma lista de opções, como no evento) ou **composto** (vários grupos —
ex.: Uniforme de Gala = Camiseta [escolha única] + Calça/Saia [escolha única] + Acessórios [itens]). Cada
grupo é "escolha única" ou "itens", com **obrigatório** sim/não e **orientação**; itens podem ser
**obrigatórios** (aviso **soft** na vitrine — avisa o que falta e pergunta se já tem, mas **não bloqueia**).
**Carrinho na sessão** (não perde a seleção ao recarregar; o configurador ainda salva rascunho em
localStorage). A compra fica **vinculada ao login** e, opcional, a um **aventureiro** (1 = automático; 2+ =
escolher — útil pro bordado do Kit Nome). **Pagamento simulado** (Pix com QR/copia-e-cola + cartão com aviso
de Mercado Pago), reaproveitando os helpers da lojinha de evento; a `CompraLoja` só é criada após a
aprovação. Diretor pode **cancelar** compra (devolve estoque). Referência: produto 7 ("Uniforme de Gala")
do sistema antigo (flag `permite_multiplas_variacoes` + `obrigatoria_compra`).

### Arquivos criados/alterados
- `core/models.py`: novos modelos `ProdutoLoja`, `GrupoLoja`, `VariacaoLoja`, `CompraLoja`, `ItemCompraLoja`
  + `MODO_GRUPO_CHOICES`. Migration **0021**.
- `core/forms.py`: `ProdutoLojaForm`.
- `core/views.py`: bloco da Loja (cadastro de grupos/variações, vitrine, carrinho na sessão, finalizar,
  pagamento simulado, sucesso, cancelar) + helpers (`_parse_grupos_loja`, `_salvar_grupos_loja`,
  `_loja_cart_detalhado`, `_criar_compra_loja`, `_aventureiros_do_usuario`, `_comprador_padrao` etc.).
  Reaproveita `_qr_svg`/`_pix_copia_cola`/`FORMAS_PAGAMENTO_ONLINE`.
- `core/urls.py`: rotas `loja`, `loja_produto`, `loja_produto_novo/editar/excluir`, `loja_carrinho_add`,
  `loja_carrinho_remover`, `loja_finalizar`, `loja_pagamento`, `loja_sucesso`, `loja_compra_cancelar`.
- `core/admin.py`: `ProdutoLoja`/`GrupoLoja`/`CompraLoja` (com inlines).
- `templates/core/_menu.html`: item "Loja" (🛍️, só Diretor).
- Templates novos: `loja.html`, `loja_produto_form.html`, `loja_produto.html`, `loja_pagamento.html`,
  `loja_sucesso.html`, `_loja_grupo.html`, `_loja_var_linha.html`.
- Estáticos novos: `static/css/loja.css`; `static/js/loja.js`, `loja_produto_form.js`, `loja_produto.js`.

### Decisões tomadas
- Modelos **novos e independentes** dos da lojinha de evento (sem PDV/balcão/check-in nem FK de evento);
  nomes distintos (`CompraLoja`/`ItemCompraLoja`) para não colidir com `PedidoLoja`/`ItemPedidoLoja`.
- Item obrigatório é **aviso soft** (client-side, modal de confirmação) — a pessoa pode já ter o item.
- **Carrinho na sessão** (chave `loja_carrinho`); checkout na sessão (chave `loja_clube_checkout`, distinta
  da `loja_checkout` do evento). `CompraLoja` só nasce após a aprovação (sem "pendente" no banco).
- Menu **só para Diretor** por ora; as views da vitrine já são `@login_required` para abrir a responsáveis
  depois sem retrabalho.

### Pendências
- Abrir a loja aos **responsáveis** (mostrar o item no menu para eles) — hoje só Diretor.
- Pagamento **real** (gateway) — base pronta e simulada.
- Migrar o **Uniforme de Gala** e demais produtos reais do sistema antigo.
- **Financeiro geral** consolidando eventos + mensalidades + loja (futuro); **mensalidades** (a fazer).

---

## 2026-07-05 - Login por AJAX (senha errada só repete o toast) + componente genérico ajax_form.js

### Resumo
A pedido do usuário, o **login** passou a enviar por **AJAX** igual às telas de recuperação: com **senha
errada**, a notificação (toast) **repete a cada clique sem recarregar** a página; com senha certa, o JS
navega para o destino. O helper de AJAX virou um **componente genérico**: `recuperar.js` foi renomeado
para **`ajax_form.js`** e o atributo `data-ajax-recup` para **`data-ajax-toast`** (usado por login e
recuperação). Sem JS, tudo continua funcionando com POST normal.

### Arquivos criados/alterados
- `static/js/recuperar.js` → **renomeado** para `static/js/ajax_form.js` (agora genérico:
  `form[data-ajax-toast]`).
- `core/views.py`: `login_view` responde JSON quando AJAX (`{"redirect":url}` no sucesso, `{"msg","tipo"}`
  no erro). Helpers `_recup_ir`/`_recup_msg` renomeados para **`_ajax_redirect`/`_ajax_toast`**.
- `templates/core/login.html`: form com `data-ajax-toast` + carrega `ajax_form.js`.
- `templates/core/recuperar_cpf.html`, `recuperar_codigo.html`, `recuperar_nova_senha.html`: atributo
  `data-ajax-toast` + `ajax_form.js`.

### Decisões tomadas
- O envio-por-AJAX-com-toast é um **componente reutilizável** (`ajax_form.js` + `data-ajax-toast`), não
  específico da recuperação — por isso o nome genérico.

### Pendências
- Sem novas.

## 2026-07-05 - Recuperação/Login: envio por AJAX (toast sem recarregar) + fim do vazamento de mensagem

### Resumo
Dois ajustes pedidos pelo usuário:
1. **Recuperação por AJAX**: os formulários das telas de recuperação (CPF, código, reenviar, nova senha)
   passam a enviar por **fetch**. Em caso de erro, a notificação (toast) **repete sem recarregar a
   página**; em caso de sucesso, o JS navega para a próxima etapa. Sem JS, os formulários continuam
   funcionando com POST normal (fallback).
2. **Login com o toast padrão + fim do vazamento**: o login agora **renderiza e consome** as mensagens
   (toast). Isso conserta um **vazamento**: a mensagem "Senha redefinida! Faça login…" era enfileirada e,
   como o login não a exibia, ficava **presa na store** e reaparecia depois (inclusive numa tentativa de
   login com senha errada). Agora ela aparece **uma vez** no login (correto) e some. O erro do próprio
   login ("Usuário ou senha inválidos.") também virou toast.

### Arquivos criados/alterados
- `core/views.py`: helpers `_eh_ajax`, `_recup_ir` (JSON `{"redirect":url}`), `_recup_msg`
  (JSON `{"msg","tipo"}`); as 4 views de recuperação respondem JSON quando AJAX (erro → toast; sucesso →
  redirect). `login_view` usa `messages.error` em vez do contexto `erro`.
- `static/js/recuperar.js` (novo): intercepta `form[data-ajax-recup]`, faz o fetch e trata
  `redirect`/`msg` (usa `window.mostrarToast`).
- `templates/core/recuperar_cpf.html`, `recuperar_codigo.html`, `recuperar_nova_senha.html`: forms com
  `data-ajax-recup` + carregam `recuperar.js`.
- `templates/core/login.html`: bloco de `.mensagens` (toast) + carrega `inicio.js`; removido o aviso
  inline `.aviso-login`.

### Decisões tomadas
- Contrato JSON das telas de recuperação: `{"redirect": url}` (JS navega; mensagens enfileiradas
  aparecem no destino) ou `{"msg","tipo"}` (só toast, sem recarregar).
- Toda página que é **destino** de um redirect com mensagem precisa **renderizar `messages`** (senão a
  mensagem vaza). Por isso o login passou a renderizar.

### Pendências
- Sem novas. (O `.aviso-login` do `login.css` ficou sem uso; mantido no CSS por ora.)

## 2026-07-05 - Recuperação de senha: espaçamento do indicador de etapas

### Resumo
No indicador de etapas (CPF → Código → Nova senha), o número/✓ (círculo de 26px) estava encostando/
sobrepondo o texto abaixo. Aumentei o `padding-top` do `.recup-passos li` de 22px para **36px**
(26px do círculo + folga). Só CSS.

### Arquivos criados/alterados
- `static/css/recuperar.css`: `.recup-passos li { padding-top: 36px; }`.

## 2026-07-05 - Recuperação de senha: usar o toast padrão (não mais avisos inline)

### Resumo
A pedido do usuário, as telas de recuperação de senha passaram a usar as **notificações padrão do
sistema (toasts)**, e não os avisos inline. Para isso, o **CSS do toast** (`.mensagens`/`.mensagem`)
foi **movido do `inicio.css` para o `base.css`** (componente reutilizável, com fallback de cores),
ficando disponível em **qualquer página** — inclusive as públicas do login/recuperação. As telas de
recuperação agora carregam `inicio.js` (o módulo de toasts é seguro em qualquer página) e todo o
feedback passa pelo framework de `messages`.

### Arquivos criados/alterados
- `static/css/base.css`: recebeu o bloco de **notificações/toasts** (antes em `inicio.css`).
- `static/css/inicio.css`: removido o bloco de toasts (agora só um comentário apontando para o `base.css`).
- `static/css/recuperar.css`: removido o `.aviso-ok` (não é mais usado).
- `core/views.py`: `recuperar_senha_view`, `recuperar_senha_codigo_view`, `recuperar_senha_nova_view`
  usam `messages.error(...)` em vez do contexto `erro`.
- `templates/core/recuperar_cpf.html`, `recuperar_codigo.html`, `recuperar_nova_senha.html`: usam o
  markup padrão `.mensagens`/`.mensagem` e carregam `inicio.js`.
- Removido `templates/core/_recup_avisos.html` (não é mais necessário).

### Decisões tomadas
- Toast é **um componente reutilizável** e deve morar no `base.css` (que já hospeda o modal), não no
  `inicio.css`. Confirmado que **toda** página que usa `inicio.css` também carrega `base.css`.

### Pendências
- Sem novas. (A tela de **login** em si continua com o aviso inline `.aviso-login` do jeito que já era.)

## 2026-07-05 - Recuperação de senha pelo WhatsApp (código de 4 dígitos)

### Resumo
O link **"Esqueci minha senha"** (login) passou a funcionar. Fluxo público em **3 etapas**
(guardadas na sessão):
1. **CPF** do responsável legal → identifica a conta (`Aventureiro.resp_cpf`) e envia um **código de
   4 dígitos** para o **WhatsApp principal** da conta (via módulo WhatsApp/W-API).
2. **Código** → validado com **limite de 5 tentativas** e **expiração de 10 min**; botão **reenviar**
   (espera mínima de 60 s).
3. **Nova senha** (2×) → grava e limpa a sessão; volta ao login.
O código é guardado **com hash** na sessão (nunca em texto puro). O número de destino aparece sempre
**mascarado** (`•••••-1234`).

Em **Usuários** (Diretor), no detalhe de cada responsável ligado a uma conta, há o controle
**"WhatsApp principal"**: escolher entre **pai / mãe / responsável legal** para onde o código será
enviado. Sem escolha, o padrão é o **WhatsApp do responsável legal**. (Mais pra frente o próprio
responsável logado poderá alterar.)

### Arquivos criados/alterados
- `core/models.py`: `PerfilUsuario.whatsapp_principal_origem` (choices pai/mae/resp, blank).
- `core/migrations/0020_perfilusuario_whatsapp_principal_origem.py`.
- `core/views.py`: helpers `_so_digitos`, `_mascara_telefone`, `_numeros_conta`, `_whatsapp_principal`,
  `_conta_por_cpf_resp`, `_recup_gerar_e_enviar`, `_recup_expirado`; views `recuperar_senha_view`,
  `recuperar_senha_codigo_view`, `recuperar_senha_reenviar_view`, `recuperar_senha_nova_view`,
  `usuario_principal_view`; `usuarios_view` passou a anexar `conta_id`/`numeros_principal`/
  `principal_origem` a cada responsável (por CPF, só quando há **uma** conta). Constantes
  `RECUP_TTL_MIN=10`, `RECUP_MAX_TENTATIVAS=5`, `RECUP_REENVIO_ESPERA=60`.
- `core/urls.py`: `/recuperar-senha/`, `.../codigo/`, `.../reenviar/`, `.../nova-senha/` e
  `/usuarios/conta/<id>/principal/`.
- `templates/core/login.html`: link "Esqueci minha senha" aponta para o fluxo.
- `templates/core/recuperar_cpf.html`, `recuperar_codigo.html`, `recuperar_nova_senha.html` e o parcial
  `_recup_avisos.html` (mensagens inline nas telas públicas).
- `templates/core/usuarios.html`: bloco **WhatsApp principal** no detalhe do responsável **+ bloco de
  `messages`** (que faltava — agora o toast do toggle ativo/inativo e do principal aparece).
- `static/css/recuperar.css` (indicador de etapas, campo do código, aviso verde, reenviar) e trecho novo
  em `static/css/usuarios.css` (bloco do principal).

### Decisões tomadas
- **Destino do código = WhatsApp principal** definido pelo Diretor (fallback: responsável legal).
  **Opções do principal**: pai, mãe ou responsável legal. **CPF aceito**: só o do responsável legal.
  (Confirmado com o usuário.)
- **Sem novas dependências**: reaproveita `normalizar_telefone` e `_enviar_whatsapp` do módulo WhatsApp
  (urllib). Código gerado com `secrets.randbelow`.
- **Estado na sessão** (não em modelo): simples e sem necessidade de limpeza; código sempre hasheado.
- **Anti-abuso**: expiração, limite de tentativas e espera entre reenvios.

### Pendências
- Permitir que o **responsável logado** altere o próprio WhatsApp principal (hoje só o Diretor).
- Se a conta tiver o mesmo CPF de responsável legal em mais de uma conta, o controle de principal em
  Usuários não aparece (fica a cargo do admin) — caso raro.

## 2026-07-05 - Módulo WhatsApp (W-API): configuração da instância + envio de mensagem

### Resumo
Novo item de menu **WhatsApp** (só Diretor) para integrar a **API da W-API**
(`https://api.w-api.app/v1`). A tela tem duas seções:
1. **Configuração da instância** — campos para o **ID da instância**, o **token** (exibido só com os
   **últimos 4 dígitos**, `••••••3456`; só é substituído se um novo for digitado) e a **URL base**
   (opcional, com o padrão já preenchido). No começo tudo vem em branco, pronto para cadastrar; um
   selo mostra "Não configurado" / "✓ Configurado".
2. **Enviar mensagem** — campos de **número** e **texto**. O número é **normalizado** (aceita espaços,
   traços, parênteses, `+55`, `00…`) para o formato que a API exige (só dígitos, com DDI 55); há uma
   **prévia ao vivo** ("Será enviado para: +55 (47) 99224-9708"). O envio é **AJAX** e usa o **toast
   padrão** do sistema para sucesso/erro. Os campos ficam desabilitados até a instância estar configurada.

### Arquivos criados/alterados
- `core/models.py`: novo model **`WhatsappConfig`** (singleton via `get_solo()`; `instance_id`, `token`,
  `base_url`, `atualizado_por/_em`; propriedades `configurado` e `token_mascarado`).
- `core/migrations/0019_whatsappconfig.py`: cria a tabela.
- `core/views.py`: `whatsapp_view` (tela), `whatsapp_config_view` (salvar — não apaga o token quando o
  campo vem vazio), `whatsapp_enviar_view` (envio AJAX/JSON), helper `normalizar_telefone` e
  `_enviar_whatsapp` (POST na W-API via **urllib** da stdlib, sem novas dependências).
- `core/urls.py`: rotas `/whatsapp/`, `/whatsapp/config/`, `/whatsapp/enviar/`.
- `templates/core/_menu.html`: item **WhatsApp** (💬) dentro de `{% if is_diretor %}`.
- `templates/core/whatsapp.html`: nova tela (mobile-first, cards do sistema).
- `static/js/whatsapp.js`: prévia do telefone, mostrar/ocultar token, envio AJAX + toast.
- `static/css/whatsapp.css`: estilos da tela (paleta azul/verde; inputs próprios; responsivo).

### Decisões tomadas
- **Sem novas dependências**: o POST na W-API usa `urllib.request` (regra do projeto).
- **Token nunca é exibido inteiro**: só os últimos 4 dígitos; para trocar, digita-se um novo (campo
  vazio mantém o token guardado). Botão "Mostrar" ajuda só na hora de colar o novo token.
- **Endpoint** (docs W-API): `POST {base_url}/message/send-text?instanceId=<id>`, header
  `Authorization: Bearer <token>`, body JSON `{"phone","message"}`.
- **Normalização de telefone** feita no back-end (fonte da verdade) e espelhada no JS só para a prévia.

### Pendências
- Envio de mensagem em lote / a partir dos cadastros (por ora é só teste de 1 número).
- Só o Diretor tem acesso (conforme pedido).

## 2026-07-05 - Usuários: contador "Vínculos" → "Ativos" (aventureiros ativos)

### Resumo
A pedido do usuário, o contador **"Vínculos"** (abstrato, pouco útil) na tela Usuários virou **"Ativos"** —
a quantidade de **aventureiros ativos**. Ficam: **Responsáveis · Aventureiros (total) · Ativos**.

### Arquivos alterados
- `core/views.py`: `usuarios_view` passa `total_ativos` (conta `ativo=True`); removido o cálculo de
  `total_vinculos`. `templates/core/usuarios.html`: card "Ativos".

### Validação
- `manage.py check` OK. Render: contadores **72 Responsáveis · 39 Aventureiros · 38 Ativos** (1 inativa).

---

## 2026-07-05 - Inativo: responsável aparece inativo + cobertura conta só ativos

### Resumo
Ajustes após o usuário testar (marcou a aventureira "Heloísa" inativa — a conta do responsável foi
desativada corretamente no banco, mas a tela não mostrava isso):
- **Responsável inativo na tela Usuários**: o card do pai/mãe/responsável agora aparece **Inativo** (selo +
  riscado) quando **todos os aventureiros vinculados a ele estão inativos** (mesma regra da conta). No modal
  do responsável, selo Ativo/Inativo + nota explicando. Vínculos inativos aparecem marcados na lista.
- **Cobertura do Resumo (dashboard)**: "Aventureiros do clube neste evento" passou a contar **só ativos**
  (`_montar_dashboard` filtra `Aventureiro.objects.filter(ativo=True)`) — inativos saem do total do clube.

### Arquivos alterados
- `core/views.py`: `usuarios_view` anota `ativo` em cada vínculo e `ativo` do responsável (any vínculo
  ativo); `_montar_dashboard` filtra aventureiros ativos na cobertura.
- `templates/core/usuarios.html`: selo/greyed no card e no modal do responsável + marca de vínculo inativo.
  `static/css/usuarios.css`: `.vinc-inativo`, strike no `.resp-nome-item`.

### Validação
- `manage.py check` OK. Verificado: conta da Heloísa (Mariane) `is_active=False` (cascata correta); os cards
  do pai (denner) e mãe (Mariane) agora vêm `av-inativo` com selo. Cobertura do evento 62: total caiu de 39
  → 38 (Heloísa fora) e cai +1 ao inativar um inscrito (testado e revertido).

### Observação
- "Heloísa Mendes carolino" foi marcada inativa pelo próprio usuário testando a feature (não é dado de teste
  meu). Fica como está.

---

## 2026-07-05 - Aventureiro inativo/desligado (com cascata na conta do responsável)

### Resumo
Alguns membros saem do clube no meio do ano e pedem para desligar. Agora, em **Usuários** (Diretor), ao
abrir o aventureiro (modal), há o botão **"Marcar como inativo"** (⛔) / **"Reativar"** (✅), com confirmação.

**Cascata na conta** (`Aventureiro.usuario`): ao inativar, se o responsável **não tiver mais nenhum
aventureiro ativo**, a **conta é desativada** (`is_active=False`, não loga mais). Se ainda tiver outro
ativo (ex.: dois irmãos, inativo só um), a conta **continua ativa** para gerenciar o que ficou. Reativar um
aventureiro reativa a conta. **Contas de Diretor/staff/superuser são protegidas** (nunca desativadas por
aqui, para não travar o acesso admin).

### Arquivos criados/alterados
- `core/models.py`: campo **`Aventureiro.ativo`** (default True). Migration **`0018`**.
- `core/views.py`: `aventureiro_toggle_ativo_view` (POST, Diretor; toggle + cascata com guarda de
  diretor/staff); `usuarios_view` anota `av.conta_ativa` (`select_related("usuario")`); `presenca_evento_view`
  passou a listar só `ativo=True`. Import de `eh_diretor`.
- `core/urls.py`: rota `aventureiro_toggle_ativo`.
- `templates/core/usuarios.html`: selo "Inativo" + card riscado; no modal, selo Ativo/Inativo, botão de
  ligar/desligar (form `data-confirmar`) e nota da cascata. `static/js/usuarios.js`: handler genérico de
  `form[data-confirmar]` (confirm antes de enviar). `static/css/usuarios.css`: `.pill-inativo`,
  `.av-inativo`, `.av-status-acao`, `.btn-inativar`/`.btn-reativar`.

### Validação
- `manage.py check` OK; `migrate` (0018). Teste (test client, Diretor): **irmãos** — inativar 1 → conta
  ativa; inativar o 2º → conta desativada; reativar 1 → conta volta. **Solo** — inativar único → conta
  desativada; reativar → volta. Diretor protegido. Registros de teste revertidos (0 aventureiros inativos).
  (A conta "Miguel Ferreira Mendes" está inativa desde a **importação** do sistema antigo — não é resíduo.)

---

## 2026-07-05 - Presença: toast ao marcar/desmarcar (confirmação)

### Resumo
Pedido do usuário: confirmar que a marcação deu certo. O `presenca.js` passou a mostrar o **toast padrão**
do sistema (`window.mostrarToast`) no **sucesso** de marcar/desmarcar — "<nome> — presente ✅" (success) ou
"<nome> — ausente" (info). Antes só havia toast em caso de erro. `inicio.js` (que expõe `mostrarToast`) já
é carregado antes do `presenca.js` na folha. `manage.py check` OK.

---

## 2026-07-05 - Módulo Presença do clube (+ guarda de exclusão por presença)

### Resumo
Novo módulo **Presença** (item no menu, Diretor), para marcar quais aventureiros do clube estiveram num
evento — pensado para **eventos simples** (reuniões, eventos fora), mas funciona para qualquer evento. É
**independente** do check-in de inscrição do evento complexo (`ParticipanteInscricao.presente`).

Fluxo (como no sistema antigo, com melhorias):
1. **Escolher o evento** (lista dos eventos cadastrados).
2. **Folha de presença**: lista de **todos os aventureiros** do clube, cada um com **foto grande**, nome +
   idade e um botão **Marcar** (toggle **presente ↔ ausente**, sem recarregar). Contador "presentes X de Y"
   ao vivo e **busca** por nome.
3. **Clicar na foto** abre a **foto ampliada** num modal (para conferir a pessoa no dia).

Também foi **ativada a guarda de exclusão** pendente da Fase 5.4: um evento com **presença marcada** não
pode mais ser excluído (junto de inscrições/pedidos).

### Arquivos criados/alterados
- `core/models.py`: model **`PresencaEvento`** (evento, aventureiro, marcado_em/por; `unique_together`;
  existência = presente). Migration **`0017`**.
- `core/views.py`: `presenca_view` (escolher evento), `presenca_evento_view` (folha), `presenca_marcar_view`
  (POST JSON toggle). `eventos_view`/`evento_excluir_view` passam a considerar `presencas` na guarda de
  exclusão. Import de `PresencaEvento`.
- `core/urls.py`: rotas `presenca`, `presenca_evento`, `presenca_marcar`.
- `templates/core/presenca_selecionar.html` e `presenca_evento.html` (novos); `_menu.html` (item
  "Presença", Diretor).
- `static/js/presenca.js` (novo: toggle fetch/JSON + modal da foto + busca). `static/css/presenca.css` (novo).

### Validação
- `manage.py check` OK; `migrate` aplicado. Teste (test client, Diretor): seletor 200; folha 200 (lista +
  modal); marcar → cria registro (presentes=1); desmarcar → remove (presentes=0); **guarda de exclusão**:
  evento com presença → `pode_excluir` False e POST excluir **bloqueado** (evento preservado). Registros de
  teste removidos. Visual do seletor conferido (headless); a folha **não** foi capturada para não expor
  fotos reais de menores (validada funcionalmente).

### Pendências / próximo passo
- (Opcional) abrir a presença a outros perfis além do Diretor. Migrar os eventos "Reunião do Clube" (2/4/5)
  do sistema antigo, onde a presença será usada.

---

## 2026-07-05 - Correção da migração do "Passaporte" (conferência com o relatório do sistema antigo)

### Resumo
O usuário baixou o **relatório PDF do evento no sistema antigo** para conferir, e havia diferenças grandes
vs a 1ª importação (evento 61). Investigado e **corrigido** (reimportado como **evento 62**; o 61 foi
apagado). Três causas:
1. **Inscrição contava como venda de loja**: no antigo, a inscrição é um **item do pedido** com título
   "Inscricao do evento: …". A 1ª importação somou essas linhas na lojinha → **R$ 4.505,50** em vez de
   **R$ 1.825,50**. Correção: itens com esse título **não** entram na loja; pedido que só tem a inscrição
   é ignorado (a inscrição já vem da `eventoinscricao`).
2. **Idade como texto**: 8 participantes tinham `Idade` = "6 anos" (texto). O parser antigo (`int`) falhava
   → caíam em "sem faixa". Correção: extrair o número por regex (`\d+`). Faixas passaram a 13 (1-4) / 58 → 56.
3. **Inscrição de teste**: 1 inscrição confirmada e **não paga** com nomes "teste/testee" (R$ 80) passou.
   Removida (heurística de nomes de teste).

Também, a pedido do usuário, a **taxa de cartão/Pix do Mercado Pago (R$ 423,73)** foi lançada como
**custo**, para o Resultado bater com o **"líquido"** do relatório.

### Resultado final (idêntico ao relatório antigo)
- Vendas lojinha **R$ 1.825,50** · Inscrições **R$ 2.500,00** (69 crianças: 13 na faixa 1-4 + 56 na 5-12)
- Bruto **R$ 4.325,50** · Custos **R$ 607,12** (R$ 183,39 + taxa R$ 423,73) · **Resultado R$ 3.718,38**

### Aprendizado (registrado p/ os próximos eventos com lojinha)
- Excluir itens "Inscricao do evento" da loja; parsear idade por regex; pular inscrições/pedidos de teste
  (`transacao_teste` + nomes de teste). Ver memória `migracao-eventos-conciliacao`.

---

## 2026-07-05 - Migração do evento "Passaporte da Diversão" (com lojinha completa)

### Resumo
Migrado o 2º evento do sistema antigo: **"Passaporte da Diversão"** (evento 6 → **evento 61**), agora com
**lojinha** (produtos, variações, fotos e vendas). Valores vieram **corretos do sistema antigo** — sem
conciliação bancária (a pedido do usuário).

- **Evento**: Colégio Adventista de São Carlos, 24/05/2026 13h–17h (1 dia), só membros. **Faixas**:
  1-4 anos R$ 20 · 5-12 anos R$ 40.
- **Inscrições**: **52** confirmadas (71 participantes), R$ 2.580,00. Puladas 6 não-confirmadas + 1
  cancelada. `valor_total` = valor gravado (correto); forma "online".
- **Lojinha**: **4 produtos** (Mini pizza, Bebidas, Pipoca, Açaí) com **fotos** + **13 variações** (preço
  por variação). Sem controle de estoque (evento histórico).
- **Vendas**: **141 pedidos** (R$ 4.505,50), só **status "pago" e não-teste** (puladas 23 canceladas +
  13 testes), com **226 itens** e a **retirada por item** (`quantidade_entregue`) preservada do antigo.
  Forma real (pix/dinheiro/cartão); dinheiro→balcão, resto→online; vínculo à inscrição via
  `evento_inscricao`.
- **Custos**: **3** (Pulseiras, pizzas, estorno) = R$ 183,39, **com comprovantes**.
- **Resultado**: receitas R$ 7.085,50 − custos R$ 183,39 = **R$ 6.902,11** (lucro).

### Como foi feito
- Script one-off (`importar_evento6.py` no scratchpad) lendo o export atualizado ("com_arquivos"): cria
  evento+faixas, produtos+variações (fotos extraídas para `media/eventos/produtos/`), inscrições
  (`criado_em` original), pedidos+itens (com mapa old→new de inscrição e variação) e custos (comprovantes
  em `media/eventos/custos/`). Mídia é **git-ignored**.
- Mapeamento de chaves flexível (o form do Passaporte usa "Nome do responsável"/"Nome da Criança", difere
  do Acampamento) via helpers de extração no script.

### Validação
- Render do evento 61 (Diretor): Inscritos 71, Arrecadação R$ 2.580, Vendas R$ 4.505,50, Custos R$ 183,39,
  **Resultado R$ 6.902,11**; "por forma" (Pix 131 / Online 52 / Dinheiro 8 / Cartão 2); faixas (5-12: 52,
  1-4: 11); **retiradas 192 de 287** (item-level); cobertura 25/39, 0 "a conferir"; 4 fotos de produto e
  3 comprovantes de custo existentes. Sem erros.

### Pendências / próximo passo
- Migrar os eventos restantes (ids 2/4/5 "Reunião do Clube" — simples, sem inscrição/lojinha).

---

## 2026-07-05 - Cobertura do clube: casamento de nomes mais esperto + lista de "a conferir"

### Resumo
No painel do evento, o card **"Aventureiros do clube neste evento"** (cobertura) casava mal os nomes: se a
inscrição abreviava o nome do meio (ex.: **"Alice Z Moreira"**), não casava com **"Alice Zanatta Moreira"**
(a regra exigia todos os tokens idênticos). Melhorias:
- **Casamento ciente de iniciais**: um token de 1 letra casa com um token que começa por ela — "Alice Z
  Moreira" → "Alice Zanatta Moreira". Mantém o subconjunto (ex.: "Beatriz Gonçalves" → "Beatriz Gonçalves
  Steinmeyer"). Helpers `_tokens_lista` + `_cobre_token` + `_nome_casa` (substituem o `_tokens_nome`/subset).
- **Desambiguação pelo sobrenome do responsável**: quando um nome curto casa com mais de um aventureiro,
  usa o sobrenome do responsável para escolher (ex.: "Beatriz" + responsável "…Staine" → "Beatriz Gonçalves
  Staine"; a outra Beatriz fica de fora). Só vira "a conferir" se ainda restar ambiguidade.
- **"A conferir" agora é uma lista** (participante + inscrição + candidatos), não só um contador — o
  Diretor vê exatamente quais nomes ficaram ambíguos.

Efeito no Acampamento 2026: cobertura subiu de **17 → 19 de 39** e **0 a conferir** (Alice e Beatriz
resolvidas). Os ~20 restantes são adultos/pais e crianças **não cadastradas** (corretamente fora).

### Arquivos alterados
- `core/views.py`: `_tokens_lista`/`_cobre_token`/`_nome_casa` (novos); `_montar_dashboard` usa o novo
  casamento + desambiguação por responsável e devolve `cobertura.ambiguos_lista`. Removido `_tokens_nome`.
- `templates/core/evento_painel.html`: lista `.cob-conferir` (os "a conferir"). `static/css/eventos.css`:
  estilo `.cob-conferir`.

### Validação
- `manage.py check` OK. Render do evento 60: cobertura **19 de 39**, sem "a conferir"; "Alice Zanatta
  Moreira" e "Beatriz Gonçalves Staine" passaram a casar. Casos legítimos fora (não-membros) seguem fora.

---

## 2026-07-05 - Migração do evento "Acampamento 2026" do sistema antigo (com conciliação bancária)

### Resumo
Migrado o primeiro evento do sistema antigo para o novo: **"ACAMPAMENTO AVENTUREIROS PINHAL JÚNIOR,
2026"** (era o evento 7 no antigo → **evento 60** no novo). Trazidos: dados do evento (nome, local,
descrição, datas 19–21/06 14h–17h), as **5 faixas etárias** (0-5 isento · 6-9 R$45 · 10-12 R$60 ·
13-17 R$80 · 18+ R$150) e as **24 inscrições reais confirmadas** (puladas as não confirmadas e um teste).

**Conciliação dos valores:** o sistema antigo gravava valores inconsistentes (taxa de cartão, campos
zerados, etc.). Os valores foram **conciliados contra o extrato bancário (Mercado Pago, abr–jun)** —
cruzando data + nome do pagador + valor — para registrar o **valor realmente recebido** em cada inscrição.
Resultado: **R$ 4.597,41** (14 Pix + 3 cartão + 7 cortesia/diretoria). Decisões de cortesia/diretoria e
casos de pagamento parcial confirmados com o usuário antes da importação.

### Como foi feito
- Análise/conciliação por **scripts one-off** no scratchpad (parser dos PDFs do extrato + matcher
  inscrição↔transação) + **relatório visual** (Artifact) para revisão do usuário. **Não** virou comando
  versionado porque a conciliação é bespoke (revisão manual do banco caso a caso).
- Importação direta no banco (SQLite): `Inscricao` + `ParticipanteInscricao` por inscrição, com
  `forma_pagamento` (pix/cartao/cortesia), `valor_total` = recebido conciliado e **`criado_em` = data
  original** da inscrição (para rastreabilidade). Sem tela de edição (decisão do usuário: subir já certo).

### Privacidade
- Os **PDFs do extrato** (`EXTRATOS/`) e os JSONs da exportação contêm dados financeiros/pessoais e
  **NÃO são versionados** (adicionado `EXTRATOS/`, `extratos/`, `*.ofx` ao `.gitignore`). Ficam só local.

### Custos (adicionado em seguida)
- Migrados os **9 custos** do evento 7 (nome, valor, data): Aluguel chácara R$ 2.000, comidas, lonas,
  pó de festa, pão, produtos vegetarianos, etc. — **total R$ 4.723,50**. Com isso o **Resultado do
  acampamento = R$ 4.597,41 − R$ 4.723,50 = −R$ 126,09**.
- **Comprovantes**: no primeiro export **não vieram** (só as assinaturas). O usuário **reexportou com
  arquivos** (`exportacao_migracao_..._com_arquivos.zip`, com `arquivos/media/eventos/custos/evento_7/`) e
  os **9 comprovantes foram anexados** (casados por nome+valor), copiados para `media/eventos/custos/`
  (git-ignored). O custo "Mini Lanterninhas" tinha 2 arquivos (screenshot + invoice); o principal
  (screenshot) ficou no campo comprovante e o invoice também foi copiado para `media/`.

### Pendências / próximo passo
- Migrar os **demais eventos** do sistema antigo (mesmo processo, um a um). Vínculo
  `Inscricao.usuario`→conta migrada não foi feito (histórico); dá para casar por nome/CPF se necessário.

### Arquivos alterados
- `.gitignore`: ignora `EXTRATOS/`, `extratos/`, `*.ofx`. (Dados do evento entram só no banco local.)

---

## 2026-07-05 - "Dia do evento": botão Voltar do balcão volta para o console (não para o painel)

### Resumo
Quando o atendente abre um atalho de balcão a partir do console **"Dia do evento"** (Nova inscrição /
Vender na lojinha), o botão **Voltar** dessas telas levava sempre ao painel. Agora ele **volta para o
"Dia do evento"**, de onde veio — para o atendente pesquisar/marcar entrega e vender na mesma tela sem
ficar navegando.

### Como
- Os atalhos no console apontam para o PDV com **`?de=dia`**.
- `evento_pdv_view` e `evento_pdv_inscricao_view` leem `de` (GET **ou** POST), passam ao template e
  **preservam** `?de=dia` no redirect após registrar (para continuar registrando e o Voltar seguir certo).
- As telas de PDV têm um **hidden `de`** no form e o link de Voltar passou a ter o ramo
  `{% if de == "dia" %}` → "← Voltar para o Dia do evento" (senão, mantém painel/operar como antes).

### Arquivos alterados
- `core/views.py`: `de` nas duas views de PDV (contexto + redirect com `?de=dia`).
- `templates/core/evento_dia.html`: atalhos com `?de=dia`.
- `templates/core/evento_pdv.html` e `evento_pdv_inscricao.html`: hidden `de` + ramo do Voltar.

### Validação
- `manage.py check` OK. Render (test client): `/pdv/?de=dia` e `/pdv/inscricao/?de=dia` mostram "Voltar
  para o Dia do evento" e o hidden `de=dia`; sem `?de=dia`, mantêm o Voltar para o painel.

---

## 2026-07-05 - Refinos de UX: abas do painel em card + atalhos de balcão no "Dia do evento"

### Resumo
Três ajustes pedidos pelo usuário:
1. **Lojinha só quando há produtos** (verificação): confirmado que a página do evento (botão "Comprar na
   loja", via `tem_loja`) e o formulário de inscrição (seção "Quer levar algo da lojinha?", via
   `produtos_loja`) **já** só aparecem quando existem produtos **ativos**. Testado com um evento sem
   produtos: nenhum dos dois aparece. Também conferido que não há produto ativo sem variação. **Sem
   mudança de código** (já estava correto).
2. **Barra de abas do painel em card**: a `.painel-abas` virou um **card/toolbar** (fundo branco, borda,
   cantos arredondados, sombra leve). A aba de seção **ativa** ficou **preenchida em azul** (antes era só
   sublinhado verde), e as **abas de ação** (Dia do evento / Vender no balcão / Operadores) ganharam um
   **divisor** à esquerda — deixando claro que o conjunto são os botões daquele painel.
3. **Atalhos de balcão no "Dia do evento"**: o topo do console ganhou **"Nova inscrição (balcão)"** e
   **"Vender na lojinha"**, para o atendente vender/inscrever **sem sair da tela** (pesquisa, marca entrega
   e vende no mesmo lugar). Gates: inscrição enquanto o evento não terminou; venda quando a loja está
   aberta e há produtos ativos.

### Arquivos alterados
- `static/css/eventos.css`: `.painel-abas` (card), `.painel-aba`/`.ativa` (pílula preenchida),
  `.painel-aba-acao::before` (divisor); `.dia-acoes` (linha de atalhos).
- `templates/core/evento_dia.html`: linha de atalhos (`.dia-acoes`) com os dois botões.
- `core/views.py`: `evento_dia_view` passa `pode_inscrever` (evento não terminou) e `pode_vender`
  (loja aberta + produtos ativos).

### Validação
- `manage.py check` OK. Teste (test client): evento sem produtos → "Comprar na loja"/"Quer levar algo da
  lojinha?" **ausentes**. **Visual (Chrome headless)**: abas do painel num card com "Resumo" ativo
  preenchido e divisor antes das ações; console "Dia do evento" com os dois atalhos no topo.

---

## 2026-07-05 - Evento complexo — Fase 5.4d: contadores do dia no painel (encerra a Fase 5.4)

### Resumo
Fecha a Fase 5.4 com a visão de acompanhamento no **painel do evento**. A aba **Resumo** ganhou um painel
**"📋 Dia do evento"** com os contadores ao vivo do dia — **Check-in** (presentes X/Y) e **Retiradas**
(itens entregues X/Y) — e um botão **"Abrir console"** que leva à tela "Dia do evento". Aparece só quando
há participantes ou itens (não polui eventos sem inscrição/lojinha). Reusa o helper `_resumo_dia`.

### Guarda de exclusão (esclarecimento)
O item "guarda de exclusão do evento simples" da Fase 5.4 **não exigiu código novo**: o evento **complexo**
já é protegido (`evento_excluir_view`/`eventos_view` bloqueiam a exclusão quando há inscrições ou pedidos,
o que cobre qualquer presença/entrega). O **evento simples** não tem módulo de presença (presença é do
evento complexo), então a guarda por presença em evento simples permanece como **item futuro** — ver
memória `exclusao-evento-presenca`. Nada a mudar por ora.

### Arquivos alterados
- `core/views.py`: `evento_painel_view` passa `dia = _resumo_dia(evento)` no contexto.
- `templates/core/evento_painel.html`: painel "Dia do evento" na aba Resumo (após os KPIs), com os
  contadores e o botão "Abrir console"; só renderiza se `dia.total_part` ou `dia.total_itens`.
- `static/css/eventos.css`: estilo `.dia-band` (+ `.dia-band-titulo`/`-nums`/`-num`).

### Validação
- `manage.py check` OK. Render do painel (test client, Diretor) com 2 presentes + 1 item entregue:
  o band aparece com **Check-in 2 de 4** e **Retiradas 1 de 12** + "Abrir console". **Visual (Chrome
  headless)**: band com gradiente azul/verde, entre os KPIs e os gráficos. Marcações de teste revertidas.

### Pendências / próximo passo
- **🎉 Fase 5.4 (Check-in + Retirada) CONCLUÍDA.** Futuro: presença em **evento simples** (aí a guarda de
  exclusão por presença passa a valer para eles). Depois: **pagamentos reais** (gateway) e **loja oficial
  do clube** (uniformes, separada da lojinha de evento).

---

## 2026-07-05 - Evento complexo — Fase 5.4c: "vai levar agora?" no balcão (entrega na hora da venda)

### Resumo
Fecha o fluxo do dia pelo lado do **balcão**: ao registrar uma venda, o atendente diz se o cliente **vai
levar os itens agora**. Um checkbox **"Entregar os itens agora"** (marcado por padrão) foi adicionado ao
**PDV de vendas** (`evento_pdv`) e ao **PDV de inscrição** (`evento_pdv_inscricao`):
- **Marcado** → o pedido já nasce **entregue** (`quantidade_entregue = quantidade`, registrando quem/quando).
- **Desmarcado** → os itens ficam **pendentes** e são retirados depois pelo console "Dia do evento" (5.4b).

Assim, a venda de balcão de consumo imediato não precisa ser marcada de novo no console, e a compra "para
levar depois" entra automaticamente na fila de retirada.

### Arquivos alterados
- `core/views.py`: `_criar_pedido` ganhou o parâmetro **`entregar_agora`** (nasce entregue, com
  `entregue_em`/`entregue_por`). `evento_pdv_view` e `evento_pdv_inscricao_view` leem o checkbox
  (`entregar_agora`, default marcado), passam ao helper e devolvem o estado ao template; a venda no PDV
  avisa "Itens entregues." quando aplicável.
- `templates/core/evento_pdv.html` e `evento_pdv_inscricao.html`: checkbox "Entregar os itens agora"
  (este só quando há itens da lojinha). `static/css/eventos.css`: estilo `.entregar-agora`.

### Decisões
- **Default marcado**: a maioria das vendas de balcão é retirada na hora; desmarca-se para "levar depois".
- Vale para venda avulsa **e** para a lojinha comprada junto da inscrição presencial. Cortesia também
  entrega (item físico), só não soma em dinheiro.

### Validação
- `manage.py check` OK. PDV de **vendas** (test client, Diretor): `entregar_agora` ausente → item **0/1**
  (pendente); marcado → **1/1** (entregue) + `entregue_por`. PDV de **inscrição**: idem no pedido vinculado
  (0/1 vs 1/1). Novos registros de teste **removidos** (banco limpo). **Visual (Chrome headless)**: checkbox
  em caixa verde, marcado por padrão, entre os itens e o vínculo/pagamento.

### Pendências / próximo passo
- **5.4d**: contadores de presença/retirada no painel + **guarda de exclusão do evento simples** (só
  exclui sem presença marcada).

---

## 2026-07-05 - Evento complexo — Fase 5.4b: marcar check-in e entrega no console "Dia do evento"

### Resumo
Continuação da Fase 5.4: o console **"Dia do evento"** (`/eventos/<id>/dia/`) deixou de ser só leitura —
agora o Diretor/operador **marca** o dia de fato, **sem recarregar a página**:
- **Check-in por participante**: cada participante tem um botão que alterna **Marcar chegada ↔ ✅ Chegou**.
- **Retirada por unidade**: o **selo** do item é clicável (entrega **tudo** ou **desfaz**); itens com mais
  de 1 unidade ganham um **stepper − x/y +** para **entrega parcial** (ex.: pegou 1 de 3 agora).
- **Resumo do dia ao vivo**: os contadores (check-in X/Y, retiradas X/Y, pendentes) atualizam na hora.
- Cada marcação guarda **quem** marcou e **quando** (`presente_por`/`presente_em`, `entregue_por`/`entregue_em`).

### Como funciona
- Endpoints JSON **`evento_checkin`** e **`evento_entrega`** (POST, `@operador_required`): validam que o
  participante/item pertence ao evento e a uma **inscrição/pedido confirmado**, limitam a entrega a
  **0..quantidade** do item e devolvem o novo status + o **resumo do dia** recalculado (helper único
  **`_resumo_dia`**, reusado pela tela e pelos endpoints). O JS envia via `fetch` com **`X-CSRFToken`** e
  atualiza a linha (selo/stepper) e o resumo. Toast só em caso de erro (marcar em massa não polui a tela).

### Arquivos criados/alterados
- `core/views.py`: helper `_resumo_dia`; views `evento_checkin_view` e `evento_entrega_view`;
  `evento_dia_view` passou a usar `_resumo_dia`. Import de `Count`/`Q`/`Sum`.
- `core/urls.py`: rotas `evento_checkin` (`.../dia/checkin/`) e `evento_entrega` (`.../dia/entrega/`).
- `templates/core/_dia_entrega.html` (novo): controle de retirada por unidade (selo clicável + stepper),
  reusado nas duas seções (inscrições e avulsos). `evento_dia.html`: botão de check-in, `#diaDados`
  (URLs + csrf), IDs no resumo, inclui o parcial de entrega nas duas seções, nota atualizada.
- `static/js/evento_dia.js`: ações de marcar (fetch/JSON, atualização inline dos selos/stepper e do
  resumo). `static/css/eventos.css`: `.selo-btn`, `.entrega`/`.entrega-stepper`/`.entrega-btn`/`.entrega-num`.

### Validação
- `manage.py check` OK. Endpoints (test client, Diretor): check-in ON→presente=True + `presente_por` +
  resumo.presentes=1; OFF→zera presente/em/por; entrega 1→entregue, 999→**clamp** para a quantidade,
  0→pendente + zera em/por; item inexistente→**404**; **GET**→**405**. Property `status_entrega` conferida.
  **Visual (Chrome headless, desktop)**: selos clicáveis "Marcar chegada"/"✅ Chegou" e "Não entregue", e
  item com qtd>1 mostrando selo **Parcial** + stepper **− 1/3 +** — consistente nas duas seções. Marcações
  de teste revertidas (banco limpo).

### Pendências / próximo passo
- **5.4c**: "vai levar agora?" no balcão (PDV venda e PDV inscrição) — já marcar a entrega na hora.
- **5.4d**: contadores no painel + guarda de exclusão do evento simples.

---

## 2026-07-05 - Evento complexo — Fase 5.4a: Check-in + Retirada (console "Dia do evento", só leitura)

### Resumo
Início da **Fase 5.4** (definida com o usuário): controle do **dia do evento** — **check-in** dos
participantes e **retirada/entrega** dos itens da lojinha. Escopo desta parte (**5.4a**): os **modelos** e
a **tela de consulta**, ainda **só leitura** (as marcações vêm na 5.4b).

- **Modelos**: `ParticipanteInscricao` ganhou **check-in por participante** (`presente`, `presente_em`,
  `presente_por`) e `ItemPedidoLoja` ganhou **retirada por unidade** (`quantidade_entregue`, `entregue_em`,
  `entregue_por`) — permite **entrega parcial** (props `entregue`/`entrega_parcial`/`status_entrega`).
  Migration **0016**.
- **Console "Dia do evento"** (`/eventos/<id>/dia/`, **Diretor + operadores**): por **família** (inscrição
  confirmada), mostra os **participantes** com o selo de check-in (✅ Chegou / Não chegou) e os **itens da
  lojinha comprados** com o selo de retirada (Não entregue / Parcial (x/y) / ✅ Entregue). Tem **resumo do
  dia** (check-in X/Y + retiradas X/Y), **busca** em tempo real (responsável/participante/código) e uma
  seção de **pedidos avulsos** (passantes sem inscrição). Os pedidos são casados à inscrição pela **mesma
  regra do painel** (vínculo direto ou mesma conta única) — helper `_casar_pedidos_inscricoes` (extraído
  para reuso).
- **Pontos de entrada**: aba-link **"📋 Dia do evento"** na barra do painel e card na landing **"Operar"**.

### Decisões (definidas com o usuário)
- **Entrega por unidade** (permite retirada parcial: pegou 1 de 3 agora, o resto depois).
- **Todos os itens** da lojinha entram no controle (sem marcar "entregável" por produto).
- **Check-in por participante** (cada criança), não por família — melhor para a presença.
- Escopo de "entregável" cobre também **pedidos avulsos** (passantes), em seção separada.

### Arquivos criados/alterados
- `core/models.py`: campos de check-in em `ParticipanteInscricao` e de retirada em `ItemPedidoLoja` (+
  props). `core/migrations/0016_itempedidoloja_entregue_em_and_more.py` (novo).
- `core/views.py`: `evento_dia_view` (`@operador_required`, só leitura) e helper `_casar_pedidos_inscricoes`.
- `core/urls.py`: rota `evento_dia` (`/eventos/<id>/dia/`).
- `templates/core/evento_dia.html` (novo); `evento_painel.html` (aba-link "Dia do evento");
  `evento_operar.html` (card "Dia do evento").
- `static/js/evento_dia.js` (novo: busca). `static/css/eventos.css`: estilos do console (`.dia-*`, `.selo-*`).

### Validação
- `manage.py check` OK; `migrate` aplicado. Render (test client, Diretor) do evento 4: **200**, com resumo
  (Check-in 1/4, Retiradas 0/12), busca, cards por inscrição (selos Chegou/Não chegou e Não entregue) e
  seção de pedidos avulsos. Property `status_entrega` conferida (0/3→pendente, 1/3→parcial, 3/3→entregue).
  **Visual (Chrome headless, desktop 900px e mobile 430px)** conferido — layout consistente com o padrão
  azul/verde. As marcações de teste feitas nos dados reais foram **revertidas** (banco limpo).

### Pendências / próximo passo
- **5.4b**: ações de marcar (check-in por participante + entrega por unidade, com status ao vivo).
- **5.4c**: "vai levar agora?" no balcão (PDV venda e PDV inscrição).
- **5.4d**: contadores no painel + guarda de exclusão do evento simples.

---

## 2026-07-05 - Lista de eventos: botões Duplicar/Excluir menores, consistentes e grudados na base

### Resumo
Ajuste visual dos botões dos cards da lista de **Eventos**:
- **Duplicar** passou a usar o mesmo estilo pequeno do "Abrir painel"/"Criar evento" (`btn-acao
  btn-acao-pequeno`, verde) — antes era o `btn-secundario` (grandão).
- **Excluir** virou um **botão pequeno vermelho** (fundo/borda suaves, mesmo tamanho) em vez de texto
  solto — mais bonito e do mesmo tamanho dos outros.
- **Bug corrigido**: os botões ficavam "no meio" do card. Havia **duas** regras `.evento-acoes` no
  `eventos.css` e a da página pública (`margin-top: 24px`) sobrescrevia a da lista (`margin-top: auto`).
  Escopei a da lista em **`.evento-card .evento-acoes`**, então os botões voltam a **grudar na base** do
  card (alinhados entre cards de alturas diferentes).

### Arquivos criados/alterados
- `templates/core/eventos.html`: "Duplicar" usa `btn-acao btn-acao-pequeno`.
- `static/css/eventos.css`: `.evento-card .evento-acoes` (escopo + `margin-top:auto`); `.btn-excluir-evento`
  menor e com fundo/borda (botão, não texto).

### Decisões tomadas
- Duplicar em verde (igual ao "Abrir painel"); Excluir em vermelho (destrutivo) — mesmo tamanho/forma.

---

## 2026-07-05 - Lista de eventos: etiqueta do tipo mais compacta e bonita

### Resumo
Na lista de **Eventos**, a etiqueta ao lado do título (antes o pill grande "Evento com inscrição" /
"Evento simples") virou uma **etiqueta compacta com ícone**: **🎟️ Com inscrição** (verde suave) e
**🗓️ Simples** (azul suave). Menor, com texto curto e sem quebrar linha.

### Arquivos criados/alterados
- `templates/core/eventos.html`: a etiqueta do tipo usa `.evento-tipo`/`.evento-tipo-<tipo>` com ícone +
  texto curto (em vez de `.pill` com `get_tipo_display`).
- `static/css/eventos.css`: estilos `.evento-tipo`, `.evento-tipo-inscricao`, `.evento-tipo-simples`.

### Decisões tomadas
- Texto curto ("Com inscrição" / "Simples") com ícone; o tipo completo continua no modal de detalhes.

---

## 2026-07-05 - Evento complexo — Fase 5.3b: cupom por participante + faixa + geração em lote + validação ao vivo

### Resumo
Evolução dos cupons de desconto (Fase 5.3), definida com o usuário. O cupom deixou de ser um campo
único da inscrição (que abatia "o participante de maior valor") e passou a ser **por participante**,
com **validação ao vivo** e **restrição por faixa etária**:
- **Cupom por participante**: cada participante da inscrição (online e balcão) tem seu **próprio campo
  de cupom**; o desconto vale **só para aquele participante** (o usuário escolhe em quem aplicar).
- **Validação ao vivo**: ao digitar/sair do campo, o sistema valida no servidor (endpoint JSON) e mostra
  o **toast padrão** — verde quando aplicado (com o **desconto em R$**) ou vermelho quando inválido.
  O **total** da inscrição já **abate** o desconto na hora e um resumo mostra **"Cupons: −R$ X"**.
- **Faixa etária no cupom**: ao gerar, o Diretor pode restringir o cupom a uma **faixa etária**. Se o
  participante não estiver na faixa, aparece o erro "**Cupom é só para <faixa>**" (no ao vivo e ao enviar).
- **Geração em lote**: a aba "Desconto" ganhou **Quantidade** (stepper − / +), gerando **até 5 cupons por
  vez** com o mesmo percentual e faixa; ao tentar passar de 5, toast "**No máximo 5 cupons por vez**".
- **Layout revisado** da aba "Desconto": o campo de **%** (que parecia sem estilo, pois o painel não
  carrega o CSS de formulário) agora é estilizado localmente, em uma **grade** (Desconto · Quantidade ·
  Faixa) dentro de um card.

### Arquivos criados/alterados
- `core/models.py`: `CupomDesconto` ganhou **`faixa`** (FK opcional a `FaixaEtariaPreco`) e **`participante`**
  (FK opcional a `ParticipanteInscricao`, quem usou). Migration **`0015`**.
- `core/views.py`: `_processar_cupons_participantes` (valida/aplica o cupom digitado na linha de cada
  participante: uso único, sem repetir código, casa a faixa) e `_marcar_cupons_usados`; **`evento_cupom_validar_view`**
  (endpoint JSON GET de validação ao vivo — não grava nada); `evento_inscrever_view` e
  `evento_pdv_inscricao_view` passaram a usar esses helpers (corrige a `_aplicar_desconto_cupom` removida);
  `evento_cupom_novo_view` aceita **`quantidade`** (1–5) e **`faixa`**; o painel anexa `i.cupons_aplicados`
  (lista) a cada inscrição (pode haver mais de um cupom por inscrição). `tem_cupons`/`faixas_json`/`diretoria_json`
  no contexto das duas telas de inscrição. Import de `JsonResponse`.
- `core/urls.py`: rota **`evento_cupom_validar`** (`.../cupom/validar/`).
- `templates/core/_participante_linha.html`: **campo de cupom por participante** (`part_cupom_<idx>`) +
  feedback inline, sob `tem_cupons`.
- `templates/core/evento_inscrever.html` e `evento_pdv_inscricao.html`: removido o campo de cupom único;
  passam `tem_cupons` e a URL de validação; JSON de faixas/diretoria; **total ao vivo** com resumo de cupons.
- `templates/core/evento_painel.html`: aba "Desconto" reformulada (grade % / quantidade-stepper / faixa) +
  nota atualizada + pílulas de faixa no cupom + pílula por cupom aplicado (loop).
- `static/js/evento_insc_cupom.js` (**novo**): total ao vivo + validação do cupom por participante + troco
  (PDV). Substitui `static/js/evento_pdv_inscricao.js` (**removido**).
- `static/js/evento_painel.js`: stepper de quantidade dos cupons (toast ao passar de 5).
- `static/css/eventos.css`: layout da geração de cupons (grade, campo de %, stepper), campo de cupom por
  participante (ok/erro) e caixa de total da inscrição.

### Decisões tomadas
- **Cupom por participante** (o usuário escolhe em quem aplicar), no lugar de "o de maior valor".
- **Validação ao vivo por GET** (endpoint JSON sem CSRF, não grava): o **uso único** só é gravado ao
  **confirmar** a inscrição (o servidor revalida). Assim não há cupom "reservado" por formulário aberto.
- **Cortesia** (balcão) ignora cupom (já é grátis) — sem erro de faixa nesse caso.
- Um script único (`evento_insc_cupom.js`) serve as duas telas (online e PDV), evitando duplicação.

### Pendências
- Presença/check-in (Fase 5.4) — próximo passo.

### Resumo
Nova frente da Fase 5: **cupons de desconto**, **somente para inscrição** (não valem na lojinha).
- **Aba "Desconto"** no painel (Diretor): gera cupom informando a **% de desconto** ("Gerar cupom" → cria
  um **código único**); a **lista** mostra cada cupom com **status** ("Disponível" / "Usado por FULANO ·
  −R$ X") e permite **remover** os não usados.
- **Campo "Cupom de desconto"** nos formulários de inscrição — **online** (`evento_inscrever`) e
  **balcão/PDV** (`evento_pdv_inscricao`). Código inválido ou já usado **bloqueia** com aviso.
- **Regra**: cupom de **uso único**; o desconto se aplica a **um participante só** — o de **maior valor**
  (decisão nossa; mais vantajoso). Reduz o valor desse participante e o total; marca o cupom como usado
  (quem usou, valor descontado e vínculo à inscrição). O cupom aparece na inscrição (painel) e na tela de
  sucesso.

### Arquivos criados/alterados
- `core/models.py`: model **`CupomDesconto`** (evento, codigo único, percentual, ativo, inscricao,
  usado_por, valor_desconto, usado_em, criado_por; property `usado`; `gerar_codigo_unico`). Migration
  `0014`.
- `core/views.py`: helpers `_buscar_cupom_valido` e `_aplicar_desconto_cupom` (aplica no participante de
  maior valor); `evento_inscrever_view` e `evento_pdv_inscricao_view` leem/validam/aplicam o cupom (num
  participante) e marcam o uso; novas `evento_cupom_novo_view` / `evento_cupom_excluir_view`; o painel
  passa `cupons` e anexa `i.cupom_aplicado` a cada inscrição.
- `core/urls.py`: rotas `evento_cupom_novo` / `evento_cupom_excluir`.
- `templates/core/evento_painel.html`: aba "Desconto" (topo) + seção (gerar + lista) + pílula do cupom
  na inscrição. `evento_inscrever.html` e `evento_pdv_inscricao.html`: campo "Cupom de desconto".
  `evento_inscricao_sucesso.html`: linha do desconto aplicado.
- `core/admin.py`: registra `CupomDesconto`. `static/css/eventos.css`: estilos do cupom (`.cupom-*`,
  `.pill-cupom`).

### Decisões tomadas
- **Um participante por cupom** (o de maior valor); **uso único**; **só inscrição**. Código
  case-insensitive.
- **Balcão**: o total ao vivo (JS) **não** reflete o cupom (precisaria validar o código no cliente); o
  **servidor** aplica o desconto e calcula o troco ao confirmar. Anotado como limitação.
- Cancelar a inscrição **não** libera o cupom (permanece usado) — simplicidade; revisitar se necessário.

### Validação
- `manage.py check` OK. Teste ponta a ponta: gerar cupom (50%); rejeitar 150% (não cria); inscrição
  online com cupom (2 participantes 30/50 → desconto no de 50 → 25; total 55); cupom marcado usado (por
  quem, −R$ 25, vínculo); **reusar** o cupom → bloqueado; **inexistente** → bloqueado; **balcão** aplica
  (20% de 40 → −R$ 8, total 32). Visual (headless): aba "Desconto" com gerar + lista (1 disponível, 1
  usado com "Usado por … · −R$ 8,00").

### Pendências / próximo passo
- **Fase 5.4 — presença/check-in** (também vira guarda de exclusão dos eventos simples). Melhoria
  possível: refletir o cupom no total ao vivo do balcão (validação via AJAX).

---

## 2026-07-04 - Barra de abas do painel unificada (ícones + mesmo estilo)

### Resumo
Ajuste visual: as abas de ação ("Vender no balcão", "Operadores") destoavam das abas de seção (tinham
ícone e cor diferente). A pedido do usuário, **todas as abas ficaram no mesmo estilo, com ícone**:
Resumo 📊 · Inscrições 🎟️ · Lojinha 🛒 · Custos 💸 · Financeiro 📈 · Vender no balcão 🧾 · Operadores 👥.
Cor base **azul** para todas; a **aba de seção ativa** ganha **sublinhado verde + fundo suave** (as de
ação, que navegam, não têm estado ativo).

### Arquivos alterados
- `templates/core/evento_painel.html`: ícone (`<span aria-hidden>`) nas 5 abas de seção.
- `static/css/eventos.css`: `.painel-aba` cor base → `--azul`; `.ativa` com fundo suave; `.painel-aba-acao`
  perdeu a cor especial (herda a base) — só mantém `text-decoration:none` + a margem separadora.

### Validação
- `manage.py check` OK. Visual (Chrome headless, desktop e mobile): as 7 abas com ícone, mesmo estilo; a
  ativa destacada (sublinhado verde). No mobile quebram em linhas mantendo a consistência.

---

## 2026-07-04 - Reorganização do painel — Etapa 4/4: cards clicáveis no Resumo (conclui a reorg)

### Resumo
**Etapa 4 (última)**: no **Resumo**, os cards de KPI (Inscritos, Arrecadação, Vendas, Receitas, Custos)
ficaram **clicáveis** — com um caret ▾. Ao clicar, abre **abaixo do grid** uma **lista simples** daquele
indicador (accordion: uma por vez; clicar de novo fecha):
- **Inscritos** → responsável + participantes (um por linha).
- **Arrecadação** → quem pagou e quanto.
- **Vendas (lojinha)** → uma linha por venda (comprador + valor).
- **Receitas** → uma linha por entrada (com etiqueta Inscrição/Lojinha).
- **Custos** → uma linha por custo.
O card **Resultado** não é clicável (é o número final). Os gráficos e a cobertura seguem abaixo.

**Com isso a reorganização do painel está completa** (Etapas 1–4): abas internas em Inscrições e Lojinha,
Balcão/Operadores no topo, e cards clicáveis no Resumo.

### Arquivos alterados
- `core/views.py`: `_montar_dashboard` agora recebe `pedidos_confirmados`/`custos` e monta
  `dashboard["listas"]` (inscritos, arrecadacao, vendas, receitas, custos) prontas para o template.
- `templates/core/evento_painel.html`: cards de KPI com `.kpi-clicavel` + `data-lista` + `role/tabindex`
  + caret; `#kpiListas` com 5 painéis `.kpi-lista` (hidden) renderizando cada lista.
- `static/js/evento_painel.js`: accordion dos cards (`.kpi-clicavel` → mostra o `.kpi-lista` do
  `data-lista`; teclado Enter/Espaço; fecha os outros).
- `static/css/eventos.css`: `.kpi-clicavel`/`.kpi-caret`/`.kpi-clicavel.ativo`, `#kpiListas`,
  `.kpi-lista`, `.lista-simples` e `.ls-*` (nome/valor/tag/sec).

### Validação
- `manage.py check` OK. Render (test client): 5 cards `.kpi-clicavel`; 5 painéis `hidden` por padrão;
  listas com os dados certos (arrecadação: quem pagou+quanto; inscritos: responsável+participantes;
  receitas com etiquetas Inscrição/Lojinha; custos). Visual (Chrome headless): ao abrir "Arrecadação", o
  card destaca e a lista aparece abaixo (Carlos R$ 30 / Maria R$ 60), um por linha.

### Pendências / próximo passo
- Reorganização concluída. Próximo da Fase 5: **5.3 códigos de desconto (cupons %)**; depois **5.4
  presença/check-in**.

---

## 2026-07-04 - Reorganização do painel — Etapa 3/4: Balcão e Operadores no topo

### Resumo
**Etapa 3**: os botões **PDV / Balcão** e **Operadores**, que ficavam no **cabeçalho da Lojinha**,
foram movidos para a **barra de abas do topo** (ao lado de Financeiro). Conforme combinado, **só mudou o
lugar do botão** — as páginas de balcão/operadores **não foram reescritas**. As duas novas abas são
**links** (`<a class="painel-aba painel-aba-acao">`) que abrem as páginas existentes; ficam em **azul**
(cor de link) + ícone, para se distinguir das abas de seção (que trocam conteúdo no cliente). O
**"PDV / Balcão"** foi renomeado para **"Vender no balcão"** (mais didático).

### Arquivos alterados
- `templates/core/evento_painel.html`: na `.painel-abas`, 2 abas-link novas ("🧾 Vender no balcão" →
  `evento_pdv`; "👥 Operadores" → `evento_operadores`); removida a `.secao-acoes` do cabeçalho da Lojinha.
- `static/js/evento_painel.js`: a troca de seção agora seleciona `.painel-aba[data-aba]` (os links
  `.painel-aba-acao`, sem `data-aba`, **não** entram no toggle — navegam para a página).
- `static/css/eventos.css`: `.painel-aba { text-decoration: none }` (para os `<a>`) e `.painel-aba-acao`
  (azul + margem separando das abas de seção).

### Decisões tomadas
- **Abas-link** (não reescrever as telas de operador, que são de tela cheia): só o ponto de entrada mudou
  de lugar. A "Nova inscrição (balcão)" segue na aba Inscrições (o usuário pediu para mover só os da
  Lojinha).

### Validação
- `manage.py check` OK. Render (test client): 2 abas-link no topo apontando para `…/pdv/` e
  `…/operadores/`; cabeçalho da Lojinha **sem** o "PDV / Balcão" antigo. Visual (desktop e mobile): abas
  de ação em azul ao lado/abaixo das abas de seção (quebram bem no responsivo).

### Pendências / próximo passo
- **Etapa 4** (última da reorg): **cards clicáveis no Resumo** → cada card abre uma lista simples.

---

## 2026-07-04 - Reorganização do painel — Etapa 2/4: abas internas na "Lojinha"

### Resumo
**Etapa 2** da reorganização: a aba **Lojinha** ganhou **sub-abas** (mesmo padrão da Etapa 1):
- **Produtos** (abre primeiro) — a lista de produtos + botão **"Novo produto"** (que saiu do cabeçalho).
- **Pedidos** — a lista de pedidos com uma **busca** (por comprador, código ou produto), igual à das
  inscrições; some quem não bate e mostra "Nenhum pedido encontrado".

Os botões **PDV / Balcão** e **Operadores** continuam **no cabeçalho da Lojinha por enquanto** — a
**Etapa 3** os move para a barra do topo (só troca de lugar, sem reescrever as páginas).

### Arquivos alterados
- `templates/core/evento_painel.html`: seção Lojinha em `.sub-abas` (Produtos/Pedidos) + 2 `.sub-secao`;
  "Novo produto" movido para a aba Produtos; busca (`#buscaPedidos`) + `.pedido-busca` nos itens +
  mensagem "pedidosVazio".
- `static/js/evento_painel.js`: `ligarBusca("buscaPedidos", ".pedido-busca", "pedidosVazio")` (reusa o
  helper de busca e o de sub-abas — ambos genéricos).

### Validação
- `manage.py check` OK. Render (test client): 2 sub-abas; Produtos visível, Pedidos `hidden`; busca de
  pedidos presente (2 itens `.pedido-busca`); "Novo produto" só na aba Produtos; `<div>` equilibrados.
  Visual (Chrome headless, desktop): Lojinha com sub-abas Produtos/Pedidos, "Novo produto" na aba.

### Pendências / próximo passo
- **Etapa 3**: mover **Balcão** e **Operadores** para a barra do topo (abas-link) + renomear "PDV /
  Balcão". Depois **Etapa 4** (cards clicáveis no Resumo).

---

## 2026-07-04 - Reorganização do painel — Etapa 1/4: abas internas em "Inscrições"

### Resumo
Início de uma **reorganização do painel do evento** (alinhada com o usuário) para dar responsabilidade
clara a cada aba e evitar rolagem. **Etapa 1 (esta)**: a aba **Inscrições** ganhou **sub-abas**:
**Lista de inscrições** (abre primeiro) · **Configuração** · **Faixas de preço** · **Formulário**. Assim
a lista (que cresce com o tempo) aparece de cara e as configurações ficam **minimizadas**, a um clique —
sem precisar rolar até o fim. O botão "Nova inscrição (balcão)" e o status/prazo ficam no topo da aba
(comuns). Removida uma nota desatualizada ("...entram nas próximas partes da Fase 2").

### Plano completo da reorganização (etapas)
1. **Etapa 1 — CONCLUÍDA ✅**: abas internas em Inscrições.
2. **Etapa 2**: abas internas em **Lojinha** (Produtos · Pedidos) + **busca** na lista de pedidos.
3. **Etapa 3**: mover os **botões** de **Balcão** (vender) e **Operadores** de dentro da Lojinha para a
   **barra do topo** (ao lado de Custos/Financeiro), como abas-link para as páginas atuais (**sem
   reescrever** as páginas — só muda o local do botão de entrada); renomear "PDV / Balcão" para algo
   didático (ex.: "Vender no balcão").
4. **Etapa 4**: no **Resumo**, tornar os **cards de KPI clicáveis** → cada um abre uma **lista simples**
   (Inscritos → responsável+participantes; Arrecadação → quem pagou+quanto; Vendas → 1/linha; Receitas →
   1/linha; Custos → 1/linha).

### Arquivos alterados
- `templates/core/evento_painel.html`: seção Inscrições envolvida em `.sub-abas` + 4 `.sub-secao`
  (`data-subsecao=lista|config|faixas|formulario`); "lista" visível, demais `hidden`.
- `static/js/evento_painel.js`: handler genérico de **sub-abas** (por `.sub-abas`, escopado à
  `.painel-secao` pai) — reutilizável na Etapa 2 (Lojinha).
- `static/css/eventos.css`: `.sub-abas`/`.sub-aba`/`.sub-aba.ativa` (pílulas) e `.sub-secao[hidden]`.

### Validação
- `manage.py check` OK. Render (test client): 4 sub-abas; "lista" sem `hidden`, Config/Faixas/Formulário
  `hidden`; `<div>` abrem == fecham (estrutura equilibrada). Visual (Chrome headless) em **desktop e
  mobile (~470px)**: sub-abas em pílula, "Lista de inscrições" ativa, configs escondidas.

### Pendências / próximo passo
- **Etapa 2**: abas na Lojinha + busca nos pedidos.

---

## 2026-07-04 - Inscrição: "nome completo" + botão "Ver detalhes"

### Resumo
Dois ajustes:
1. **Nome completo**: o formulário de inscrição passou a pedir **"Nome completo do responsável"**
   (placeholder "Nome e sobrenome" + dica "evite só o primeiro nome") e **"Nome completo do
   participante"** (placeholder). Assim a pessoa não põe só o primeiro nome e o **casamento** com o
   cadastro do clube (cobertura) funciona melhor. Vale para a inscrição online e a do PDV (mesmo form).
2. **Botão de expandir**: na lista de inscrições do painel, o `<summary>` mudou de "Ver participantes e
   respostas" para **"Ver detalhes"** — que agora cobre participantes, respostas **e** as compras na
   lojinha.

### Arquivos alterados
- `core/forms.py`: `InscricaoForm.responsavel_nome` → label "Nome completo do responsável" + placeholder
  + `help_text`.
- `templates/core/_participante_linha.html`: placeholder "Nome completo do participante".
- `templates/core/evento_painel.html`: `<summary>Ver detalhes</summary>`.

### Validação
- `manage.py check` OK. Render: o form de inscrição mostra "Nome completo do responsável" + placeholder +
  dica + "Nome completo do participante"; o painel (com inscrição) mostra "Ver detalhes" (antigo texto
  ausente).

---

## 2026-07-04 - Compras da lojinha por inscrição (o que cada pessoa comprou)

### Resumo
O usuário sentia falta de ver **o que cada pessoa comprou** na lojinha (casamento inscrição × pedidos).
Agora, na aba **Inscrições** do painel, cada inscrito mostra (ao expandir "Ver participantes…") um bloco
**"🛒 Compras na lojinha"** com os pedidos daquela pessoa e o **Total geral (inscrição + lojinha)**; o
topo do card ganha uma **pílula 🛒** com o valor gasto na lojinha.

**Como casa (do confiável ao menos):** (1) **vínculo direto** `PedidoLoja.inscricao` (comprou junto da
inscrição ou vinculado no PDV); (2) **mesma conta logada** — `pedido.usuario == inscricao.usuario`,
**somente** quando esse responsável tem **uma** inscrição no evento (evita atribuir a inscrição errada);
pedidos da mesma conta ganham a etiqueta "· mesma conta". Pedidos **avulsos** (sem conta e sem vínculo —
passante) **não** são atribuídos e seguem só na aba Lojinha. Não usa casamento por nome aqui (evita o
falso positivo).

### Arquivos alterados
- `core/views.py`: `evento_painel_view` calcula `compras_por_insc` (FK ou mesma conta única) e anexa a
  cada inscrição `i.compras`, `i.total_compras` e `i.total_geral`.
- `templates/core/evento_painel.html`: bloco "Compras na lojinha" no detalhe da inscrição + pílula
  `pill-loja` no topo + linha "Total geral".
- `static/css/eventos.css`: `.pill-loja`, `.inscrito-compras`, `.inscrito-compras-titulo`,
  `.inscrito-total-geral`.

### Decisões tomadas
- **Só sinais confiáveis** (FK + mesma conta logada única); nada de casar por nome para dinheiro.
- **Avulsos ficam na aba Lojinha** (são passantes/anônimos, sem dono).
- Divisão: **Inscrição** = o que aquela pessoa/família comprou; **Lojinha** = todos os pedidos (inclui
  avulsos).

### Validação
- `manage.py check` OK. Teste (render, test client): pedido **vinculado (FK)** + pedido da **mesma conta**
  aparecem no bloco (o 2º com "mesma conta"); **Total geral = R$ 94,00** (60 + 24 + 10), **excluindo** um
  pedido **avulso** de R$ 8; visual do card (pílula 🛒 + bloco + total) conferido em headless.

### Pendências / próximo passo
- (Opcional futuro) **vínculo exato na inscrição** (selecionar o aventureiro) melhoraria também a
  atribuição de compras de anônimos. Fase 5: **5.3 códigos de desconto**, depois **5.4 presença/check-in**.

---

## 2026-07-04 - Corrige edição de produto: preço e estoque não vinham preenchidos

### Resumo
Ao **editar** um produto da lojinha, as variações mostravam o **nome**, mas os campos de **preço** e
**estoque** vinham **vazios** (não reexibiam os últimos valores). **Causa**: a view passava o valor como
`Decimal`/`int` cru e o template, em **pt-BR**, **localizava** o número (ex.: `12,00` com vírgula); um
`<input type="number">` **não aceita vírgula** e descarta o valor → campo vazio. **Correção**: a view
passa `valor_raw`/`estoque_raw` como **string com ponto** (`str(v.valor)` / `str(v.estoque)`), que o
template não localiza.

### Arquivos alterados
- `core/views.py`: `_produto_form` (GET de edição) usa `str(v.valor)` e `str(v.estoque)` ao montar as
  linhas de variação.

### Validação
- `manage.py check` OK. Render da edição (test client): os inputs vêm com `value="12.00"` / `value="18.50"`
  (preço, com ponto) e `value="20"` / `value="15"` (estoque); sem vírgula; nomes preservados.

### Nota técnica
- **Ao reexibir número em `<input type="number">` cru**, passar **string com ponto** (ou `unlocalize`) —
  um `Decimal`/`float` é localizado no template (vírgula em pt-BR) e o input rejeita. Ver REGRAS.

---

## 2026-07-04 - Refinos do dashboard: busca (visual + bug) e cobertura inteligente

### Resumo
Ajustes pedidos após validar o dashboard:
1. **Caixas de busca repaginadas**: viraram um campo "pill" com **ícone de lupa** (SVG inline), foco
   azul e largura total (antes era um input cru com emoji no placeholder).
2. **Bug da busca corrigido**: ao pesquisar algo inexistente, a **lista continuava aparecendo** e a
   mensagem "nada encontrado" surgia embaixo. **Causa**: os itens têm `display:flex`, que **vence** o
   atributo `[hidden]` (do UA stylesheet). **Correção**: o JS passou a alternar a classe
   **`.busca-oculto { display:none !important }`** — agora a lista **some** e sobra só a mensagem; ao
   limpar a busca, tudo volta.
3. **Cobertura do clube — casamento inteligente**: antes exigia **nome exato**. Agora compara por
   **conjunto de nomes** (tokens sem acento/caixa e **sem conectores** de/da/do): o participante casa
   com um aventureiro quando **todos os nomes digitados estão contidos** no nome cadastrado **e** isso
   aponta para **um único** aventureiro. Se servir para mais de um → **"a conferir"** (não casa errado),
   com aviso "⚠️ N a conferir". Ex.: "Beatriz Gonçalves" casa com "Beatriz Gonçalves Steinmeyer"; "Beatriz"
   sozinho (duas Beatriz) fica a conferir.

### Arquivos alterados
- `core/views.py`: helpers `_tokens_nome`/`_CONECTORES_NOME`; `_montar_dashboard` refez a cobertura
  (subconjunto de tokens + unicidade + contagem de `ambiguos`).
- `static/js/evento_painel.js`: `ligarBusca` usa `classList.toggle("busca-oculto", …)` (não mais o
  atributo `hidden`).
- `templates/core/evento_painel.html`: buscas (Inscrições e cobertura) em `.busca-box` com lupa SVG;
  aviso "a conferir" na cobertura.
- `static/css/eventos.css`: `.busca-box`/`.busca-icone`/`.busca-input` (pill + foco), `.busca-oculto`
  (`display:none !important`) e `.cob-aviso`.

### Decisões / proposta
- **Casamento por tokens + unicidade** é conservador (prefere não casar a casar errado — como o usuário
  pediu no caso "Beatriz"). Continua sendo **melhor esforço**.
- **Proposta para o vínculo EXATO** (a combinar): no formulário de inscrição, quando o **responsável
  está logado**, oferecer para **escolher o participante entre os aventureiros DELE** (lista curta e
  privada — não expõe o clube todo). Cria `ParticipanteInscricao.aventureiro` (FK opcional) → cobertura
  100% exata. Para inscrição pública/sem login, mantém texto livre + o casamento por nome. Requer
  migration + mexer no form público — **não implementado ainda** (aguarda o "ok").

### Validação
- `manage.py check` OK. Teste do casamento (nomes fictícios p/ não colidir com dados reais): "Xbeatriz
  Xgoncalves" → casa com "...Xstein"; "Xbeatriz Xsilva" → casa com "...Xsilva"; "Xjoao Xalves" → casa;
  "Xbeatriz" sozinho → **ambíguo** (não casa; conta em "a conferir"). Visual (Chrome headless, dados
  fictícios): caixa de busca com lupa + aviso "a conferir" conferidos.

### Pendências / próximo passo
- Decidir o **vínculo exato na inscrição** (proposta acima). Fase 5: **5.3 códigos de desconto**, depois
  **5.4 presença/check-in**.

---

## 2026-07-04 - Evento complexo — Fase 5 (parte 2): Resumo vira dashboard

### Resumo
A aba **Resumo** do painel virou um **dashboard** visual e didático (pedido do usuário: "bem bonito,
fácil de entender"). Conteúdo:
1. **KPIs repaginados**: ícones por card; **Receitas em verde**, **Custos em vermelho**, **Resultado**
   em destaque (verde/vermelho); hover.
2. **Gráficos em CSS/SVG puro** (sem bibliotecas — regra do projeto): **Receitas × Custos** (barras
   verde/vermelho + resultado), **Entradas por forma de pagamento** e **Inscritos por faixa etária**
   (barras azul, com valor rotulado). Cor segue a boa prática: magnitude num **tom só** (azul), status
   (verde/vermelho) **sempre com rótulo** — a cor nunca é a única pista.
3. **Cobertura do clube** ("Aventureiros do clube neste evento"): **donut** ("X de Y inscritos", %) +
   duas listas — **Inscritos** e **Ainda não inscritos** — dos aventureiros cadastrados, **casadas por
   nome** (melhor esforço — a inscrição guarda nome livre, sem vínculo rígido com o cadastro), com
   **busca em tempo real**.
4. **Busca na aba Inscrições**: filtra a lista por responsável/participante ("fulano se inscreveu?" —
   se não aparece, não se inscreveu).

Divisão de responsabilidades (para não duplicar com o Financeiro): **gráfico/visual mora no Resumo;
número/tabela/extrato mora no Financeiro**.

### Arquivos criados/alterados
- `core/views.py`: helper **`_montar_dashboard`** (cobertura por nome via `_normaliza`/`Aventureiro`;
  séries dos gráficos: formas, faixas, receitas×custos com percentuais prontos); `evento_painel_view`
  passa `dashboard` no contexto (e `financeiro` como variável).
- `templates/core/evento_painel.html`: aba **Resumo** reconstruída (KPIs com ícone, gráficos de barra,
  donut e cobertura com busca); aba **Inscrições** ganhou a caixa de busca + `.inscricao-busca` nos itens
  e a mensagem "nenhuma inscrição encontrada".
- `static/js/evento_painel.js`: helper **`ligarBusca`** (normaliza + filtra, padrão do `usuarios.js`)
  ligado à cobertura (`#buscaCobertura`) e às inscrições (`#buscaInscricoes`).
- `static/css/eventos.css`: KPIs (ícone/cores), `.dash-graficos`/`.dash-card`, barras
  (`.barra-*`, verde/vermelho/azul), **donut** (`.donut*`, via `pathLength="100"` + `stroke-dasharray`),
  cobertura (`.cobertura-*`, `.cob-item`) e `.busca-input` (largura total). Responsivo.

### Decisões tomadas
- **Cobertura por nome (melhor esforço)**: não há vínculo rígido entre `ParticipanteInscricao` (nome
  livre) e `Aventureiro`; casa por nome normalizado (ignora caixa/acentos). Serve como referência; um dia
  pode virar vínculo real.
- **Charts sem lib** (CSS/SVG). Paleta: magnitude em tom único (azul); status verde/vermelho com rótulo.
- **Duas buscas**: cobertura (membros do clube, inscrito/não) e Inscrições (todos, inclusive público).

### Validação
- `manage.py check` OK. Teste do helper `_montar_dashboard` com dados fictícios: cobertura casa por nome
  **mesmo em minúsculo** (1 inscrito), não-membro fica **fora** da cobertura, faixas/formas/receitas×custos
  com contagens e percentuais corretos. **Visual (Chrome headless, dados fictícios — sem expor nomes
  reais de menores)**: KPIs, 3 gráficos de barra, donut de cobertura e listas com busca — conferidos em
  **desktop e mobile (~470px)**, sem overflow.

### Pendências / próximo passo
- **Fase 5 — parte 3: códigos de desconto** (cupons %). Depois: **presença/check-in**. Pagamento real
  (gateway) segue para depois.

---

## 2026-07-04 - Painel de evento inexistente redireciona (em vez de 404 cru)

### Resumo
Depois de excluir um evento, um **link/aba antigo** para o painel dele (`/eventos/<id>/`) mostrava um
**404 cru do Django**. Agora, se o evento não existe (ex.: foi excluído), o painel **redireciona** para a
lista de Eventos com um **toast**: "Esse evento não existe mais (pode ter sido excluído)." — UX
consistente com o resto do sistema (o 404 do evento 33/`_TESTE_PGTO`, já removido, foi o gatilho).

### Arquivos alterados
- `core/views.py`: `evento_painel_view` troca `get_object_or_404` por busca + redirect com `messages.info`
  para `core:eventos` quando o evento não existe.

### Validação
- `manage.py check` OK. Teste (Diretor): `GET /eventos/999999/` → **302** para `/eventos/`; seguindo o
  redirect, a página traz o **toast** "não existe mais".

### Observação
- As demais rotas de evento (loja/página/PDV/etc.) seguem com `get_object_or_404`; dá para estender o
  mesmo tratamento se algum link antigo delas incomodar.

---

## 2026-07-04 - Evento complexo — Fase 5 (parte 1): Financeiro (extrato completo)

### Resumo
A aba **Financeiro** do painel do evento deixou de ser "em breve" e virou o **extrato/prestação de
contas** do evento — a pedido do usuário, "bem completo, bonito e responsivo". Conteúdo:
1. **Resultado** em destaque: **Entradas − Saídas = Resultado** (banner verde/vermelho, com selo
   Lucro/Prejuízo/Zerado).
2. **Resumos** (cards): **por fonte** (inscrições × lojinha), **por forma de pagamento** (dinheiro/Pix/
   cartão/cortesia/online, com quantidade), **por canal** (online × balcão) e **saídas** (total de
   custos + botão "Gerenciar custos" que troca para a aba Custos).
3. **Vendidos por produto** (tabela **movida do Resumo** para o Financeiro).
4. **Extrato**: lista **cronológica** de **todos** os lançamentos — cada inscrição, pedido e custo — com
   data, tipo (badge), código, forma, canal e valor (**+** verde para entradas, **−** vermelho para
   saídas). **Cancelados aparecem** (riscados, selo "cancelado") para auditoria, mas **não entram nos
   totais** (só confirmados contam; cortesia soma R$ 0).

**Divisão de responsabilidades** (definida com o usuário, para não duplicar): **número/tabela** mora no
**Financeiro**; **gráfico** morará no **Resumo/dashboard** (próxima parte da Fase 5). O único indicador
repetido de propósito é o **Resultado**. Os **custos continuam sendo cadastrados na aba Custos** — o
Financeiro só **consolida** (não duplica o CRUD).

### Arquivos criados/alterados
- `core/views.py`: helper **`_montar_financeiro(...)`** (entradas por forma/canal, extrato de todos os
  lançamentos com flag `cancelado`, totais) e `evento_painel_view` passa `financeiro` no contexto.
- `templates/core/evento_painel.html`: aba **Financeiro** completa (banner de resultado, cards de
  resumo, "vendidos por produto" e extrato); o bloco "vendidos por produto" saiu do **Resumo** (que
  ficou com os KPIs + nota de que os gráficos vêm em breve).
- `static/js/evento_painel.js`: botões `[data-aba-ir]` trocam de aba (ex.: "Gerenciar custos →").
- `static/css/eventos.css`: estilos do Financeiro — `.fin-resultado` (banner), `.fin-cards`/`.fin-card`,
  `.tabela-extrato` e `.lanc-*` (badges por tipo, +/−, cancelado riscado). Responsivo (cards empilham no
  celular; extrato rola dentro de `.tabela-scroll`).

### Decisões tomadas
- **Financeiro = extrato/contabilidade** (números + extrato); **Resumo/dashboard = visual** (KPIs +
  gráficos, próxima parte). Evita duplicar responsabilidades.
- Só **confirmados** entram nos totais; **cancelados** ficam visíveis no extrato (auditoria). Cortesia
  conta como transação com valor R$ 0.
- **Custos** permanecem na aba Custos (com upload de comprovante); o Financeiro apenas consolida.

### Validação
- `manage.py check` OK. Render (test client + Chrome headless) com dados variados (1 inscrição online, 1
  pedido Pix, 1 pedido cancelado, 1 pedido cortesia, 1 custo): **Entradas R$ 54 − Saídas R$ 50 =
  Resultado R$ 4 (Lucro)**; "por forma" (Online 30 / Pix 24 / Cortesia 0), "por canal" (Online 54 /
  Balcão 0), "vendidos por produto" (qtd 3 / R$ 24), extrato com 5 lançamentos (3 entradas + 1 saída;
  cancelado riscado fora do total). Conferido em **mobile (~490px)** e **desktop** — sem overflow (extrato
  rola no próprio contêiner).

### Pendências / próximo passo
- **Fase 5 — parte 2: dashboard/gráficos** no Resumo (CSS/SVG puro, sem bibliotecas). Depois: **códigos
  de desconto** e **presença/check-in**. Pagamento real (gateway) segue para depois.

---

## 2026-07-04 - Excluir evento (Diretor) — só quando o evento está vazio

### Resumo
O Diretor agora pode **excluir um evento** pela lista de Eventos. Para proteger dados de pessoas e de
vendas, a exclusão é permitida **apenas quando o evento está "vazio"** — sem nenhuma **inscrição** e sem
nenhum **pedido** da lojinha. Assim dá para apagar eventos de **teste/erro** sem risco; eventos que já
têm gente inscrita ou vendas são **preservados** (independentemente da data). Decisão alinhada com o
usuário (a alternativa "só por data" foi descartada por permitir apagar um evento futuro que já tem
inscrições/pedidos). Também foi **removido** um evento de teste que sobrou de uma execução anterior
(`_TESTE_PGTO`, id 33 — vazio).

### Comportamento
- Na lista, cada evento **vazio** ganha um botão **🗑️ Excluir** (discreto/destrutivo). Eventos com
  inscrições/pedidos **não** exibem o botão. Ao excluir, pede **confirmação** e mostra **toast** de
  sucesso; a exclusão remove em cascata a configuração do evento (custos, produtos, faixas, campos,
  operadores). A regra é **revalidada no servidor** (não confia só na ausência do botão).

### Arquivos criados/alterados
- `core/views.py`: `eventos_view` anota `e.pode_excluir` (sem inscrições nem pedidos); nova
  `evento_excluir_view` (`@diretor_required` + `@require_POST`) — bloqueia com mensagem se houver
  inscrições/pedidos, senão apaga e redireciona para a lista com toast.
- `core/urls.py`: rota `evento_excluir` (`/eventos/<id>/excluir/`).
- `templates/core/eventos.html`: botão **Excluir** (form POST com `data-confirmar`) só quando
  `e.pode_excluir`.
- `static/js/eventos.js`: guarda genérica — `<form data-confirmar="...">` pede `confirm()` antes de
  enviar (reutilizável para ações destrutivas).
- `static/css/eventos.css`: estilo do `.btn-excluir-evento` (ghost destrutivo) + `align-items` no
  `.evento-acoes`.

### Decisões tomadas
- **Guardar por conteúdo, não por data**: só exclui evento sem inscrições e sem pedidos. É o que
  cobre com segurança o caso de "apagar evento de teste/erro" sem destruir dados reais.
- Confirmação via `data-confirmar` (JS puro em `eventos.js`), reaproveitável em outras exclusões.

### Validação
- Teste (test client, logado como Diretor): GET lista 200; **excluir evento vazio** → some (302);
  **excluir evento com pedido** → bloqueado (302, evento e pedido **preservados**); **GET** em
  `/excluir/` → **405** (`require_POST`); **não-diretor** → redirecionado, evento preservado; o **botão
  Excluir não aparece** no evento com dados. Todos passaram. `manage.py check` OK. **Visual (Chrome
  headless)**: na lista, o botão 🗑️ Excluir aparece só nos eventos vazios (Reunião e o de teste), e
  **não** no "ACAMPAMENTO…" (que tem pedidos).

---

## 2026-07-04 - Correções de notificação (toast) no fluxo de pagamento da loja

### Resumo
Ajustes pedidos após validar o fluxo de pagamento da lojinha pública:
1. **Toast "Pagamento aprovado!" na hora**: ao "Simular pagamento aprovado", a notificação aparecia só
   **na página seguinte** (ao clicar em "Fazer outro pedido"/"Voltar para o evento"). **Causa**: a tela
   de sucesso (`evento_pedido_sucesso.html`) **não renderizava** o bloco `{% if messages %}`, então a
   mensagem ficava pendente e só era exibida na próxima página que renderizava o bloco. **Correção**: a
   tela de sucesso passou a renderizar o bloco de mensagens → o toast aparece **na própria tela de
   sucesso**.
2. **Balão não sumia** nas páginas públicas: o toast ficava na tela mesmo depois da barrinha de
   progresso. **Causa**: as páginas públicas do evento (loja, página do evento, inscrição, e as novas de
   pagamento/sucesso) **não carregavam** o `inicio.js` (que faz mover para o `<body>` + auto-fechar).
   **Correção**: `inicio.js` passou a ser carregado nessas páginas (é seguro — cada bloco tem guarda de
   elemento).
3. **Copiar o Pix usa a notificação padrão**: o botão "Copiar" do código Pix mostrava um aviso próprio;
   agora dispara o **toast clássico** do sistema ("Código Pix copiado!").

Para isso, o **toast foi centralizado** no `inicio.js` (padrão único do sistema) e ganhou uma API
`window.mostrarToast(texto, tipo)` para criar toast pelo JS, reaproveitada pela cópia do Pix — sem
duplicar a lógica de toast em outro arquivo.

### Arquivos alterados
- `static/js/inicio.js`: bloco de toast reestruturado (helpers `garantirContainer`/`fechar`/`agendar`)
  + **`window.mostrarToast(texto, tipo)`** (cria o contêiner se faltar; mesmo visual/tempo — 4,5s).
- `templates/core/evento_pedido_sucesso.html`: renderiza o bloco `{% if messages %}` (toast na hora) e
  carrega `inicio.js`.
- `templates/core/evento_loja.html`, `evento_pagina.html`, `evento_inscrever.html`,
  `evento_pagamento.html`: passam a carregar `inicio.js` (no pagamento, **antes** do
  `evento_pagamento.js`, para `window.mostrarToast` já existir).
- `static/js/evento_pagamento.js`: o feedback de "copiado" usa `window.mostrarToast(...)` (com fallback
  no texto do botão). `evento_pagamento.html`: removido o aviso próprio `#pixCopiado`.
- `static/css/eventos.css`: removida a regra órfã `.pix-aviso`.

### Decisões tomadas
- **Um único módulo de toast** (`inicio.js`), carregado onde houver notificação (inclusive páginas
  públicas). Nada de segundo mecanismo — mantém o "padrão único" documentado nas REGRAS.
- Toast criado por JS usa o **mesmo** visual/tempo dos toasts do servidor (classe `.mensagem`/CSS).

### Validação
- Teste ponta a ponta (test client): fluxo Pix continua OK (POST sem WhatsApp/sem forma rejeitados;
  válido → pagamento sem criar pedido; aprovar cria confirmado, baixa estoque, limpa sessão; sucesso com
  código/"Pago com"; cartão com aviso Mercado Pago). A tela de sucesso agora **contém** o toast
  (`mensagem-success` "Pagamento aprovado! Pedido confirmado.") e carrega `inicio.js`. `manage.py check`
  OK. **Visual (Chrome headless ~490px)**: toast aparece no topo da tela de sucesso (auto-some em ~4,5s).

---

## 2026-07-04 - Lojinha pública: fluxo de pagamento (simulado) Pix/Cartão

### Resumo
Melhoria do fluxo de **compra na lojinha pela página pública** do evento (o cliente final — sem ser
atendente/diretoria — que compra para chegar já pago e **evitar fila** na retirada). Antes, ao
"Finalizar", o pedido era confirmado na hora, sem escolher forma de pagamento. Agora:
1. **WhatsApp obrigatório** (e-mail opcional) nos dados do comprador.
2. **Autopreenchimento**: os dados do comprador (nome/WhatsApp/e-mail) são lembrados no **localStorage**
   do próprio aparelho (celular e PC) e preenchem sozinhos em pedidos seguintes.
3. **Forma de pagamento** na loja: **Pix** ou **Cartão de crédito** (cards selecionáveis).
4. **Tela de pagamento** (`/eventos/<id>/loja/pagamento/`): no **Pix**, a tela clássica com **QR Code
   (simulado)** e **código "copia e cola"** com botão **Copiar**; no **cartão**, aviso de que **em
   produção** haverá **redirecionamento ao Mercado Pago** (integração futura). Botão **"Simular
   pagamento aprovado"**.
5. **Sucesso melhorado**: lista dos itens em linhas (qtd × produto/variação → subtotal), total e
   "**Pago com Pix/Cartão**".

O **pagamento é simulado** (só ilustra o processo). O **`PedidoLoja` só é criado no banco após a
aprovação**: enquanto pendente, o pedido fica na **sessão** (`loja_checkout`) — evita pedido "pendente"
e estoque reservado por carrinho abandonado; a baixa de estoque (revalidada) acontece só na aprovação.
Escopo: **apenas a loja pública** — o PDV/balcão e o fluxo de inscrição continuam como estavam.

### Arquivos criados/alterados
- `core/views.py`: `evento_loja_view` (WhatsApp obrigatório + forma de pagamento → guarda `loja_checkout`
  na sessão e redireciona para o pagamento, **sem** criar pedido); nova `evento_pagamento_view` (GET
  mostra Pix/cartão; POST simula a aprovação, revalida estoque, cria o pedido confirmado e vai ao
  sucesso). Helpers novos: `_erros_estoque`, `_pseudo_qr`, `_qr_svg` (SVG de QR **simulado**),
  `_pix_copia_cola` (payload Pix **simulado**). Constante `FORMAS_PAGAMENTO_ONLINE` (pix/cartão).
- `core/urls.py`: rota `evento_pagamento` (`/eventos/<id>/loja/pagamento/`).
- `templates/core/evento_loja.html`: WhatsApp `*`, e-mail "(opcional)", seção "Forma de pagamento",
  botão "Ir para o pagamento"; inclui `loja_comprador.js`.
- `templates/core/evento_pagamento.html` (novo): tela de pagamento (Pix: QR + copia e cola; cartão:
  aviso Mercado Pago) + botão "Simular pagamento aprovado".
- `templates/core/evento_pedido_sucesso.html`: lista de itens em linhas + forma de pagamento.
- `static/js/loja_comprador.js` (novo): autopreenchimento via localStorage. `static/js/evento_pagamento.js`
  (novo): botão "Copiar" do código Pix (com fallback `execCommand`).
- `static/css/eventos.css`: cards de forma de pagamento (`.pagamento-metodo`), tela de pagamento
  (`.pagamento-resumo`, `.pix-qr`, `.pix-copia`, `.cartao-mock`, `.pagamento-simulado`) e lista de
  sucesso (`.pedido-lista`).

### Decisões tomadas
- **Pedido só após a aprovação** (dados na sessão enquanto pendente): "só aparece pedido confirmado",
  sem lixo de pedidos abandonados nem estoque preso. Reaproveita `_criar_pedido` com
  `forma_pagamento` pix/cartão e `origem="online"`.
- **QR e "copia e cola" simulados**, gerados sem biblioteca externa (regra do projeto) — o QR é
  decorativo/determinístico (não escaneável) e o payload Pix é fictício. O QR/pagamento reais virão
  com a integração do gateway (**Mercado Pago**), a conversar depois.
- **Formas online = Pix e Cartão** apenas (dinheiro/cortesia continuam no PDV/balcão).

### Validação
- Teste ponta a ponta (test client): GET loja; POST **sem WhatsApp** e **sem forma** rejeitados (0
  pedidos); POST válido → redireciona ao pagamento **sem criar pedido** (dados na sessão); GET pagamento
  Pix (QR/`<svg>` + código Pix + botão simular); **POST aprovar** cria o pedido **confirmado**
  (forma=pix, origem=online, total correto), **baixa o estoque** (5→3) e **limpa a sessão**; GET sucesso
  com código e "Pago com"; GET pagamento **cartão** com aviso do Mercado Pago (sem QR). Todos passaram.
  `manage.py check` OK. **Visual (Chrome headless ~490px)**: loja (WhatsApp*/forma), pagamento Pix
  (QR + copia e cola), pagamento cartão (mock + aviso) e sucesso (lista + total) — sem overflow.

### Pendências / próximo passo
- **Pagamento real (gateway)**: Pix real (QR/BR Code) e **redirecionamento ao Mercado Pago** no cartão
  — a alinhar em conversa futura. Depois, avaliar aplicar o mesmo passo de pagamento à **inscrição** online.
- **Fase 5 — Financeiro/gráficos** segue como o próximo grande passo do evento complexo.

---

## 2026-07-04 - Toasts melhorados (canto da tela + visual) — padrão único do sistema

### Resumo
Refinamento das notificações (pedido do usuário):
- **Posição**: o balão agora aparece **sempre no canto superior direito da TELA** (topo no celular),
  não mais "grudado" na região do conteúdo. **Causa do bug**: `.conteudo-interno` tem
  `animation: entrar` (com `transform`), e um ancestral com `transform` quebra o `position: fixed`
  (vira o bloco de contenção). **Correção**: o `inicio.js` move o contêiner `.mensagens` para o
  `<body>`, fora de qualquer ancestral transformado.
- **Visual**: toast **maior**, com **ícone por tipo** (✅ sucesso, ⛔ erro, ℹ️ info, ⚠️ aviso),
  sombra mais forte, entrada com leve escala e uma **barra de progresso** (mostra o tempo até fechar).
- **Padrão único**: documentado que **todo o sistema** (inscrições, cadastros, e o que vier) deve usar
  esse mesmo tipo de notificação, só nos pontos que realmente exigem aviso (sem poluir a tela).
- A venda/inscrição **cancelada** continua exibida (mais apagada + selo "Cancelado") de propósito,
  para **auditoria** — confirmado com o usuário.

### Arquivos alterados
- `static/js/inicio.js`: move `.mensagens` para o `<body>` antes de exibir/auto-fechar os toasts.
- `static/css/inicio.css`: toast maior, ícone (`::before`), barra de progresso (`::after`), sombra e
  animações de entrada/saída aprimoradas.
- `docs/REGRAS_CODEX.md`: reforça que os toasts são o padrão único de notificação do sistema.

### Validação
- Toast conferido no desktop: aparece no **canto superior direito da tela**, maior, com ícone ✅,
  sombra e barra de progresso. `manage.py check` OK.

---

## 2026-07-04 - Página do evento (botões claros) + notificações (toasts) no módulo de eventos

### Resumo
1. **Página do evento** (`evento_pagina.html`): removida a seção "O formulário de inscrição pedirá…"
   (preview dos campos) — a pessoa vê os campos ao clicar em inscrever. Os dois botões ficaram
   **claros**: **"🎟️ Inscrever-se no evento"** (com dica "Para fazer a inscrição dos participantes.")
   e **"🛒 Comprar na loja"** (com dica "Só para comprar produtos/itens — não faz inscrição."), para
   o visitante não confundir inscrição com compra.
2. **Notificações (toasts)**: as mensagens de feedback viraram **toasts flutuantes** (canto superior
   direito no desktop, topo no celular), com cor por tipo (sucesso/erro/info/aviso), animação de
   entrada e **auto-fecham** em alguns segundos (ou ao clicar). Assim toda ação no módulo de eventos
   (criar/editar/remover produto, evento, faixa, campo, custo; registrar venda/inscrição no PDV;
   operadores; etc.) mostra visualmente que **deu certo** (ou o erro). Faltava aviso ao **reordenar
   campo** — adicionado ("Ordem dos campos atualizada.").

### Arquivos alterados
- `templates/core/evento_pagina.html`: sem preview de campos; botões com rótulo + dica claros.
- `static/css/eventos.css`: `.evento-acoes`/`.evento-acao-item`/`.evento-acao-dica`.
- `static/css/inicio.css`: `.mensagens` viram **toasts fixos** + `.mensagem`/variantes (success/error/
  info/warning) + animações `toast-entra`/`toast-sai`.
- `static/js/inicio.js`: toasts fecham ao clicar e somem sozinhos (auto-dismiss escalonado).
- `core/views.py`: `evento_campo_mover_view` passou a notificar.

### Decisões tomadas
- Toasts são as **mensagens do Django** (`messages`) estilizadas — mantém 1 só mecanismo. Auto-dismiss
  no `inicio.js` (carregado nas telas internas/PDV, onde estão as ações). Em páginas públicas de
  compra os erros continuam visíveis (não somem sozinhos), o que é desejável.
- **Regra**: toda ação relevante do usuário deve gerar uma notificação (sucesso/erro) — ver REGRAS.

### Validação
- Teste ponta a ponta: página do evento sem o preview e com os dois botões claros (incl. a dica "não
  faz inscrição"); CSS/JS de toast presentes; reordenar campo notifica; ação (salvar config) mostra o
  toast de sucesso. Todos passaram. `manage.py check` OK. Toast e página conferidos visualmente.

---

## 2026-07-04 - Ajustes da lojinha/PDV (feedback da validação)

### Resumo
Ajustes pedidos após validar a Lojinha:
1. **Botões +/- de quantidade**: nas telas de compra (loja, inscrição, PDV de venda e de inscrição),
   cada variação agora tem um **stepper** `[− n +]` (arredondado, com hover/efeito) em vez de digitar
   a quantidade — mais rápido no balcão. O total ao vivo recalcula ao clicar.
2. **"Nome do cliente" (PDV venda)**: texto de ajuda explicado — se preencher, é esse nome que fica no
   pedido; se vazio, usa o nome da inscrição vinculada (se houver) ou "Cliente (balcão)".
3. **WhatsApp, e-mail e CPF do responsável** viraram **obrigatórios** no formulário de inscrição
   (com o asterisco), junto do nome.
4. **Ajudante externo — navegação corrigida**: o botão "Voltar" das telas de PDV agora leva à landing
   **"Operar"** (não ao painel do Diretor, que dava "acesso restrito"); a landing "Operar" só mostra
   "Voltar para o painel" para o Diretor; e o ajudante externo, ao cair em "/inicio/", é **redirecionado
   para o evento dele** (não vê mais "Meus Dados"/"cadastrar aventureiro").

### Arquivos alterados
- `templates/core/_loja_itens.html`: variação com stepper `.qtd-stepper` (botões `.qtd-btn`).
- `static/js/qtd_stepper.js` (novo): +/- ajusta o input e dispara `input` (recalcula o total).
  Incluído em `evento_loja.html`, `evento_inscrever.html`, `evento_pdv.html`, `evento_pdv_inscricao.html`.
- `static/css/eventos.css`: estilo do stepper.
- `core/forms.py`: `InscricaoForm` — `responsavel_whatsapp/email/cpf` obrigatórios.
- `templates/core/evento_pdv.html`: ajuda do "Nome do cliente"; "Voltar" condicional (diretor→painel /
  operador→operar). `evento_pdv_inscricao.html`: "Voltar" condicional. `evento_operar.html`: "Voltar
  para o painel" só para diretor.
- `core/views.py`: `inicio_view` redireciona ajudante externo para o "Operar" do evento dele.

### Validação
- Teste ponta a ponta: stepper presente; whatsapp/email/cpf obrigatórios (bloqueia sem eles, cria com
  todos); ajudante externo (inicio→operar, PDV "Voltar"→operar, sem link para o painel); diretor
  "Voltar"→painel. Todos passaram. `manage.py check` OK. Stepper conferido visualmente (~490px).

---

## 2026-07-04 - Evento complexo — Lojinha Fase 4.4c: operadores do evento (conclui a Lojinha)

### Resumo
**Parte 4.4c** (última do PDV/Lojinha): o **Diretor** define, por evento, **quem pode operar o PDV**:
- **Diretoria selecionada**: habilita membros da diretoria (Diretor/Tesoureiro/Secretário/Professor).
- **Ajudantes externos**: cria uma **conta temporária** (usuário + senha inicial **`1234`**) só para o
  evento; no 1º acesso a pessoa é **obrigada a trocar a senha** (2×); o Diretor pode **resetar** para
  `1234`; ao logar, o ajudante vê **só o(s) evento(s) dele** no menu e cai direto na tela **"Operar"**.
Operadores acessam o **PDV** (venda + inscrição) via a landing **"Operar"** (`/eventos/<id>/operar/`).
Gerência em **"Operadores"** na aba Lojinha do painel (habilitar/criar/resetar/remover). O menu lateral
foi **centralizado** num único parcial (`_menu.html`) para tratar os três casos (diretor/membro,
operador, ajudante externo) de forma consistente.

### Arquivos criados/alterados
- `core/models.py`: `PerfilUsuario` (OneToOne User, `precisa_trocar_senha`) e `OperadorEvento`
  (evento, usuario, `externo`). Migration `0013`.
- `core/permissoes.py`: `pode_operar_evento` + decorator `operador_required` (Diretor ou operador).
- `core/middleware.py` (novo) + `config/settings.py`: `TrocaSenhaObrigatoriaMiddleware` (enquanto
  `precisa_trocar_senha`, redireciona tudo para a troca de senha).
- `core/context_processors.py`: expõe `operador_eventos` e `eh_operador_externo`.
- `core/views.py`: `evento_operar_view` (landing), `evento_operadores_view` + add diretoria/externo,
  reset e remover; `trocar_senha_view`; PDV agora com `@operador_required`; login redireciona o
  ajudante externo para o evento dele.
- `core/urls.py`: rotas de operador + `trocar-senha/`. `core/admin.py`: `OperadorEvento`, `PerfilUsuario`.
- `templates/core/_menu.html` (novo, menu central) — substituiu o `<nav class="menu">` inline em **todos**
  os 9 templates internos. `evento_operar.html`, `evento_operadores.html`, `trocar_senha.html` (novos);
  `evento_painel.html` (botão "Operadores").
- `static/css/eventos.css`: cards de "Operar" e lista de operadores.

### Decisões tomadas
- Operadores por evento (`OperadorEvento`); `externo=True` = conta temporária de ajudante.
- Troca de senha obrigatória via **middleware** (cobre qualquer rota). Reset volta para `1234`.
- Menu do ajudante externo restrito a seus eventos (via `_menu.html` + `eh_operador_externo`); login
  o leva direto ao "Operar". Remover um ajudante externo sem outros eventos **apaga a conta**.
- Menu lateral **centralizado** em `_menu.html` (fim da duplicação; editar o menu num lugar só).

### Validação
- Teste ponta a ponta: gerência (habilitar diretoria; criar ajudante com senha 1234 + troca
  obrigatória); operador da diretoria acessa PDV/operar e **estranho é bloqueado**; login do ajudante
  externo → **troca de senha obrigatória** → "Operar" com **menu restrito** (só o evento; sem "Meus
  Dados"); ajudante vende no PDV; **reset** de senha; **remover** apaga a conta externa; menu do
  diretor intacto. Todos passaram. `manage.py check` OK. **Responsividade** (~490px) das telas novas +
  menu no desktop conferidos.

### Pendências / próximo passo
- **🎉 Lojinha (Fase 4) concluída.** Próximo: **Fase 5 — Financeiro/gráficos** (resultado detalhado,
  cupons de desconto, presença/check-in). Depois: pagamentos reais (gateway); loja oficial do clube.

---

## 2026-07-04 - Evento complexo — Lojinha Fase 4.4b: PDV inscrição + relatório de vendas por produto

### Resumo
Dois ajustes/entregas a partir da validação:
1. **Relatório "Vendidos por produto"** no **Resumo** (dashboard): tabela Produto | **Qtd** | **Arrecadado**.
   A **quantidade conta tudo, inclusive cortesia** (controle de quantos saíram); o **arrecadado é só o
   dinheiro** (cortesia entra com 0). Decisão: cortesia continua com **valor zerado** no financeiro.
2. **PDV — Nova inscrição (4.4b)**: o atendente faz uma **inscrição presencial** e, no mesmo balcão,
   pode **adicionar itens da lojinha**; tudo num **pagamento só** (forma de pagamento; **troco** no
   dinheiro sobre o **total combinado** = inscrição + itens; **total ao vivo**). Cria a inscrição +
   um **pedido de lojinha vinculado**; **cortesia** deixa o conjunto grátis (baixa estoque). Botão
   **"Nova inscrição (balcão)"** na aba Inscrições. A venda **só lojinha** continua na 4.4a. Restrito
   ao Diretor por ora (operadores → 4.4c).

### Arquivos criados/alterados
- `core/models.py`: `Inscricao` ganhou `origem`, `forma_pagamento`, `valor_recebido`, `registrado_por`
  + props `total_com_loja` e `troco`. Choices de pagamento movidas para antes de `Inscricao`.
  Migration `0012`.
- `core/views.py`: `evento_painel_view` calcula `vendas_por_produto`; nova `evento_pdv_inscricao_view`
  (inscrição + lojinha + pagamento combinado; cortesia zera; troco).
- `core/urls.py`: rota `evento_pdv_inscricao`. `core/admin.py`: inscrição mostra origem/forma.
- `templates/core/evento_pdv_inscricao.html` (novo). `evento_painel.html`: tabela "Vendidos por
  produto" no Resumo + botão "Nova inscrição (balcão)" + selo origem/forma nas inscrições.
- `static/js/evento_pdv_inscricao.js` (total combinado ao vivo por faixa/diretoria + lojinha + troco).
- `static/css/eventos.css`: tabela do relatório.

### Decisões (validadas com o usuário)
- **Cortesia**: valor 0 no financeiro; controle de quantidade fica no **relatório** (dashboard).
- **PDV inscrição + lojinha = um pagamento só** (uma transação, um troco); gera inscrição + pedido
  vinculado por baixo. Mantida a venda **só lojinha** (4.4a) para quem não vai se inscrever.

### Validação
- Teste ponta a ponta: PDV inscrição + lojinha com pagamento combinado (troco 6 sobre 54); inscrição
  sem lojinha (cartão); **cortesia** (inscrição+item grátis, baixa estoque); dinheiro insuficiente
  sobre o combinado rejeitado; relatório "Vendidos por produto" (qtd inclui cortesia); arrecadação (60)
  × vendas (24) separadas. Todos passaram. `manage.py check` OK. **Responsividade** (~490px) conferida.

### Pendências / próximo passo
- **Lojinha 4.4c** — **operadores do evento**: diretoria selecionada + contas temporárias de ajudantes
  externos (senha `1234`, troca obrigatória no 1º login, reset pelo Diretor; ajudante vê só o evento).

---

## 2026-07-04 - Evento complexo — Lojinha Fase 4.4a: PDV / balcão de vendas

### Resumo
**Parte 4.4a** (primeira do PDV): tela de **balcão** (`/eventos/<id>/pdv/`) para registrar vendas da
lojinha no dia do evento. O operador monta o pedido (quantidade por variação, **total ao vivo**),
escolhe a **forma de pagamento** (**Dinheiro** com **campo de valor recebido → troco automático**,
Pix, Cartão, **Cortesia**) e registra; pode **vincular a venda a uma inscrição** (opcional — para
rastrear o que foi comprado por pessoa) ou deixar **avulsa**. Baixa estoque e entra em "Vendas
(lojinha)" (cortesia não soma). Por ora **restrito ao Diretor**; os **operadores** (diretoria
selecionada + ajudantes externos) virão na 4.4c; a inscrição pelo PDV vem na 4.4b. Acesso pela aba
"Lojinha" do painel (botão **"PDV / Balcão"**).

### Arquivos criados/alterados
- `core/models.py`: `PedidoLoja` ganhou `origem` (online/pdv), `forma_pagamento`
  (online/dinheiro/pix/cartão/cortesia), `valor_recebido`, `registrado_por` + property `troco`.
  Choices `FORMA_PAGAMENTO_CHOICES`/`ORIGEM_PEDIDO_CHOICES`. Migration `0011`.
- `core/views.py`: `evento_pdv_view` (Diretor); `_criar_pedido` passou a aceitar
  forma/valor_recebido/origem/registrado_por e trata **cortesia** (itens grátis, estoque baixa).
- `core/urls.py`: rota `evento_pdv`. `core/admin.py`: pedido mostra origem/forma.
- `templates/core/evento_pdv.html` (novo, layout interno). `evento_painel.html`: botão "PDV / Balcão"
  na aba Lojinha + badges de origem/forma nos pedidos.
- `static/js/evento_pdv.js`: total ao vivo + alternância da forma + troco (e cortesia = total 0).
- `static/css/eventos.css`: formas de pagamento, troco, `.secao-acoes`.

### Decisões tomadas
- Vínculo venda×inscrição **opcional** (rastreia quando quiser; permite venda a passante). Reaproveita
  `PedidoLoja.inscricao`.
- **Cortesia** registra o item (baixa estoque) com valor 0 (não entra em vendas).
- PDV volta pra si mesmo após registrar (com mensagem de código + troco) para vendas rápidas em série.

### Validação
- Teste ponta a ponta (Diretor): GET; venda em dinheiro avulsa (troco 18, baixa estoque); venda
  vinculada a inscrição (herda o nome do responsável); cortesia (total 0, baixa estoque); dinheiro
  insuficiente e sem itens rejeitados; Resumo com vendas do PDV (cortesia não soma); **não-diretor
  bloqueado**. Todos passaram. `python manage.py check` OK. **Responsividade** (~490px) do PDV conferida.

### Pendências / próximo passo
- **Lojinha 4.4b** — fazer **inscrição** pelo PDV (presencial, com pagamento).
- **Lojinha 4.4c** — **operadores do evento**: diretoria selecionada + contas temporárias de ajudantes
  externos (senha `1234`, troca obrigatória no 1º login, reset pelo Diretor; ajudante vê só o evento).

---

## 2026-07-04 - Evento complexo — Lojinha Fase 4.3: comprar junto da inscrição + pedir mais

### Resumo
**Parte 4.3**: no fim do **formulário de inscrição** aparece uma seção **opcional** "Quer levar algo da
lojinha?" com os produtos (quantidade por variação + **subtotal ao vivo**). Ao confirmar, num envio
só, cria-se a **inscrição** e — se houver itens — um **pedido da lojinha vinculado** a ela (pagamento
simulado, baixa de estoque). Se qualquer item exceder o estoque, **nada** é criado (nem a inscrição).
Para **pedir mais**, as telas de sucesso (inscrição e pedido) trazem botão **"Comprar (mais) na
lojinha"**, e o evento continua no menu (logado) para voltar quando quiser. O pedido vinculado aparece
na lista de pedidos do painel e conta em "Vendas (lojinha)".

### Arquivos criados/alterados
- `core/models.py`: `PedidoLoja.inscricao` (FK opcional → `Inscricao`). Migration `0010`.
- `core/views.py`: helpers `_coletar_itens_loja`, `_marcar_quantidades`, `_criar_pedido` (extraídos e
  reaproveitados); `evento_loja_view` refatorada; `evento_inscrever_view` passou a ler os itens da
  lojinha e criar o pedido vinculado (comprador = responsável) na mesma transação;
  `evento_inscricao_sucesso_view` mostra o pedido vinculado + oferece a lojinha.
- `templates/core/_loja_itens.html` (novo parcial, usado na loja e na inscrição);
  `evento_loja.html` e `evento_inscrever.html` usam o parcial; `evento_inscrever.html` ganhou a seção
  opcional + subtotal ao vivo; `evento_inscricao_sucesso.html` mostra o pedido + botão "Comprar mais".
- `static/js/evento_loja.js`: agora funciona por documento (loja e inscrição), atualizando `#lojaTotal`.
- `static/css/eventos.css`: `.loja-total-inline`, `.sucesso-pedido`.

### Decisões tomadas
- Um envio → **duas entidades** (Inscricao + PedidoLoja vinculado); financeiro separado (arrecadação de
  inscrições × vendas da lojinha), mas ambos no evento. Validação **tudo-ou-nada** (estoque).
- Reaproveitamento por helpers/parcial para loja e inscrição ficarem consistentes.

### Validação
- Teste ponta a ponta: seção da lojinha no form; inscrição + pedido vinculado (herda comprador, baixa
  estoque, sucesso mostra os dois + "Comprar mais"); inscrição sem itens não cria pedido (mas oferece a
  lojinha); estoque insuficiente bloqueia inscrição+pedido; dashboard com ambos. Todos passaram.
  `python manage.py check` OK. **Responsividade** (Chrome headless ~490px) do form com lojinha conferida.

### Pendências / próximo passo
- **Lojinha 4.4** — PDV dos atendentes autorizados (vendem/inscrevem no dia, marcam pago/forma de
  pagamento).

---

## 2026-07-04 - Evento complexo — Lojinha Fase 4.2: comprar na página do evento

### Resumo
**Parte 4.2**: a lojinha passou a **vender**. Na página do evento há o botão **"Comprar na lojinha"**
(quando há produtos ativos e o evento não terminou), que abre a **loja** (`/eventos/<id>/loja/`):
lista os produtos ativos com suas variações (preço, estoque quando controlado), um campo de
**quantidade** por variação e o **total ao vivo** (JS). No fim, dados do comprador e **Finalizar
pedido** → **pagamento simulado**, gera **código**, **baixa o estoque** (dos produtos que controlam) e
mostra a tela de sucesso. Acesso igual ao evento (público sem login; só-membros com login); a loja
fica aberta **enquanto o evento não terminou** (independe do prazo de inscrição — dá para comprar no
dia). No **painel**, a aba "Lojinha" ganhou a **lista de pedidos** (com itens e **cancelar**, que
devolve ao estoque) e o **Resumo** passou a contar **"Vendas (lojinha)"** de verdade (entra nas
receitas/resultado).

### Arquivos criados/alterados
- `core/models.py`: `PedidoLoja` (evento, comprador, código, status, valor_total) e `ItemPedidoLoja`
  (variação + snapshots + quantidade + valores); `Evento.ja_terminou()`/`loja_aberta()`; props
  `VariacaoProduto.rotulo`/`esgotado`. Migration `0009`.
- `core/views.py`: `evento_loja_view` (monta o pedido, valida estoque, baixa com `F()`),
  `evento_pedido_sucesso_view`, `evento_pedido_cancelar_view` (Diretor; devolve estoque). Painel
  calcula `vendas_loja` e passa `pedidos`; `evento_pagina_view` passa `tem_loja`.
- `core/urls.py`: rotas `evento_loja`, `evento_pedido_sucesso`, `evento_pedido_cancelar`.
  `core/admin.py`: `PedidoLoja` (inline de itens).
- `templates/core/evento_loja.html` (novo, loja + carrinho) e `evento_pedido_sucesso.html`;
  `evento_pagina.html` (botão "Comprar na lojinha"); `evento_painel.html` (lista de pedidos + cancelar).
- `static/js/evento_loja.js` (total ao vivo). `static/css/eventos.css` (loja mobile-first).

### Decisões tomadas
- **Pedido numa página só** (quantidade por variação), sem carrinho persistente — simples e rápido no
  celular; total ao vivo no cliente, mas o valor é **recomputado no servidor** (Decimal).
- **Baixa/devolução de estoque** com `F()` (atômico); só afeta produtos que controlam estoque.
- Loja independente do prazo de inscrição; fecha quando o evento termina (`fim_datetime`).

### Validação
- Teste ponta a ponta: GET público (esconde inativos); botão na página; pedido válido (2 produtos,
  total e itens corretos, baixa de estoque); estoque insuficiente e pedido sem itens/sem nome
  rejeitados; dashboard com "Vendas (lojinha)"; cancelar devolve estoque e zera vendas; loja fechada
  após o evento terminar. Todos passaram. `python manage.py check` OK.
- **Responsividade (Chrome headless ~490px)**: loja com quantidades, "esgotado" sem campo, total e
  botão — sem overflow.

### Pendências / próximo passo
- **Lojinha 4.3** — comprar **junto da inscrição** (opcional) + **voltar e pedir mais** fácil.
- Depois: 4.4 (PDV dos atendentes: pago/forma de pagamento).

---

## 2026-07-04 - Evento complexo — Lojinha Fase 4.1: cadastro de produtos

### Resumo
Início da **Lojinha** (mini-sistema de vendas por evento). **Parte 4.1**: a aba "Lojinha" do painel
deixou de ser "em breve" e agora permite **cadastrar produtos** com **variações** (cada uma com seu
**preço**) e **controle de estoque opcional por produto** (alguns vendem à vontade; outros têm
quantidade por variação). Produto tem nome, descrição, **foto** opcional e liga/desliga ("à venda").
Cadastro em página dedicada, com **linhas de variação** repetíveis (adicionar/remover) e a coluna
"Estoque" aparecendo só quando "Controlar estoque" está marcado. A **venda** (carrinho/pedidos) vem
nas próximas partes.

### Contexto (alinhado com o usuário)
A lojinha do evento será usada de vários jeitos, em fases: comprar **junto da inscrição** (opcional),
**voltar e pedir mais** depois (ex.: mais lanche no dia do evento) e, no futuro, um **PDV para
atendentes** autorizados (caixa/cantina) que vendem/inscrevem no dia e marcam pago/forma de pagamento.
Tudo dentro da página do evento (para o financeiro do evento fechar). A loja **oficial do clube**
(uniformes etc.) é outra coisa, separada, para bem depois.

### Arquivos criados/alterados
- `core/models.py`: `ProdutoEvento` (evento, nome, descrição, foto, controla_estoque, ativo, ordem) e
  `VariacaoProduto` (produto, nome, valor, estoque, ordem). Migration `0008`.
- `core/forms.py`: `ProdutoEventoForm` (dados do produto; variações tratadas na view).
- `core/views.py`: `evento_produto_novo_view`, `evento_produto_editar_view`,
  `evento_produto_excluir_view` + helpers `_parse_variacoes`/`_salvar_variacoes` (linhas indexadas,
  sincroniza criar/editar/remover). Painel carrega `produtos`.
- `core/urls.py`: rotas `evento_produto_novo`/`_editar`/`_excluir`. `core/admin.py`: `ProdutoEvento`
  (inline de variações) e `VariacaoProduto`.
- `templates/core/evento_produto_form.html` (novo, com layout interno + variações) e
  `_variacao_linha.html` (linha repetível). `evento_painel.html`: aba "Lojinha" lista os produtos.
- `static/js/evento_produto.js`: adicionar/remover variação + mostrar/ocultar estoque.
- `static/css/eventos.css`: lista de produtos e linhas de variação (mobile-first).

### Validação
- Teste ponta a ponta: cadastro com estoque + 3 variações; produto sem estoque (estoque zerado);
  edição (mudar preço, remover e adicionar variação — sincroniza); preço inválido e produto sem
  variação rejeitados; painel lista os produtos; excluir; **responsável (não-diretor) bloqueado**.
  `python manage.py check` sem problemas.
- **Responsividade (Chrome headless ~484px)**: página de cadastro de produto, aba "Lojinha" do painel
  e formulário de inscrição conferidos — sem overflow horizontal; variações e cartões quebram bem.

### Pendências / próximo passo
- **Lojinha 4.2** — comprar na página do evento (carrinho + finalizar, pagamento simulado, baixa de
  estoque, entra em "Vendas (lojinha)" no Resumo).
- Depois: 4.3 (comprar junto da inscrição + voltar e pedir mais) e 4.4 (PDV dos atendentes).

---

## 2026-07-04 - Ajustes de validação das inscrições (feedback do usuário)

### Resumo
Após validar a Fase 2 na tela, o usuário apontou ajustes; feitos todos:
1. **Bug — comentário vazando na tela**: `_menu_eventos.html` e `_participante_linha.html` usavam
   comentário `{# … #}` de **duas linhas** (que no Django só vale numa linha), então o texto do
   comentário aparecia no menu e na página de inscrição. Trocado por `{% comment %}…{% endcomment %}`.
2. **Botão "Ver no mapa"** na página do evento: link que abre o **Google Maps** no endereço do evento
   (sem API/biblioteca externa — respeita a regra do projeto). Aparece abaixo do local.
3. **Campos do formulário — por participante ou uma vez**: ao cadastrar um campo, o Diretor agora
   escolhe **"Perguntar para cada participante"**. Se marcado, o campo aparece **dentro de cada
   participante** (além de nome/idade); senão, é preenchido **uma vez**, junto dos dados do
   responsável. A seção genérica "Informações do evento" saiu.
4. **Textos**: "Perguntas extras" → "Campos do formulário de inscrição"; "Seus dados/Seu nome" →
   "Dados do responsável/Nome do responsável".

### Arquivos alterados
- `core/models.py`: `CampoInscricao.por_participante` (bool) e `RespostaInscricao.participante` (FK
  opcional). Migration `0007`.
- `core/forms.py`: `CampoInscricaoForm` inclui `por_participante`; `InscricaoForm` monta como campos
  do form **só** os de inscrição única (`por_participante=False`).
- `core/views.py`: `evento_inscrever_view` reescrita — participantes com **índice por linha**
  (`part_*_<idx>`), leitura/validação dos campos por participante (`_ler_resposta_participante`,
  `_linha_participante`, `_linha_vazia`); grava `RespostaInscricao` ligada ao participante. Painel
  separa respostas gerais (`respostas_gerais`) das por participante.
- `templates/core/_menu_eventos.html`, `_participante_linha.html`: comentário corrigido; a linha de
  participante agora renderiza os campos "por participante" (com nomes indexados e repopulação).
- `templates/core/evento_inscrever.html`: campos únicos sob "Dados do responsável"; sem "Informações
  do evento". `evento_pagina.html`: botão "Ver no mapa". `evento_painel.html`: etiqueta de escopo
  ("por participante"/"uma vez") e respostas por participante na lista de inscritos; textos revistos.
- `static/js/evento_inscrever.js`: clonagem de linha por **índice** (substitui `__IDX__`), sem o
  antigo hidden de diretoria. `static/css/eventos.css`: linha vira cartão com campos, grupos de
  checkbox, etiqueta de escopo e botão do mapa.

### Validação
- Teste ponta a ponta: comentários não vazam mais (menu e inscrição); botão "Ver no mapa" com link do
  Google Maps; form com rótulos certos e sem "Informações do evento"; POST com **2 participantes com
  tamanhos diferentes** grava a resposta certa por participante e a resposta geral separada; campo
  obrigatório por participante faltando é rejeitado; painel mostra as respostas e as etiquetas de
  escopo. Todos passaram. `python manage.py check` sem problemas.

---

## 2026-07-04 - Evento complexo — Fase 2.4: inscrição de fato (conclui a Fase 2)

### Resumo
**Parte 2.4** (última da Fase 2): a inscrição passa a **funcionar de verdade** (pagamento **simulado**).
Na página do evento, "Inscrever-se" abre o **formulário de inscrição** (`/eventos/<id>/inscrever/`):
dados do responsável + **participantes** (linhas repetíveis: nome + idade + opção "diretoria") + os
**campos personalizados** do evento (renderizados conforme o tipo). O **preço** de cada participante é
calculado no servidor (faixa etária pela idade, ou valor da diretoria se marcado); soma no **valor
total**. A inscrição nasce **confirmada**, com **código único**, e leva a uma **tela de sucesso**
(código + total). No **painel**, a aba "Inscrições" ganhou a **lista de inscritos** (código, responsável,
contato, participantes/valores, respostas, situação) com ação **Cancelar**; o **Resumo** passou a
contar **inscritos** (participantes confirmados) e **arrecadação** de verdade. Acesso: público sem
login se o evento é aberto ao público, senão exige login; após o prazo, o formulário trava.

### Arquivos criados/alterados
- `core/models.py`: modelos `Inscricao` (código único, status, valor_total), `ParticipanteInscricao`
  (nome/idade/diretoria/faixa/valor) e `RespostaInscricao` (campo + rótulo snapshot + valor); método
  `Evento.preco_participante(idade, eh_diretoria)`. Migration `0006`.
- `core/forms.py`: `InscricaoForm` (responsável + campos personalizados dinâmicos por tipo;
  `campos_personalizados` e `resposta_texto`).
- `core/views.py`: `evento_inscrever_view`, `evento_inscricao_sucesso_view`,
  `evento_inscricao_cancelar_view` (Diretor) + helper `_parse_participantes`; painel agora carrega
  inscrições e calcula inscritos/arrecadação no Resumo.
- `core/urls.py`: rotas `evento_inscrever`, `evento_inscricao_sucesso`, `evento_inscricao_cancelar`.
- `core/admin.py`: `Inscricao` (inlines de participantes e respostas).
- `templates/core/`: `evento_inscrever.html` (form), `evento_inscricao_sucesso.html`,
  `_participante_linha.html` (linha repetível); `evento_pagina.html` (botão → formulário);
  `evento_painel.html` (lista de inscritos + Cancelar na aba "Inscrições").
- `static/js/evento_inscrever.js`: adicionar/remover participante + checkbox "diretoria" → hidden.
- `static/css/eventos.css`: linhas de participante, resumo de valores, lista de inscritos, sucesso.

### Decisões tomadas
- **Diretoria** por participante (checkbox, só aparece se o evento tem valor de diretoria) → aplica o
  valor da diretoria no lugar da faixa. Alinhamento por índice via input hidden (checkbox desmarcado
  não some da lista). Autodeclarado nesta etapa; o Diretor confere na lista.
- Preço **calculado e gravado no servidor** (snapshot em cada participante); dashboard soma o
  `valor_total` das inscrições **confirmadas**. Cancelar muda o status (sai da contagem).
- Campos personalizados viram campos de formulário Django conforme o tipo (validação de obrigatório e
  de opções “de graça”); respostas gravadas como texto legível, com rótulo em snapshot.
- Pagamento **simulado**: inscrição já confirmada; sem gateway (fica para “depois”, como no plano).

### Validação
- Teste ponta a ponta (test client): precificação (faixa/diretoria/sem-faixa); GET público do form;
  POST válido (2 participantes incl. diretoria + respostas, total e faixas corretos, sim/não = "Não",
  código de 6 chars, tela de sucesso); POST inválido (obrigatório vazio + idade faltando) rejeitado;
  escolha fora das opções rejeitada; painel com lista + Resumo (inscritos=2, arrecadação); cancelar
  remove da contagem; inscrição após o prazo bloqueada; evento só-membros exige login. Todos passaram.
  `python manage.py check` sem problemas.

### Pendências / próximo passo
- **Fase 2 concluída.** A "página pública com pagamento simulado" (antiga Fase 3) ficou coberta por
  2.3 + 2.4. Próximos: **Lojinha** (produtos/variações/estoque + pedidos), **Financeiro/gráficos** e,
  depois, pagamentos reais (gateway) + mapa. Possíveis refinos: gating de “diretoria” por perfil real,
  editar inscrição, exportar lista, e-mail de confirmação.

---

## 2026-07-04 - Evento complexo — Fase 2.3: evento no menu de todos os perfis + página do evento

### Resumo
**Parte 2.3** da Fase 2: todo evento com inscrição **ainda não encerrado** (data futura/em andamento)
aparece numa seção **"Eventos ativos"** no menu lateral de **todos os perfis logados** (responsável,
diretor, tesoureiro, secretário, professor), com o **nome do evento** levando à **página do evento**.
Eventos passados somem do menu sozinhos. Criada a **página do evento** (`/eventos/<id>/pagina/`) —
página própria (sem a barra lateral interna) com nome, descrição, local, datas/horários, **status**
das inscrições (aberto/encerrado + prazo), **valores** (faixas etárias + diretoria) e um **preview
dos campos** do formulário. **Acesso**: evento **aberto ao público** → qualquer pessoa vê (sem login);
evento **só para membros** → exige login. O **botão "Inscrever-se"** aparece desabilitado com aviso de
que o envio virá na Fase 2.4.

### Arquivos criados/alterados
- `core/context_processors.py`: `perfis` passou a expor também `eventos_menu` (eventos com inscrição
  não encerrados) a todos os templates; helper `_eventos_menu` (filtra por data, só autenticados).
- `templates/core/_menu_eventos.html`: **novo** parcial com a seção "Eventos ativos" do menu.
- `templates/core/{inicio,usuarios,eventos,evento_form,evento_complexo_form,evento_painel}.html`:
  incluem o parcial no `<nav class="menu">` (fora do `is_diretor`, visível a todos).
- `templates/core/evento_pagina.html`: **nova** página do evento (pública/interna).
- `core/views.py`: nova `evento_pagina_view` (pública se `inscricao_aberta_publico`, senão login).
- `core/urls.py`: rota `evento_pagina` (`/eventos/<id>/pagina/`).
- `static/css/inicio.css`: estilos da seção "Eventos ativos" no menu (com truncagem do nome).
- `static/css/eventos.css`: estilos da página do evento + `.btn-acao:disabled`.

### Decisões tomadas
- Menu de eventos via **context processor** (aparece em todas as telas sem repetir lógica); inserido
  por **parcial** (`_menu_eventos.html`) para não reescrever a barra inteira em cada template.
- "Eventos ativos" = complexos com `data_fim` (ou `data`) **>= hoje** — filtro no nível de data
  (simples e suficiente); some sozinho quando o evento passa.
- **Página própria** (sem sidebar) para o evento, funcionando logada ou anônima; acesso público só
  quando `inscricao_aberta_publico=True` (senão, redireciona ao login com `?next=`).
- Botão "Inscrever-se" **desabilitado** nesta fase — o envio real (respostas + participantes) é a 2.4.

### Validação
- Teste ponta a ponta (test client): menu do **responsável** (não-diretor) mostra os eventos ativos e
  **oculta** o passado e os itens de diretor; página pública abre **sem login** (com dados, valores,
  campos e botão); evento só-membros **sem login redireciona** e **com login abre**; evento **simples**
  não tem página (404); **todas** as telas internas seguem renderizando com o menu. Todos passaram.
  `python manage.py check` sem problemas.

### Pendências / próximo passo
- **Parte 2.4** — inscrição de fato: participantes por faixa/diretoria (cálculo do valor), respostas
  do formulário personalizado, pagamento **simulado**, código, **lista de inscritos** no painel e
  **contagem/arrecadação no dashboard**. Aí o botão "Inscrever-se" passa a funcionar.

---

## 2026-07-04 - Evento complexo — Fase 2.2: formulário de inscrição personalizável

### Resumo
**Parte 2.2** da Fase 2: o Diretor monta, por evento, os **campos personalizados** do formulário de
inscrição, na aba "Inscrições" do painel (subseção "Formulário de inscrição"). Cada campo tem
**pergunta/rótulo**, **tipo** (conjunto completo: texto curto, texto longo, número, escolha única,
escolha múltipla, sim/não, data), **opções** (só para escolha única/múltipla) e **obrigatório?**.
Os campos são adicionados por **modal**, podem ser **reordenados** (▲▼) e **removidos**. O
preenchimento/envio desse formulário (respostas) virá na Fase 2.4.

### Arquivos criados/alterados
- `core/models.py`: modelo `CampoInscricao` (evento, rótulo, tipo, opções, obrigatório, ordem) +
  `TIPO_CAMPO_INSCRICAO_CHOICES`; props `usa_opcoes` e `opcoes_lista`. Migration `0005_campoinscricao`.
- `core/forms.py`: `CampoInscricaoForm` (valida ≥2 opções para escolha; limpa `opcoes` nos demais tipos).
- `core/views.py`: painel passa `campos_inscricao` e `campo_form`; novas views `evento_campo_novo_view`,
  `evento_campo_excluir_view`, `evento_campo_mover_view` (reordenação robusta por renumeração).
  **Prefixos de formulário** (`faixa` e `campo`) para evitar colisão de IDs entre os modais.
- `core/urls.py`: rotas `evento_campo_novo`, `evento_campo_excluir`, `evento_campo_mover`.
- `core/admin.py`: registra `CampoInscricao`.
- `templates/core/evento_painel.html`: subseção "Formulário de inscrição" (lista com ▲▼ e remover) +
  modal "Adicionar campo".
- `static/js/evento_painel.js`: modal do campo + mostrar/ocultar "Opções" conforme o tipo escolhido.
- `static/css/eventos.css`: estilos da lista de campos, botões de ordenar e `.obrigatorio`.

### Decisões tomadas
- Um modelo por campo (`CampoInscricao`), opções como texto (uma por linha) → `opcoes_lista`.
- Formulários dos modais agora usam **prefixo** (`faixa-…`, `campo-…`) porque `faixa` e `campo`
  compartilham o nome de campo `rotulo` (evita `id` duplicado na mesma página).
- Reordenar por renumeração sequencial da `ordem` (robusto a valores repetidos).
- Erros do form voltam com mensagem (padrão dos demais modais do painel).

### Validação
- Teste ponta a ponta (test client, Diretor): painel renderiza a subseção e **não há colisão de IDs**
  (`id_faixa-rotulo` e `id_campo-rotulo` presentes, `id_rotulo` ausente); regressão da faixa com o novo
  prefixo; campo de texto; escolha única com 1 opção é rejeitada; escolha única válida normaliza as
  opções (`["P","M","G"]`); reordenar; excluir. Todos passaram. `python manage.py check` sem problemas.

### Pendências / próximo passo
- **Parte 2.3** — evento no menu de todos os perfis + página do evento (descrição/local/prazo).
- Depois: 2.4 (inscrição de fato: participantes por faixa/diretoria, pagamento simulado, respostas
  do formulário, lista de inscritos + contagem/arrecadação no dashboard).

---

## 2026-07-04 - Evento complexo — Fase 2.1: fundação das inscrições (config + faixas)

### Resumo
Início da **Fase 2 (Inscrições)**, dividida em 4 partes (2.1 a 2.4). Esta é a **Parte 2.1 —
Fundação**: cada evento com inscrição passa a ter **configuração de inscrição** no painel (aba
"Inscrições"), com:
1. **Local** (obrigatório no evento com inscrição), **aberto ao público geral?** (sim = qualquer
   pessoa; não = só membros do clube) e **prazo limite de inscrição** (data/hora).
2. **Trava automática**: passado o prazo (ou, se vazio, o fim do evento), as inscrições ficam
   "encerradas" (badge verde "Abertas" / cinza "Encerradas" + data-limite exibida).
3. **Faixas etárias com valores** por evento (rótulo opcional + idade mín/máx + valor), adicionadas
   por modal e removíveis. Cada evento define as suas (variam de evento para evento).
4. **Valor da diretoria** (valor fixo que a diretoria paga, independe da idade; vazio = sem valor
   especial, 0 = grátis).
O formulário de inscrição personalizável (2.2), o evento no menu de todos os perfis + página do
evento (2.3) e a inscrição de fato com pagamento simulado + lista de inscritos (2.4) vêm nas
próximas partes.

### Arquivos criados/alterados
- `core/models.py`: `Evento` ganhou `inscricao_aberta_publico`, `inscricao_limite`,
  `valor_diretoria` + métodos `fim_datetime()`, `prazo_inscricao()`, `inscricoes_abertas()`.
  Novo modelo `FaixaEtariaPreco` (evento, rótulo, idade_min, idade_max, valor, ordem).
  Migration `0004_evento_inscricao_aberta_publico_and_more`.
- `core/forms.py`: `EventoInscricaoConfigForm` e `FaixaEtariaPrecoForm` (com validação idade_máx ≥
  idade_mín); `EventoComplexoForm` passou a exigir `local`.
- `core/views.py`: `evento_painel_view` monta config/faixas/status; novas views
  `evento_inscricao_config_view`, `evento_faixa_nova_view`, `evento_faixa_excluir_view` (POST).
- `core/urls.py`: rotas `evento_inscricao_config`, `evento_faixa_nova`, `evento_faixa_excluir`.
- `core/admin.py`: registra `FaixaEtariaPreco`.
- `templates/core/evento_painel.html`: aba "Inscrições" com status, form de configuração, lista de
  faixas e modal "Adicionar faixa".
- `static/js/evento_painel.js`: modais generalizados (helper `configurarModal`) para custo e faixa.
- `static/css/eventos.css`: estilos da config, faixas e `pill-cinza`.

### Decisões tomadas
- Faixas etárias como modelo próprio por evento (`FaixaEtariaPreco`); valor da diretoria no próprio
  `Evento` (independe da idade). Nada de faixas/valores fixos no sistema — cada evento define.
- Trava por comparação com `timezone.now()` (USE_TZ=True); prazo efetivo = `inscricao_limite` ou o
  fim do evento (`data_fim`/`data` + `horario_fim`/23:59), sempre aware.
- Erros dos forms de config/faixa voltam com mensagem (framework de messages), como já era nos custos.

### Validação
- Teste ponta a ponta (test client, logado como Diretor): GET do painel (200) com a config; salvar
  config (local/público/prazo/valor diretoria, com fuso correto SP→UTC); adicionar faixa válida;
  rejeitar faixa inválida (idade máx < mín); trava (evento passado = encerrado, futuro = aberto);
  excluir faixa. Todos passaram. `python manage.py check` sem problemas.

### Pendências / próximo passo
- **Parte 2.2** — formulário de inscrição personalizável por evento.
- Depois: 2.3 (evento no menu de todos os perfis + página do evento) e 2.4 (inscrição + pagamento
  simulado + lista de inscritos + contagem no dashboard).

---

## 2026-07-04 - Atualização geral da documentação (continuidade)

### Resumo
Revisão dos documentos para garantir continuidade em uma nova sessão. `README_PROJETO.md` atualizado
(perfis/permissões, Usuários restrita, módulo Eventos simples + complexo Fase 1, comandos
`configurar_perfis` e `importar_migracao`, novas rotas e models). `PLANEJAMENTO_EVENTO_COMPLEXO.md`
marca a **Fase 1 como concluída** e a **Fase 2 (Inscrições) como próximo passo** (seção "ONDE CONTINUAR").
`REGRAS_CODEX.md` passa a ter, na lista de regras obrigatórias, a **verificação obrigatória dos modais**
(só fechar no fundo se o mousedown E o click ocorreram no fundo — não fechar ao arrastar seleção).

### Arquivos alterados
- `docs/README_PROJETO.md`, `docs/PLANEJAMENTO_EVENTO_COMPLEXO.md`, `docs/REGRAS_CODEX.md`,
  `docs/HISTORICO_ALTERACOES.md`.

---

## 2026-07-04 - Ajustes na tela de Eventos (cards, moeda e modais)

### Resumo
Ajustes pedidos antes de seguir com o evento complexo:
1. **Card de evento com altura limitada**: título e descrição com no máximo 2 linhas (line-clamp) e
   cards da mesma linha com altura uniforme — não crescem mais com textos longos.
2. **Clicar no card** (fora dos botões) abre um **modal de visualização** com todos os dados do evento
   (só leitura). Os botões "Abrir painel"/"Duplicar" seguem seu comportamento normal.
3. **Moeda no padrão brasileiro** (`R$ 1.500,00`): novo filtro `moeda` usado no painel do evento.
4. **Modais não fecham ao arrastar seleção de texto** de dentro para fora (fecha só quando o mousedown
   e o clique ocorreram no fundo). Corrigido em todos os modais (Usuários, Eventos e Custos).

### Arquivos criados/alterados
- `core/templatetags/formato.py` (novo) + `__init__.py`: filtro `moeda`.
- `templates/core/evento_painel.html`: usa `{{ ...|moeda }}`.
- `templates/core/eventos.html`: card clicável, fonte oculta dos detalhes e modal de visualização.
- `static/css/eventos.css`: line-clamp do título/descrição, altura uniforme, card clicável, modal-desc.
- `static/js/eventos.js`: modal de visualização do evento (clona detalhe; ignora cliques em links/botões).
- `static/js/usuarios.js`, `static/js/eventos.js`, `static/js/evento_painel.js`: fechar modal só quando
  o mousedown começou no fundo (corrige o fechamento ao selecionar texto).
- `docs/REGRAS_CODEX.md`: nota do comportamento do modal + seção de formatação de moeda.

---

## 2026-07-04 - Evento complexo (com inscrição) — Fase 1: painel + custos

### Resumo
Início do "evento complexo" (mini-sistema por evento). **Fase 1**: criar o evento complexo
(`tipo=inscricao`, com data/hora de início e término) e seu **painel/dashboard** (`/eventos/<id>/`)
com abas (Resumo, Inscrições, Lojinha, Custos, Financeiro). Nesta fase funcionam **Resumo**
(indicadores: inscritos, arrecadação, vendas, receitas, custos e **resultado**) e **Custos**
(adicionar/remover custo com comprovante anexo; total reflete no resultado). Inscrições/Lojinha/
Financeiro ficam como "em breve". Pagamentos serão simulados nas próximas fases. Plano completo em
`docs/PLANEJAMENTO_EVENTO_COMPLEXO.md`.

### Arquivos criados/alterados
- `core/models.py`: campo `Evento.data_fim` + modelo `CustoEvento` (migration `0003`).
- `core/forms.py`: `EventoComplexoForm` e `CustoEventoForm`.
- `core/views.py`: `evento_complexo_novo_view`, `evento_painel_view`, `evento_custo_novo_view`,
  `evento_custo_excluir_view`. `core/urls.py`: rotas correspondentes. `core/admin.py`: `CustoEvento`.
- `templates/core/evento_complexo_form.html` e `evento_painel.html`; `eventos.html` (habilita o card
  "Evento com inscrição" e mostra "Abrir painel" nos eventos complexos).
- `static/css/eventos.css` (painel: abas, KPIs, custos) e `static/js/evento_painel.js` (abas + modal).
- `docs/PLANEJAMENTO_EVENTO_COMPLEXO.md` (novo) e demais docs atualizados.

### Decisões tomadas
- Reaproveita o modelo `Evento` (tipo `inscricao`) como base; `CustoEvento` relacionado por FK.
- Painel em página dedicada com abas (JS); demais módulos entram nas próximas fases.
- Resumo com indicadores (números); gráficos entram quando houver dados.

---

## 2026-07-03 - Corrige estilo do botão secundário nas telas internas

### Resumo
O botão "Cancelar" (e o "Duplicar") aparecia sem estilo porque `.btn-secundario` só existia em
`cadastro.css`, que não é carregado nas telas internas. Movido/adicionado o `.btn-secundario` para
`inicio.css` (carregado por todas as telas internas) e alinhados os botões do formulário de evento.

### Arquivos alterados
- `static/css/inicio.css`: adiciona o estilo do `.btn-secundario` (botão secundário das telas internas).
- `static/css/eventos.css`: alinha os botões do `.form-acoes` (zera o `margin-top` do `.btn-acao`).
- `docs/HISTORICO_ALTERACOES.md`: atualizado.

### Observação
- Isso também corrige o botão "Editar dados do aventureiro" em "Meus Dados", que usava a mesma classe.

---

## 2026-07-03 - Novo módulo "Eventos" (cadastro de evento simples)

### Resumo
Criado o módulo **Eventos** (restrito ao Diretor): tela `/eventos/` que lista os eventos do clube e
permite **criar evento**. O botão "Criar evento" abre um **modal** com a escolha do tipo — **Evento
simples** (implementado) e **Evento com inscrição** ("Em breve"). O cadastro simples (`/eventos/novo/`)
tem nome, local, descrição, data, horário de início e término. Cada evento tem **Duplicar**
(`?duplicar=<id>`), que abre o formulário pré-preenchido para recadastrar algo recorrente mudando só a
data. O componente de modal foi movido para `base.css` (reutilizável por Usuários e Eventos).

### Arquivos criados/alterados
- `core/models.py`: modelo `Evento` (+ migration `0002_evento`).
- `core/forms.py`: `EventoForm`. `core/views.py`: `eventos_view` e `evento_novo_view` (`@diretor_required`).
- `core/urls.py`: rotas `core:eventos` e `core:evento_novo`. `core/admin.py`: registra `Evento`.
- `templates/core/eventos.html` e `evento_form.html`: novas telas; item de menu "Eventos" (só diretor)
  adicionado também em `inicio.html` e `usuarios.html`.
- `static/css/eventos.css` e `static/js/eventos.js`: novos.
- `static/css/base.css`: passa a hospedar o **componente de modal** reutilizável.
- `static/css/usuarios.css`: removidos os estilos genéricos de modal (agora em `base.css`); mantidos os
  específicos (`.modal-pessoa*`, `.clicavel`).
- Documentação atualizada (`ESTADO_ATUAL`, `HISTORICO`, `REGRAS_CODEX`).

### Decisões tomadas
- Escolha do tipo via **um botão → modal com 2 cards** (a pedido do usuário). Pré-preenchimento apenas
  via **Duplicar** (sem auto-preencher do último). Evento "com inscrição" fica para depois.
- Modal como componente compartilhado em `base.css` (evita duplicação entre telas).

---

## 2026-07-03 - Tela "Usuários" restrita ao Diretor + modal com todos os dados

### Resumo
A tela "Usuários" passou a ser **restrita ao perfil Diretor** e, ao **clicar em qualquer card**
(responsável ou aventureiro), abre um **modal responsivo** (tela cheia no celular) com **todos os
dados** daquela pessoa. Isso inverte a regra anterior (que proibia dados sensíveis nessa tela): como
agora é restrita ao Diretor, exibir dados completos é permitido.

### Arquivos criados/alterados
- `core/permissoes.py`: novo (`eh_diretor` + decorator `diretor_required`).
- `core/context_processors.py`: novo (`is_diretor` em todos os templates).
- `config/settings.py`: registra o context processor `core.context_processors.perfis`.
- `core/views.py`: `usuarios_view` agora usa `@diretor_required`, guarda o contato dos responsáveis
  e passa os aventureiros completos (com idade/classes/foto/ficha preparadas).
- `templates/core/_aventureiro_detalhe.html`: novo parcial com o detalhe do aventureiro, reaproveitado
  em "Meus Dados" e no modal.
- `templates/core/inicio.html`: usa o parcial; item de menu "Usuários" só para o diretor (`is_diretor`).
- `templates/core/usuarios.html`: cards clicáveis, `#detalhesFonte` (fonte do modal) e o modal.
- `static/css/usuarios.css`: estilos do modal e dos cards clicáveis (responsivo, tela cheia no celular).
- `static/js/usuarios.js`: abre/fecha o modal (clona o detalhe, expande seções; fecha no X/fora/Esc).
- `docs/REGRAS_CODEX.md`: nova seção "Padrão de perfis e permissões" e atualização do "Padrão da tela
  Usuários"; `docs/ESTADO_ATUAL.md` e `docs/HISTORICO_ALTERACOES.md` atualizados.

### Decisões tomadas
- Perfis como grupos nativos do Django; gating por `@diretor_required` + `is_diretor` nos templates.
- Detalhes do modal renderizados no servidor (sem AJAX) num container fora de `.conteudo-interno`,
  para não afetar a pesquisa nem o accordion de `inicio.js`; o JS clona para o modal e expande as seções.

### Lições/armadilhas (documentadas em REGRAS_CODEX)
- `{# ... #}` é comentário de **uma linha**; para várias, usar `{% comment %}...{% endcomment %}`
  (um `{# #}` multi-linha fez o `{% include %}` de exemplo virar include real → recursão).
- Não escrever tags `{% ... %}` dentro de comentários HTML `<!-- -->` (o Django processa mesmo assim).

---

## 2026-07-03 - CSS global: interface sem cursor de texto fora de campos

### Resumo
Corrigido o "cursor de texto piscando" (caret) que aparecia ao clicar em textos que não são campos
digitáveis (títulos, rótulos, ícones, estado vazio, etc.). Criado `static/css/base.css` com
`user-select: none` no corpo e reativação da seleção apenas em campos de formulário e valores de
dados (`.dado-valor` / `.selecionavel`), para ainda permitir copiar CPF/telefone/e-mail. O `base.css`
passa a ser linkado em todas as telas, antes do CSS específico de cada página.

### Arquivos criados/alterados
- `static/css/base.css`: novo (regras globais de interface).
- `templates/core/{login,inicio,cadastro,cadastro_sucesso,editar_responsavel,usuarios}.html`:
  passam a linkar o `base.css` antes do CSS da página.
- `docs/REGRAS_CODEX.md`: nova seção "Padrão global de interface (base.css)".
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`: atualizados.

### Decisões tomadas
- Comportamento de app: texto de interface não é selecionável (some o caret e o cursor I-beam);
  apenas campos e valores de dados permanecem selecionáveis/copiáveis.
- Regra documentada para valer em telas futuras (sempre linkar `base.css`; nunca usar
  `contenteditable`/`tabindex` em elementos que não são campos).

### Observação
- Se o caret ainda aparecer em qualquer texto mesmo com isso, pode ser o modo "navegação por cursor"
  (caret browsing) do navegador — geralmente ligado/desligado com a tecla F7.

---

## 2026-07-03 - Login sem diferenciar maiúsculas/minúsculas no usuário

### Resumo
Corrigido o login: o usuário agora é resolvido de forma case-insensitive (ex.: `fabiano`, `Fabiano`
e `FABIANO` autenticam o mesmo usuário). Antes, o Django exigia o username exato (`Fabiano`), o que
impedia o login de quem digitava em minúsculas. A senha continua sendo validada normalmente.

### Arquivos criados/alterados
- `core/views.py` (`login_view`): resolve o username real por `iexact` antes de `authenticate`.
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`: atualizados.

### Decisões tomadas
- Consistente com o cadastro (`ContaForm.clean_username`), que já impede usernames duplicados por
  `iexact`. Verificado que não há usernames que colidam só por caixa (seguro).

---

## 2026-07-03 - Planejamento do cadastro de diretoria (documentado, não implementado)

### Resumo
Gravado o planejamento do **cadastro de diretoria**, do **cadastro de diretoria + aventureiro**
(mesclagem) e da tela "Cadastre-se" com 3 tipos, em `docs/PLANEJAMENTO_CADASTRO_DIRETORIA.md`, para
não perder o que foi alinhado. **Nada implementado ainda** — aguarda a documentação oficial dos campos
e os textos dos termos (compromisso de voluntariado e autorização de imagem).

### Arquivos criados/alterados
- `docs/PLANEJAMENTO_CADASTRO_DIRETORIA.md`: novo (especificação/planejamento).
- `docs/HISTORICO_ALTERACOES.md`: atualizado.

### Pendências
- Ver a lista "Pontos em aberto" dentro do próprio arquivo de planejamento.

---

## 2026-07-03 - Perfis de acesso + usuário diretor inicial

### Resumo
Criado o comando `configurar_perfis`, que cria os 5 perfis de acesso (grupos nativos do Django) e o
usuário diretor inicial. Primeira execução: 5 grupos criados e usuário `Fabiano` (diretor) vinculado
ao perfil Diretor; login `Fabiano`/`1234` autentica.

### Perfis de acesso
- **Diretor, Responsável, Professor, Tesoureiro, Secretário.**
- Conceito: "Diretoria" é o grupo de integrantes do clube (diretor, secretário, tesoureiro, professor);
  "Responsável" é o lado dos pais. Uma pessoa pode ser das duas partes e alternar o perfil ao logar
  (lógica de alternância ainda a implementar). Por ora, só o Diretor receberá permissões nas telas.

### Arquivos criados/alterados
- `core/management/commands/configurar_perfis.py`: novo comando (idempotente).
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`: atualizados.

### Decisões tomadas
- Usar **grupos nativos do Django** para os perfis (integram com o sistema de permissões; sem
  migration). Um modelo próprio de perfil/alternância poderá ser criado depois, se necessário.
- Usuário diretor inicial `Fabiano` com senha de desenvolvimento `1234` (trocar em produção),
  seguindo o mesmo padrão do `criar_dados_teste`. `is_staff`/`is_superuser` = False (é diretor no
  app, não admin do Django).

### Pendências / próximos passos (a validar antes de implementar)
- Cadastro de diretoria (inscrição) e a "mesclagem" diretoria + aventureiro.
- Tela "Cadastre-se" com escolha entre 3 tipos (aventureiro / diretoria / diretoria + aventureiro).
- Alternância de perfil (responsável ↔ diretoria) ao logar.
- Restringir o menu/tela "Usuários" ao perfil Diretor.
- Excluir a conta de teste `teste_responsavel` (2 aventureiros de teste).

---

## 2026-07-03 - Importação/migração dos cadastros do sistema antigo

### Resumo
Criado o comando de gerenciamento `importar_migracao`, que migra para o sistema novo **apenas os dados
de cadastro** ("cadastre-se") do sistema antigo, a partir do pacote exportado (pasta com `dados_json/`
e `arquivos/`). Importa: a conta de acesso (login com **hash de senha preservado**, então o responsável
continua logando com a mesma senha), dados de **pai, mãe e responsável legal**, **endereço**, dados de
cada **aventureiro**, **ficha médica**, **termo de autorização de imagem** e a **foto** de cada
aventureiro. Primeira execução real: **35 logins + 37 aventureiros** (todos com ficha médica, termo e
foto), com as telas "Meus Dados" e "Usuários" renderizando os dados corretamente.

### Arquivos criados/alterados
- `core/management/commands/importar_migracao.py`: novo comando (leitura dos JSON, mapeamento
  campo a campo, cópia de fotos para `media/`, idempotente, com `--dry-run`).
- `.gitignore`: passa a ignorar o pacote de exportação (`exportacao_migracao_*.zip`) e a pasta
  `migracao/` (dados de migração), para não versionar dados pessoais de menores.
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`: atualizados.

### Decisões tomadas
- **Escopo**: só os cadastros com aventureiro. Dos 106 registros de responsável do sistema antigo, 71
  não tinham nenhum aventureiro e ficaram de fora; entram apenas os 35 com aventureiro. Um registro-lixo
  de teste (nome "teste", CPF inválido) foi pulado.
- **Diretoria não é importada.** A única pessoa que era diretoria e também responsável de aventureiro
  entra apenas como mãe/responsável do aventureiro; nenhum dado de diretoria é trazido.
- **Responsáveis no plural**: pai, mãe e responsável legal de cada aventureiro são preservados; a tela
  "Usuários" agrupa por CPF e junta os papéis (ex.: quem é pai e também responsável legal aparece uma
  vez com os dois papéis).
- **Modelo novo**: não existe model `Responsavel` separado — os dados de pai/mãe/responsável ficam em
  cada `Aventureiro`, e o "responsável" do sistema é o usuário Django (login).
- **Datas originais** de criação/inscrição preservadas (contornando `auto_now_add`).
- **Campos inexistentes no export** (ex.: nacionalidade/estado civil/RG do responsável no termo) ficam
  em branco; `tamanho_camiseta` (texto livre no sistema antigo) é gravado como está.

### Segurança de menores
- As **fotos** importadas são dados **reais** dos membros do clube (com termo de imagem) e ficam
  **apenas** em `media/` (git-ignored) — **nunca** versionadas.
- O pacote de exportação e os JSON/CSV com CPFs/nomes/dados de saúde de menores **não** vão ao Git.

### Pendências
- (Opcional) Importar também os logins de responsáveis sem aventureiro, caso desejado no futuro.
- Fotos e assinaturas em imagem além da foto 3x4 (ex.: assinaturas do termo) não foram importadas.

---

## 2026-07-02 - Arquivo de contexto CLAUDE.md

### Resumo
Criado `CLAUDE.md` na raiz: um guia rápido de contexto (o que é o projeto, stack, como rodar/testar,
estrutura, rotas, models, regras inegociáveis e convenções) que aponta para os docs oficiais como
fonte da verdade. Não altera código nem comportamento — só documentação. Sem migrations.

### Arquivos criados/alterados
- `CLAUDE.md`: novo (arquivo de contexto).
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`: atualizados.

### Observação
As imagens soltas na raiz (foto de crianças e outra) continuam **fora do versionamento**
propositalmente (não versionar fotos reais de crianças).

---

## 2026-07-02 - Tela "Usuários" com vínculos familiares e pesquisa

### Resumo
Novo item de menu **Usuários** e nova tela `/usuarios/` (protegida por login) que mostra, de forma
resumida e visual, os responsáveis (pai, mãe e responsável legal de todos os aventureiros), os
aventureiros e o vínculo entre eles, com pesquisa inteligente em tempo real. Só dados resumidos —
nenhum dado sensível. Nenhum model foi alterado — sem migrations.

### Menu e rota
- Item **Usuários** adicionado abaixo de **Meus Dados** no menu lateral (mesmo visual; ativo em
  `/usuarios/`; funciona no desktop e no mobile). Adicionado nas duas telas (`inicio.html` e
  `usuarios.html`).
- Rota criada: `/usuarios/` (`core:usuarios`), com `@login_required`.

### Como os responsáveis são agrupados
- Para cada aventureiro consideram-se pai, mãe e responsável legal.
- Deduplicação por chave: **CPF**; se não houver, **nome + WhatsApp**; se não houver, **nome
  normalizado** (sem acentos/caixa). Responsáveis sem nome são ignorados.
- A mesma pessoa que aparece em mais de um papel (ex.: mãe e responsável legal) é mostrada **uma
  única vez**, com os papéis juntos; e lista todos os aventureiros a que está vinculada.

### Vínculos e resumo
- Card por responsável: nome, pílulas de papéis e "Aventureiros vinculados" (nome, idade e papel do
  vínculo, ex.: "Mãe / Responsável legal").
- Seção "Resumo por aventureiro": nome, idade e pai/mãe/responsável legal.
- Contadores no topo: Responsáveis (pessoas únicas), Aventureiros (total) e Vínculos (relações
  papel×aventureiro).

### Pesquisa inteligente
- `static/js/usuarios.js`: filtra os cards ao digitar (nome do responsável, papel, nome/idade do
  aventureiro e vínculos), ignorando maiúsculas/minúsculas e acentos; exibe "Nenhum vínculo
  encontrado para essa pesquisa." por seção quando não há resultado. Sem AJAX/bibliotecas.

### Dados sensíveis ocultos
- Não exibe CPF, RG, certidão, endereço, e-mail, telefone/WhatsApp, ficha médica, autorização de
  imagem nem foto (validado por teste automatizado).

### Arquivos criados/alterados
- `core/views.py`: helpers `_normaliza`, `_ordena_papeis`, `_chave_responsavel` e nova
  `usuarios_view`; import de `Aventureiro` e `unicodedata`.
- `core/urls.py`: rota `/usuarios/`.
- `templates/core/usuarios.html`: novo template.
- `templates/core/inicio.html`: item "Usuários" no menu.
- `static/css/usuarios.css`: novo (pesquisa, contadores, cards de responsável/aventureiro, vínculos).
- `static/js/usuarios.js`: novo (pesquisa em tempo real).
- `docs/README_PROJETO.md`, `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`,
  `docs/REGRAS_CODEX.md`: documentação atualizada.

### Decisões tomadas
- Visão geral do sistema (todos os aventureiros), pois é uma consulta de vínculos; acesso liberado
  a qualquer autenticado por ora (restrição por perfil fica para o futuro, documentado).
- Reuso do layout/menu de `inicio.css`; estilos próprios em `usuarios.css`. Pesquisa 100% no
  front-end (sem AJAX), conforme pedido.
- Sem alterar models nem `Meus Dados`; sem migrations.

### Validação
- Test client: proteção de login; menu "Usuários" ativo; agrupamento (Mariana aparece 1× como
  Mãe + Responsável legal, vinculada a Ana e Lucas; Roberto como Pai); contadores 2/2/6; resumo por
  aventureiro; e **nenhum dado sensível** vazado (CPF, e-mail, WhatsApp, endereço, RG, plano, foto).
- Visual (Chrome headless): desktop e mobile — layout bonito, responsivo e sem overflow.

### Pendências
- Restrição de acesso por perfil à tela "Usuários"; edição completa do aventureiro; "Esqueci minha
  senha"; validação avançada de CPF; envio de e-mail.

---

## 2026-07-02 - Avatar fictício nas fotos de teste e moldura redonda em "Meus Dados"

### Resumo
Ajustes visuais nas fotos: o comando de teste passou a gerar um **avatar de desenho fictício**
(silhueta com rosto sorridente + "Foto teste"), no lugar do quadrado com iniciais, e a moldura
da foto em "Meus Dados" ficou **redonda** (foto de perfil). Nenhuma foto real de pessoa/criança
é usada — apenas formas desenhadas com Pillow. Nenhum model alterado — sem migrations.

### Contexto
Foi solicitado usar fotos reais de crianças; isso foi **recusado** por segurança/privacidade de
menores e pela regra do projeto (não usar fotos reais de crianças). A alternativa segura adotada
foi desenhar um avatar fictício.

### Arquivos alterados
- `core/management/commands/criar_dados_teste.py`: `_gerar_foto_ficticia` agora desenha um avatar
  (cabeça, ombros, olhos e sorriso) sobre fundo colorido, com "Foto teste".
- `static/css/inicio.css`: moldura da foto do aventureiro agora circular (`border-radius: 50%`,
  100x100, `object-position: center 28%` para enquadrar o rosto).
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`: atualizados.

### Como regenerar
```
python manage.py criar_dados_teste
```
(As fotos são regeradas quando ausentes; para forçar o novo avatar em fotos antigas, apague os
arquivos em `media/aventureiros/fotos_teste/` antes de rodar.)

### Validação
- Fotos regeradas e exibidas em cards com moldura redonda (validado por captura em Chrome headless).

---

## 2026-07-02 - Correção de fotos, dados completos e fechar painéis ao clicar fora em "Meus Dados"

### Resumo
Revisão da tela `/inicio/` ("Meus Dados") para: (1) exibir a foto do aventureiro de forma robusta,
com placeholder quando o arquivo não existe; (2) mostrar TODOS os dados do cadastro, organizados
por seção; e (3) fechar os painéis expansíveis ao clicar fora, abrir um recolhendo os outros, com
`Esc`. Nenhum model foi alterado — sem migrations.

### Fotos
- Investigação: o serving de mídia em DEBUG e a URL estão corretos (verificado: `GET /media/...`
  responde HTTP 200 e o `<img>` renderiza `src="/media/aventureiros/fotos_teste/..."`). A falha
  real acontecia quando o banco referenciava uma foto cujo **arquivo não existe fisicamente**
  (situação comum, pois `media/` é gitignored): `{% if av.foto %}` era verdadeiro e gerava um
  `<img>` quebrado.
- Correção: a view marca `av.foto_ok` usando `foto.storage.exists(...)`; o template só mostra a
  imagem quando o arquivo existe. Caso contrário (ou se a imagem falhar ao carregar, via `onerror`),
  exibe um **placeholder com as iniciais** do nome (`av.iniciais`). A página nunca quebra.
- As fotos dos aventureiros de teste continuam em `media/aventureiros/fotos_teste/`
  (`lucas_teste.png` / `ana_teste.png`), geradas/mantidas pelo comando `criar_dados_teste`.

### Dados completos (auditoria cadastro × Meus Dados)
- Seções reorganizadas: **Dados pessoais**, **Documentos e informações pessoais** (nova, separada),
  **Endereço**, **Pai**, **Mãe**, **Responsável legal**, **Ficha médica**, **Declaração médica**
  (nova, separada) e **Autorização de imagem**.
- Campos adicionados que faltavam:
  - Ficha médica: medicamentos por condição (cardíaco/diabetes/renais/psicológicos), exibidos como
    "Sim (medicamentos: …)"/"Não"; listas de doenças, alergias (com "qual") e histórico recente.
  - Declaração médica: status do aceite + resumo do termo + data.
  - Autorização de imagem: nacionalidade do menor, nacionalidade do responsável, estado civil,
    endereço, número e bairro (além dos que já apareciam).

### Fechar ao clicar fora
- `static/js/inicio.js`: um listener de clique fecha todo `<details>` aberto que não contém o
  elemento clicado (fecha ao clicar fora e recolhe os demais ao abrir um — accordion); `Esc` fecha
  tudo; clique dentro não fecha. Funciona no celular. As seções continuam sendo `<details>` nativos.

### Arquivos criados/alterados
- `core/views.py`: helpers `_iniciais` e `_foto_valida`; `inicio_view` marca `foto_ok`/`iniciais`;
  `_preparar_ficha` passou a montar os textos das condições com medicamentos.
- `templates/core/inicio.html`: foto com `foto_ok` + placeholder de iniciais + `onerror`; seções
  Documentos e Declaração médica separadas; Ficha médica com medicamentos; Autorização de imagem
  completa.
- `static/js/inicio.js`: fechamento dos painéis ao clicar fora / `Esc` / accordion.
- `static/css/inicio.css`: placeholder de foto (iniciais) mais bonito.
- `docs/README_PROJETO.md`, `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`,
  `docs/REGRAS_CODEX.md`: documentação atualizada.

### Validação
- Servidor real: `GET /media/aventureiros/fotos_teste/ana_teste.png` → HTTP 200 (image/png);
  `/inicio/` (logado) renderiza `<img src="/media/...">` para os dois aventureiros.
- Test client: auditoria confirma todas as seções/campos (Documentos, Declaração médica,
  medicamentos por condição, nacionalidades, estado civil, endereço/número/bairro, etc.);
  placeholder de iniciais quando o arquivo não existe ("FQ") e quando não há foto ("SS"), sem
  quebrar a página (200).
- Visual (Chrome headless): card totalmente expandido com todas as seções, responsivo e sem
  overflow horizontal.

### Pendências
- Edição completa dos dados do aventureiro; "Esqueci minha senha"; permissões/perfis; validação
  avançada de CPF; envio de e-mail.

---

## 2026-07-02 - "Meus Dados" reorganizado: responsável (com edição) + aventureiros clicáveis

### Resumo
Reorganização da tela `/inicio/` ("Meus Dados") para um fluxo mais claro: um card do
**Responsável** no topo (expansível, com edição) e a seção **Aventureiros cadastrados**
com cards clicáveis que abrem todos os dados do aventureiro em seções recolhíveis. Criada
a edição dos dados do responsável, que propaga a alteração aos aventureiros do usuário que
compartilham o mesmo responsável. Nenhum model foi alterado — sem migrations.

### Como ficou a tela
- **Card Responsável**: dados do responsável legal do aventureiro mais recente (nome, parentesco,
  e-mail, WhatsApp, total de aventureiros). Expande mostrando também CPF e cidade/estado (do termo
  de imagem), a meta da conta e o botão **Editar**. Sem aventureiros, mostra os dados da conta.
- **Aventureiros cadastrados**: card por aventureiro com foto 3x4 destacada, nome, pílulas
  (idade, camiseta, classes) e status (✓ ficha médica / ✓ autorização). Ao clicar, abre as seções:
  Dados pessoais, Endereço, Pai, Mãe, Responsável legal, Ficha médica e Autorização de imagem.
  Botão "Editar dados do aventureiro" desabilitado (com aviso de que a edição virá depois).
- Botão "Cadastrar outro aventureiro" (→ `/cadastro/novo-aventureiro/`) e estado vazio amigável.
- Mensagens de sucesso/erro via framework de `messages`.

### Edição do responsável
- Rota `/meus-dados/responsavel/editar/` (`core:editar_responsavel`), protegida por login.
- Form `ResponsavelLegalForm` (nome, parentesco, CPF, e-mail, WhatsApp), pré-preenchido com o
  responsável do aventureiro mais recente.
- Ao salvar, aplica os dados a todos os aventureiros do usuário logado com o **mesmo CPF de
  responsável** (base: o mais recente); se nenhum coincidir, altera só o mais recente. Nunca
  altera dados de outro usuário. Redireciona a `/inicio/` com mensagem de sucesso.

### Rotas criadas/alteradas
- Criada: `/meus-dados/responsavel/editar/` (`core:editar_responsavel`).
- `inicio_view`: passou a montar o contexto do responsável (além dos aventureiros).

### Arquivos criados/alterados
- `core/forms.py`: novo `ResponsavelLegalForm`.
- `core/views.py`: contexto do responsável em `inicio_view`; nova `editar_responsavel_view`;
  import de `messages`.
- `core/urls.py`: rota de edição do responsável.
- `templates/core/inicio.html`: reescrita (card do responsável + cards clicáveis + mensagens).
- `templates/core/editar_responsavel.html`: novo (form de edição, reutiliza `cadastro.css` e `_campo.html`).
- `static/css/inicio.css`: estilos de mensagens, painel do responsável, cards de aventureiro
  (foto destacada, status, accordion), botões e responsividade; `overflow-x: hidden` de guarda.
- `docs/README_PROJETO.md`, `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`,
  `docs/REGRAS_CODEX.md`: documentação atualizada.

### Decisões tomadas
- Reaproveitar `<details>/<summary>` nativos (sem JS) para painel do responsável e cards dos
  aventureiros; reutilizar a parcial `_dado.html` e cálculos na view (idade, listas).
- Edição do responsável de forma segura: propaga por CPF do responsável, materializando os alvos
  antes de alterar o CPF; sempre restrita a `request.user`.
- Não alterar models (os dados do responsável já vivem em `Aventureiro`); sem migrations.
- Edição completa do aventureiro deixada para depois (botão apenas visual/desabilitado), para não
  introduzir edição incompleta que pudesse quebrar o cadastro.

### Validação
- Test client: `/inicio/` mostra card do responsável (Mariana), os 2 aventureiros com foto,
  status e seções (Pai/Mãe separados); edição do responsável atualiza os **dois** aventureiros
  (mesmo CPF), com mensagem de sucesso; segurança (outro usuário não vê nem edita dados alheios);
  proteção de login na rota de edição.
- Visual (Chrome headless): desktop colapsado e expandido e mobile — layout bonito, responsivo e
  **sem overflow horizontal** (confirmado por diagnóstico de largura).

### Pendências
- Edição completa dos dados do aventureiro; "Esqueci minha senha"; permissões/perfis; validação
  avançada de CPF; envio de e-mail.

---

## 2026-07-02 - Fotos fictícias dos aventureiros de teste (com verificação de existência)

### Resumo
Ajuste no comando `criar_dados_teste` para garantir que cada aventureiro de teste tenha
uma foto 3x4 fictícia associada e válida. Antes, a foto era regerada a cada execução;
agora o comando **verifica se a foto está correta** (campo preenchido, apontando para o
caminho esperado e com o arquivo existindo em `media/`) e só (re)gera quando está faltando
ou quebrada — caso contrário, mantém. Nenhum model foi alterado — sem migrations.

### O que muda
- `Lucas Henrique Oliveira Santos` → `media/aventureiros/fotos_teste/lucas_teste.png` (iniciais "LH").
- `Ana Clara Oliveira Santos` → `media/aventureiros/fotos_teste/ana_teste.png` (iniciais "AC").
- O comando informa, por aventureiro, "foto mantida" ou "foto gerada".

### Arquivos criados/alterados
- `core/management/commands/criar_dados_teste.py`: bloco da foto agora verifica a existência
  física do arquivo e a correspondência do caminho antes de decidir manter ou regerar; a
  saída passou a informar o status da foto de cada aventureiro.
- `docs/README_PROJETO.md`, `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`: atualizados.

### Como recriar os dados de teste
```
python manage.py criar_dados_teste
```

### Validação
- Rodado com as fotos já corretas → "foto mantida" para os dois.
- Apagado o arquivo do Lucas e rodado de novo → "foto gerada" só para o Lucas, "foto mantida"
  para a Ana; ambos os arquivos existem no disco e os campos `foto` apontam para eles.
- A tela "Meus Dados" exibe as fotos dos dois aventureiros (validado no passo anterior).

### Pendências
- Sem novas pendências (mantêm-se as anteriores: "Esqueci minha senha", edição pela área logada,
  permissões/perfis, validação avançada de CPF, envio de e-mail).

---

## 2026-07-02 - Autenticação real e tela "Meus Dados" funcional

### Resumo
Implementação da autenticação real do Django (login, logout e proteção de rota) e
transformação da tela `/inicio/` em uma área funcional "Meus Dados", que exibe os dados
da conta e os aventureiros do usuário logado (com foto, ficha médica e autorização de
imagem em seções recolhíveis). O cadastro inicial passou a autenticar o usuário
automaticamente. Nenhum model foi alterado — sem migrations.

### Login real
- `login_view` autentica com `authenticate` + `login` (campos `usuario`/`senha`). Em erro,
  exibe "Usuário ou senha inválidos.". Sucesso vai para `/inicio/` (ou `next`, se seguro).
  Removido o script inline que apenas navegava. Mantidos os links "Cadastre-se" e "Esqueci
  minha senha" (este último ainda sem função).

### Rotas protegidas / criadas
- `/inicio/` agora usa `@login_required` (sem login, redireciona para `/?next=/inicio/`).
- Criada `/sair/` (`core:sair`), logout via POST (`@require_POST`), redireciona para o login.

### Área "Meus Dados"
- Card "Dados da Conta": usuário, e-mail, data de criação e total de aventureiros.
- Um card por aventureiro: foto 3x4, pílulas de resumo (sexo, idade, cidade/UF, camiseta) e
  seções recolhíveis (`<details>`): Dados pessoais, Endereço, Responsáveis, Ficha médica e
  Autorização de imagem. Idade e listas (classes, doenças, alergias, condições, histórico)
  são calculadas na view. Estado vazio amigável quando não há aventureiros.
- Menu lateral com nome do usuário e botão "Sair" (acessível também no mobile).
- Botão "Cadastrar outro aventureiro" leva a `/cadastro/novo-aventureiro/`.

### Cadastro ajustado para autenticação real
- Após criar o `User`, o cadastro faz `login(...)` automático (backend `ModelBackend`) e mantém
  a sessão como retaguarda. A tela de sucesso e o botão "Ir para a tela inicial" abrem `/inicio/`
  já logado.
- `cadastro_novo_aventureiro_view` prioriza `request.user`; sem usuário (nem sessão), vai ao login.

### Arquivos criados/alterados
- `config/settings.py`: `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`.
- `core/views.py`: login/logout reais, `@login_required` em `inicio_view`, contexto de "Meus Dados"
  (helpers `_idade`, `_classes_investidas`, `_preparar_ficha`), login automático no cadastro e uso
  de `request.user` no fluxo de novo aventureiro.
- `core/urls.py`: rota `/sair/`.
- `templates/core/login.html`: formulário de login real + aviso de erro; sem JS de navegação falsa.
- `templates/core/inicio.html`: reescrita como "Meus Dados" (conta + cards dos aventureiros + Sair);
  usa `static/js/inicio.js`.
- `templates/core/_dado.html`: nova parcial rótulo+valor.
- `static/js/inicio.js`: novo (menu recolhível do mobile; detalhes via `<details>` nativo).
- `static/css/login.css`: estilo `.aviso-login`.
- `static/css/inicio.css`: estilos de "Meus Dados" (conta, cards de aventureiro, pílulas, accordion,
  botões de ação e Sair, estado vazio) e responsividade.
- `core/admin.py`: `list_display`/`search_fields` de Aventureiro com responsável legal e `criado_em`.
- `docs/README_PROJETO.md`, `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`,
  `docs/REGRAS_CODEX.md`: documentação atualizada.

### Decisões tomadas
- Reaproveitar a autenticação padrão do Django (sem libs). Login/logout com as rotas e settings
  padrão; logout via POST + CSRF (não link GET), por segurança.
- Seções recolhíveis com `<details>/<summary>` nativos (acessível e sem JS extra).
- Cálculos de exibição na view (idade, listas) e parcial `_dado.html` para reduzir repetição.
- Sem alterar models: a relação existente já bastava; sem migrations.
- `.gitignore` inalterado: `media/` e `db.sqlite3` seguem fora do Git.

### Validação (test client, ponta a ponta)
- `/inicio/` sem login → redireciona para `/?next=/inicio/`.
- Login errado → mensagem de erro; login `teste_responsavel`/`123456` → `/inicio/`.
- "Meus Dados" mostra conta, os 2 aventureiros de teste, fotos, ficha médica (doenças/alergias),
  autorização de imagem e os aceites.
- Logout → volta ao login; depois `/inicio/` volta a exigir login.
- Cadastro inicial autentica automaticamente (sessão com `_auth_user_id`); novo aventureiro na
  conta logada aparece em "Meus Dados".

### Pendências
- "Esqueci minha senha", edição dos dados pela área logada, permissões/perfis, validação avançada
  de CPF e envio de e-mail: futuros.

---

## 2026-07-02 - Comando de gerenciamento para gerar dados de teste

### Resumo
Criação do management command `criar_dados_teste`, que popula o banco local com uma
conta de teste (`teste_responsavel`, senha `123456`) e 2 aventureiros fictícios completos
(ficha de inscrição, ficha médica, autorização de imagem e fotos fictícias geradas com
Pillow). O comando é idempotente: pode ser rodado várias vezes sem duplicar dados e sem
tocar em dados de outros usuários. Nenhum model foi alterado — sem migrations.

### Como rodar
```
python manage.py criar_dados_teste
```
- Conta: usuário `teste_responsavel`, senha `123456`, e-mail `teste.responsavel@example.com`.
- Aventureiros: "Lucas Henrique Oliveira Santos" e "Ana Clara Oliveira Santos" (mesma família,
  mesmos responsáveis; a mãe é a responsável legal).
- Fotos fictícias salvas em `media/aventureiros/fotos_teste/lucas_teste.png` e `ana_teste.png`.

### Arquivos criados/alterados
- `core/management/__init__.py`: novo (pacote de comandos).
- `core/management/commands/__init__.py`: novo.
- `core/management/commands/criar_dados_teste.py`: novo — o comando em si (dados fictícios,
  geração das fotos com Pillow e mensagens de saída).
- `docs/README_PROJETO.md`: seção "Popular o banco com dados de teste".
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`: atualizados.

### Decisões tomadas
- Idempotência: `get_or_create` no `User` (reutiliza se existir) e `update_or_create` para
  Aventureiro (chaveado por `usuario` + `cpf`), FichaMedica e AutorizacaoImagem (por aventureiro).
  A senha é sempre redefinida para `123456` para garantir o acesso de teste.
- Fotos geradas localmente com Pillow (fundo colorido + iniciais + "Foto teste", proporção 3x4),
  sem imagens externas nem fotos reais. O campo `foto` aponta para o arquivo em
  `media/aventureiros/fotos_teste/` (caminho de teste solicitado, distinto do `upload_to` padrão).
- Carregamento de fonte robusto (tenta Arial/DejaVu e a fonte que acompanha o Pillow; cai na
  fonte padrão se nenhuma existir), para as iniciais aparecerem grandes.
- Não foram alterados models, admin nem o fluxo de cadastro do usuário final.
- `media/` e `db.sqlite3` continuam fora do Git (`.gitignore`); os dados/fotos de teste são
  recriados pelo comando quando necessário.

### Validação
- Comando executado duas vezes: 1ª "criados com sucesso", 2ª "já existiam e foram atualizados",
  sem duplicar (segue 1 usuário, 2 aventureiros, 2 fichas médicas, 2 autorizações).
- Conferido: `check_password("123456")` verdadeiro, fotos existentes em disco, aceites (declaração
  médica e imagem) verdadeiros, e os três models visíveis no admin (já registrados).

### Pendências
- Sem novas pendências específicas. Mantêm-se as anteriores (autenticação real, "Meus Dados",
  permissões, validação avançada de CPF, "Esqueci minha senha", envio de e-mail).

---

## 2026-07-02 - Fluxo para cadastrar múltiplos aventureiros na mesma conta

### Resumo
Implementação do fluxo que permite ao mesmo usuário/responsável cadastrar mais de um
aventureiro sem criar uma nova conta. A tela de sucesso passou a oferecer "Cadastrar
outro aventureiro" e "Ir para a tela inicial". Foi criada a rota
`/cadastro/novo-aventureiro/` (wizard de 6 etapas, sem "Conta de acesso"), que vincula
o novo aventureiro ao mesmo usuário e permite reaproveitar os dados dos responsáveis do
último cadastro. NÃO foi implementado login real nem permissões: o usuário atual é
mantido temporariamente na sessão.

### Problema encontrado
Apesar de o model já permitir `um usuário → vários aventureiros`, não havia caminho de
UI para isso: `/cadastro/` sempre exigia criar uma conta nova; após o cadastro o usuário
não era identificado (sem sessão/login); e a tela de sucesso só oferecia "Ir para a tela
inicial". Na prática, cada aventureiro exigiria um novo usuário.

### Solução implementada
- Após o cadastro inicial, o id do usuário é guardado na sessão (`cadastro_usuario_id`)
  junto com o nome do último aventureiro (`cadastro_ultimo_nome`) — solução **temporária**
  até a autenticação real (basta trocar por `request.user` no futuro).
- Nova rota `/cadastro/novo-aventureiro/` (nome `core:cadastro_novo_aventureiro`) que exige
  esse usuário na sessão, não cria novo `User` e salva o aventureiro na mesma conta.
- O mesmo template `cadastro.html` serve os dois fluxos (parametrizado por `modo_novo` e
  `conta_form`), evitando duplicar o wizard. A numeração das etapas e os índices usados pelo
  JS são calculados dinamicamente.
- Reaproveitamento dos dados de pai/mãe/responsável legal do último aventureiro, enviados
  pelo backend via `json_script` e preenchidos pelo JS quando o usuário marca a opção
  (ainda editáveis).

### Rotas criadas/alteradas
- Criada: `/cadastro/novo-aventureiro/` (`core:cadastro_novo_aventureiro`).
- Alteradas (comportamento): `/cadastro/` (grava usuário na sessão) e `/cadastro/sucesso/`
  (mostra nome e as duas opções).

### Arquivos criados/alterados
- `core/urls.py`: nova rota `cadastro/novo-aventureiro/`.
- `core/views.py`: refatorado — helpers `_instanciar_forms_aventureiro`, `_validar_aceites`,
  `_salvar_aventureiro` e `_dados_responsaveis_anteriores`; `cadastro_view` grava usuário na
  sessão; nova `cadastro_novo_aventureiro_view`; `cadastro_sucesso_view` passa nome e opções.
  Constantes `SESSAO_USUARIO_ID` / `SESSAO_ULTIMO_NOME`.
- `templates/core/cadastro.html`: cabeçalho/banner condicional (`modo_novo`), etapa "Conta"
  condicional (`conta_form`), bloco de reuso dos responsáveis + `json_script`, link de rodapé
  condicional.
- `templates/core/cadastro_sucesso.html`: nome do aventureiro e botões "Cadastrar outro
  aventureiro" / "Ir para a tela inicial".
- `static/js/cadastro.js`: numeração das etapas e índices de validação dinâmicos; usuário
  condicional na revisão; reaproveitamento dos dados dos responsáveis.
- `static/css/cadastro.css`: estilos `.aviso-info`, `.reuso-responsaveis`, `.sucesso-acoes`,
  `.sucesso-pergunta`.
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`, `docs/REGRAS_CODEX.md`,
  `docs/README_PROJETO.md`: documentação atualizada.

### Decisões tomadas
- Reaproveitar um único template/JS/CSS em vez de duplicar o wizard, controlando as diferenças
  por contexto (`modo_novo`, `conta_form`) e cálculo dinâmico das etapas no JS.
- Manter a identificação do usuário por sessão como solução simples e segura enquanto não há
  login real, documentando claramente que é temporária.
- Não alterar models — a relação `ForeignKey` (um-para-muitos) já suportava o cenário; sem
  migrations nesta tarefa.
- Validação autoritativa no servidor (aceites, forms) preservada nos dois fluxos.
- Fluxo testado ponta a ponta (cadastro inicial + segundo aventureiro na mesma conta, sem novo
  usuário, com ficha médica/autorização/aceites; redirecionamento sem sessão; bloqueio sem aceites).

### Pendências
- Autenticação real (login/logout) ainda NÃO implementada — substituir a sessão temporária por `request.user`.
- Página real de "Meus Dados" e listagem de aventureiros ainda NÃO criadas.
- Permissões / perfis, validação avançada de CPF, "Esqueci minha senha" e envio de e-mail: futuros.

---

## 2026-07-01 - Ajuste visual do link "Cadastre-se" no login

### Resumo
O link "Cadastre-se" da tela de login deixou de ser um botão em destaque e passou a
ser um link de texto discreto, porém não menor que "Esqueci minha senha" (0.95rem,
peso 600, contra 0.92rem do "Esqueci minha senha").

### Arquivos criados/alterados
- `static/css/login.css`: `.link-cadastro` reescrito como link de texto discreto (sem
  caixa/borda/fundo), com hover de sublinhado.
- `docs/ESTADO_ATUAL.md` e `docs/HISTORICO_ALTERACOES.md`: atualizados.

### Decisões tomadas
- Manter o "Cadastre-se" visível e um pouco maior que o "Esqueci minha senha", conforme pedido.
- Apenas CSS alterado; HTML e demais telas preservados.

### Pendências
- Sem novas pendências (mantêm-se as anteriores: autenticação, "Meus Dados", permissões, etc.).

---

## 2026-07-01 - Fluxo de cadastro de aventureiro

### Resumo
Implementação da estrutura inicial de criação de conta e cadastro completo de
aventureiro: link "Cadastre-se" no login, tela de cadastro em formato wizard de
7 etapas (`/cadastro/`), models para salvar os dados, upload de foto, aceites
obrigatórios e tela de confirmação (`/cadastro/sucesso/`). Ao finalizar, é criado
o `User` do Django e salvos os dados do aventureiro. NÃO há login automático,
permissões, recuperação de senha nem envio de e-mail.

### Models criados
- `Aventureiro`: FK `usuario` (um usuário pode ter vários aventureiros); dados principais,
  classes investidas (4 BooleanFields), endereço, documentos, dados de pai/mãe/responsável legal,
  cidade e data da inscrição (`data_inscricao` automática), aceites e `criado_em`.
- `FichaMedica`: OneToOne com `Aventureiro` (plano de saúde, doenças, alergias, condições de saúde,
  outras informações e tipo sanguíneo). Campos "qual/motivo" condicionais.
- `AutorizacaoImagem`: OneToOne com `Aventureiro` (dados do menor e do responsável legal para o termo).

### Rotas criadas
- `/cadastro/` (`core:cadastro`) e `/cadastro/sucesso/` (`core:cadastro_sucesso`).
- Em DEBUG, o Django passa a servir `/media/` (uploads).

### Arquivos criados/alterados
- `core/models.py`: novos models Aventureiro, FichaMedica, AutorizacaoImagem (com `choices`, `verbose_name`, BooleanFields, TextField, DateField/DateTimeField).
- `core/forms.py`: novo — ContaForm, AventureiroForm, FichaMedicaForm, AutorizacaoImagemForm (com mixin de estilo e validações de senha/username).
- `core/views.py`: novas views `cadastro_view` e `cadastro_sucesso_view` (validação conjunta + criação transacional).
- `core/urls.py`: novas rotas de cadastro e sucesso.
- `core/admin.py`: registro dos três models no admin.
- `core/migrations/0001_initial.py`: migration inicial dos models (criada e aplicada).
- `templates/core/cadastro.html`, `templates/core/cadastro_sucesso.html`, `templates/core/_campo.html`, `templates/core/_campo_check.html`: novos templates.
- `static/css/cadastro.css` e `static/js/cadastro.js`: novos (wizard, progresso, condicionais, preview de foto, atalhos, revisão).
- `templates/core/login.html`: link "Cadastre-se" entre "Entrar" e "Esqueci minha senha".
- `static/css/login.css`: estilo do link "Cadastre-se".
- `config/settings.py`: `MEDIA_URL` e `MEDIA_ROOT`.
- `config/urls.py`: serve mídia em DEBUG.
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`, `docs/REGRAS_CODEX.md`, `docs/README_PROJETO.md`: documentação atualizada.

### Decisões tomadas
- Wizard de 7 etapas em uma única página/`<form>` (etapas mostradas/ocultadas via JS); validação
  autoritativa no servidor. Solução simples, bonita e segura, sem bibliotecas externas.
- Quatro formulários combinados com `prefix` (conta/av/med/img) para evitar colisão de nomes.
- Uso do `User` padrão do Django para a conta; aventureiros ligados por FK (um-para-muitos),
  preparando o reaproveitamento de responsáveis no futuro.
- Aceites obrigatórios (declaração médica e autorização de imagem) validados no servidor e no JS.
- Foto via `ImageField` (requer Pillow, já instalado); preview no navegador antes do envio.
- Validação básica: senha obrigatória e confirmada, username único. CPF sem validação avançada (futuro).
- Fluxo testado ponta a ponta (criação de User + models, casos negativos) e visual validado em mobile/desktop.

### Pendências
- Autenticação real (login/logout) ainda NÃO implementada.
- Página real de "Meus Dados" e listagem de aventureiros ainda NÃO criadas.
- Reaproveitamento de responsáveis em novos cadastros ainda NÃO implementado (depende de login).
- Validação avançada de CPF, permissões, recuperação de senha e envio de e-mail: futuros.

---

## 2026-07-01 - Configuração do versionamento Git e regras de commit/push

### Resumo
Configuração do versionamento do projeto no Git e no GitHub, e registro das regras
obrigatórias de commit e push para toda alteração futura. Não houve alteração de
funcionalidades, layout ou telas.

### Git
- Git já estava inicializado (criado na tarefa anterior); branch principal: `main`.
- Remoto `origin` configurado para: https://github.com/fabianopolone123/PINHALJUNIOR2.0.git
- `.gitignore` revisado (Python/Django): passou a ignorar também `.env`, `*.sqlite3`,
  `staticfiles/` e `media/`, mantendo as entradas anteriores.
- `README.md` criado na raiz (não existia) com descrição básica e links para a pasta `docs/`.
- Commit criado com o estado atual e push enviado para o GitHub.

### Arquivos criados/alterados
- `.gitignore`: revisado com as entradas exigidas para Python/Django.
- `README.md`: criado na raiz do projeto.
- `CODEX.md`: adicionadas as seções "Fluxo obrigatório de Git" e "Padrão de mensagens de commit".
- `docs/REGRAS_CODEX.md`: adicionadas as seções "Fluxo obrigatório para toda alteração"
  (antes/durante/depois + segurança no Git) e "Padrão obrigatório para mensagens de commit".
- `docs/ESTADO_ATUAL.md`: adicionada a seção "Versionamento (Git)".
- `docs/HISTORICO_ALTERACOES.md`: esta entrada.

### Decisões tomadas
- Branch principal padronizada como `main`.
- Não versionar arquivos sensíveis/locais (`.env`, banco SQLite, ambientes virtuais, cache).
- Não sobrescrever conteúdo existente do `README.md` (foi criado por não existir).
- Regra: nunca usar `force push` nem apagar histórico; em caso de conflito, analisar com segurança.

### Pendências
- Autenticação real (login/logout) ainda NÃO implementada.
- Página real de "Meus Dados", permissões/perfis, models e migrations ainda NÃO existem.

---

## 2026-07-01 - Tela inicial interna com menu lateral

### Resumo
Criação da tela inicial interna (área logada) na rota `/inicio/`, com menu lateral
fixo no desktop e menu recolhível (gaveta) no celular. O primeiro e único item de
menu é "Meus Dados" (em destaque como ativo). A área principal traz um cabeçalho de
boas-vindas, um card em destaque de "Meus Dados" e cards ilustrativos. NÃO há
autenticação, permissões, sessão, models ou migrations — apenas estrutura visual.

### Arquivos criados/alterados
- `core/views.py`: adicionada a view `inicio_view` (renderiza `core/inicio.html`).
- `core/urls.py`: adicionada a rota `inicio/` (nome `core:inicio`).
- `templates/core/inicio.html`: novo template da tela interna (menu lateral, área principal,
  cards, script inline do menu recolhível e comentários indicando onde adicionar futuros
  itens de menu / permissões).
- `static/css/inicio.css`: novo CSS próprio da tela interna (mobile first, menu lateral,
  cards, hover, animação de entrada, `prefers-reduced-motion`).
- `templates/core/login.html`: botão "Entrar" agora redireciona (apenas visualmente) para
  `/inicio/`; continua sem validar usuário/senha.
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`, `docs/REGRAS_CODEX.md`: documentação atualizada.

### Decisões tomadas
- No celular, o menu lateral vira gaveta recolhível (botão hambúrguer + overlay) — solução
  simples e segura, sem cortar a tela.
- CSS da tela interna em arquivo próprio (`inicio.css`), sem misturar com `login.css`.
- Menu estruturado para permissões futuras: item ativo via classe `ativo` e comentários
  no template indicando onde novos itens (condicionais por perfil) serão inseridos.
- Ícones do menu/cards com emoji (sem biblioteca externa).
- Botão "Entrar" reaproveita o script inline existente, apenas redirecionando para `/inicio/`.
- Validação visual com Chrome headless (CDP): mobile 390px (sem overflow, menu fechado e aberto)
  e desktop 1280px.

### Pendências
- Autenticação real (login/logout) ainda NÃO implementada.
- Página real de "Meus Dados" (visualizar/editar) ainda NÃO criada.
- Permissões / perfis de usuário ainda NÃO implementados.
- Cadastro / banco de usuários e models/migrations ainda NÃO existem.

---

## 2026-07-01 - Melhoria visual da tela de login

### Resumo
Melhoria visual da tela de login (rota `/`), deixando-a mais moderna, com efeitos
suaves e mantendo total responsividade mobile first. Alteração apenas de CSS — o
HTML e a estrutura do projeto foram preservados. Nenhuma autenticação foi
implementada e nenhuma dependência foi instalada.

### Arquivos criados/alterados
- `static/css/login.css`: reescrito de forma organizada (sem duplicação), adicionando:
  fundo com gradiente animado e formas circulares desfocadas flutuando; card com
  glassmorphism suave, sombra mais elegante e animação de entrada; brilho atrás do
  logo com `drop-shadow`; título com linha decorativa; foco realçado nos campos;
  botão "Entrar" com gradiente, brilho deslizante no hover e efeito de clique;
  link "Esqueci minha senha" com sublinhado animado; suporte a `prefers-reduced-motion`.
- `docs/ESTADO_ATUAL.md`: atualizado com o novo padrão visual da tela de login.
- `docs/HISTORICO_ALTERACOES.md`: esta entrada.
- `docs/REGRAS_CODEX.md`: adicionada seção com o padrão visual a ser preservado.

### Decisões tomadas
- Manter o HTML da tela de login intacto (todas as classes, campos, botão e link preservados);
  concentrar as melhorias apenas no CSS.
- Usar glassmorphism suave (card translúcido com `backdrop-filter`) mantendo bom contraste
  do texto escuro.
- Incluir `@media (prefers-reduced-motion: reduce)` para acessibilidade.
- Validação visual feita com Chrome headless (CDP) em 390px (mobile, sem overflow horizontal:
  scrollWidth = innerWidth = 390) e 1280px (desktop).

### Pendências
- Autenticação real (login/logout) ainda NÃO implementada.
- Cadastro / banco de usuários do sistema ainda NÃO implementado.
- Funcionalidade do link "Esqueci minha senha" ainda NÃO implementada.
- Dashboard / área interna ainda NÃO criada.

---

## 2026-07-01 - Estrutura inicial, tela de login e documentação interna

### Resumo
Criação da estrutura inicial do projeto Django, da tela de login visual
(responsiva, mobile first) acessível na rota principal `/`, e do sistema de
documentação interna do projeto. A autenticação ainda NÃO foi implementada.

### Estado atual do projeto (resumo do que já existe)
- Projeto Django configurado (`config/`) com `templates/` e `static/`.
- App principal `core` com a view da tela de login.
- Tela de login visual na rota `/` com logo, título, campos de usuário e senha,
  botão "Entrar" e link "Esqueci minha senha".
- Logo do clube exibido no topo (`static/img/logo.png`, com fundo transparente).
- CSS próprio da tela de login (`static/css/login.css`), sem frameworks externos.

### Arquivos criados/alterados
- `manage.py`: utilitário de linha de comando do Django.
- `config/settings.py`: configurações do projeto (apps, templates, static, idioma pt-br, fuso America/Sao_Paulo).
- `config/urls.py`: rotas raiz do projeto (inclui as rotas do app `core` e o admin).
- `config/wsgi.py` e `config/asgi.py`: pontos de entrada WSGI/ASGI.
- `config/__init__.py`: pacote do projeto.
- `core/views.py`: view `login_view` que renderiza a tela de login.
- `core/urls.py`: rota `/` nomeada `core:login`.
- `core/apps.py`, `core/admin.py`, `core/models.py`, `core/__init__.py`, `core/migrations/__init__.py`: estrutura do app `core` (sem models por enquanto).
- `templates/core/login.html`: template da tela de login (logo, título, formulário e script inline que impede o envio real).
- `static/css/login.css`: estilos da tela de login (mobile first, gradiente azul/verde, card arredondado, foco nos campos, hover no botão).
- `static/img/logo.png`: logo do clube (fundo tornado transparente).
- `static/img/logo_original_backup.png`: backup do logo original recebido.
- `static/img/LEIA-ME.txt`: instruções sobre o logo.
- `requirements.txt`: dependência do Django.
- `.gitignore`: arquivos ignorados pelo Git.
- `CODEX.md`: guia rápido para o Codex.
- `docs/README_PROJETO.md`, `docs/REGRAS_CODEX.md`, `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`: documentação interna do projeto.

### Decisões tomadas
- Usar CSS próprio, sem Bootstrap ou Tailwind.
- Layout mobile first, com card de login centralizado.
- Paleta de cores azul/verde inspirada no logo do clube.
- O botão "Entrar" não autentica; o envio do formulário é bloqueado via script inline.
- O link "Esqueci minha senha" aponta para `#` (sem funcionalidade ainda).
- O logo original vinha com fundo cinza sólido (RGB, sem transparência); o fundo foi
  recortado para transparente e o arquivo original foi mantido como backup.

### Pendências
- Autenticação real (login/logout) ainda NÃO implementada.
- Cadastro / banco de usuários do sistema ainda NÃO implementado.
- Funcionalidade do link "Esqueci minha senha" ainda NÃO implementada.
- Dashboard / área interna ainda NÃO criada.
- App `core` ainda não possui models nem migrations de negócio.
