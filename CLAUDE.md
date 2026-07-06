# CLAUDE.md — Contexto do projeto

Guia rápido para o assistente (e para devs). Leia também, obrigatoriamente, antes de alterar:
`CODEX.md`, `docs/README_PROJETO.md`, `docs/REGRAS_CODEX.md`, `docs/ESTADO_ATUAL.md`,
`docs/HISTORICO_ALTERACOES.md`. **Estes docs são a fonte da verdade e devem ser atualizados a cada mudança.**

## O que é
Sistema web do **Clube de Aventureiros Pinhal Júnior** (Django). Já possui autenticação real,
cadastro de conta e de aventureiros (com ficha médica e autorização de imagem), área interna
"Meus Dados", a tela "Usuários" (vínculos familiares) e um **módulo de Eventos** completo: evento
simples e **evento complexo** com inscrições (Fase 2), lojinha e **PDV/balcão** com operadores
(Fase 4). Também há o módulo **Presença**, o módulo **WhatsApp** (integração com a API da W-API —
configurar a instância e enviar mensagens; só Diretor) e a **Loja do Clube** (loja oficial de uniformes/
lenços, independente da lojinha de evento; cadastro de produtos com **grupos/variações** + vitrine com
**carrinho** e pagamento simulado; só Diretor por ora) e o módulo **Mensalidades** (cobranças mensais por aventureiro,
inscrição+mensalidade, valores configuráveis, isenção/desconto, controle de pago; só Diretor). O clube tem
**3 áreas financeiras**: eventos, **mensalidades** e **loja** — todas consolidadas no módulo **Financeiro**
(📈, Diretor): resumo por fonte, gráficos, extrato consolidado e lançamento de custos do clube. Ver
`docs/PLANEJAMENTO_EVENTO_COMPLEXO.md` e `docs/ESTADO_ATUAL.md`.

## Stack
- Django 5.2 / Python 3.10+ · SQLite · Pillow (foto 3x4)
- HTML + **CSS próprio** (sem Bootstrap/Tailwind/libs) + JS puro
- Idioma pt-br, fuso America/Sao_Paulo

## Como rodar / testar
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver          # http://127.0.0.1:8000/
python manage.py criar_dados_teste  # popula dados de teste (idempotente)
```
Usuário de teste: **`teste_responsavel`** / senha **`123456`** (2 aventureiros com foto/ficha/autorização).

## Estrutura
- `config/` — projeto Django (settings, urls). `core/` — app único (views, models, forms, urls, admin,
  management command `criar_dados_teste`).
- Templates em `templates/core/`, estáticos em `static/{css,js,img}`, uploads em `media/` (git-ignored).

## Rotas (todas as internas exigem `@login_required`)
- `/` login (auth real) · `/sair/` logout (POST) · `/inicio/` "Meus Dados" · `/trocar-senha/`
- `/meus-dados/responsavel/editar/` editar responsável · `/usuarios/` responsáveis+aventureiros+vínculos ·
  `/usuarios/aventureiro/<id>/termos/` termos assinados (Diretor; página pra imprimir/salvar PDF)
- `/cadastro/` conta+1º aventureiro · `/cadastro/novo-aventureiro/` outro na mesma conta · `/cadastro/sucesso/`
- **Recuperação de senha** (pública, via WhatsApp): `/recuperar-senha/` (CPF do resp. legal → código de 4 dígitos → nova senha), `.../codigo/`, `.../reenviar/`, `.../nova-senha/`
- **Eventos** (Diretor; PDV/operar também por operadores): `/eventos/`, `/eventos/<id>/` (painel),
  `/eventos/<id>/pagina|inscrever|loja|pdv|pdv/inscricao|operar|operadores/` etc. — lista completa em `docs/ESTADO_ATUAL.md`.
- **Presença** (Diretor): `/presenca/`, `/presenca/<id>/`, `/presenca/<id>/marcar/`
- **WhatsApp** (Diretor): `/whatsapp/` (config W-API + envio), `/whatsapp/config/`, `/whatsapp/enviar/`
- **Pagamentos (Mercado Pago)** (Diretor p/ config): `/mercadopago/` (config credenciais teste/produção + modo),
  `/mercadopago/config/`; **webhook público** `/webhooks/mercadopago/`; página/sucesso de pagamento **genéricos**
  `/pagamento/<ref>/` e `/pagamento/<ref>/sucesso/`; status/simulação `/pagamento/<ref>/status/` (polling) e
  `/pagamento/<ref>/simular/` (só no modo teste). Mensalidades: `/mensalidades/cobrar/` (gera Pix p/ meses em aberto)
- **Loja do Clube** (Diretor no menu; vitrine/carrinho `@login_required`): `/loja/` (abas Gerenciar/Loja),
  `/loja/produto/novo|<id>/editar|<id>/excluir/`, `/loja/produto/<id>/` (vitrine), `/loja/carrinho/…`,
  `/loja/finalizar|pagamento|sucesso/`, `/loja/compra/<id>/cancelar/`, `/loja/entrega/…`
- **Mensalidades** (Diretor): `/mensalidades/`, `/mensalidades/config|gerar|pagar|isencao|reajustar|editar/`
- **Financeiro** (Diretor): `/financeiro/` (abas Resumo/Extrato/Custos), `/financeiro/custo/novo|<id>/excluir/`, `/financeiro/caixa/` (editar "Onde está o dinheiro"). Mostra o **líquido** (bruto − custos − **taxa do Mercado Pago**) por fonte e no resultado; a taxa vem de `Pagamento.taxa`. Idem no painel do evento, Mensalidades e Loja/Vendas.
- `/admin/`

## Models (`core/models.py`)
- `Aventureiro` (FK `usuario`; ficha de inscrição + pai/mãe/responsável legal; campo `ativo`). Um usuário → vários.
- `FichaMedica` (OneToOne) · `AutorizacaoImagem` (OneToOne) · `AssinaturaDocumento` (assinatura desenhada de
  cada documento da inscrição — ficha/médica/imagem; imagem PNG + snapshot do texto do termo; só o Diretor vê).
- **Eventos/Lojinha/Presença**: `Evento`, `CustoEvento`, `FaixaEtariaPreco`, `CampoInscricao`, `Inscricao`,
  `ParticipanteInscricao`, `RespostaInscricao`, `ProdutoEvento`, `VariacaoProduto`, `PedidoLoja`,
  `ItemPedidoLoja`, `OperadorEvento`, `PerfilUsuario`, `CupomDesconto`, `PresencaEvento`.
- **WhatsApp**: `WhatsappConfig` (singleton; ID/token/URL base da W-API) — módulo WhatsApp (só Diretor).
- **Pagamentos (Mercado Pago)**: `MercadoPagoConfig` (singleton; credenciais teste/produção + modo ativo) e
  `Pagamento` (engine única: tipo/forma/`referencia`/`mp_payment_id`/status/`valor_bruto`/`taxa`/`valor_liquido`/
  `payload` JSON/`finalizado`). FK `PedidoLoja.pagamento`. Cliente HTTP em `core/mercadopago.py` (urllib, sem dep
  nova). FKs `Mensalidade/CompraLoja/PedidoLoja/Inscricao.pagamento`. Pix ligado na **lojinha de evento**
  (Etapa 1), **mensalidades** (Etapa 2: baixa múltipla), **Loja do Clube** (Etapa 3) e **inscrição de evento**
  (Etapa 4: online paga difere a criação até aprovar; grátis/balcão como antes). Página de pagamento/sucesso
  **genéricas** (`/pagamento/<ref>/`). `Pagamento` no /admin/ (só-leitura). Taxa **real** do MP (fallback 1%).
  Ver ESTADO_ATUAL.
- **Loja do Clube**: `ProdutoLoja` → `GrupoLoja` → `VariacaoLoja` (produto composto: grupos "escolha única"/
  "itens", com obrigatório + orientação), `FotoProdutoLoja` (galeria + lightbox; capa = 1ª foto) e
  `CompraLoja`/`ItemCompraLoja` (compra vinculada ao login e, opc., a um aventureiro; `kit` agrupa itens de
  um mesmo uniforme; itens têm controle de entrega). Pagamento simulado. Aba **Vendas** = relatório
  (mais vendidos, a entregar, KPIs) + todas as compras.
- **Mensalidades**: `ConfigMensalidade` (singleton; valores padrão) e `Mensalidade` (aventureiro, ano, mês,
  tipo inscrição/mensalidade, valor, isento, status pago/aberto). Campos `Aventureiro.mensalidade_isento`/
  `mensalidade_desconto_pct`. Geração automática no cadastro.
- **Financeiro**: `CustoClube` (nome, valor, data, destino) + `ComprovanteCustoClube` (vários anexos por custo) —
  gastos gerais do clube; `CaixaClube` (singleton `get_solo`: `saldo_banco`; espécie = resultado − banco,
  calculada) para o card "Onde está o dinheiro". O resto do Financeiro é **consolidação** (lê mensalidades/loja/eventos).
- **Recuperação de senha**: `PerfilUsuario.whatsapp_principal_origem` (pai/mãe/resp legal) — para onde vai
  o código; código de recuperação fica na **sessão** (não há model novo pra ele).
- **Assinatura de documentos**: `AssinaturaDocumento` (aventureiro + tipo de documento + imagem PNG da assinatura
  desenhada + `titulo/texto_documento` snapshot do termo no ato + assinante nome/CPF + data; único por
  aventureiro+documento). No cadastro a assinatura **substitui o checkbox** de aceite (assinar = aceitar) nos 3
  documentos; o responsável não vê a própria assinatura depois; só o Diretor gera o termo assinado.
  (migrations até `0034`). Detalhes em ESTADO_ATUAL.

## Regras inegociáveis
- **Após CADA alteração**: atualizar `docs/ESTADO_ATUAL.md` e `docs/HISTORICO_ALTERACOES.md`
  (e `REGRAS_CODEX.md`/`README_PROJETO.md` quando aplicável) e **versionar no Git**:
  `git status` → `git add` → `commit` (mensagem em pt-BR, verbo no presente) → `git push origin main`.
  **Nunca** `force push` nem reescrever histórico.
- CSS próprio, mobile-first; preservar a paleta azul/verde e o padrão visual existente.
- Não instalar dependências novas sem autorização. Não alterar models sem necessidade; se alterar, criar migrations.
- **Segurança de menores: NUNCA usar fotos reais de crianças** nem baixar imagens da internet.
  Imagens de teste são avatares fictícios desenhados com Pillow. (Há imagens soltas na raiz que
  NÃO devem ser versionadas.)
- Fazer só o que foi pedido; não quebrar login, cadastro nem o cadastro de múltiplos aventureiros.

## Convenções úteis
- Parciais de template reutilizáveis: `_campo.html`, `_campo_check.html` (formulários) e `_dado.html`
  (rótulo+valor em "Meus Dados").
- Painéis expansíveis usam `<details>/<summary>` nativos; fechar-ao-clicar-fora em `static/js/inicio.js`.
- **Campos de valor (R$) usam máscara pt-BR** (`static/js/moeda_br.js`), em **dois modos**: (1) **par
  visível+oculto** — input **texto** com `data-moeda data-moeda-alvo="idOculto"` + um `<input type="hidden"
  id="idOculto" name="...">` (o oculto é o enviado); (2) **inline** — um único `input[type=text] data-moeda`
  **sem** `data-moeda-alvo` (o próprio campo é enviado; normalizado para o valor limpo pouco antes do
  `submit`), ideal para campos de formulário Django e linhas repetíveis clonadas por JS. Em ambos, mostra
  `1.234,56` e envia `1234.56` (back-end não muda). Aplicar isso a **todo** campo de valor novo. **Já em todos
  os campos de valor R$**: custo do clube, mensalidades, preços de produto (Loja do Clube e lojinha de evento),
  custo/faixa/valor da diretoria de evento e o **`valor_recebido` do PDV** (dinheiro). Quem lê um campo
  mascarado **em JS** (ex.: cálculo de troco) deve interpretar **os dígitos como centavos** (`value.replace(/\D/g,"")/100`),
  não `parseFloat` (que quebra com o separador de milhar). (Percentual, idade, estoque e quantidade **não** usam
  a máscara — não são valor em R$.)
- **Modais** fecham no fundo só com `mousedown`+`click` no fundo (não fechar ao arrastar seleção).
- "Meus Dados": foto só aparece se o arquivo existir (`foto.storage.exists`), senão placeholder com iniciais.
- Verificação visual sem navegador dedicado: renderizar via test client + Chrome headless
  (`--force-device-scale-factor=1`; o viewport mínimo do headless é ~484px).
