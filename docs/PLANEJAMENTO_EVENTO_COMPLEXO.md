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
- **PRÓXIMO PASSO = Fase 2.3 (evento no menu de todos os perfis + página do evento).** Alinhar: como
  o botão do evento aparece no menu (todos os perfis) e o que a página do evento mostra (descrição,
  local, prazo, faixas/valores, botão de inscrever).

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
   - **2.3 — PRÓXIMA ⏭️** — **Evento no menu de todos os perfis** + **página do evento**
     (descrição/local/prazo + botão de inscrever).
   - **2.4** — **Inscrição de fato**: participantes por faixa/diretoria, preço calculado, pagamento
     **simulado**, código, **lista de inscritos** no painel e **contagem/arrecadação no dashboard**.
3. **Fase 3** — **Página pública** de inscrição (pagamento **simulado**).
4. **Fase 4** — **Lojinha** (produtos/variações/estoque + pedidos, pagamento simulado).
5. **Fase 5** — **Financeiro completo** + gráficos + códigos de desconto + presença/check-in.
6. **Depois** — Pagamentos reais (gateway) + mapa (Google Maps).

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
