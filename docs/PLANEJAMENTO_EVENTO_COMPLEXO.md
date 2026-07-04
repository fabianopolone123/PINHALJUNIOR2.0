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
  (Resumo + Custos funcionando; Inscrições/Lojinha/Financeiro como "em breve"), moeda em R$ 1.500,00.
- **PRÓXIMO PASSO = Fase 2 (Inscrições).** Antes de codar, alinhar com o usuário: campos do formulário
  customizável (ex.: responsável + CPF + crianças vinculadas) e as regras de preço (faixa etária,
  gratuito/diferente para diretoria, valor fixo, grátis). Pagamento continua **simulado**.

## Fases
1. **Fase 1 — CONCLUÍDA ✅** — Base do evento complexo (título, descrição, datas de início/fim, local) +
   **painel/dashboard** (resumo com indicadores) + **Custos** (com comprovante). Modelos: `Evento`
   (+`data_fim`) e `CustoEvento`. Telas: `evento_complexo_form.html`, `evento_painel.html`.
2. **Fase 2 — PRÓXIMA ⏭️** — **Inscrições**: formulário customizável + preços (faixa etária / diretoria /
   fixo / grátis) + lista de inscritos + contagem no dashboard.
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
