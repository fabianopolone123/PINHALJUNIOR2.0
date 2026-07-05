# Planejamento — Evento complexo (evento com inscrição)

> Mapa geral do "evento complexo" — um **mini-sistema por evento** (inscrições, lojinha,
> custos e financeiro próprios). Construído **em fases**, validando cada uma.
> Registrado em 2026-07-03. Pagamentos reais e mapa ficam para o fim.

## Conceito
Eventos grandes (ex.: acampamento, "Passaporte da Diversão") funcionam como um negócio próprio,
com controle de caixa e fluxo financeiro. Cada evento complexo tem seu painel, inscrições,
lojinha, custos e resultado (lucro/prejuízo).

## Módulos (o que o evento complexo terá)
- **Dados do evento**: título, descrição, data/hora de início e de término, local (mapa/Google Maps → depois).
- **Painel/Dashboard**: resumo com gráficos — nº de inscritos, arrecadação de inscrições, vendas da
  lojinha, total de custos e **resultado (receitas − custos)**.
- **Inscrições**: formulário **customizável** (ex.: responsável + CPF + crianças vinculadas); preços por
  **faixa etária**, **gratuito/diferente para a diretoria**, valor fixo ou gratuito; status
  (confirmada/cancelada); código de inscrição.
- **Página pública**: página do evento aberta (sem login) para qualquer pessoa se inscrever e comprar itens.
- **Lojinha do evento**: produtos com **variações**, valor e **estoque**; pedidos vinculados à inscrição.
- **Custos**: título, descrição, valor e **anexo de comprovante** — entram no resultado.
- **Códigos de desconto**: cupons com % de desconto.
- **Financeiro**: receitas (inscrições + loja) − custos = resultado do evento.
- **Depois**: pagamentos reais (gateway, ex.: Mercado Pago), mapa (Google Maps), presença/check-in.

## Organização (UX)
- A tela **"Eventos"** lista os dois tipos (simples e complexo).
- Evento **simples**: continua no modal atual.
- Evento **complexo**: ao abrir, entra num **painel dedicado** (`/eventos/<id>/`) com **abas/seções**
  (Resumo · Inscrições · Lojinha · Custos · Financeiro · Página pública). É o "sistema dentro do sistema".

## ▶️ ONDE CONTINUAR (retomar aqui)
- **Fase 1 CONCLUÍDA** (2026-07-04): evento complexo criável, painel `/eventos/<id>/` com abas
  (Resumo + Custos funcionando), moeda em R$ 1.500,00.
- **Fase 2.1 CONCLUÍDA** (2026-07-04): fundação das inscrições na aba "Inscrições" do painel —
  configuração (local obrigatório, aberto ao público?, prazo limite, valor da diretoria), **faixas
  etárias com valores** por evento e **trava automática** no prazo/fim do evento.
- **Fase 2.2 CONCLUÍDA** (2026-07-04): **formulário de inscrição personalizável** — o Diretor monta,
  por evento, os campos (conjunto completo de tipos: texto curto/longo, número, escolha única/múltipla,
  sim/não, data), com opções, obrigatório e reordenação. Modelo `CampoInscricao`. Falta o
  preenchimento/envio (respostas) → Fase 2.4.
- **Fase 2.3 CONCLUÍDA** (2026-07-04): **evento no menu de todos os perfis** (seção "Eventos ativos",
  eventos não encerrados) + **página do evento** (`/eventos/<id>/pagina/`, pública se aberto ao
  público, senão só logado) com dados/status/valores/preview dos campos.
- **Fase 2.4 CONCLUÍDA** (2026-07-04): **inscrição de fato** — formulário (`/eventos/<id>/inscrever/`)
  com responsável + participantes (nome/idade/diretoria) + campos personalizados; preço calculado no
  servidor (faixa/diretoria), inscrição confirmada com código, tela de sucesso; **lista de inscritos**
  no painel (com cancelar) e **Resumo** com inscritos/arrecadação reais. Pagamento **simulado**.
  Modelos `Inscricao`, `ParticipanteInscricao`, `RespostaInscricao`.
- **🎉 FASE 2 (INSCRIÇÕES) CONCLUÍDA.** A "página pública com pagamento simulado" (antiga Fase 3)
  ficou coberta por 2.3 + 2.4.
- **Lojinha 4.1 CONCLUÍDA** (2026-07-04): cadastro de produtos com variações (preço por variação) e
  controle de estoque **opcional** por produto. Modelos `ProdutoEvento` e `VariacaoProduto`.
- **Lojinha 4.2 CONCLUÍDA** (2026-07-04): **comprar na página do evento** — loja com quantidade por
  variação + total ao vivo; pagamento **simulado**, baixa estoque; pedidos no painel e "Vendas
  (lojinha)" no Resumo. Modelos `PedidoLoja` e `ItemPedidoLoja`.
- **Lojinha 4.2 — passo de pagamento (simulado) — CONCLUÍDO** (2026-07-04): a compra pública ganhou um
  **passo de pagamento** antes de confirmar. WhatsApp obrigatório + autopreenchimento do comprador
  (localStorage); escolha **Pix/Cartão**; **tela de pagamento** (`/eventos/<id>/loja/pagamento/`) com
  **QR Pix simulado + copia e cola** (Pix) ou aviso de **redirecionamento ao Mercado Pago** (cartão);
  botão "Simular pagamento aprovado". O **pedido só é criado após a aprovação** (fica na sessão
  enquanto pendente). QR/payload **sem biblioteca externa**. **Pagamento real (gateway) fica para
  depois** — Pix real e API do Mercado Pago a alinhar em conversa futura.
- **Lojinha 4.3 CONCLUÍDA** (2026-07-04): **comprar junto da inscrição** (seção opcional no fim do
  form → pedido vinculado, mesma transação) + **pedir mais** (telas de sucesso com botão "Comprar
  (mais) na lojinha"). `PedidoLoja.inscricao` (FK).
- **Lojinha 4.4a CONCLUÍDA** (2026-07-04): **PDV / balcão de vendas** (`/eventos/<id>/pdv/`, Diretor):
  forma de pagamento (dinheiro c/ troco, pix, cartão, cortesia), vínculo **opcional** a inscrição,
  baixa de estoque. `PedidoLoja` ganhou origem/forma_pagamento/valor_recebido/registrado_por (mig. 0011).
- **Lojinha 4.4b CONCLUÍDA** (2026-07-04): **PDV de inscrição** (`/eventos/<id>/pdv/inscricao/`):
  inscrição presencial + lojinha num **pagamento só** (total combinado, troco, cortesia). `Inscricao`
  ganhou origem/forma_pagamento/valor_recebido/registrado_por + `troco` (mig. 0012). **Relatório
  "Vendidos por produto"** no Resumo (qtd inclui cortesia; arrecadado só o dinheiro).
- **Lojinha 4.4c CONCLUÍDA** (2026-07-04): **operadores do evento** — diretoria selecionada + ajudantes
  externos (conta temporária, senha `1234`, troca obrigatória no 1º acesso, reset pelo Diretor; vê só o
  evento dele). `OperadorEvento`/`PerfilUsuario` (mig. 0013), middleware de troca de senha, menu
  central `_menu.html`, landing "Operar", `operador_required` no PDV.
- **🎉 LOJINHA (FASE 4) CONCLUÍDA.**
- **Fase 5 — parte 1 (Financeiro: extrato completo) CONCLUÍDA** (2026-07-04): aba "Financeiro" com
  resultado (Entradas − Saídas), resumos (por fonte / forma de pagamento / canal / saídas), "vendidos por
  produto" (movido do Resumo) e o **extrato** cronológico de todos os lançamentos (cancelados riscados,
  fora dos totais). Helper `_montar_financeiro`. **Divisão**: número/tabela no Financeiro; gráfico no
  Resumo/dashboard. Custos seguem cadastrados na aba Custos (Financeiro só consolida).
- **Fase 5 — parte 2 (Resumo/dashboard) CONCLUÍDA** (2026-07-04): KPIs repaginados + gráficos CSS/SVG
  (receitas×custos, formas de pagamento, faixa etária) + **cobertura do clube** (donut + listas
  inscritos/não, por nome) com busca; e **busca na aba Inscrições**. Helper `_montar_dashboard`.
- **Fase 5 — parte 3 (cupons de desconto) CONCLUÍDA** (2026-07-04): aba "Desconto" gera cupom por % +
  lista (usado/quem usou); campo de cupom na inscrição (online e balcão); uso único; só inscrição.
  Model `CupomDesconto` (mig. 0014).
- **Fase 5 — parte 3b (evolução dos cupons) CONCLUÍDA** (2026-07-05): o cupom virou **por participante**
  (o usuário escolhe em quem aplicar, digitando na linha dele) com **validação ao vivo** (endpoint JSON
  `evento_cupom_validar` + toast + abate do total + desconto em R$); pode ser **restrito a uma faixa
  etária** (erro se o participante não casar); a geração ganhou **quantidade** (stepper, até **5 por
  vez**) e **seletor de faixa**, com o **layout** do campo de % revisado. `CupomDesconto.faixa`/
  `.participante` (mig. 0015). JS único `evento_insc_cupom.js` (substituiu `evento_pdv_inscricao.js`).
- **Fase 5.4a CONCLUÍDA** (2026-07-05): **Check-in + Retirada — console "Dia do evento" (só leitura)**.
  Modelos com check-in por participante (`ParticipanteInscricao.presente/…`) e retirada **por unidade**
  (`ItemPedidoLoja.quantidade_entregue/…`, mig. **0016**); tela `/eventos/<id>/dia/` (Diretor/operador)
  lista, por família, o status de check-in e de retirada dos itens (+ pedidos avulsos), com busca e resumo
  do dia. Helper `_casar_pedidos_inscricoes`. Decisões: entrega por unidade, todos os itens entregáveis,
  check-in por participante.
- **Fase 5.4b CONCLUÍDA** (2026-07-05): **ações de marcar** no console — check-in por participante (botão
  alterna Marcar chegada ↔ ✅ Chegou) e **entrega por unidade** (selo entrega/desfaz tudo; stepper − x/y +
  para parcial), tudo via endpoints JSON `evento_checkin`/`evento_entrega` + atualização inline e resumo ao
  vivo; guarda quem/quando. Helper `_resumo_dia`; parcial `_dia_entrega.html`.
- **PRÓXIMO PASSO = Fase 5.4c**: **"vai levar agora?" no balcão** (PDV venda e PDV inscrição) — já marcar a
  entrega dos itens na hora da venda. Depois **5.4d** (contadores no painel + guarda de exclusão do evento
  simples — ver memória do projeto).

#### PDV — decisões (definidas com o usuário em 2026-07-04)
- **Operadores** (4.4c): o Diretor escolhe, por evento — **diretoria selecionada** + **ajudantes
  externos** (conta temporária: usuário + senha `1234`; **troca obrigatória no 1º login** — 2×;
  **reset** pelo Diretor volta pra `1234`). Ajudante externo vê **só o botão do evento** dele.
- **O que o PDV faz**: vender lojinha (4.4a ✅) e fazer inscrição (4.4b) — em etapas.
- **Vínculo venda×inscrição**: **opcional** (rastrear por inscrição quando quiser; passante → avulso).
- **Formas de pagamento**: Dinheiro (com **troco**), Pix, Cartão, Cortesia.

### Lojinha — contexto (definido com o usuário em 2026-07-04)
Usada em vários momentos, tudo dentro do evento (para o financeiro fechar):
- Comprar **junto da inscrição** (opcional) → 4.3.
- **Voltar e pedir mais** depois de forma fácil (ex.: mais lanche no dia) → 4.3.
- Comprar **avulso** pela seção da lojinha na página do evento → 4.2.
- Futuro **PDV para atendentes** autorizados (caixa/cantina): vendem/inscrevem no dia, marcam
  **pago / forma de pagamento** → 4.4.
- Produtos com **variações** (preço por variação) e **estoque opcional** por produto (✅ 4.1).
- A **loja oficial do clube** (uniformes etc.) é OUTRA coisa, separada, para bem depois (não é a
  lojinha de evento).

## Requisitos da Fase 2 (definidos com o usuário em 2026-07-04)
> Cada evento complexo é um **mini-sistema configurável**; nada é fixo no sistema.
- **Preço por faixa etária, variável por evento**: as faixas (ex.: 6–10) e os valores mudam a cada
  evento. A **diretoria** paga um **valor próprio** (fixo, independe da idade). ✅ feito na 2.1.
- **Formulário de inscrição personalizável** por evento (cada evento tem campos diferentes). → 2.2.
- **Aberto ao público geral OU só membros** do clube (flag por evento). ✅ campo criado na 2.1.
- **Local obrigatório** no evento com inscrição. ✅ 2.1.
- **Prazo limite + trava automática**: passada a data/hora limite (ou o fim do evento), ninguém mais
  se inscreve. ✅ 2.1.
- **Evento no menu de TODOS os perfis** (responsável, diretor, tesoureiro, secretário, professor):
  ao criar um evento complexo, aparece um **botão com o nome do evento** no menu, levando à página
  do evento / ficha de inscrição. → 2.3.
- **Só o Diretor cria** o evento e o libera; os demais apenas se inscrevem. Pagamento **simulado**.
- Cada evento complexo também terá **lojinha** (Fase 4).

## Fases
1. **Fase 1 — CONCLUÍDA ✅** — Base do evento complexo (título, descrição, datas de início/fim, local) +
   **painel/dashboard** (resumo com indicadores) + **Custos** (com comprovante). Modelos: `Evento`
   (+`data_fim`) e `CustoEvento`. Telas: `evento_complexo_form.html`, `evento_painel.html`.
2. **Fase 2 — Inscrições** (dividida em 4 partes):
   - **2.1 — CONCLUÍDA ✅** — Fundação: config da inscrição (local, aberto ao público?, prazo limite,
     valor da diretoria), **faixas etárias com valores** por evento e **trava automática** no prazo.
     Modelo `FaixaEtariaPreco` + campos no `Evento`. Aba "Inscrições" do painel.
   - **2.2 — CONCLUÍDA ✅** — **Formulário de inscrição personalizável** por evento: campos com tipos
     (texto curto/longo, número, escolha única/múltipla, sim/não, data), opções, obrigatório e
     reordenação. Modelo `CampoInscricao`. (Falta o preenchimento/respostas → 2.4.)
   - **2.3 — CONCLUÍDA ✅** — **Evento no menu de todos os perfis** (seção "Eventos ativos") +
     **página do evento** (`evento_pagina.html`, pública/só-membros) com dados/status/valores/preview
     dos campos. Botão "Inscrever-se" desabilitado até a 2.4.
   - **2.4 — CONCLUÍDA ✅** — **Inscrição de fato**: participantes por faixa/diretoria, preço calculado,
     respostas do formulário, pagamento **simulado**, código, **lista de inscritos** no painel e
     **contagem/arrecadação no dashboard**. Modelos `Inscricao`/`ParticipanteInscricao`/`RespostaInscricao`.
3. **Fase 3 — coberta ✅** — **Página pública** de inscrição com pagamento **simulado** (feita em 2.3 + 2.4).
4. **Fase 4 — Lojinha** (em partes):
   - **4.1 — CONCLUÍDA ✅** — Cadastro de produtos: variações (preço por variação) + estoque opcional.
     Modelos `ProdutoEvento` e `VariacaoProduto`.
   - **4.2 — CONCLUÍDA ✅** — Comprar **avulso** na página do evento: carrinho + finalizar (pagamento
     simulado), baixa de estoque, "Vendas (lojinha)" no Resumo. Modelos `PedidoLoja`/`ItemPedidoLoja`.
   - **4.3 — CONCLUÍDA ✅** — Comprar **junto da inscrição** (seção opcional → pedido vinculado) +
     **pedir mais** (telas de sucesso oferecem a lojinha). `PedidoLoja.inscricao`.
   - **4.4 — PDV dos atendentes** (em partes):
     - **4.4a — CONCLUÍDA ✅** — PDV de **vendas** da lojinha (forma de pagamento, troco, cortesia,
       vínculo opcional a inscrição). Restrito ao Diretor por ora.
     - **4.4b — CONCLUÍDA ✅** — **inscrição** pelo PDV (presencial + lojinha, pagamento combinado) +
       relatório "Vendidos por produto".
     - **4.4c — CONCLUÍDA ✅** — **operadores** (diretoria selecionada + ajudantes externos com conta
       temporária: senha `1234`, troca obrigatória no 1º login, reset pelo Diretor; vê só o evento).
5. **Fase 5 — Financeiro + dashboard** (em partes):
   - **5.1 — CONCLUÍDA ✅** — **Financeiro (extrato completo)**: resultado (Entradas − Saídas), resumos
     (por fonte / forma de pagamento / canal / saídas), "vendidos por produto" e **extrato** cronológico
     de todos os lançamentos (cancelados riscados, fora dos totais). Helper `_montar_financeiro`.
   - **5.2 — CONCLUÍDA ✅** — **Dashboard/gráficos** no Resumo (CSS/SVG puro, sem libs): KPIs, barras
     (receitas×custos, formas de pagamento, faixa etária), **cobertura do clube** (donut + listas por
     nome) e busca na aba Inscrições. Helper `_montar_dashboard`.
   - **5.3 — CONCLUÍDA ✅** — **Cupons de desconto** (só inscrição): aba "Desconto" gera cupom por % +
     lista (usado/quem usou); campo de cupom na inscrição (online e balcão); uso único. Model
     `CupomDesconto` (mig. 0014).
   - **5.3b — CONCLUÍDA ✅** — Cupom **por participante** (validação ao vivo + toast + abate do total +
     desconto em R$), com **faixa etária** (erro se não casar), **geração em lote** (até 5 por vez, com
     stepper) e **seletor de faixa**; layout do campo de % revisado. `CupomDesconto.faixa`/`.participante`
     (mig. 0015); endpoint `evento_cupom_validar`; JS único `evento_insc_cupom.js`.
   - **5.4 — Check-in + Retirada** ("Dia do evento"), em partes:
     - **5.4a — CONCLUÍDA ✅** (2026-07-05) — modelos (check-in por participante + retirada por unidade,
       mig. 0016) + **console "Dia do evento"** (`/eventos/<id>/dia/`, só leitura): status de check-in e
       de retirada por família + pedidos avulsos, com busca e resumo. Helper `_casar_pedidos_inscricoes`.
     - **5.4b — CONCLUÍDA ✅** (2026-07-05) — **ações de marcar**: check-in por participante + entrega por
       unidade (selo clicável + stepper), via endpoints JSON `evento_checkin`/`evento_entrega` (POST,
       operador/Diretor) com atualização inline e resumo ao vivo. Helper `_resumo_dia`; parcial
       `_dia_entrega.html`.
     - **5.4c — PRÓXIMA ⏭️** — "vai levar agora?" no balcão (PDV venda e PDV inscrição): já marcar a
       entrega dos itens na hora da venda.
     - **5.4d** — contadores no painel + **guarda de exclusão do evento simples** (só exclui sem presença).
6. **Depois** — Pagamentos reais (gateway); mapa (o botão "Ver no mapa" já abre o Google Maps);
   **loja oficial do clube** (uniformes) — separada da lojinha de evento.

## Decisões
- Reaproveitar o modelo **`Evento`** (tipo `inscricao`) como base do evento complexo + modelos
  relacionados (Custo, Inscrição, Produto, Variação, Pedido, ItemPedido, CódigoDesconto, Presença).
- Painel em **página dedicada** (não modal).
- **Pagamentos simulados** nesta etapa (estrutura pronta; sem gateway real).
- Gráficos entram quando houver dados (Fase 5); no começo, o resumo usa **indicadores (cards de número)**.

## Referência — tabelas do sistema ANTIGO (para consulta; não vamos importar)
- `evento` (name, event_type, event_location, event_description, datas/horas, inscricao_publica,
  pagina_ativa, inscricao_valor_modo, inscricao_valor_unitario, inscricao_valor_config, taxa_cartao_evento,
  fields_data = formulário customizável).
- `eventoinscricao` (evento, user, responsavel, dados=JSON do formulário, codigo_inscricao, descontos,
  valores, cashback, confirmada/cancelada).
- `eventocusto` (evento, nome, valor, comprovante) + `eventocustocomprovante` (vários anexos).
- `eventodescontocodigo` (codigo, percentual_desconto, usado).
- `eventoatendente` (usuários que operam o evento), `eventopresenca` (presença por aventureiro),
  `eventofaltainscricao` (presentes sem inscrição).
- Lojinha: `lojaproduto`, `lojaprodutovariacao` (valor/estoque), `lojaprodutofoto`, `lojapedido`
  (com campos de Mercado Pago), `lojapedidoitem`.
