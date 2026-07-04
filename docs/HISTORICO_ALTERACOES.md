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
