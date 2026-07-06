# Estado Atual do Sistema

> Resumo rápido do estado atual. Atualize este arquivo após qualquer alteração.

**Última atualização:** 2026-07-05 (**Mensalidades: dashboard mês a mês**): a tela de Mensalidades ganhou
**abas** — **Resumo** (dashboard: **donut de taxa de pagamento**, **gráfico de barras mês a mês** recebido ×
em aberto em CSS puro, e **cards "Detalhe por mês"** — % paga com barra colorida, pagas/em aberto/isentos e
recebido/a receber por mês) e **Aventureiros** (a lista operacional). O resumo conta inscrições + mensalidades.
Tudo por **ano**. Antes: módulo Mensalidades (base).

**Anterior:** (**Módulo Mensalidades**): novo item **"Mensalidades"** (💰, só Diretor),
separado do financeiro. Cada aventureiro tem, por mês do ano, uma cobrança — o mês de inscrição nasce como
**"inscrição"** e os seguintes como **"mensalidade"** (gerado **automaticamente** no cadastro). **Valores
configuráveis** (padrão R$ 30, `ConfigMensalidade`); aventureiros podem ser **isentos** ou ter **desconto %**.
Tela com KPIs (previsto/recebido/em aberto/isentos), seletor de ano, **"Gerar cobranças <ano>"** e, por
aventureiro, os 12 meses com **marcar pago/desfazer** (forma, sem recarregar), **isenção/desconto do
aventureiro** e **edição por mês** (botão ✏️: **% de desconto** com o valor calculado ao vivo, ou isentar só
aquele mês, rota `mensalidades/editar/`); busca e filtro **"Só quem deve"**. Novos aventureiros geram as
cobranças automaticamente no cadastro (não há botão de gerar em massa). Há um **reajuste em massa** ("aplicar
os valores atuais às cobranças em aberto a partir de [mês]", rota `mensalidades/reajustar/`). Modelos `ConfigMensalidade`/`Mensalidade` +
campos no Aventureiro (mig. **0024**); rotas `/mensalidades/…`. O **histórico de 2026** do sistema antigo foi
**importado** (352 cobranças, 104 pagas; dados locais). Antes: Loja (aba Vendas + import de pedidos).

**Anterior:** (**Loja: aba "Vendas" (relatório + entrega) + import de pedidos**): a tela
da Loja ganhou a aba **"Vendas"** (📊, Diretor): **KPIs** (arrecadado, nº de compras, ticket médio, itens a
entregar), **Mais vendidos** (produto **composto** conta **por pedido**; simples por **unidade**) e **Por
forma de pagamento**, e **Todas as compras** — lista detalhada, **buscável** (busca + filtro **"Só a
entregar"**), com **marcar entrega por item** e **"Entregar tudo"** por pedido (rota `loja/entrega/compra/`).
O KPI de média é "Média por compra" (arrecadado ÷ nº de compras). O `ItemCompraLoja` ganhou controle de **entrega** (`quantidade_entregue`/`entregue_em`/
`entregue_por`; mig. **0023**). Foram **importados os pedidos pagos** da loja antiga (21 compras, R$ 3.083,50,
Pix) com comprador/forma/data/entrega preservados (dados locais, não versionados). Rota `loja/entrega/`.
Antes: galeria de fotos + fix de estilo.

**Anterior:** (**Loja: galeria de fotos + fix de estilo**): produto agora tem
**galeria de fotos** (várias por produto — como fica o uniforme, tabela de tamanhos) com **miniaturas** e
**ampliação em tela cheia (lightbox)** no celular e no PC; no cadastro há **upload múltiplo** e remoção; a 1ª
foto é a **capa** (`ProdutoLoja.capa`, modelo `FotoProdutoLoja`, mig. **0022**). Corrigido o **estilo dos
campos do comprador** no carrinho (faltava a classe `evento-form`). Importado o **"Uniforme de Gala -
Aventureiro (Completo)"** do sistema antigo: **61 variações** (Camiseta / Calça-Saia em escolha única +
Acessórios obrigatórios) + **5 fotos** (as fotos ficam só em `media/`, git-ignored). Antes: criação do módulo Loja.

**Anterior:** (**Loja do Clube (loja oficial)**): novo módulo **"Loja"** (🛍️) no menu
(**só Diretor** por ora), **independente** da lojinha de evento — é a 1ª das 3 áreas financeiras do clube
(eventos ✅, mensalidades ⏳, loja ▶). Tela com **2 abas**: **Gerenciar** (cadastrar produtos + compras
recentes) e **Loja** (vitrine com **carrinho na sessão**). Produto em 3 níveis **Produto → Grupos →
Variações**: **simples** (lista direta) ou **composto** (ex.: **Uniforme de Gala** = Camiseta/Calça/Saia em
"escolha única" + Acessórios em "itens"). Grupo tem modo (escolha única/itens), **obrigatório** e
**orientação**; itens podem ser obrigatórios com **aviso soft** (avisa o que falta e pergunta se já tem — não
bloqueia). Compra **vinculada ao login** e opcionalmente a um **aventureiro** (1 = automático; 2+ = escolher,
útil pro bordado do Kit Nome). **Pagamento simulado** (Pix QR/copia-e-cola + cartão via Mercado Pago no
futuro), reaproveitando os helpers do evento; `CompraLoja` só nasce após a aprovação; Diretor pode
**cancelar** (devolve estoque). Modelos `ProdutoLoja`/`GrupoLoja`/`VariacaoLoja`/`CompraLoja`/`ItemCompraLoja`
(mig. **0021**). Rotas `/loja/…`. Antes: Recuperação de senha pelo WhatsApp + notificações/AJAX.

**Anterior:** (**Recuperação de senha pelo WhatsApp** + notificações/AJAX): o link
**"Esqueci minha senha"** funciona. Fluxo público em 3 etapas (sessão): **CPF** do responsável legal →
envia **código de 4 dígitos** para o **WhatsApp principal** da conta → digita o código (5 tentativas,
expira em 10 min, reenvio com espera de 60 s) → **nova senha** (2×). Código guardado **com hash** na
sessão; destino sempre **mascarado**. Em **Usuários** (Diretor) há o controle **"WhatsApp principal"**
(pai/mãe/resp legal; padrão = responsável legal) por conta — campo `PerfilUsuario.whatsapp_principal_origem`
(mig. **0020**). Rotas `/recuperar-senha/…` e `/usuarios/conta/<id>/principal/`.
**Refinamentos (mesmo dia):** todas as notificações usam o **toast padrão** (o CSS do toast foi para o
`base.css`; o **login** também virou toast); os formulários de **login e recuperação** enviam por **AJAX**
(`static/js/ajax_form.js` + `form[data-ajax-toast]`), então **erro repete o toast sem recarregar** a
página (contrato JSON `{"redirect":url}` ou `{"msg","tipo"}`; helpers `_eh_ajax`/`_ajax_redirect`/
`_ajax_toast`); corrigido um **vazamento de `messages`** (login passou a renderizar `messages`). Antes:
Módulo WhatsApp (W-API))

**Anterior:** (**Módulo WhatsApp (W-API)**: novo item **"WhatsApp"** (💬) no menu
(**só Diretor**). Tela `/whatsapp/` com duas seções: **Configuração da instância** (ID da instância,
**token** exibido só com os **últimos 4 dígitos** e só substituído se digitar um novo, e **URL base**
opcional com padrão `https://api.w-api.app/v1`) e **Enviar mensagem** (número + texto). O número é
**normalizado** (aceita espaços/traços/parênteses/`+55`) para o formato da API (DDI 55 + dígitos), com
**prévia ao vivo**; envio **AJAX** com **toast padrão**. POST na W-API via **urllib** (sem novas
dependências): `POST {base_url}/message/send-text?instanceId=<id>`, `Authorization: Bearer <token>`,
body `{"phone","message"}`. Model **`WhatsappConfig`** (singleton, mig. **0019**). Antes: Aventureiro
inativo/desligado + cascata na conta)

**Anterior:** (**Aventureiro inativo/desligado + cascata na conta**: em **Usuários**
(Diretor), ao abrir um aventureiro (modal), há o botão **"Marcar como inativo"** (⛔) / **"Reativar"** (✅).
Campo `Aventureiro.ativo` (mig. **0018**). **Cascata**: ao inativar, se o responsável (conta `usuario`) não
tiver mais **nenhum** aventureiro ativo, a **conta é desativada** (`is_active=False`); se tiver outro ativo
(irmão), a conta continua ativa; reativar volta a conta. **Contas de Diretor/staff são protegidas** (nunca
desativadas). Cards de aventureiro inativo ficam com selo **"Inativo"** e riscados; o **responsável** (pai/
mãe/resp) também aparece **Inativo** quando **todos os aventureiros dele** estão inativos; a **Presença** e
a **cobertura do Resumo** contam só **ativos**. Antes: Módulo Presença do clube)

**Anterior:** (**Módulo Presença do clube**: novo item **"Presença"** no menu
(Diretor) → escolhe o **evento** → **lista de todos os aventureiros** do clube com **foto grande** e botão
**Marcar** (toggle presente/ausente, sem recarregar); **clicar na foto** abre a foto ampliada num **modal**.
Busca em tempo real e contador "presentes X de Y". É **independente** do check-in de inscrição do evento
complexo. Model `PresencaEvento` (existência = presente; mig. **0017**). Também **ativada a guarda de
exclusão**: evento com **presença marcada** não pode ser excluído (fecha o item pendente da Fase 5.4).
Antes: Refinos de UX dos eventos)

**Anterior:** (**Refinos de UX dos eventos**: (1) a **barra de abas do painel** virou
um **card/toolbar** (fundo, borda, cantos arredondados), com a aba de seção ativa **preenchida** em azul e
um **divisor** antes das abas de ação (Dia do evento / Vender no balcão / Operadores) — fica claro que são
os botões do painel; (2) o console **"Dia do evento"** ganhou **atalhos de balcão** no topo (**Nova
inscrição (balcão)** e **Vender na lojinha**), para o atendente vender/inscrever sem sair da tela. Também
**confirmado** que a lojinha (botão "Comprar na loja" e seção "Quer levar algo da lojinha?") **já** só
aparece quando há produtos ativos. Antes: Fase 5.4d (contadores do dia no painel; Fase 5.4 concluída))

## Nome do sistema
Clube de Aventureiros Pinhal Júnior

## Objetivo do sistema
Sistema web do clube com autenticação real, cadastro de conta e de aventureiros e
área interna "Meus Dados" que exibe os dados do usuário logado e de seus aventureiros.

## Funcionalidades prontas
- Estrutura inicial do Django funcionando.
- Tela de login responsiva (mobile first) na rota `/`, com visual moderno.
- **Autenticação real**: login por username/senha (`authenticate` + `login`), com mensagem
  "Usuário ou senha inválidos." em caso de erro; após logar, vai para `/inicio/`. O usuário é
  resolvido **sem diferenciar maiúsculas/minúsculas** (ex.: `fabiano` = `Fabiano`), consistente
  com o cadastro (que impede usernames duplicados por `iexact`).
- **Logout** em `/sair/` (POST, botão "Sair" no menu lateral); volta para o login.
- **Proteção de rota**: `/inicio/` usa `@login_required`; sem login, redireciona para `/`
  (com `?next=`). Configurados `LOGIN_URL`, `LOGIN_REDIRECT_URL` e `LOGOUT_REDIRECT_URL`.
- Tela interna "Meus Dados" (`/inicio/`) **funcional e reorganizada**:
  - Card do **Responsável** no topo (dados do responsável legal do aventureiro mais recente):
    nome, parentesco, e-mail, WhatsApp e total de aventureiros; expande (`<details>`) mostrando
    nome, parentesco, CPF, e-mail, WhatsApp, cidade/estado (do termo de imagem) e um botão **Editar**.
    Sem aventureiros, exibe os dados básicos da conta.
  - Seção **Aventureiros cadastrados**: um card clicável por aventureiro com foto 3x4 destacada,
    nome, pílulas (idade, camiseta, classes) e status de ficha médica/autorização; ao abrir, mostra
    **todos** os dados em seções recolhíveis: Dados pessoais, Documentos, Endereço, Pai, Mãe,
    Responsável legal, Ficha médica (com medicamentos por condição), Declaração médica e
    Autorização de imagem (completa). Botão "Editar dados do aventureiro" ainda desabilitado.
  - **Foto**: exibida em **moldura redonda** (foto de perfil). Só aparece se o arquivo existir
    fisicamente (a view checa `storage.exists`); caso contrário, mostra um placeholder com as
    **iniciais** do nome. O `<img>` tem `onerror` que troca para o placeholder se a imagem falhar
    (nunca quebra a página). As fotos de teste são **avatares fictícios** desenhados com Pillow
    (silhueta com rosto sorridente) — nunca fotos reais de crianças.
  - **Fechar ao clicar fora**: painéis `<details>` abertos (responsável, aventureiro e seções
    internas) recolhem ao clicar fora deles; abrir um recolhe os outros (accordion); `Esc` fecha
    tudo. Implementado em `static/js/inicio.js` (clique dentro não fecha).
  - Botão "Cadastrar outro aventureiro" e estado vazio amigável quando não há aventureiros.
- Edição do responsável em `/meus-dados/responsavel/editar/` (form `ResponsavelLegalForm`): altera
  nome, parentesco, CPF, e-mail e WhatsApp de todos os aventureiros do usuário com o mesmo CPF de
  responsável (ou apenas o mais recente, se nenhum coincidir); volta a `/inicio/` com mensagem de sucesso.
- Menu lateral fixo (desktop) e recolhível/gaveta (mobile), com nome do usuário e botão "Sair".
- Menu com dois itens: **Meus Dados** e **Usuários** (item ativo destacado conforme a tela).
- Tela **Usuários** (`/usuarios/`, **restrita ao perfil Diretor** via `@diretor_required`): visão
  geral de responsáveis e aventureiros com o vínculo familiar. Agrupa responsáveis únicos (pai, mãe e
  responsável legal de todos os aventureiros) por CPF (ou nome+WhatsApp, ou nome), juntando papéis
  quando é a mesma pessoa; mostra os aventureiros vinculados a cada responsável (com idade e papel do
  vínculo) e um resumo por aventureiro. Tem contadores (Responsáveis/Aventureiros/**Ativos**) e
  **pesquisa inteligente** em tempo real (ignora maiúsculas/acentos). **Ao clicar em qualquer card**
  (responsável ou aventureiro), abre um **modal responsivo** (tela cheia no celular) com **todos os
  dados** daquela pessoa — no responsável: CPF, e-mail, celular/WhatsApp, papéis e aventureiros
  vinculados; no aventureiro: dados pessoais, documentos, endereço, pai/mãe/responsável, ficha médica,
  termo de imagem e foto (reaproveita o parcial `_aventureiro_detalhe.html` de "Meus Dados"). Como é
  restrita ao Diretor, aqui é permitido exibir dados sensíveis. O item de menu "Usuários" aparece só
  para o diretor.
- **Perfis/permissões**: `core/permissoes.py` (`eh_diretor` + decorator `diretor_required`) e o context
  processor `core/context_processors.py` (`is_diretor` e `eventos_menu` em todos os templates — o
  primeiro para `{% if is_diretor %}`, o segundo para a seção "Eventos ativos" do menu).
- Módulo **Eventos** (`/eventos/`, **restrito ao Diretor**): lista os eventos do clube em cards
  (nome, tipo, data, horário, local, descrição) e permite **criar evento**. O botão "Criar evento"
  abre um **modal** para escolher o tipo: **Evento simples** (implementado) ou **Evento com inscrição**
  (marcado como "Em breve"). O cadastro de evento simples (`/eventos/novo/`) tem nome, local, descrição,
  data, horário de início e término. Cada evento na lista tem um botão **Duplicar** que abre o
  formulário já preenchido com aquele evento (`?duplicar=<id>`), para recadastrar algo recorrente
  mudando só a data/horário. Menu "Eventos" aparece só para o diretor. Cada evento tem também um botão
  **Excluir** (🗑️) que aparece **apenas quando o evento está "vazio"** (sem nenhuma inscrição, sem
  nenhum pedido **e sem presença marcada**); a exclusão pede **confirmação** e mostra **toast**. Eventos
  com inscrições/pedidos/presença **não** têm o botão (são preservados). A view (`evento_excluir_view`, POST) revalida a regra no
  servidor e a exclusão remove em cascata a configuração do evento (custos, produtos, faixas, campos,
  operadores).
- **Evento complexo (com inscrição) — Fase 1**: no modal de "Criar evento", a opção **"Evento com
  inscrição"** cria um evento `tipo=inscricao` (com data/hora de início **e término**, para eventos de
  vários dias) e leva ao **painel do evento** (`/eventos/<id>/`). O painel tem **abas** (Resumo,
  Inscrições, Lojinha, Custos, Financeiro): **Resumo** mostra indicadores (inscritos, arrecadação,
  vendas, receitas, custos e **resultado** — verde/vermelho); **Custos** permite adicionar custos
  (título, descrição, valor e **comprovante** anexo) e removê-los, com o total refletindo no resultado.
  (Lojinha e Financeiro **já implementados** — ver adiante.) O plano completo (todas as fases) está em
  `docs/PLANEJAMENTO_EVENTO_COMPLEXO.md`. Pagamentos ficam simulados por ora.
- **Evento complexo — Fase 2.1 (fundação das inscrições)**: a aba **Inscrições** do painel deixou de
  ser "em breve" e agora tem a **configuração da inscrição** do evento: **local** (obrigatório no
  evento com inscrição), **aberto ao público geral?** (sim = qualquer pessoa; não = só membros do
  clube), **prazo limite de inscrição** (data/hora) e **valor da diretoria** (valor fixo que a
  diretoria paga, independe da idade; vazio = sem valor especial, 0 = grátis). Mostra um **status**
  ("✅ Abertas" / "⛔ Encerradas") com a data-limite: passado o prazo (ou, se vazio, o fim do evento),
  trava automaticamente. Também gerencia **faixas etárias com valores** por evento (rótulo opcional +
  idade mín/máx + valor), adicionadas por modal e removíveis — cada evento define as suas.
- **Evento complexo — Fase 2.2 (formulário de inscrição personalizável)**: na mesma aba "Inscrições",
  subseção **"Formulário de inscrição"**, o Diretor monta os **campos personalizados** do evento:
  pergunta/rótulo, **tipo** (texto curto, texto longo, número, escolha única, escolha múltipla,
  sim/não, data), **opções** (só para escolha única/múltipla), **obrigatório?** e **por participante?**
  (se marcado, o campo é perguntado em cada participante; senão, uma vez, junto do responsável). Os
  campos são adicionados por modal, **reordenáveis** (▲▼) e removíveis.
- **Evento complexo — Fase 2.3 (evento no menu de todos os perfis + página do evento)**: todo evento
  com inscrição **ainda não encerrado** aparece numa seção **"Eventos ativos"** no menu lateral de
  **todos os perfis logados** (responsável, diretor, tesoureiro, secretário, professor), com o nome do
  evento levando à **página do evento** (`/eventos/<id>/pagina/`). Eventos passados somem do menu
  sozinhos. A página do evento é uma **página própria** (sem a barra lateral) com nome, descrição,
  local (com botão **"Ver no mapa"** que abre o Google Maps no endereço), datas/horários, **status**
  das inscrições (aberto/encerrado + prazo), **valores** (faixas + diretoria) e **preview dos campos**
  do formulário. **Acesso**: evento **aberto ao público** → sem login; **só membros** → exige login.
- **Evento complexo — Fase 2.4 (inscrição de fato — Fase 2 CONCLUÍDA)**: na página do evento,
  "Inscrever-se" abre o **formulário de inscrição** (`/eventos/<id>/inscrever/`) com dados do
  responsável + **participantes** (linhas repetíveis: nome + idade + opção "diretoria") + os **campos
  personalizados** (os "uma vez" junto do responsável; os "por participante" dentro de cada
  participante). O **preço** de cada participante é calculado no servidor (faixa pela
  idade ou valor da diretoria) e somado no **valor total**. A inscrição nasce **confirmada**, com
  **código único**, e mostra uma **tela de sucesso** (pagamento **simulado**). No painel, a aba
  "Inscrições" tem a **lista de inscritos** (com participantes/valores, respostas e ação **Cancelar**)
  e o **Resumo** conta **inscritos** (participantes confirmados) e **arrecadação** de verdade. Acesso:
  público sem login se aberto ao público, senão exige login; após o prazo, o formulário trava.
- **Evento complexo — Lojinha Fase 4.1 (cadastro de produtos)**: a aba **"Lojinha"** do painel permite
  cadastrar **produtos** com **variações** (cada uma com seu **preço**) e **controle de estoque
  opcional** por produto (quando ligado, cada variação tem quantidade). Produto tem nome, descrição,
  **foto** opcional e "à venda" (liga/desliga). Cadastro em página dedicada com linhas de variação
  repetíveis; a coluna "Estoque" aparece só se "Controlar estoque" estiver marcado.
- **Evento complexo — Lojinha Fase 4.2 (comprar na página do evento)**: botão **"Comprar na lojinha"**
  na página do evento abre a **loja** (`/eventos/<id>/loja/`) com os produtos ativos, **quantidade por
  variação** e **total ao vivo**; ao finalizar (dados do comprador), o **pagamento é simulado**, gera
  **código**, **baixa o estoque** dos produtos que controlam e mostra tela de sucesso. Acesso igual ao
  evento (público sem login; só-membros com login); a loja fica aberta **enquanto o evento não
  terminou**. No painel, a aba "Lojinha" lista os **pedidos** (com itens e **cancelar** — devolve ao
  estoque) e o **Resumo** conta **"Vendas (lojinha)"** (entra em receitas/resultado).
- **Evento complexo — Lojinha: fluxo de pagamento online (simulado)**: a compra pela **página pública**
  do evento (cliente final, para chegar já pago e **evitar fila** na retirada) ganhou um passo de
  pagamento. Na loja, o **WhatsApp é obrigatório** (e-mail opcional) e os **dados do comprador são
  lembrados** no próprio aparelho (localStorage — celular e PC) para não redigitar em pedidos
  seguintes; a pessoa escolhe a **forma de pagamento** (**Pix** ou **Cartão de crédito**). Ao
  "Ir para o pagamento", abre a **tela de pagamento** (`/eventos/<id>/loja/pagamento/`): no **Pix**,
  a tela clássica com **QR Code (simulado/decorativo)** e **código "copia e cola"** com botão
  **Copiar**; no **cartão**, um aviso de que **em produção** haverá **redirecionamento ao Mercado
  Pago** (integração futura). O botão **"Simular pagamento aprovado"** confirma o pedido. O
  **`PedidoLoja` só é criado no banco após a aprovação** (enquanto pendente fica na **sessão** —
  sem pedido "pendente" nem estoque reservado por carrinho abandonado); só então baixa o estoque
  (revalidado) e mostra a **tela de sucesso melhorada** (lista dos itens, total e "Pago com Pix/
  Cartão"). O QR e o "copia e cola" são **simulados** (sem biblioteca externa); o pagamento real
  virá com o gateway. Escopo: **só a loja pública** (o PDV/balcão e a inscrição seguem como estavam).
- **Evento complexo — Lojinha Fase 4.3 (comprar junto da inscrição + pedir mais)**: no fim do
  formulário de inscrição há uma seção **opcional** "Quer levar algo da lojinha?" (quantidade por
  variação + subtotal ao vivo); ao confirmar, cria a inscrição **e** um **pedido vinculado** (mesma
  transação, baixa de estoque; se faltar estoque, nada é criado). As telas de sucesso (inscrição e
  pedido) trazem botão **"Comprar (mais) na lojinha"** para pedir mais facilmente. O pedido vinculado
  (`PedidoLoja.inscricao`) aparece na lista de pedidos e conta em "Vendas (lojinha)".
- **Evento complexo — Lojinha Fase 4.4a (PDV / balcão)**: tela **"PDV / Balcão"** (`/eventos/<id>/pdv/`,
  botão na aba Lojinha) para registrar vendas no dia: monta o pedido, escolhe **forma de pagamento**
  (**Dinheiro** com **valor recebido → troco automático**, Pix, Cartão, **Cortesia**), **vínculo
  opcional** a uma inscrição (rastreabilidade) e registra (baixa estoque; cortesia não soma em vendas).
  **Restrito ao Diretor** por ora.
- **Evento complexo — Lojinha Fase 4.4b (PDV inscrição + relatório)**: botão **"Nova inscrição
  (balcão)"** na aba Inscrições → tela onde o atendente faz a **inscrição presencial** e, opcional,
  **adiciona itens da lojinha**, tudo num **pagamento só** (forma + **troco** sobre o total combinado;
  **total ao vivo**). Cria a inscrição + pedido de lojinha vinculado; cortesia deixa grátis (baixa
  estoque). No **Resumo**, tabela **"Vendidos por produto"** (Qtd conta tudo, inclusive cortesia;
  Arrecadado só o dinheiro). Restrito ao Diretor por ora.
- **Evento complexo — Lojinha Fase 4.4c (operadores do evento) — CONCLUI a Lojinha**: o Diretor define,
  por evento (botão **"Operadores"** na aba Lojinha), quem opera o PDV: **diretoria selecionada** e/ou
  **ajudantes externos** (conta temporária com senha inicial **`1234`**, **troca obrigatória no 1º
  acesso**, **reset** pelo Diretor). O operador acessa a landing **"Operar"** (`/eventos/<id>/operar/`)
  → PDV de venda e/ou inscrição. O **ajudante externo** vê **só o(s) evento(s) dele** no menu e cai
  direto no "Operar". Menu lateral **centralizado** em `_menu.html`; middleware força a troca de senha.
- **Evento complexo — Fase 5 (Financeiro) — parte 1: extrato completo**: a aba **"Financeiro"** do
  painel deixou de ser "em breve" e virou o **extrato/prestação de contas** do evento. Mostra: o
  **Resultado** em destaque (**Entradas − Saídas = Resultado**, verde/vermelho, com selo Lucro/Prejuízo/
  Zerado); **resumos** em cards (**por fonte** — inscrições × lojinha; **por forma de pagamento** —
  dinheiro/Pix/cartão/cortesia/online, com quantidade; **por canal** — online × balcão; **saídas** —
  total de custos + botão que leva à aba Custos); a tabela **"Vendidos por produto"** (movida do
  Resumo); e o **Extrato** — lista **cronológica** de **todos** os lançamentos (cada inscrição, pedido e
  custo), com data, tipo (badge), código, forma, canal e valor (**+ verde** para entradas, **− vermelho**
  para saídas). **Cancelados aparecem** no extrato (riscados, com selo "cancelado") para auditoria, mas
  **não entram nos totais** (só contam confirmados; cortesia soma R$ 0). Divisão de responsabilidades
  definida: **número/tabela mora no Financeiro; gráfico mora no Resumo/dashboard**. Custos continuam
  sendo **cadastrados** na aba Custos (o Financeiro só consolida).
- **Evento complexo — Fase 5 (Financeiro) — parte 2: Resumo/dashboard**: a aba **"Resumo"** virou um
  **dashboard** visual e didático. Tem: **KPIs repaginados** (ícones; Receitas em verde, Custos em
  vermelho, Resultado em destaque verde/vermelho); **gráficos em CSS/SVG puro, sem bibliotecas** —
  **Receitas × Custos** (barras verde/vermelho + resultado), **Entradas por forma de pagamento** e
  **Inscritos por faixa etária** (barras azul, com valor rotulado); e um painel **"Aventureiros do clube
  neste evento"** com um **donut** ("X de Y inscritos", %) e duas listas — **Inscritos** e **Ainda não
  inscritos** — dos aventureiros cadastrados no clube, com **busca em tempo real**. O casamento é por
  **conjunto de nomes** (tokens sem acento/caixa/conectores, helper `_nome_casa`): o participante casa com
  o aventureiro quando **todos os nomes digitados são cobertos** por tokens do nome cadastrado **e** isso
  aponta para **um único** aventureiro. O casamento é **ciente de iniciais** — um token de 1 letra casa
  com um token que começa por ela (ex.: "Alice **Z** Moreira" casa com "Alice **Zanatta** Moreira") — e,
  quando um nome curto serve para mais de um, **desambigua pelo sobrenome do responsável** (ex.: "Beatriz"
  + responsável "…Staine" → "Beatriz Gonçalves Staine"). Se ainda restar mais de um, vira **"a conferir"**
  — e agora a tela **lista** cada caso (participante + inscrição + os candidatos), em vez de só um contador.
  Ainda é **melhor esforço** (inscrição guarda nome livre) — o vínculo exato/manual pode vir depois. A
  cobertura conta **só aventureiros ativos** (os inativos/desligados saem do total do clube). A aba **Inscrições** ganhou uma **busca** sobre a lista (por responsável/participante) para
  responder "fulano se inscreveu?" (quando não acha, **a lista some** e aparece só "nenhuma inscrição
  encontrada"). Cor segue a regra: barras de magnitude em **um tom** (azul) e status (verde/vermelho)
  sempre com **rótulo** (cor nunca é a única pista).
- **Evento complexo — Fase 5.3 (Cupons de desconto)**: aba **"Desconto"** no painel (Diretor) para
  **gerar cupons** — informa a **% de desconto**, a **quantidade** (stepper − / +, **até 5 por vez**; ao
  passar de 5, toast "no máximo 5 cupons por vez") e a **faixa etária** a que o cupom se aplica (ou
  "qualquer faixa"). A **lista** mostra cada cupom com a **faixa**, o **percentual** e o **status**
  (Disponível / "Usado por FULANO · −R$ X") e permite remover os não usados. O cupom vale **só para
  inscrição** (não na lojinha) e é de **uso único**.
  - **Cupom por participante**: nos formulários de inscrição (**online** e **balcão/PDV**) cada
    participante tem seu **próprio campo de cupom** — o desconto vale **só para aquele participante** (o
    usuário escolhe em quem aplicar). Pode haver mais de um cupom por inscrição (um por participante).
  - **Validação ao vivo**: ao digitar/sair do campo, o sistema valida no servidor (endpoint JSON
    `evento_cupom_validar`, que **não grava nada**) e mostra o **toast padrão** — verde quando aplicado
    (com o **desconto em R$**) ou vermelho quando inválido. O **total** já **abate** o desconto na hora e
    um resumo mostra **"Cupons: −R$ X"** (vale para online **e** balcão).
  - **Faixa etária**: se o cupom é restrito a uma faixa e a idade do participante não casar, aparece o
    erro "**Cupom é só para <faixa>**" (no ao vivo e ao enviar). **Cortesia** (balcão) ignora o cupom.
  - **Uso único**: o cupom só é marcado como usado ao **confirmar** a inscrição (o servidor revalida —
    não há cupom "reservado" por formulário aberto). Guarda quem usou, **qual participante**, valor e
    vínculo à inscrição; aparece na inscrição (painel) e na tela de sucesso. Models `CupomDesconto.faixa`
    e `.participante` (migration `0015`; base era a `0014`).
- **Evento complexo — Fase 5.4 (Check-in + Retirada: console "Dia do evento")**: tela **"Dia do evento"**
  (`/eventos/<id>/dia/`, botão na barra de abas do painel e na landing "Operar"), aberta ao **Diretor e
  aos operadores** do evento. Serve para o dia do evento: por **família** (inscrição confirmada), lista os
  **participantes** com o **check-in** (Marcar chegada ↔ ✅ Chegou) e os **itens da lojinha comprados**
  com a **retirada** (Não entregue / Parcial (x/y) / ✅ Entregue). Os pedidos são casados à inscrição por
  **vínculo direto** (`PedidoLoja.inscricao`) ou **mesma conta única** (mesma regra do painel; helper
  `_casar_pedidos_inscricoes`); os **pedidos avulsos** (passantes, sem dono) aparecem numa **seção
  separada**. Tem **resumo do dia** (check-in X/Y + retiradas X/Y) e **busca** em tempo real
  (responsável/participante/código).
  - **5.4a** (só leitura): os campos de modelo e a tela de consulta. Novos campos:
    `ParticipanteInscricao.presente`/`presente_em`/`presente_por` e `ItemPedidoLoja.quantidade_entregue`/
    `entregue_em`/`entregue_por` (props `entregue`/`entrega_parcial`/`status_entrega`; migration **0016**).
  - **5.4b** (marcar): dá para **marcar check-in por participante** e **entrega por unidade** direto na
    tela, **sem recarregar** — o **selo é clicável** (entrega/desfaz tudo) e itens com mais de 1 têm
    **stepper − x/y +** (entrega parcial). Endpoints JSON `evento_checkin` e `evento_entrega` (POST,
    `@operador_required`, validam que o participante/item é do evento e de inscrição/pedido **confirmado**,
    limitam a entrega a 0..quantidade) atualizam a linha e o **resumo do dia** ao vivo; guardam **quem
    marcou e quando** (`presente_por`/`presente_em`, `entregue_por`/`entregue_em`). Parcial: `_dia_entrega.html`
    (parcial reutilizado nas duas seções) + `evento_dia.js` (fetch com `X-CSRFToken`).
  - **5.4c** ("vai levar agora?" no balcão): tanto o **PDV de vendas** (`evento_pdv`) quanto o **PDV de
    inscrição** (`evento_pdv_inscricao`) têm um checkbox **"Entregar os itens agora"** (marcado por
    padrão). Marcado → o pedido já nasce **entregue** (`quantidade_entregue = quantidade` + quem/quando);
    desmarcado → itens ficam **pendentes** para retirar depois no console. Implementado com o parâmetro
    `entregar_agora` no helper `_criar_pedido` (usado pelos dois PDVs).
  - **5.4d** (contadores no painel — encerra a Fase 5.4): a aba **Resumo** tem o painel **"📋 Dia do
    evento"** com **check-in** (presentes X/Y) e **retiradas** (itens entregues X/Y) + botão **"Abrir
    console"** (só quando há participantes/itens) — helper `_resumo_dia` reusado no contexto do painel
    (`dia`). **Guarda de exclusão**: o evento complexo já é protegido (não exclui com inscrições/pedidos —
    cobre presença/entrega); guarda por presença em **evento simples** fica como futuro (não há presença
    em evento simples ainda).
  - **Atalhos de balcão no console** (refino): o topo do "Dia do evento" tem os botões **"Nova inscrição
    (balcão)"** (`evento_pdv_inscricao`) e **"Vender na lojinha"** (`evento_pdv`) — para o atendente
    vender/inscrever sem sair da tela. Gates: inscrição enquanto o evento não terminou; venda quando a loja
    está aberta e há produtos ativos (contexto `pode_inscrever`/`pode_vender`). Os atalhos passam
    **`?de=dia`**; nas telas de PDV o botão **Voltar** então retorna ao **"Dia do evento"** (o `de` é
    preservado no redirect após registrar).
  - **Barra de abas em card** (refino): a `.painel-abas` virou um card/toolbar (fundo/borda/cantos), aba de
    seção ativa **preenchida** em azul e **divisor** antes das abas de ação — deixa claro que são os botões
    do painel.
- **Evento complexo — Compras da lojinha por inscrição**: na aba **Inscrições** do painel, cada inscrito
  mostra (ao expandir) um bloco **"Compras na lojinha"** com os pedidos daquela pessoa — casados por
  **vínculo direto** (`PedidoLoja.inscricao`) **ou pela mesma conta logada** (`pedido.usuario ==
  inscricao.usuario`, só quando o responsável tem **uma** inscrição no evento, para não atribuir errado).
  Cada pedido lista os itens e o valor; os da mesma conta ganham a etiqueta "· mesma conta". Mostra o
  **Total geral (inscrição + lojinha)** e uma **pílula 🛒** no topo com o gasto na lojinha. Pedidos
  **avulsos** (passante, sem conta/vínculo) não são atribuídos e continuam só na aba **Lojinha**.
- Na lista de Eventos, os cards têm **altura limitada** (título/descrição em até 2 linhas) e **clicar no
  card** (fora dos botões) abre um **modal de visualização** com todos os dados do evento (só leitura).
  Valores monetários usam o filtro `moeda` (`core/templatetags/formato.py`) → `R$ 1.500,00`.
- Logo do clube exibido no topo da tela de login (com fallback "CA" caso não carregue).
- Ao finalizar o cadastro inicial, o usuário é **autenticado automaticamente** (login real) e
  levado à tela de sucesso; "Ir para a tela inicial" abre `/inicio/` já logado.
- Fluxo de cadastro de aventureiro em `/cadastro/`: wizard de 7 etapas (conta, ficha de inscrição,
  responsáveis, ficha médica, declaração médica, autorização de imagem, revisão), com barra de
  progresso, campos condicionais, upload/preview de foto e tela de sucesso em `/cadastro/sucesso/`.
- Link "Cadastre-se" na tela de login (entre "Entrar" e "Esqueci minha senha"), em estilo
  discreto de link de texto (levemente maior que "Esqueci minha senha").
- Ao finalizar o cadastro, cria o `User` do Django e salva Aventureiro + FichaMedica + AutorizacaoImagem.
- Cadastro de **múltiplos aventureiros na mesma conta**: a tela de sucesso mostra o nome cadastrado e
  oferece "Cadastrar outro aventureiro" e "Ir para a tela inicial". A opção leva a
  `/cadastro/novo-aventureiro/` (wizard de 6 etapas, sem "Conta de acesso"), que vincula o novo
  aventureiro ao usuário logado (`request.user`); como retaguarda, ainda aceita o usuário guardado
  na sessão (`cadastro_usuario_id`). Sem nenhum dos dois, redireciona para o login.
- Nesse fluxo, é possível reaproveitar os dados de pai, mãe e responsável legal do último cadastro
  marcando uma opção; os campos são preenchidos automaticamente e podem ser editados antes de finalizar.
- Comando de gerenciamento `criar_dados_teste` para popular o banco local com uma conta de teste
  (`teste_responsavel` / `123456`) e 2 aventureiros completos (ficha de inscrição, ficha médica,
  autorização de imagem e fotos 3x4 fictícias geradas com Pillow: `lucas_teste.png`/`ana_teste.png`).
  Idempotente (pode rodar várias vezes); as fotos só são regeradas quando estão faltando ou apontam
  para arquivo inexistente — se já estiverem corretas, são mantidas.
- Comando de gerenciamento `importar_migracao` para **migrar os cadastros do sistema antigo** a partir
  do pacote exportado (pasta com `dados_json/` e `arquivos/`). Traz **apenas** os dados de cadastro
  ("cadastre-se"): a conta de acesso (login com **hash de senha preservado** → o responsável continua
  logando com a mesma senha), os dados de **pai, mãe e responsável legal**, o **endereço**, os dados de
  cada **aventureiro**, a **ficha médica**, o **termo de autorização de imagem** e a **foto** de cada
  aventureiro. **Não** importa: diretoria, financeiro, eventos, loja, whatsapp, assinaturas, nem
  responsáveis sem nenhum aventureiro vinculado; pula um registro-lixo de teste do sistema antigo.
  Uso: `python manage.py importar_migracao --origem "<pasta>"` (com `--dry-run` para simular).
  Idempotente (reaproveita o login pelo username; pula aventureiro já existente por usuário+nome).
  Primeira execução (2026-07-03): **35 logins + 37 aventureiros** (com ficha médica, termo e foto).
  As fotos importadas são dados **reais** dos membros e ficam **apenas** em `media/` (git-ignored) —
  **nunca** versionadas. Os dados pessoais de menores (JSON/CSV/zip da exportação) **não** vão ao Git.
- **Migração de eventos (por evento, com conciliação bancária)**: o **"ACAMPAMENTO 2026"** (evento 7 do
  sistema antigo) foi migrado para o **evento 60** — dados do evento + 5 faixas + **24 inscrições reais**
  com **valor recebido conciliado contra o extrato** (Mercado Pago): R$ 4.597,41 (14 Pix + 3 cartão + 7
  cortesia/diretoria), `forma_pagamento` e **data original** preservadas. Feito por scripts one-off
  (parser do extrato + matcher + Artifact de revisão), sem comando versionado (conciliação é manual). Os
  **extratos bancários** (`EXTRATOS/`) são dados financeiros e **não** vão ao Git (`.gitignore`). Também
  migrados os **9 custos** do evento (R$ 4.723,50) com nome/valor/data — **Resultado do acampamento =
  −R$ 126,09** — e os **9 comprovantes anexados** (contrato da chácara, invoices, fotos das compras),
  trazidos do export atualizado ("com_arquivos") e copiados para `media/eventos/custos/` (git-ignored).
  Também migrado o **"Passaporte da Diversão"** (evento 6 antigo → **evento 62**): faixas (1-4=R$20 /
  5-12=R$40), **51 inscrições / 69 crianças** (R$ 2.500), **4 produtos da lojinha com fotos** + 13
  variações, **vendas R$ 1.825,50** (229 itens; só pagas e não-teste) com **retirada por item** preservada,
  e custos R$ 607,12 (3 do antigo R$ 183,39 + **taxa de cartão/Pix do Mercado Pago R$ 423,73** lançada como
  custo). **Resultado = R$ 3.718,38**. Conferido contra o **relatório PDF do sistema antigo** (bruto/loja/
  inscrições/faixas/líquido idênticos). Valores corretos do antigo (sem conciliação bancária).
  **Cuidado aprendido**: no sistema antigo a **inscrição é um item do pedido da loja** ("Inscricao do
  evento") — não contar como venda; e a **idade** pode vir como texto ("6 anos") — parsear o número.
  Próximo: migrar os eventos restantes (ids 2/4/5 "Reunião do Clube"), um a um.
- **Perfis de acesso** (grupos nativos do Django): **Diretor, Responsável, Professor, Tesoureiro,
  Secretário**. Conceito: "Diretoria" é o grupo de integrantes do clube (diretor, secretário,
  tesoureiro, professor); "Responsável" é o lado dos pais. Uma pessoa pode ter os dois lados e
  alternar o perfil ao logar (lógica de alternância a implementar). Por enquanto, só o **Diretor**
  receberá permissões nas telas; os demais perfis existem sem permissões (definir depois).
- Comando de gerenciamento `configurar_perfis`: cria os 5 perfis e o **usuário diretor inicial**
  (`Fabiano` / senha `1234` — senha de desenvolvimento, trocar em produção), vinculado ao perfil
  Diretor. Idempotente. Uso: `python manage.py configurar_perfis`.

## Padrão visual da tela de login (atual)
- Fundo com gradiente azul→verde animado (movimento lento) e formas circulares desfocadas flutuando.
- Card com glassmorphism suave (fundo translúcido + `backdrop-filter`), sombra elegante e animação de entrada.
- Brilho radial suave atrás do logo, dando profundidade; logo com leve `drop-shadow`.
- Título em destaque com linha decorativa (gradiente azul→verde) abaixo do subtítulo.
- Campos com foco realçado (borda azul + halo) e leve elevação.
- Botão "Entrar" com gradiente, efeito de brilho deslizante no hover, elevação e clique.
- Link "Esqueci minha senha" discreto, com sublinhado animado no hover.
- Animações desativadas automaticamente quando o usuário prefere menos movimento (`prefers-reduced-motion`).
- Testado visualmente em mobile (390px, sem overflow) e desktop (1280px).

## Padrão visual da tela interna (atual)
- Menu lateral fixo à esquerda no desktop (gradiente azul), com logo, nome do sistema
  e itens de menu; item ativo destacado em verde.
- No celular, o menu vira gaveta recolhível: barra superior com botão hambúrguer,
  gaveta deslizante e overlay que fecha ao tocar fora.
- Rodapé da barra com o nome do usuário logado e o botão "Sair".
- Área principal "Meus Dados": card do **Responsável** no topo (expansível, com botão Editar) e
  a seção **Aventureiros cadastrados** com cards clicáveis (foto 3x4 destacada, pílulas de resumo,
  status de ficha/autorização e seções recolhíveis com todos os detalhes).
- Pílulas/etiquetas para informações rápidas; cards com sombras suaves, bordas arredondadas
  e hover leve; painéis e seções recolhíveis via `<details>/<summary>` nativos (sem JS).
- Mensagens de feedback via framework de messages do Django, exibidas como **toasts flutuantes**
  (canto superior direito / topo no celular) que somem sozinhos ou ao clicar. Toda ação relevante do
  módulo de eventos gera uma notificação (sucesso/erro/info).
- Fundo claro com detalhes decorativos radiais suaves; animação de entrada dos cards.
- Suporte a `prefers-reduced-motion`. Layout responsivo (mobile first): cards empilhados no
  celular e em grade de 2 colunas em telas largas; sem overflow horizontal (validado).

## Models existentes
- `Aventureiro` — ficha de inscrição + dados dos responsáveis (pai, mãe, responsável legal);
  FK `usuario` (um usuário pode ter vários aventureiros); `data_inscricao` e `criado_em` automáticos.
- `FichaMedica` — OneToOne com `Aventureiro` (plano de saúde, doenças, alergias, condições, tipo sanguíneo).
- `AutorizacaoImagem` — OneToOne com `Aventureiro` (dados do menor e do responsável para o termo).
- `Evento` — evento do clube (`tipo` simples/inscrição, nome, local, descrição, data, **data_fim**,
  horário de início/término, `criado_por` FK User, `criado_em`). Campos de inscrição (evento complexo):
  **`inscricao_aberta_publico`**, **`inscricao_limite`** (prazo) e **`valor_diretoria`**. Métodos
  `fim_datetime()`, `prazo_inscricao()` e `inscricoes_abertas()`. Migrations `0002`, `0003`, `0004`.
- `CustoEvento` — custo/despesa de um evento (FK `evento`, nome, descrição, valor, comprovante,
  `criado_por`). Migration `0003_evento_data_fim_custoevento`.
- `FaixaEtariaPreco` — faixa etária com valor de inscrição, por evento (FK `evento`, rótulo,
  idade_min, idade_max, valor, ordem). Migration `0004`.
- `CampoInscricao` — campo personalizado do formulário de inscrição, por evento (FK `evento`, rótulo,
  tipo, opções, obrigatório, **por_participante**, ordem). Migrations `0005`, `0007`.
- `PerfilUsuario` — OneToOne com User (`precisa_trocar_senha`, usado pelas contas temporárias;
  **`whatsapp_principal_origem`** = pai/mãe/resp legal, para onde vai o código de recuperação, mig.
  **0020**). E `OperadorEvento` — quem opera o PDV de um evento (FK `evento`, FK `usuario`, `externo`). Migration `0013`.
- `Inscricao` — inscrição num evento (FK `evento`, FK `usuario` opcional, dados do responsável, código
  único, status, **origem** online/pdv, **forma_pagamento**, **valor_recebido**, **registrado_por**,
  valor_total; props `total_com_loja`/`troco`). Migration `0012`. `ParticipanteInscricao` (nome, idade, eh_diretoria,
  faixa, valor + **check-in**: `presente`/`presente_em`/`presente_por`, mig. `0016`) e `RespostaInscricao` (FK `inscricao`, FK `participante` opcional, campo + rótulo
  snapshot + valor). Migrations `0006`, `0007`. Respostas de campos "por participante" têm
  `participante` preenchido; as de campos "uma vez" ficam com `participante` nulo.
- `ProdutoEvento` — produto da lojinha do evento (FK `evento`, nome, descrição, foto, controla_estoque,
  ativo, ordem) e `VariacaoProduto` (FK `produto`, nome, valor, estoque, ordem). Migration `0008`.
  O preço fica em cada variação; estoque só conta quando `controla_estoque` está ligado.
- `PedidoLoja` — pedido da lojinha (FK `evento`, FK `usuario` opcional, **FK `inscricao` opcional**,
  dados do comprador, código, status, **origem** online/pdv, **forma_pagamento**, **valor_recebido**,
  **registrado_por**, valor_total; property `troco`) e `ItemPedidoLoja` (FK `pedido`, FK `variacao`
  opcional + snapshots de nome, quantidade e valores + **retirada por unidade**:
  `quantidade_entregue`/`entregue_em`/`entregue_por`, props `entregue`/`entrega_parcial`/`status_entrega`,
  mig. `0016`). Migrations `0009`, `0010`, `0011`.
- `CupomDesconto` — cupom de desconto de **inscrição** (FK `evento`, `codigo` único, `percentual`,
  `ativo`, FK **`faixa`** opcional = faixa etária a que se aplica, FK `inscricao` opcional = onde foi
  usado, FK **`participante`** opcional = quem usou, `usado_por`, `valor_desconto`, `usado_em`,
  `criado_por`; property `usado`). Uso único; aplica em **1 participante** (o que o usuário escolher,
  digitando o código na linha dele). Migrations `0014` (base) e **`0015`** (`faixa` + `participante`).
- `Aventureiro.ativo` (BooleanField, default True; mig. **0018**) — aventureiro ativo/inativo (desligado).
  Ao desligar, a conta (`usuario`) é desativada se não sobrar nenhum aventureiro ativo. A Presença lista só
  aventureiros ativos.
- `PresencaEvento` — presença de um **aventureiro** do clube num **evento** (FK `evento` related_name
  `presencas`, FK `aventureiro`, `marcado_em`, `marcado_por`; `unique_together` evento+aventureiro). A
  **existência do registro = presente**. Independente do check-in de inscrição do evento complexo. Usado
  pelo módulo **Presença** e pela **guarda de exclusão** de eventos. Migration **0017**.
- `WhatsappConfig` — configuração do gateway **W-API** (**linha única/singleton** via `get_solo()`,
  `pk=1`). Campos: `instance_id`, `token`, `base_url` (default `https://api.w-api.app/v1`),
  `atualizado_por`/`atualizado_em`. Propriedades: `configurado` (tem ID + token) e `token_mascarado`
  (só os últimos 4 dígitos). Usado pelo módulo **WhatsApp**. Migration **0019**.
- **Loja do Clube** (loja oficial, independente da lojinha de evento; mig. **0021**):
  - `ProdutoLoja` — produto da loja (nome, descrição, foto, `composto`, `controla_estoque`, `ativo`, ordem).
    Props `variacoes_ativas`, `preco_minimo`, `preco_base` (estimativa "a partir de" somando obrigatórios).
  - `GrupoLoja` — grupo de variações de um produto (FK `produto`, nome, `modo` = `unica`/`itens`,
    `obrigatorio`, `orientacao`, ordem). Produto simples = 1 grupo padrão.
  - `VariacaoLoja` — opção de um grupo (FK `grupo`, nome, valor, estoque, `obrigatorio` [itens], `ativo`,
    ordem). Props `rotulo`, `esgotado`.
  - `CompraLoja` — compra (FK `usuario`, dados do comprador, código `LC…`, status, `forma_pagamento`,
    `valor_total`; props `status_entrega`/`falta_entregar_total`). `ItemCompraLoja` — item (FK `compra`/
    `produto`/`variacao`/`aventureiro` + snapshots + `quantidade`/valores + `kit` = agrupa itens de um kit +
    **entrega** `quantidade_entregue`/`entregue_em`/`entregue_por`, props `entregue`/`status_entrega`/
    `falta_entregar`, mig. **0023**). Pedidos migrados do sistema antigo usam código `LM<id>`.
  - `FotoProdutoLoja` — foto da **galeria** de um produto (FK `produto`, `imagem`, `ordem`; a 1ª é a capa,
    via property `ProdutoLoja.capa`). Mig. **0022**. Suporta várias fotos + lightbox na vitrine.

## Funcionalidades incompletas / não implementadas
- Recuperação de senha ("Esqueci minha senha") — **IMPLEMENTADA** pelo WhatsApp (código de 4 dígitos).
  Falta permitir que o **responsável logado** altere o próprio WhatsApp principal (hoje só o Diretor).
- Edição dos dados do aventureiro pela área logada — hoje "Meus Dados" é somente visualização.
- Permissões / perfis de usuário — NÃO implementados.
- Validação avançada de CPF — NÃO implementada (deixada para o futuro).
- Envio de e-mail — NÃO implementado.

## Próximas etapas previstas
- **🎉 Lojinha (Fase 4) concluída** (produtos, comprar na página, junto da inscrição, PDV de vendas,
  PDV de inscrição, operadores).
- **Fase 5 — Financeiro**: parte 1 (**extrato** na aba Financeiro), parte 2 (**Resumo/dashboard**:
  KPIs, gráficos CSS/SVG, cobertura do clube + buscas) e parte 3 (**cupons de desconto** — por
  participante, com faixa, geração em lote e validação ao vivo) **CONCLUÍDAS**. **Fase 5.4 (Check-in +
  Retirada) CONCLUÍDA** (5.4a console + campos; 5.4b marcar check-in/entrega; 5.4c "entregar agora" no
  balcão; 5.4d contadores do dia no painel). Guarda de exclusão por presença em **evento simples** fica
  como item futuro (depende de presença em evento simples, que não existe). **Próximos:** pagamentos reais
  (gateway) e loja oficial do clube (uniformes, separada).
- **Depois**: pagamentos reais (gateway); loja oficial do clube (uniformes) — separada da lojinha.
- **Depois**: pagamentos reais (gateway); loja oficial do clube (uniformes) — separada da lojinha de evento.
- Possíveis refinos das inscrições: gating de "diretoria" por perfil real, editar inscrição, exportar
  lista de inscritos, e-mail de confirmação.
- **Evento complexo — Fase 2.4**: inscrição de fato (participantes por faixa/diretoria, pagamento
  simulado, código), lista de inscritos no painel e contagem/arrecadação no dashboard.
- (A definir) Permitir editar os dados do aventureiro pela área logada.
- (A definir) Permitir ao responsável logado escolher o próprio WhatsApp principal (recuperação).

## Apps existentes
- `config` — projeto Django (settings, urls, wsgi, asgi).
- `core` — app principal (views de login, tela inicial e cadastro; models de aventureiro).

## Templates existentes
- `templates/core/login.html` (login real, com mensagem de erro)
- `templates/core/inicio.html` (área "Meus Dados": card do responsável + cards clicáveis dos aventureiros)
- `templates/core/editar_responsavel.html` (edição do responsável legal)
- `templates/core/usuarios.html` (responsáveis, aventureiros e vínculos, com pesquisa e modal de detalhes)
- `templates/core/eventos.html` (lista de eventos + modal de escolha de tipo)
- `templates/core/evento_form.html` (formulário do evento simples)
- `templates/core/evento_complexo_form.html` (criação do evento complexo)
- `templates/core/evento_painel.html` (painel/dashboard do evento complexo)
- `templates/core/evento_pagina.html` (página do evento — pública/interna, com botão de inscrever)
- `templates/core/evento_inscrever.html` (formulário de inscrição) e `evento_inscricao_sucesso.html`
- `templates/core/evento_produto_form.html` (cadastro/edição de produto da lojinha)
- `templates/core/evento_loja.html` (loja/carrinho do evento), `evento_pagamento.html` (tela de
  pagamento simulada: Pix com QR/copia-cola ou cartão) e `evento_pedido_sucesso.html`
- `templates/core/evento_pdv.html` (PDV / balcão de vendas) e `evento_pdv_inscricao.html` (PDV inscrição)
- `templates/core/_loja_itens.html` (parcial: itens da lojinha para escolher — loja, inscrição e PDV)
- `templates/core/_menu.html` (parcial: menu lateral central, usado por todas as telas internas)
- `templates/core/evento_operar.html` (landing do operador), `evento_operadores.html` (gerência) e `trocar_senha.html`
- `templates/core/evento_dia.html` (console "Dia do evento": check-in + retirada) e `_dia_entrega.html`
  (parcial: controle de retirada por unidade de um item — selo clicável + stepper)
- `templates/core/presenca_selecionar.html` (escolher evento) e `presenca_evento.html` (folha de presença:
  lista de aventureiros com foto + marcar + modal da foto ampliada)
- `templates/core/whatsapp.html` (módulo WhatsApp: configurar instância W-API + enviar mensagem de teste)
- `templates/core/recuperar_cpf.html`, `recuperar_codigo.html`, `recuperar_nova_senha.html` (recuperação
  de senha em 3 etapas; **envio por AJAX** via `ajax_form.js` — `form[data-ajax-toast]` —, com **toast
  padrão**; erro não recarrega a página)
- `templates/core/_menu_eventos.html` (parcial: seção "Eventos ativos" do menu, para todos os perfis)
- **Loja do Clube**: `loja.html` (abas Gerenciar + vitrine/carrinho), `loja_produto_form.html` (cadastro
  com grupos/variações), `loja_produto.html` (configurador + carrinho + aviso soft), `loja_pagamento.html`
  (pagamento simulado), `loja_sucesso.html`; parciais `_loja_grupo.html` e `_loja_var_linha.html`
- `templates/core/_participante_linha.html` e `_variacao_linha.html` (parciais de linha repetível)
- `templates/core/_aventureiro_detalhe.html` (parcial com o detalhe completo do aventureiro)
- `templates/core/cadastro.html` (wizard de cadastro)
- `templates/core/cadastro_sucesso.html`
- `templates/core/_campo.html` e `templates/core/_campo_check.html` (parciais de campo reutilizáveis)
- `templates/core/_dado.html` (parcial rótulo+valor usada em "Meus Dados")

## Arquivos CSS existentes
- `static/css/base.css` — regras globais de interface (linkado em todas as telas, **antes** do CSS
  da página). Torna o texto de interface **não selecionável** (sem cursor de texto/caret fora de
  campos digitáveis); mantém selecionáveis os campos de formulário e os valores de dados
  (`.dado-valor` / `.selecionavel`). Também hospeda os **componentes reutilizáveis** de **modal** (janela
  suspensa) e de **notificações/toasts** (`.mensagens`/`.mensagem`, com fallback de cores) — para o toast
  valer em qualquer página, inclusive as públicas do login/recuperação. (Antes o toast ficava no `inicio.css`.)
- `static/css/eventos.css` — tela de Eventos (lista, cards, formulário e cards de escolha de tipo).
- `static/css/login.css`
- `static/css/inicio.css`
- `static/css/cadastro.css`
- `static/css/usuarios.css` (complementa `inicio.css` na tela "Usuários")
- `static/css/presenca.css` — módulo Presença (seletor de evento, folha com foto grande + botão marcar,
  foto ampliada no modal)
- `static/css/whatsapp.css` — módulo WhatsApp (cards de configuração e de envio; inputs próprios;
  paleta azul/verde; mobile-first)
- `static/css/recuperar.css` — recuperação de senha (indicador de etapas, campo do código grande,
  link de reenvio); complementa `login.css`. As notificações usam o **toast padrão** (CSS em `base.css`).
- `static/css/loja.css` — **Loja do Clube** (abas, cards de gerenciamento, vitrine em grade, carrinho,
  cadastro de grupos/variações, configurador do produto e telas de pagamento); mobile-first; paleta azul/verde.

## Arquivos JavaScript existentes
- `static/js/cadastro.js` — wizard de etapas (numeração e índices calculados dinamicamente, servindo
  tanto ao cadastro de 7 etapas quanto ao de 6 etapas), barra de progresso, campos condicionais,
  preview da foto, atalhos (copiar pai/mãe para responsável legal), reaproveitamento dos dados dos
  responsáveis no cadastro de novo aventureiro, revisão e validação dos aceites.
- `static/js/inicio.js` — menu recolhível no celular; painéis `<details>` de "Meus Dados" (fechar ao
  clicar fora / abrir outro / `Esc`); e o **módulo único de toasts** do sistema: move `.mensagens` para
  o `<body>`, auto-fecha (~4,5s, igual à barra de progresso), fecha ao clicar e expõe
  **`window.mostrarToast(texto, tipo)`** para criar toast pelo JS (ex.: "copiado!"). É seguro em
  qualquer página (cada bloco tem guarda de elemento), por isso é carregado também nas páginas públicas
  do evento (loja, pagamento, sucesso, página do evento, inscrição) e nas telas de **recuperação de
  senha**. O CSS do toast vive no `base.css` (componente reutilizável).
- `static/js/usuarios.js` — pesquisa em tempo real na tela "Usuários" e o **modal** de dados
  completos (clona o detalhe do card, expande as seções e fecha no X/fora/Esc).
- `static/js/eventos.js` — abre/fecha o modal de escolha do tipo de evento (X/fora/Esc).
- `static/js/evento_painel.js` — abas do painel do evento complexo + modais (custo, faixa, campo);
  botões `[data-aba-ir]` (trocar de aba); e a **busca em tempo real** da cobertura do clube e da lista de
  inscrições (helper `ligarBusca`, padrão do `usuarios.js`).
- `static/js/evento_inscrever.js` — linhas de participante (adicionar/remover) + campos por participante.
- `static/js/evento_produto.js` — linhas de variação (adicionar/remover) + mostrar/ocultar estoque.
- `static/js/qtd_stepper.js` — botões +/- de quantidade nas telas de compra (dispara o recálculo).
- `static/js/evento_loja.js` — total ao vivo da loja/inscrição conforme as quantidades.
- `static/js/loja_comprador.js` — lembra os dados do comprador (nome/WhatsApp/e-mail) no localStorage
  e autopreenche na loja pública (celular e PC).
- `static/js/evento_pagamento.js` — botão "Copiar" do código Pix na tela de pagamento (com fallback);
  o feedback usa o toast padrão via `window.mostrarToast`.
- `static/js/evento_pdv.js` — PDV vendas: total, forma de pagamento e troco.
- `static/js/evento_insc_cupom.js` — inscrição (online **e** balcão): total ao vivo (faixa/diretoria +
  lojinha), **cupom por participante** (validação ao vivo contra o servidor + toast + abate do total) e
  troco no balcão. Substituiu o antigo `evento_pdv_inscricao.js`.
- `static/js/evento_dia.js` — console "Dia do evento": busca em tempo real (responsável/participante/
  código) + **ações de marcar** (check-in por participante e entrega por unidade via fetch/JSON com
  `X-CSRFToken`, atualização inline dos selos/stepper e do resumo do dia).
- `static/js/presenca.js` — módulo Presença: marcar/desmarcar (fetch/JSON + `X-CSRFToken`, atualiza botão e
  contador), **modal da foto** ampliada e busca em tempo real. Ao marcar/desmarcar com sucesso, mostra o
  **toast** padrão ("<nome> — presente ✅" / "<nome> — ausente"); toast de erro em falha.
- `static/js/whatsapp.js` — módulo WhatsApp: **prévia ao vivo** do telefone normalizado, botão
  **mostrar/ocultar** token e **envio AJAX** (fetch/JSON + `X-CSRFToken`) com o **toast** padrão de
  sucesso/erro.
- `static/js/ajax_form.js` — **componente genérico**: envia qualquer `form[data-ajax-toast]` por
  **fetch**; a resposta é `{"redirect":url}` (navega) ou `{"msg","tipo"}` (só toast, sem recarregar).
  Assim o erro **repete a notificação** sem recarregar a página. Usado no **login** (senha errada) e nas
  telas de **recuperação de senha**. Fallback: sem JS, POST normal.
- `static/js/loja.js` — **Loja**: alternância das abas (Gerenciar/Loja), confirmação de ações destrutivas
  (`form[data-confirmar]`) e atalho para o carrinho.
- `static/js/loja_produto_form.js` — cadastro de produto: alternar simples/composto, adicionar/remover
  **grupos** e **opções** (índices únicos), mostrar/ocultar estoque e a coluna "obrig." por modo do grupo.
- `static/js/loja_produto.js` — configurador do produto na vitrine: **subtotal ao vivo**, **aviso soft** de
  itens obrigatórios (modal: continuar/voltar) e rascunho da seleção no localStorage (não perde ao recarregar).

## Rotas existentes
- `/` — tela de login com autenticação real (`core.views.login_view`, nome `core:login`).
- `/sair/` — logout (POST) (`core.views.sair_view`, nome `core:sair`).
- `/inicio/` — área "Meus Dados", protegida por `@login_required` (`core.views.inicio_view`, nome `core:inicio`).
- `/meus-dados/responsavel/editar/` — edição do responsável, protegida por login (`core.views.editar_responsavel_view`, nome `core:editar_responsavel`).
- `/usuarios/` — responsáveis, aventureiros e vínculos, **restrita ao Diretor** (`core.views.usuarios_view`, nome `core:usuarios`).
- `/usuarios/aventureiro/<id>/ativo/` — marca inativo/reativa um aventureiro (POST, Diretor; cascata na conta) (`core:aventureiro_toggle_ativo`).
- `/usuarios/conta/<id>/principal/` — define o **WhatsApp principal** da conta (pai/mãe/resp legal) p/ recuperação (POST, Diretor) (`core:usuario_principal`).
- `/eventos/` — lista de eventos, **restrita ao Diretor** (`core.views.eventos_view`, nome `core:eventos`).
- `/eventos/novo/` — cadastro de evento simples, **restrita ao Diretor** (`core.views.evento_novo_view`, nome `core:evento_novo`; aceita `?duplicar=<id>`).
- `/eventos/complexo/novo/` — cria evento complexo (`core.views.evento_complexo_novo_view`, nome `core:evento_complexo_novo`).
- `/eventos/<id>/excluir/` — exclui um evento (POST, Diretor), **só se vazio** (sem inscrições/pedidos) (`core.views.evento_excluir_view`, nome `core:evento_excluir`).
- `/eventos/<id>/` — painel do evento complexo (`core.views.evento_painel_view`, nome `core:evento_painel`).
  Se o evento não existir (ex.: link antigo de um evento excluído), **redireciona** para `/eventos/` com
  um toast informativo (em vez de 404).
- `/eventos/<id>/pagina/` — página do evento (pública se aberto ao público, senão exige login) (`core.views.evento_pagina_view`, nome `core:evento_pagina`).
- `/eventos/<id>/inscrever/` — formulário de inscrição (`core.views.evento_inscrever_view`, nome `core:evento_inscrever`).
- `/eventos/<id>/inscrever/sucesso/` — confirmação da inscrição (`core:evento_inscricao_sucesso`).
- `/eventos/<id>/inscricoes/<id>/cancelar/` — cancela inscrição (POST, Diretor) (`core:evento_inscricao_cancelar`).
- `/eventos/<id>/produtos/novo/`, `.../produtos/<id>/editar/` e `.../produtos/<id>/excluir/` — lojinha: cadastro/edição/remoção de produto (Diretor).
- `/eventos/<id>/loja/` — loja do evento (comprar), `.../loja/pagamento/` (tela de pagamento simulada:
  GET mostra Pix/cartão; POST simula a aprovação e cria o pedido), `.../loja/sucesso/` (confirmação) e
  `.../pedidos/<id>/cancelar/` (POST, Diretor).
- `/eventos/<id>/pdv/` — PDV / balcão de vendas da lojinha (Diretor por ora) (`core:evento_pdv`).
- `/eventos/<id>/pdv/inscricao/` — PDV: inscrição presencial + lojinha, pagamento combinado (`core:evento_pdv_inscricao`).
- `/eventos/<id>/operar/` — landing do operador (vender/inscrever) (`core:evento_operar`, operador ou Diretor).
- `/eventos/<id>/dia/` — console "Dia do evento": check-in dos participantes + retirada dos itens (`core:evento_dia`, operador ou Diretor).
- `/eventos/<id>/dia/checkin/` — marca/desmarca check-in de um participante (POST JSON, operador/Diretor) (`core:evento_checkin`).
- `/eventos/<id>/dia/entrega/` — registra a entrega de um item por unidade (POST JSON, operador/Diretor) (`core:evento_entrega`).
- `/eventos/<id>/operadores/` — gerência de operadores (Diretor); rotas POST de add diretoria/externo, reset e remover.
- `/trocar-senha/` — troca de senha (obrigatória no 1º acesso das contas temporárias) (`core:trocar_senha`).
- `/eventos/<id>/custos/novo/` e `/eventos/<id>/custos/<id>/excluir/` — adicionar/remover custo (POST).
- `/eventos/<id>/inscricoes/config/` — salva a configuração da inscrição (POST, `core:evento_inscricao_config`).
- `/eventos/<id>/inscricoes/faixa/novo/` e `/eventos/<id>/inscricoes/faixa/<id>/excluir/` — adicionar/remover faixa etária (POST).
- `/eventos/<id>/inscricoes/campo/novo/`, `.../campo/<id>/excluir/` e `.../campo/<id>/mover/` — adicionar/remover/reordenar campo do formulário (POST).
- `/eventos/<id>/descontos/novo/` e `/eventos/<id>/descontos/<id>/excluir/` — gerar (com quantidade/faixa) / remover cupom de desconto (POST, Diretor).
- `/eventos/<id>/cupom/validar/` — validação **ao vivo** de um cupom para um participante (GET, JSON; não grava) (`core:evento_cupom_validar`).
- `/presenca/` — módulo Presença: escolher o evento (Diretor) (`core.views.presenca_view`, nome `core:presenca`).
- `/presenca/<id>/` — folha de presença: lista de aventureiros com foto + marcar (`core:presenca_evento`).
- `/presenca/<id>/marcar/` — marca/desmarca presença de um aventureiro (POST JSON, Diretor) (`core:presenca_marcar`).
- `/whatsapp/` — módulo WhatsApp: configurar a instância W-API + enviar mensagem de teste (Diretor) (`core.views.whatsapp_view`, nome `core:whatsapp`).
- `/whatsapp/config/` — salva ID/token/URL base da instância (POST, Diretor; token vazio não sobrescreve) (`core:whatsapp_config`).
- `/whatsapp/enviar/` — envia uma mensagem pela W-API (POST JSON, Diretor; normaliza o telefone) (`core:whatsapp_enviar`).
- `/cadastro/` — cadastro inicial: conta + primeiro aventureiro (`core.views.cadastro_view`, nome `core:cadastro`).
- `/cadastro/novo-aventureiro/` — outro aventureiro na mesma conta (`core.views.cadastro_novo_aventureiro_view`, nome `core:cadastro_novo_aventureiro`).
- `/cadastro/sucesso/` — confirmação (`core.views.cadastro_sucesso_view`, nome `core:cadastro_sucesso`).
- `/recuperar-senha/` — recuperação de senha, etapa 1: CPF do responsável legal (`core:recuperar_senha`).
- `/recuperar-senha/codigo/` — etapa 2: digitar o código de 4 dígitos (`core:recuperar_senha_codigo`).
- `/recuperar-senha/reenviar/` — reenvia o código (POST, espera de 60 s) (`core:recuperar_senha_reenviar`).
- `/recuperar-senha/nova-senha/` — etapa 3: definir a nova senha 2× (`core:recuperar_senha_nova`).
- **Loja do Clube** (Diretor no menu; vitrine/carrinho `@login_required`):
  - `/loja/` — tela com abas Gerenciar/Loja (`core:loja`, Diretor).
  - `/loja/produto/novo/`, `/loja/produto/<id>/editar/`, `/loja/produto/<id>/excluir/` — CRUD de produto (Diretor).
  - `/loja/produto/<id>/` — página do produto na vitrine (configurar + adicionar ao carrinho) (`core:loja_produto`).
  - `/loja/carrinho/adicionar/`, `/loja/carrinho/remover/` — carrinho na sessão (POST).
  - `/loja/finalizar/` → `/loja/pagamento/` → `/loja/sucesso/` — checkout + pagamento simulado.
  - `/loja/compra/<id>/cancelar/` — cancela compra e devolve estoque (POST, Diretor).
  - `/loja/entrega/` — marca/desmarca entrega de um item (POST/JSON, Diretor). Aba "Vendas" = relatório.
- `/admin/` — Django admin (models de cadastro registrados).
- Em DEBUG, o Django serve os arquivos de mídia em `/media/`.

## Configurações importantes
- `DEBUG = True` (desenvolvimento).
- `ALLOWED_HOSTS = []` (desenvolvimento).
- Idioma: `pt-br`. Fuso horário: `America/Sao_Paulo`.
- Banco: SQLite (`db.sqlite3`), já com os models de cadastro migrados.
- `STATICFILES_DIRS` aponta para a pasta `static/`.
- `MEDIA_URL = "media/"` e `MEDIA_ROOT = BASE_DIR / "media"` (uploads, ex.: foto 3x4).
- `TEMPLATES DIRS` aponta para a pasta `templates/`.
- Autenticação: `LOGIN_URL = "core:login"`, `LOGIN_REDIRECT_URL = "core:inicio"`,
  `LOGOUT_REDIRECT_URL = "core:login"`.
- `SECRET_KEY` é de desenvolvimento (trocar em produção).
- Middleware próprio `core.middleware.TrocaSenhaObrigatoriaMiddleware` (após o de autenticação):
  força a troca de senha das contas temporárias de ajudantes.
- Requer `Pillow` (já instalado) para o `ImageField` da foto.

## Versionamento (Git)
- Repositório Git inicializado; branch principal: `main`.
- Remoto `origin`: https://github.com/fabianopolone123/PINHALJUNIOR2.0.git
- `.gitignore` configurado para Python/Django (ignora `.env`, `*.sqlite3`, ambientes virtuais, cache, `staticfiles/`, `media/`, etc.).
- `README.md` na raiz com descrição básica e apontando para a pasta `docs/`.
- `CLAUDE.md` na raiz: arquivo de contexto (guia rápido) que aponta para os docs oficiais.
- Regra obrigatória: após qualquer alteração, rodar `git add .`, criar commit descritivo em
  português do Brasil e fazer `git push` (ver `CODEX.md` e `docs/REGRAS_CODEX.md`).

## Observações importantes para continuação
- Não usar Bootstrap, Tailwind ou frameworks visuais externos (CSS é próprio).
- Manter responsividade mobile first e o padrão visual azul/verde já criado.
- Ao criar models, gerar as migrations correspondentes.
- Sempre atualizar `docs/ESTADO_ATUAL.md` e `docs/HISTORICO_ALTERACOES.md` após qualquer alteração.
- Ao final de cada alteração, versionar no Git (commit + push) conforme o fluxo obrigatório.
