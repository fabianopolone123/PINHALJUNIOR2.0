# CLAUDE.md — Contexto do projeto

Guia rápido para o assistente (e para devs). Leia também, obrigatoriamente, antes de alterar:
`CODEX.md`, `docs/README_PROJETO.md`, `docs/REGRAS_CODEX.md`, `docs/ESTADO_ATUAL.md`,
`docs/HISTORICO_ALTERACOES.md`. **Estes docs são a fonte da verdade e devem ser atualizados a cada mudança.**

## O que é
Sistema web do **Clube de Aventureiros Pinhal Júnior** (Django). Já possui autenticação real,
cadastro de conta e de aventureiros (com ficha médica e autorização de imagem), área interna
"Meus Dados", a tela "Usuários" (vínculos familiares) e um **módulo de Eventos** completo: evento
simples e **evento complexo** com inscrições (Fase 2), lojinha e **PDV/balcão** com operadores
(Fase 4). Também há o módulo **Presença**, o módulo **WhatsApp** (integração com a W-API: instância +
envio de teste, **Grupos**, **Webhook** de mensagens recebidas e o **módulo de liberação de números** —
autorização por link `wa.me` + reengajamento de inativos; só Diretor) e a **Loja do Clube** (loja oficial de
uniformes/lenços, independente da lojinha de evento; cadastro de produtos com **grupos/variações** + vitrine com
**carrinho** e pagamento simulado; só Diretor por ora) e o módulo **Mensalidades** (cobranças mensais por aventureiro,
inscrição+mensalidade, valores configuráveis, isenção/desconto, controle de pago; **cobrança por WhatsApp** com
**mensagem padrão ou gerada por IA** e termômetro de contato; só Diretor). Há ainda o módulo **Configurações IA**
(🤖, Diretor): configura a chave da API do GPT (OpenAI) + contador de tokens; 1º uso = a cobrança pela IA. O clube tem
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
- `/` login (auth real) · `/sair/` logout (POST) · `/inicio/` "Meus Dados" · `/trocar-senha/` ·
  `/trocar-perfil/` (troca o **perfil ativo** de quem tem 2+ perfis — seletor no topo do menu)
- `/meus-dados/responsavel/editar/` editar responsável · `/usuarios/` responsáveis+aventureiros+vínculos ·
  `/usuarios/aventureiro/<id>/termos/` termos assinados (Diretor; página pra imprimir/salvar PDF)
- `/cadastro/` **tela de escolha** (Aventureiro / Diretoria / Diretoria+Aventureiro) · `/cadastro/aventureiro/` conta+1º aventureiro · `/cadastro/diretoria/` cadastro de diretoria (`?com_aventureiro=1` emenda no aventureiro → 2 perfis) · `/cadastro/novo-aventureiro/` outro na mesma conta · `/cadastro/sucesso/`
- **Recuperação de senha** (pública, via WhatsApp): `/recuperar-senha/` (CPF do resp. legal **ou da ficha de diretoria** → código de 4 dígitos → nova senha), `.../codigo/`, `.../reenviar/`, `.../nova-senha/`. A tela do código **mostra o usuário de acesso** da conta (e a mensagem do WhatsApp também) — quem esquece o login resolve aqui; ver REGRAS_CODEX.
- **Eventos** (Diretor; PDV/operar também por operadores; baixa do pagamento por fora em
  `/eventos/<id>/inscricoes/<id>/pago/`; baixa de parcela da diretoria em
  `/eventos/<id>/parcelas/<id>/pago/`): `/eventos/`, `/eventos/<id>/` (painel),
  `/eventos/<id>/ativar/` (POST: inativa/reativa o evento — sai do menu e fecha inscrição/lojinha),
  `/eventos/<id>/pagina|inscrever|loja|pdv|pdv/inscricao|operar|operadores/` etc. — lista completa em `docs/ESTADO_ATUAL.md`.
- **Presença** `/presenca/` **ramifica por perfil**: Diretor marca presença (`/presenca/<id>/`,
  `/presenca/<id>/marcar/`); **Responsável** vê um **relatório só-leitura** da frequência dos próprios filhos.
- **WhatsApp** (Diretor): `/whatsapp/` com abas **Configurações/Grupos/Webhook/Autorização/Liberação/Templates/Envios**;
  `/whatsapp/config/`, `/whatsapp/enviar/`, `/whatsapp/grupos/sincronizar/`, `/whatsapp/webhook/configurar|eventos/`,
  `/whatsapp/webhook/entrega/` (liga o webhook de entrega: entregue/lida/falhou → aba 📨 Envios),
  `/whatsapp/autorizacao/`, `/whatsapp/reengajar/config/`, `/whatsapp/reengajar/` (envia 1 por request; JS faz 10s
  entre cada). **Webhook público** de recebidas `/webhooks/whatsapp/`. **Link curto público** `/autorizar/`
  (redireciona pro `wa.me` de autorização). Comando `reengajar_inativos` (cron).
- **Configurações IA** (🤖, Diretor): `/ia/` (chave da API do GPT + teste + contador de tokens), `/ia/config/`,
  `/ia/testar/`, `/ia/zerar/`. Modelo fixo `gpt-4.1-nano`; cliente `core/openai_ia.py` (urllib).
- **Aniversariantes** (🎂, Diretor): `/aniversarios/` (abas 🎈 lista, ✏️ mensagens e 📬 envios),
  `/aniversarios/mensagem/`, `/aniversarios/enviar/`. Junta os **3 perfis** numa lista só, deduplicando a
  pessoa que tem mais de um perfil. Um `TemplateAniversario` por perfil (com canais). Disparo pelo cron
  `enviar_aniversarios` (diário, 10s entre cada) + botão manual por pessoa.
- **E-mail** (✉️, Diretor): `/email/` (conta SMTP + envio de teste + contador), `/email/config/`,
  `/email/testar/`, `/email/zerar/`. Cliente `core/email_envio.py` (`django.core.mail`, **nativo**). É o
  **2º canal de notificação**; hoje só a base — nada dispara por e-mail ainda (ver ESTADO_ATUAL).
- **Pagamentos (Mercado Pago)** (Diretor p/ config): `/mercadopago/` (config credenciais teste/produção + modo),
  `/mercadopago/config/`; **webhook público** `/webhooks/mercadopago/`; página/sucesso de pagamento **genéricos**
  `/pagamento/<ref>/` e `/pagamento/<ref>/sucesso/`; status/simulação `/pagamento/<ref>/status/` (polling) e
  `/pagamento/<ref>/simular/` (só no modo teste). Mensalidades: `/mensalidades/cobrar/` (gera Pix p/ meses em aberto)
- **Loja do Clube** `/loja/` **ramifica por perfil**: Diretor vê abas Gerenciar/Loja/Vendas; **Responsável**
  vê só a vitrine + **"Meus pedidos"**. Rotas: `/loja/produto/novo|<id>/editar|<id>/excluir/`,
  `/loja/produto/<id>/` (vitrine), `/loja/carrinho/…`, `/loja/finalizar|pagamento|sucesso/`,
  `/loja/compra/<id>/cancelar/`, `/loja/entrega/…`
- **Mensalidades** `/mensalidades/` **ramifica por perfil**: Diretor vê o painel
  (`/mensalidades/config|gerar|pagar|isencao|reajustar|editar|cobrar/`); aba **Cobranças**
  (`/mensalidades/cobrancas/config|modo|telefone|enviar/`): mensagem padrão **ou IA** (alavanca `modo`),
  escolher o **telefone do responsável financeiro** por família (`telefone`), enviar 1/todos (10s entre cada,
  filtro "só quem já mandou msg") e **termômetro** de contato/autorização por família.
  **Responsável** vê a própria visão (resumo + em aberto + apelo) e paga o que seleciona em
  `/mensalidades/pagar-selecionadas/`.
- **Financeiro** (Diretor): `/financeiro/` (abas Resumo/Extrato/Custos), `/financeiro/custo/novo|<id>/excluir/`, `/financeiro/caixa/` (editar "Onde está o dinheiro"). Mostra o **líquido** (bruto − custos − **taxa do Mercado Pago**) por fonte e no resultado; a taxa vem de `Pagamento.taxa`. Idem no painel do evento, Mensalidades e Loja/Vendas.
- `/admin/`

## Models (`core/models.py`)
- `Aventureiro` (FK `usuario`; ficha de inscrição + pai/mãe/responsável legal; campos `ativo` e **`demo`**).
  Um usuário → vários. `demo=True` = dado fictício (NUNCA entra nas contagens do clube — ver Convenções).
- **Diretoria**: `MembroDiretoria` (OneToOne `usuario`; ficha "Compromisso para Voluntários" — identificação,
  contato, endereço, escolaridade, aceites; `ativo`/`demo`) e `FichaMedicaDiretoria`. A ficha médica é
  compartilhada com o aventureiro via molde abstrato **`FichaMedicaBase`** (mesmos campos, sem duplicar).
  Cadastro de diretoria cria a conta e entra no perfil **"Diretoria"** (grupo); quem também tem aventureiro
  fica com **2 perfis** (alternância "Ver como"). O **Diretor atribui o papel específico** (Diretor/Secretário/
  Tesoureiro/Professor) em `/usuarios/diretoria/` (ajusta os grupos). Os 3 documentos da diretoria (compromisso,
  declaração médica, imagem do adulto) são **assinados no canvas** (`AssinaturaDocumentoDiretoria`). "Meus Dados"
  mostra um card "Diretoria" com os dados do próprio integrante.
- `FichaMedica` (OneToOne) · `AutorizacaoImagem` (OneToOne) · `AssinaturaDocumento` (assinatura desenhada de
  cada documento da inscrição — ficha/médica/imagem; imagem PNG + snapshot do texto do termo; só o Diretor vê).
- **Eventos/Lojinha/Presença**: `Evento`, `CustoEvento`, `FaixaEtariaPreco`, `CampoInscricao`, `Inscricao`,
  `ParticipanteInscricao`, `RespostaInscricao`, `ProdutoEvento`, `VariacaoProduto`, `PedidoLoja`,
  `ItemPedidoLoja`, `OperadorEvento`, `PerfilUsuario`, `CupomDesconto`, `PresencaEvento`.
- **WhatsApp**: `WhatsappConfig` (singleton; ID/token/URL base + `numero_clube`, `mensagem_autorizacao`/
  `resposta_autorizacao`, `reengajar_dias`/`mensagem_reengajamento`), `GrupoWhatsapp` (grupo `id↔nome`,
  `usar_liberacao`) e `WhatsappWebhookEvent` (mensagens recebidas: campos extraídos + `raw_payload`; 100 últimos).
  Cliente `core/wapi.py` (grupos/webhook/enviar) + parser `core/wapi_parser.py` (portado do BEEZAP, defensivo).
  **Liberação de números** (só Diretor): webhook casa o telefone recebido com responsável/diretoria e grava em
  `PerfilUsuario` (`ultima_msg_whatsapp_em`, `autorizacao_recebida_em`, `reengajado_em`); reengajamento manda 1x
  por silêncio (só de novo se a pessoa responder). Comando `reengajar_inativos` (cron).
  A **resposta automática da autorização** passa por `_confirmar_autorizacao`: marca
  `confirmacao_autorizacao_em` **só quando a W-API confirma o envio**; falha é **logada** e fica **pendente**,
  e a próxima mensagem da pessoa tenta de novo. Ao mexer nesse fluxo, não volte a ignorar o retorno de
  `_enviar_whatsapp` — o `except: pass` anterior fazia autorização virar silêncio.
- **Extrato de envios do WhatsApp**: `MensagemWhatsapp` (migration **0064**) grava **toda** mensagem que sai —
  o registro está **dentro do `_enviar_whatsapp`** (que é casca de `_wapi_post_texto`), então nenhum ponto de
  envio escapa; passe `origem=`/`nome=` ao chamar. **Nunca o texto**, como no `LogEmail`. `ok=True` do envio só
  diz que a **W-API aceitou**: quem confirma entrega é o **webhook de entrega**, casado pelo `message_id`
  (`wapi_parser.extrair_status` → `MensagemWhatsapp.atualizar_status`). No webhook público o **status é tratado
  antes de tudo** — se virar "mensagem recebida", marca contato/autorização de quem não escreveu nada (há teste).
  O status **não retrocede** (avisos chegam fora de ordem), mas `FAILED` sempre vale. Tela: aba **📨 Envios**.
- **Configurações IA (OpenAI/GPT)**: `OpenAIConfig` (singleton; só `api_key` + contadores de tokens
  `chamadas`/`tokens_prompt`/`tokens_cache`/`tokens_completion`). Modelo/URL fixos em `core/openai_ia.py`
  (`gpt-4.1-nano`; `conversar`/`enviar_prompt` devolvem `(ok, texto, uso)`). Todo uso deve chamar `registrar_uso`.
- **E-mail (SMTP)**: `EmailConfig` (singleton; `host`/`porta`/`seguranca`/`usuario`/`senha` de app mascarada/
  `remetente_nome`/`reply_to`/`site_url`/`rodape` + contador `enviados`/`falhas`/`ultimo_envio_em`/`ultimo_erro`).
  Cliente `core/email_envio.py` — `enviar(config, destino, assunto, corpo, contato=, transacional=)` →
  `(ok, detalhe)`, mesmo contrato do `_enviar_whatsapp`. A conexão SMTP vem do **model**, não do settings (as
  variáveis `EMAIL_*` do Django não são usadas). Helper `_email_do_usuario` resolve o endereço: conta de login →
  ficha da diretoria → `Aventureiro.resp_email`.
- **Consentimento de e-mail (anti-spam)**: `ContatoEmail` (endereço único + `descadastrado_em` +
  `bounce_em`/`bounce_motivo` + `token`) é a fonte do gate `_pode_enviar_email`; o ponto único de envio é
  `_enviar_email`. Regra: **bounce bloqueia tudo** (até `forcar`), **descadastro bloqueia só o não-transacional**
  (comprovante do que a pessoa fez sempre chega). Descadastro público em `/descadastrar/<token>/` (`@csrf_exempt`
  — Gmail/Outlook fazem POST One-Click, RFC 8058), reversível. Todo e-mail leva rodapé de identificação; os
  não-transacionais levam também `List-Unsubscribe`. Só recusa **5xx** marca bounce (4xx/conexão é problema
  nosso). Ao criar envio novo de e-mail, **use `_enviar_email`** — nunca `email_envio.enviar` direto.
- **Aviso interno de inscrição**: `Evento.notificar_inscricoes` + `notificar_inscricoes_para` (migration
  **0067**) ligam, **por evento**, o envio da **lista de inscritos** a UM integrante da diretoria a cada
  inscrição. Template `inscricao_evento_interno` (aba Templates) só define texto/canais — o destinatário vem
  do evento, então o POST daquela aba **não** mexe na M2M `avisos_internos_para` desse tipo. O gancho é
  `_agendar_aviso_inscricao`, chamado nos **dois** caminhos de inscrição (site `_criar_inscricao_de_payload`
  **e** balcão/PDV) — inscrição nova por outro caminho precisa chamá-lo também. A lista é agrupada por
  inscrição (responsável + WhatsApp; participantes com nome e idade) e separa quem tem `pagamento_externo`
  pendente, que é a parte acionável. **Inscrito nunca sai da lista** (pagou na hora ou por fora, tanto faz):
  se o texto não cabe numa mensagem, `_partir_texto_whatsapp` (dentro do `_notificar_whatsapp`, portanto vale
  para toda notificação) manda em **partes numeradas** — nunca aparar a lista. Envio manual: rota
  `/eventos/avisar-inscritos/` (evento no POST), usada pelo painel do evento e pela aba Templates.
- **Notificações são multicanal**: `_notificar(tipo, numero, ctx, *, forcar=False, email="")` é o ponto único e
  **despacha** para WhatsApp e/ou e-mail conforme `TemplateNotificacao.enviar_whatsapp`/`enviar_email`. O texto é
  renderizado **uma vez** (a IA é chamada 1× por notificação) e no e-mail passa por `texto_para_email`, que tira
  o `*negrito*` do WhatsApp. Ao ligar um gatilho novo, passe **os dois** destinos (`_whatsapp_familia` e
  `_email_familia`) e deixe o template decidir. Cobrança/lembrete **não** é transacional: vai com
  `transacional=False` e respeita descadastro.
- **Cobrança tem canal**: `CobrancaEnviada.canal` (`whatsapp`/`email`, default `whatsapp`). A contagem "já
  cobrei este mês" e o filtro da tela são **por canal** — sem isso, mandar por um canal silenciaria o outro. Ao
  criar envio em lote novo, mantenha o padrão **1-por-request + 10s no front**. O seletor tem ainda
  **`CANAL_AMBOS`**, que é opção de *envio* e nunca é gravada: sai um `CobrancaEnviada` por canal real. Em
  "ambos" a mensagem é gerada **uma vez por família** (a IA não pode ser chamada 2×) e o filtro "não recebeu
  este mês" é avaliado **por canal**, então quem já foi cobrada por um canal recebe só pelo outro.
- **Extrato de e-mail**: todo envio (e todo bloqueio pelo gate) grava um `LogEmail` — destinatário, assunto,
  `origem`, resultado; **nunca o corpo**. Aparece no card 📬 Últimos envios em `/email/`; guarda os últimos 200.
  Ao criar um envio novo, passe `origem=` para a linha sair identificada.
- **`Reply-To` vazio é o certo** quando as respostas devem cair na própria conta de envio (sem ele a resposta
  vai para o `From`). Só preencha para desviar a outro endereço.
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
- **Envio de aniversário**: `_enviar_aniversario(pessoa, ...)` é o ponto único. **Não é transacional** (o clube
  inicia), então passa pelos **dois gates** — `_pode_notificar` no WhatsApp e `_enviar_email(transacional=False)`
  no e-mail; um canal barrado não impede o outro, e `forcar=True` **não** fura gate. A trava é
  `EnvioAniversario` com `UniqueConstraint(chave, ano, canal)` **condicionada a `ok=True`**: uma vez por ano por
  canal, à prova de corrida entre o cron e o botão manual. **Falha não ocupa a trava** (pode retentar);
  reenvio forçado usa `update_or_create`, nunca `create`.
- **Aniversários**: `_aniversariantes()` monta a lista dos 3 perfis. A **deduplicação** usa `_chave_pessoa`
  (CPF → WhatsApp → nome) com prioridade **diretoria > responsável**; o **aventureiro fica fora dela**, com
  chave `av:<id>` — a criança usa telefone/e-mail do responsável e seria engolida por ele. Datas de nascimento:
  `Aventureiro.data_nascimento` (obrigatória), `MembroDiretoria.data_nascimento` e os opcionais
  `pai_/mae_/resp_data_nascimento` (criados em 08/2026; famílias antigas estão sem).
- **Regra do clube: aventureiro INATIVO não é cobrado**, mesmo com mês em aberto — quem saiu não recebe
  cobrança e a dívida não conta como "a receber". Toda query de cobrança/em-aberto precisa de
  `aventureiro__ativo=True` (além de `demo=False`). Já aplicado em `_cobrancas_familias`,
  `_mensalidades_abertas_familia` (acerto público), `_mensalidades_familia_abertas` (área do responsável),
  no total `aberto` do painel do Diretor e no Financeiro. **Pagas contam sempre** (histórico não muda).
- **Mensalidades**: `ConfigMensalidade` (singleton; valores padrão + `mensagem_cobranca`, **`mensagem_apelo`**,
  `cobranca_via_ia` (alavanca padrão×IA) e `prompt_cobranca_ia`) e `Mensalidade` (aventureiro, ano, mês, tipo
  inscrição/mensalidade, valor, isento, status pago/aberto); `CobrancaEnviada` (histórico do envio). Campos
  `Aventureiro.mensalidade_isento`/`mensalidade_desconto_pct`. Geração automática no cadastro. Cobrança por
  WhatsApp usa a engine da IA (`core/openai_ia.py`) quando a alavanca está ligada.
- **Perfis/menu**: `Evento` também tem **`demo`** (evento fictício, fora das contagens/menu). O acesso por
  perfil e o seletor de perfil ficam em `core/menus.py` (ver Convenções); comando `dados_demo_fabiano` popula
  o perfil de Responsável do Fabiano com dados fictícios.
- **Financeiro**: `CustoClube` (nome, valor, data, destino) + `ComprovanteCustoClube` (vários anexos por custo) —
  gastos gerais do clube; `CaixaClube` (singleton `get_solo`: `saldo_banco`; espécie = resultado − banco,
  calculada) para o card "Onde está o dinheiro". O resto do Financeiro é **consolidação** (lê mensalidades/loja/eventos).
- **Recuperação de senha**: `PerfilUsuario.whatsapp_principal_origem` (pai/mãe/resp legal) — para onde vai
  o código; código de recuperação fica na **sessão** (não há model novo pra ele). O **telefone de cobrança** é
  um campo **separado** (`PerfilUsuario.cobranca_whatsapp_origem` — responsável financeiro), independente do
  principal. **A conta é achada por CPF em dois lugares** (`_conta_por_cpf`): `Aventureiro.resp_cpf` **e**
  `MembroDiretoria.cpf` — procurar só no primeiro deixava a diretoria sem filho no clube sem recuperação
  nenhuma; cadastro novo com CPF entra aqui também. O destino sai de `_whatsapp_recuperacao`: escolha do
  Diretor > WhatsApp da **ficha de diretoria** quando o CPF veio dela (quem pede com o próprio CPF recebe no
  próprio número) > responsável legal > ficha como fallback. `_numeros_conta` **não** basta: ele só lê os
  aventureiros e devolve vazio numa conta só de diretoria.
- **Assinatura de documentos**: `AssinaturaDocumento` (aventureiro + tipo de documento + imagem PNG da assinatura
  desenhada + `titulo/texto_documento` snapshot do termo no ato + assinante nome/CPF + data; único por
  aventureiro+documento). No cadastro a assinatura **substitui o checkbox** de aceite (assinar = aceitar) nos 3
  documentos; o responsável não vê a própria assinatura depois; só o Diretor gera o termo assinado.
  (migrations até `0062`). Detalhes em ESTADO_ATUAL.
- **Evento ligado/desligado**: `Evento.ativo` (padrão `True`, migration **0063**) é o "inativar evento".
  Inativo, o evento **sai do menu** (`_eventos_menu` filtra `ativo=True`) e as telas públicas **não abrem**
  (`_evento_inativo_bloqueio` em `views.py`: 404 para visitante, volta ao `/inicio/` para quem está logado; o
  Diretor passa). A trava de verdade está no **model** — `inscricoes_abertas()` e `loja_aberta()` devolvem
  `False` com `ativo=False`, então POST forjado também é barrado. **Não confundir com `demo`**: `demo` tira o
  evento de tudo (contagens/financeiro); `ativo=False` só fecha o lado público — painel, balcão, presença e
  financeiro do Diretor continuam, e inscrição/pedido/dinheiro já registrados permanecem. Ao criar tela
  pública nova de evento, **chame o bloqueio no início da view**. O botão Inativar/Reativar **não aparece em
  evento que já terminou** (`ja_terminou()`) — lá não faria nada; só sobra o "Reativar" se estiver inativo.
- **Formas de pagamento por evento**: `Evento.formas_pagamento_online` (`ambos`/`pix`/`cartao`, padrão
  `ambos`) define o que o **site** aceita naquele evento — vale para a inscrição e para a lojinha. Use
  `evento.formas_online()` para montar a tela e **`evento.aceita_forma_online(forma)` para validar o POST**:
  esconder o rádio no HTML não impede envio forjado. O **PDV/balcão não usa isso** (lá o operador segue com
  dinheiro/cortesia, na variável `formas`). A lista canônica `FORMAS_PAGAMENTO_ONLINE` fica em `models.py`.
- **Inscrição paga direto ao evento**: `Evento.formas_pagamento_fora` (`nenhuma`/`pix`/`cartao`/`ambos`, padrão
  `nenhuma`) + `instrucoes_pagamento_fora` dizem **quais formas** confirmam sem cobrar — é **por forma** (dá
  para cobrar cartão pelo site e deixar o Pix por fora). Use **`evento.forma_paga_por_fora(forma)`** para
  decidir o caminho; `formas_fora()` já interseta com `formas_online()` (marcar forma não oferecida não faz
  nada). Escolhida uma delas, a inscrição é criada **na hora** (`Inscricao.pagamento_externo=True`, sem
  passar pelo Mercado Pago) e fica **pendente** até a baixa manual do Diretor (`pago_externo_em`, rota
  `/eventos/<id>/inscricoes/<id>/pago/`). **Esse dinheiro nunca entra no caixa** — nem no resultado do evento,
  nem no Financeiro do clube, **nem depois da baixa** (a baixa só registra que a pessoa acertou com o evento).
  Toda soma de caixa nova precisa excluir `pagamento_externo=True` (já feito em `evento_painel_view`,
  `_montar_financeiro`, `_montar_dashboard` e `financeiro_view`); item de lojinha levado junto herda a flag
  (`PedidoLoja.pagamento_externo`). A forma escolhida vira só o registro de **como** será o acerto.
- **Prazo de inscrição próprio da diretoria**: `Evento.inscricao_limite_diretoria` (mig. **0069**; vazio = o
  prazo de todos). **Só estende, nunca restringe** — `prazo_inscricao_diretoria()` devolve o `max` entre ele e
  o prazo comum, e uma inscrição com diretoria vale por ele **inteira** (o aventureiro que entra junto aproveita
  a janela). `inscricoes_abertas(tem_diretoria=False)`: chame com **`True` para decidir se a tela abre** (senão
  a diretoria não chega ao formulário na janela extra) e valide o **POST pela composição real** da inscrição —
  é lá que a regra vale, com a trava final no model. Quem é "diretoria" é **quem marca a caixinha**, como já
  vale para o valor (o sistema não confere o cadastro). O **PDV não checa prazo** (presencial). A janela extra
  é **discreta**: **nenhuma tela pública** a menciona — passado o prazo comum, a página do evento diz só
  "Inscrições encerradas", **o botão some para todos** e o erro de POST é **genérico**; a diretoria entra pelo
  **link direto** (que a view continua abrindo). O **menu do Responsável** também perde o evento
  (`_eventos_menu(user, perfil)` filtra por `inscricoes_abertas()` no perfil Responsável — e com ele some o caminho
  para a lojinha daquele evento). `tem_prazo_diretoria`/`so_diretoria_pode_inscrever` são estado **interno**:
  use-os só no painel do Diretor. Ao criar tela pública nova de evento, siga o prazo **comum**.
- **Valor da diretoria parcelado**: `Evento.parcelas_diretoria` (mig. **0068**; `1` = à vista) divide **só a
  parte da diretoria** em parcelas cobradas **pelo clube** (estilo mensalidade — não é o parcelamento do cartão,
  que o MP já oferece em cima da 1ª parcela). A 1ª parcela é cobrada **no ato**, junto do valor **integral** dos
  outros participantes e da lojinha, numa **única** cobrança; as demais viram `ParcelaInscricao` vencendo mês a
  mês. **A 1ª parcela pode ficar para o mês seguinte** (`Evento.parcelas_diretoria_primeira`, mig. **0070**;
  `primeira_parcela_no_ato()`): aí ela vence no dia **`DIA_VENCIMENTO_PARCELA` (10)** do mês que vem — dia
  **fixo**, não depende do dia da inscrição — e a parte da diretoria **inteira** sai da cobrança do ato, então
  numa inscrição só de diretoria **não há cobrança** e a inscrição é concluída na hora (o fluxo decide o
  parcelamento **antes** do gateway e só cobra quando `a_pagar_agora > 0`; cobrança de R$ 0,00 não existe). O
  que separa "entrou no caixa hoje" de "ficou para depois" é **`ParcelaInscricao.no_ato`**, **nunca** o
  `numero` — com a 1ª diferida, nenhuma parcela é do ato, e filtrar por `numero == 1` conta a 1ª parcela duas
  vezes no extrato. O `primeira_no_ato` viaja no **payload** do pagamento (a configuração do evento pode mudar
  entre o POST e a aprovação do Pix). Use **`evento.permite_parcelar_diretoria()` no POST** — forjar
  `parcelar_diretoria=1` não parcela nada.
  Não existe com "pago direto ao evento" nem sem MP configurado (não há cobrança para dividir).
  **A regra financeira é a que mais pega**: `Inscricao.valor_total` é o valor da inscrição, não o que entrou —
  **toda soma de caixa usa `valor_no_caixa`** (total − parcelas em aberto), e o **extrato** usa `valor_no_ato`
  mais **um lançamento por parcela paga** (senão a mesma parcela conta duas vezes; há teste que soma o extrato
  e compara com a arrecadação). Cada parcela paga online tem o **seu** `Pagamento` (`tipo="parcela_inscricao"`,
  finalizado por `_finalizar_parcela_inscricao`, idempotente). A família paga pela página pública
  `/inscricao/<token>/parcelas/` (token da inscrição, como o `token_acerto` da família). A **baixa manual** do
  Diretor **entra** no caixa — ao contrário da baixa do pagamento por fora; reabrir solta o `pagamento` para a
  taxa não ficar presa a uma parcela em aberto. **Ainda não há cobrança automática** das parcelas seguintes.
- **Cookies de sessão/CSRF só por HTTPS**: `SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE` = `not DEBUG`.
  **Não ligar `SECURE_SSL_REDIRECT`** — o Nginx já faz o 301; o aviso `security.W008` é esperado (há teste
  documentando). Ao mexer em settings, lembre que o test runner do Django força `DEBUG=False` **depois** do
  import, então não dá para comparar o cookie com `settings.DEBUG` num teste.

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
- **O repositório é PÚBLICO.** Nunca escreva dado pessoal real em lugar nenhum versionado — e isso inclui a
  **documentação** e as **mensagens de commit**, não só o código: nome de aventureiro ou responsável, e-mail,
  telefone, CPF, login. Ao relatar um diagnóstico com caso real, descreva o **padrão da falha** ("caso 1:
  mensagem chegou, confirmação não saiu"), nunca quem foi. Em teste, use dados claramente fictícios
  (`@exemplo.com`, `abcd efgh ijkl mnop`) — **jamais** um valor real copiado do banco.
- Fazer só o que foi pedido; não quebrar login, cadastro nem o cadastro de múltiplos aventureiros.

## Convenções úteis
- **Menu/acesso por perfil**: fonte única em `core/menus.py` (`ITENS_MENU` + `ACESSO_PADRAO` por perfil +
  `itens_menu_do_perfil`/`perfil_efetivo`/`perfis_do_usuario`/`pode_trocar_perfil`). O `_menu.html` **itera
  `menu_itens`** (via context processor `perfis`) — **não** chumbar itens com `{% if is_diretor %}`. O menu
  tem o seletor **"Ver como"** (`trocar_perfil`, chave `PERFIL_ATIVO_KEY` na sessão): troca a visão entre os
  perfis que o usuário **possui**. Telas compartilhadas (Loja, Mensalidades, Presença) usam a **mesma URL** e a
  view **ramifica por perfil** (`atua_como_responsavel`; Diretor vê o painel, o **Responsável** tem a sua:
  `*_responsavel.html`). O futuro **módulo de permissões** encaixa em `perfil_efetivo`/`ACESSO_PADRAO` sem mexer
  em menu/views.
- **Dados fictícios (`demo`)**: `Aventureiro.demo`/`Evento.demo` marcam dados de teste (ex.: perfil de
  responsável do Diretor via `dados_demo_fabiano`). **Toda** query de contagem/relatório do clube (Usuários,
  Mensalidades/Presença do Diretor, Financeiro, menu de eventos) **deve excluir `demo`** (`demo=False` /
  `.exclude(aventureiro__demo=True)`). Telas do próprio responsável (escopo `usuario=request.user`) incluem os
  demos de propósito. Ao criar nova estatística do clube, **lembre de excluir `demo`**.
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
- **Integrações externas** seguem um padrão: cliente HTTP próprio via **`urllib`** (sem dep nova) — um módulo por
  serviço (`core/mercadopago.py`, `core/openai_ia.py`, `core/wapi.py` + parser `core/wapi_parser.py`). A exceção
  é o **e-mail** (`core/email_envio.py`), que usa o `django.core.mail` — também nativo, então a regra de fundo
  (**zero dependência nova**) se mantém. **Webhooks
  públicos** (`/webhooks/mercadopago/`, `/webhooks/whatsapp/`) são `@csrf_exempt`, idempotentes e **nunca** devolvem
  erro/traceback ao chamador. **Envio em lote** (cobrança e reengajamento do WhatsApp) tem **pausa de 10s entre
  cada** (front-end faz o pacing com barra+cancelar; comando de cron usa `time.sleep`) — evita bloqueio por spam.
- **Coluna de grade com conteúdo largo usa `minmax(0, 1fr)`, nunca `1fr`**: `1fr` tem `min-width: auto` e não
  encolhe abaixo do conteúdo, então gráfico/tabela/nome comprido **estica a grade e cria rolagem horizontal na
  página** — e um wrapper de rolagem interna (`*-scroll`) nunca entra em ação. Já aconteceu em Aniversários e
  em Mensalidades (`.mens-resumo-topo`).
- **Modais** fecham no fundo só com `mousedown`+`click` no fundo (não fechar ao arrastar seleção).
- "Meus Dados": foto só aparece se o arquivo existir (`foto.storage.exists`), senão placeholder com iniciais.
- Verificação visual sem navegador dedicado: renderizar via test client + Chrome headless
  (`--headless=new --force-device-scale-factor=1`; o viewport mínimo do headless é ~485px — pedir 360px
  **renderiza em 485 e reduz**, o que parece corte de layout sem ser). Para overflow, não confie na captura:
  injete uma **sonda** que compara `documentElement.scrollWidth` com `clientWidth` e lista quem estoura.
  A sonda também serve para contar elementos (`querySelectorAll(...).length`) — foi assim que se descobriu
  um `{% include %}` que faltava numa das listas.
- **Abas seguem um padrão só**: trilho `*-abas` (fundo suave + borda + cantos) com pílulas `*-aba`, a ativa em
  **gradiente azul** e badge de contagem — ver `loja.css`, `mensalidades.css`, `aniversarios.css`. Ao criar uma
  tela com abas, **copie esse padrão**; não invente nomes de classe. Classe usada no HTML sem regra em CSS
  nenhum não quebra nada e não falha teste — só renderiza feio (já aconteceu).
- **Comentário em template Django: `{# ... #}` é de UMA linha.** Em várias linhas ele **não** comenta — o texto
  vaza como conteúdo na tela. Para bloco, use `{% comment %}...{% endcomment %}`. Já aconteceu duas vezes.
