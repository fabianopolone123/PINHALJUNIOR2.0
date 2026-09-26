# Regras do Codex

Estas são as regras obrigatórias para toda nova alteração feita neste projeto.

## Regras obrigatórias

- Antes de fazer qualquer alteração, ler os arquivos dentro da pasta `docs/`.
- Ler também o arquivo `CODEX.md` da raiz do projeto.
- Antes de alterar qualquer arquivo, entender o padrão já existente.
- Não apagar código existente sem necessidade.
- Não alterar nomes de rotas, templates, apps, arquivos ou classes sem motivo.
- Não implementar funcionalidades além do que foi pedido.
- Não instalar bibliotecas externas sem autorização.
- Não usar Bootstrap, Tailwind ou frameworks visuais externos, a menos que seja solicitado.
- Manter o projeto simples, organizado e fácil de continuar.
- Criar migrations quando alterar models.
- Atualizar a documentação sempre que fizer qualquer alteração no projeto.
- Registrar no histórico o que foi feito, quais arquivos foram alterados e o motivo da alteração.
- Manter foco em responsividade mobile first.
- Preservar o padrão visual já criado.
- Evitar duplicação de CSS, HTML e lógica Python.
- Usar nomes claros para funções, views, templates, classes CSS e arquivos.
- Quando houver dúvida, fazer a solução mais simples e segura.
- No final de cada tarefa, informar quais arquivos foram criados ou alterados.
- Nenhuma tarefa deve ser considerada concluída sem atualizar `docs/ESTADO_ATUAL.md` e `docs/HISTORICO_ALTERACOES.md`.
- **VERIFICAÇÃO OBRIGATÓRIA — janelas suspensas (modais):** toda janela suspensa (modal) deve fechar
  ao clicar no fundo **apenas quando o `mousedown` E o `click` ocorreram no próprio fundo** (rastrear um
  flag no `mousedown`). NUNCA fechar quando o usuário começa a arrastar/selecionar texto de dentro do
  modal e solta o mouse fora dele. Ao criar/revisar qualquer modal, testar este cenário. Detalhes na
  seção "Componente reutilizável de modal".

## Regra obrigatória de manutenção da documentação

Toda vez que o Codex fizer qualquer alteração no sistema, deve atualizar obrigatoriamente:

- docs/ESTADO_ATUAL.md
- docs/HISTORICO_ALTERACOES.md

Se criar nova regra ou padrão técnico, deve atualizar:

- docs/REGRAS_CODEX.md

Se mudar estrutura geral, rota, app, configuração ou modo de rodar o projeto, deve atualizar:

- docs/README_PROJETO.md

## Fluxo obrigatório para toda alteração

Toda alteração futura feita pelo Codex deve seguir este fluxo completo:

### Antes de alterar
- Ler `CODEX.md`.
- Ler todos os arquivos da pasta `docs/`.
- Entender o estado atual do projeto.
- Preservar o padrão existente.

### Durante a alteração
- Fazer somente o que foi solicitado.
- Não implementar funcionalidades extras sem pedido.
- Não apagar código sem necessidade.
- Não instalar dependências sem autorização.
- Manter o padrão visual e técnico do projeto.

### Depois de alterar
- Atualizar `docs/ESTADO_ATUAL.md`.
- Atualizar `docs/HISTORICO_ALTERACOES.md`.
- Se criar regra nova, atualizar `docs/REGRAS_CODEX.md`.
- Se mudar estrutura, rota, app, configuração ou modo de rodar, atualizar `docs/README_PROJETO.md`.
- Rodar `git status`.
- Rodar `git add .`.
- Criar commit descritivo em português do Brasil.
- Fazer push para o repositório remoto (`origin`, branch `main`).

### Segurança no Git
- Nunca fazer `force push`.
- Nunca apagar histórico do Git.
- Nunca sobrescrever arquivos remotos sem autorização.
- Se o push falhar por conflito, informar o erro e analisar com segurança antes de qualquer pull/merge.

## Padrão obrigatório para mensagens de commit

As mensagens de commit devem:
- Ser sempre em português do Brasil.
- Ser curtas, claras e descritivas.
- Explicar objetivamente o que foi alterado.
- Usar verbo no presente, quando possível.

Exemplos de mensagens:
- `cria tela inicial de login`
- `melhora visual da tela de login`
- `cria documentação interna do projeto`
- `configura versionamento inicial`
- `cria tela inicial interna com menu lateral`
- `ajusta responsividade da tela inicial`
- `implementa estrutura de autenticação`
- `corrige layout do menu lateral`

## Padrão visual a preservar (tela de login)

Ao mexer na tela de login ou em novas telas, preservar o padrão visual já criado:

- Paleta azul/verde inspirada no logo (ver variáveis CSS em `static/css/login.css`).
- Fundo com gradiente azul→verde e formas decorativas suaves.
- Cards com bordas arredondadas, glassmorphism suave e sombra elegante.
- Campos com foco realçado (borda azul + halo) e boa altura para toque (mobile first).
- Botão principal com gradiente e transições suaves (hover/clique).
- Reaproveitar as variáveis CSS (`:root`) em vez de repetir cores/valores.
- Sempre manter `@media (prefers-reduced-motion: reduce)` para acessibilidade.
- CSS puro, sem Bootstrap/Tailwind ou frameworks externos.

## Padrão de layout interno (área logada)

Para as telas internas (após o login), preservar o padrão criado em
`templates/core/inicio.html` e `static/css/inicio.css`:

- Menu lateral fixo à esquerda no desktop (gradiente azul) com logo, nome do sistema e itens.
- No celular, o menu vira gaveta recolhível (botão hambúrguer + overlay). Nada pode ficar cortado.
- Item de menu ativo recebe a classe `ativo` (destaque em verde), calculado pela URL atual.
- Cada tela interna deve ter seu próprio CSS (não misturar com `login.css`), reaproveitando a paleta.
- **O menu lateral é CENTRALIZADO** no parcial `templates/core/_menu.html` (usado por todas as telas
  internas via `{% include "core/_menu.html" %}`). Para mudar itens do menu, editar **só** esse parcial —
  nunca voltar a colocar `<nav class="menu">` inline nos templates. Ele já trata os perfis: diretor/
  membro (menu normal), operador (seção "Operar") e ajudante externo (vê só os eventos dele).
- Itens restritos usam `{% if is_diretor %}`; a seção "Eventos ativos" usa o parcial `_menu_eventos.html`.
- Ícones podem ser emoji, caractere ou SVG inline — nunca biblioteca externa.

## Notificações (toasts) — obrigatório dar feedback
- **Toda ação relevante do usuário** (criar/editar/remover/registrar/cancelar/salvar, etc.) deve
  gerar uma notificação de **sucesso** ou **erro** com `django.contrib.messages`
  (`messages.success/error/info`). Nunca deixar o usuário sem saber se a ação funcionou.
- As mensagens são exibidas como **toasts flutuantes** — **padrão ÚNICO de notificação do sistema
  inteiro** (eventos, inscrições, cadastros, tudo). Bloco `.mensagens` + `.mensagem` com a classe
  `mensagem-{{ tags }}` (success/error/info/warning, cada um com ícone), estilizados em `inicio.css`.
  O `inicio.js` é o **módulo único de toast**: **move o `.mensagens` para o `<body>`** (para aparecer
  no canto da tela, fora de ancestrais com `transform`), **auto-fecha** (~4,5s, igual à barra de
  progresso) e permite fechar no clique. Não criar outro mecanismo/arquivo de aviso.
- **`inicio.js` deve ser carregado em TODA página que exibe toast** — inclusive as **páginas públicas**
  do evento (loja, pagamento, sucesso, página do evento, inscrição). Sem ele, o balão não se auto-fecha
  e não vai para o canto da tela. É seguro em qualquer página (cada bloco tem guarda de elemento).
- Para criar um toast **pelo JS** (ex.: "copiado!"), usar **`window.mostrarToast(texto, tipo)`**
  (exposto pelo `inicio.js`) — mesmo visual/tempo dos toasts do servidor. Carregar o `inicio.js`
  **antes** do script que chama `mostrarToast`. Não reimplementar toast em outro lugar.
- Ao criar novas views que alteram dados, **sempre** incluir a `messages.*` correspondente e
  redirecionar (padrão POST-redirect-GET) para uma página que **renderize o bloco `{% if messages %}`
  E carregue o `inicio.js`** — senão a mensagem "vaza" e só aparece na página seguinte.

## Padrão global de interface (`static/css/base.css`)

Regras de comportamento da interface válidas para **todas** as telas:

- **Sem "cursor de texto piscando" (caret) fora de campos digitáveis**: texto de interface
  (títulos, rótulos, botões, ícones, pílulas, menus, textos de estado vazio, etc.) **não** é
  selecionável e **não** deve exibir cursor de texto — não são campos editáveis. Isso é garantido
  por `body { user-select: none; }` em `static/css/base.css`.
- **O que continua selecionável/copiável**: apenas campos de formulário (`input`, `textarea`,
  `select`, `[contenteditable="true"]`) e **valores de dados** — a classe `.dado-valor` (parcial
  `_dado.html`) e a utilitária `.selecionavel`. Assim o usuário ainda copia CPF, telefone, e-mail, etc.
- **Toda tela nova deve linkar o `base.css` ANTES do CSS específico da página**, no `<head>`:
  `<link rel="stylesheet" href="{% static 'css/base.css' %}">`.
- Para permitir seleção de algum texto de dado que não use `_dado.html`, aplicar a classe
  `.selecionavel` a esse elemento. Não reintroduzir seleção/caret em elementos de interface.
- Nunca usar `contenteditable`, `tabindex` ou campos ocultos em elementos que não são campos de
  fato — isso reintroduz o caret indevido.

## Padrão de models, formulários e cadastro (wizard)

Ao criar novos cadastros/formulários, seguir o padrão de `/cadastro/`:

- **Models**: separar em models coesos (evitar um único model gigante); usar `verbose_name`,
  `choices` para seleção, `BooleanField` para sim/não, `TextField` para textos longos,
  `DateField` para datas e `DateTimeField(auto_now_add=True)` para criação. Relacionar por FK/OneToOne.
- Um `User` pode ter vários registros de negócio (ex.: `Aventureiro`) — usar `ForeignKey` para
  permitir reaproveitar dados no futuro.
- **Forms**: usar `ModelForm` sempre que possível; combinar vários forms num mesmo envio com `prefix`
  distinto para evitar colisão de nomes; centralizar o estilo dos widgets num mixin (classes CSS).
- **Wizard**: etapas em uma única página/`<form>`, mostradas/ocultadas via JS, com barra de progresso.
  A validação autoritativa é sempre no servidor; o JS apenas guia o preenchimento.
- **Campos condicionais**: campos "qual/motivo" aparecem só quando o "Sim" é marcado (JS), mas o
  backend deve aceitar o envio mesmo quando ocultos.
- **Pergunta Sim/Não obrigatória**: quando o cadastro precisa que a pessoa **responda** Sim ou Não (não só
  um checkbox), usar `forms.TypedChoiceField` (helper `campo_sim_nao` em `forms.py`, `coerce` para bool) +
  parcial **`_campo_simnao.html`** (radios lado a lado). O detalhe "qual" fica `required=False` e é exigido no
  `clean()` só quando "Sim". Os blocos condicionais desses Sim/Não usam **`data-depende-nome="{{ campo.html_name }}"`**
  (grupo de radios), tratado no JS do wizard — diferente do `data-depende` (id de checkbox) antigo.
- **Ficha médica**: o corpo é compartilhado (aventureiro + diretoria) no parcial `_ficha_medica_campos.html` e
  no mixin `FichaMedicaCamposMixin` (forms.py) — alterar num lugar só.
- **Validação com aviso (wizard)**: `static/js/wizard_validacao.js` (`window.WizardValidacao`) acha os
  `[required]` vazios num escopo (etapa ou form), lista os rótulos na caixa `#avisoValidacao` e pula até o
  primeiro. Chamar no "Próximo" (etapa atual) e no "Finalizar" (form todo + assinaturas). A validação do
  servidor continua sendo a autoritativa.
- **Uploads**: usar `ImageField`/`FileField` com `MEDIA_URL`/`MEDIA_ROOT`; em DEBUG o Django serve a mídia.
  Requer `Pillow` para imagens. Mostrar preview no navegador quando possível.
- **Aceites obrigatórios**: validar no servidor (não confiar só no JS).
- Reaproveitar os parciais `templates/core/_campo.html` e `_campo_check.html` para renderizar campos.
- Sempre criar as migrations ao alterar models (`makemigrations` + `migrate`).

## Padrão de cadastro de múltiplos aventureiros (mesma conta)

Um mesmo usuário/responsável pode cadastrar vários aventureiros. O fluxo é:

- **Cadastro inicial** (`/cadastro/`): cria a conta de acesso **e** o primeiro aventureiro.
- **Novo aventureiro** (`/cadastro/novo-aventureiro/`, nome `core:cadastro_novo_aventureiro`):
  cadastra outro aventureiro **na mesma conta**, sem a etapa "Conta de acesso".
- Após o cadastro, a tela de sucesso (`/cadastro/sucesso/`) oferece "Cadastrar outro aventureiro"
  e "Ir para a tela inicial".

Regras técnicas deste fluxo:

- **Identificação temporária do usuário**: enquanto a autenticação real (login/logout) não existe,
  o id do usuário é guardado na sessão nas chaves `cadastro_usuario_id` e `cadastro_ultimo_nome`
  (constantes `SESSAO_USUARIO_ID` / `SESSAO_ULTIMO_NOME` em `core/views.py`). Isso é **temporário**:
  quando o login real existir, trocar por `request.user`.
- A rota de novo aventureiro **exige** `cadastro_usuario_id` na sessão; sem ele, redireciona para
  `/cadastro/`. Nunca cria um novo `User` nesse fluxo — apenas vincula o aventureiro ao usuário atual.
- **Reaproveitar sem duplicar template**: o mesmo `templates/core/cadastro.html` serve os dois fluxos,
  controlado pelas variáveis de contexto `modo_novo` e `conta_form` (a etapa "Conta" só aparece quando
  `conta_form` existe). A numeração das etapas e os índices usados pelo JS são calculados
  dinamicamente em `static/js/cadastro.js` (não fixar números de etapa no código).
- **Reaproveitar dados dos responsáveis**: no fluxo de novo aventureiro, o backend envia os dados de
  pai/mãe/responsável legal do último aventureiro (helper `_dados_responsaveis_anteriores`) via
  `json_script`; o JS preenche os campos quando o usuário marca a opção, e ele ainda pode editar.

## Padrão de autenticação e área logada

O sistema usa a **autenticação padrão do Django** (username + senha). Ao mexer em telas
internas ou no fluxo de login, seguir estas regras:

- **Login** (`core:login`, rota `/`): a view usa `authenticate` + `login`. Os campos do formulário
  se chamam `usuario` e `senha`. O form é **AJAX** (`data-ajax-toast` + `ajax_form.js`): senha errada
  **só repete o toast, sem recarregar** a página (view responde `{"msg","tipo"}`); sucesso responde
  `{"redirect": url}` e o JS navega. Sem JS, POST normal com `messages.error` (o login renderiza
  `.mensagens`); também mostra mensagens de outros fluxos (ex.: "Senha redefinida…" da recuperação).
  Respeita o parâmetro `next` (validado com `url_has_allowed_host_and_scheme`).
- **Logout** (`core:sair`, rota `/sair/`): view protegida por `@require_POST` (usar sempre um
  `<form method="post">` com `{% csrf_token %}`, nunca um link GET). Redireciona para o login.
- **Proteção de telas internas**: usar `@login_required` nas views logadas. Estão configurados
  em `settings.py`: `LOGIN_URL`, `LOGIN_REDIRECT_URL` e `LOGOUT_REDIRECT_URL` — reutilizar.
- **Cadastro inicial**: após criar o `User` (com `create_user`, senha via hash — nunca texto puro),
  fazer `login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")` para já
  deixar o usuário autenticado.
- **Fluxos logados** devem usar `request.user` como fonte de verdade. A sessão
  (`cadastro_usuario_id`) permanece apenas como retaguarda no cadastro de novo aventureiro.
- **Preferir dados prontos na view**: cálculos de exibição (idade, listas de classes/doenças/alergias)
  são feitos na view e anexados ao objeto; o template só exibe. Reutilizar a parcial
  `templates/core/_dado.html` (rótulo + valor) para listar campos.
- **Detalhes recolhíveis**: usar `<details>/<summary>` nativos (sem biblioteca), estilizados via CSS.
- Preservar o layout da área interna (menu lateral fixo no desktop / gaveta no mobile) e a paleta.

## Padrão de exibição e edição em "Meus Dados"

- **Responsável principal**: derivado dos campos `resp_*` do aventureiro mais recente do usuário
  (cidade/estado vêm do `AutorizacaoImagem` do mesmo aventureiro). Sem aventureiros, exibir os
  dados básicos da conta (`request.user`).
- **Edição do responsável** (`core:editar_responsavel`): como o responsável é gravado em cada
  `Aventureiro`, a alteração é propagada para **todos os aventureiros do usuário logado com o mesmo
  CPF de responsável** (base: o mais recente); se nenhum coincidir, altera só o mais recente.
  Materializar a lista de alvos ANTES de alterar o CPF. Nunca tocar em dados de outro usuário.
  Usar o framework de `messages` para feedback e redirecionar para `core:inicio` após salvar.
- **Cards clicáveis**: usar `<details>` com o `<summary>` sendo o cabeçalho bonito do card
  (foto + nome + pílulas + status); ao abrir, mostrar as seções internas (também `<details>`).
- **Painéis/accordions aninhados**: remover o marcador nativo (`::-webkit-details-marker`) e indicar
  aberto/fechado via `.ver-mais` / `::after`. Nada de bibliotecas.
- **Responsividade**: em flex com texto longo (nomes, e-mails), usar `min-width: 0` +
  `overflow-wrap: anywhere` para permitir quebra; manter `overflow-x: hidden` no `body` como guarda.
- **Placeholders**: foto ausente → placeholder; campos vazios → "Não informado" (parcial `_dado.html`).
- **Foto do aventureiro**: exibir a imagem só quando o arquivo existir de fato — a view marca
  `av.foto_ok` via `foto.storage.exists(...)` (ter só o nome no banco não basta). Sem foto válida,
  mostrar placeholder com as iniciais do nome (`av.iniciais`). No `<img>`, incluir `onerror` que
  troca para o placeholder, para nunca exibir imagem quebrada.
- **Fechar painéis ao clicar fora**: em telas com `<details>` (ex.: "Meus Dados"), o
  `static/js/inicio.js` fecha os painéis abertos ao clicar fora deles e ao apertar `Esc`, e recolhe
  os demais quando um é aberto (accordion). Clique dentro do painel não fecha. Sem bibliotecas.
- **Cobertura de dados**: "Meus Dados" deve exibir TODOS os campos do cadastro, agrupados por seção
  (Dados pessoais, Documentos, Endereço, Pai, Mãe, Responsável legal, Ficha médica, Declaração
  médica e Autorização de imagem). Ao adicionar campos ao cadastro, refletir aqui também.

## Padrão de perfis e permissões

- **Perfis** são grupos nativos do Django (Diretor, Responsável, Professor, Tesoureiro, Secretário),
  criados pelo comando `configurar_perfis`. "Diretoria" é o grupo de integrantes do clube
  (diretor/secretário/tesoureiro/professor); "Responsável" é o lado dos pais.
- **Helpers** em `core/permissoes.py`: `eh_diretor(user)` e o decorator `diretor_required` (sem login
  → login; logado sem perfil Diretor → volta a `core:inicio` com mensagem). Usar `@diretor_required`
  em views restritas ao diretor.
- **Nos templates**: o context processor `core.context_processors.perfis` injeta `is_diretor` em todas
  as páginas. Envolver itens de menu/telas restritas em `{% if is_diretor %}`. Por enquanto, só o
  Diretor recebe permissões; os demais perfis existem sem permissões (liberar no futuro).
- **Atenção**: NUNCA escrever tags de template (`{% ... %}`) dentro de comentários HTML `<!-- -->` nem
  usar `{# ... #}` de múltiplas linhas (o `{# #}` é de uma linha só; para várias, usar
  `{% comment %}...{% endcomment %}`). Ambos os casos quebram o parser (tag "solta"/recursão).

## Padrão da tela "Usuários" (vínculos familiares)

- **Rota** `core:usuarios` (`/usuarios/`), com `@diretor_required` — **restrita ao perfil Diretor**
  (pois exibe dados completos/sensíveis). O item de menu "Usuários" aparece só para o diretor
  (`{% if is_diretor %}`).
- **Agrupamento de responsáveis** (helpers em `core/views.py`): para cada aventureiro considerar
  pai, mãe e responsável legal; a chave de deduplicação é `_chave_responsavel` — CPF, senão
  nome+WhatsApp, senão nome normalizado (`_normaliza` remove acentos/caixa); responsáveis sem nome
  são ignorados. A mesma pessoa em papéis diferentes aparece uma única vez, com os papéis juntos.
  Guardar também o contato (CPF, e-mail, celular, WhatsApp) para exibir no modal.
- **Vínculos**: por responsável, listar os aventureiros ligados (nome, idade e papéis do vínculo).
  Contadores: Responsáveis (pessoas únicas), Aventureiros (total), Vínculos (total de relações
  papel×aventureiro).
- **Cards clicáveis → modal com TODOS os dados**: cada card (responsável ou aventureiro) tem
  `class="clicavel" data-modal="<id>"`. O detalhe completo é renderizado no servidor dentro de
  `#detalhesFonte` (que fica **fora** de `.conteudo-interno`, para não entrar na pesquisa nem no
  accordion de `inicio.js`), num `<div id="detalhe-<id>" data-titulo="...">`. O `static/js/usuarios.js`
  clona esse conteúdo para o `#modalCorpo`, expande as seções e abre o modal (fecha no X, ao clicar
  fora e com Esc). Como a tela é restrita ao Diretor, aqui **é permitido exibir dados sensíveis**
  (CPF, contato, ficha médica, foto) — o detalhe do aventureiro reaproveita o parcial
  `core/_aventureiro_detalhe.html` (o mesmo de "Meus Dados").
- **Pesquisa**: filtro no front-end (`static/js/usuarios.js`) sobre o texto dos cards visíveis
  (`.busca-item`), ignorando caixa e acentos; mensagem "Nenhum vínculo encontrado para essa pesquisa."
  quando não houver resultado. Sem AJAX. O `#detalhesFonte` não é `.busca-item` (não entra na busca).
- **Reuso visual**: a tela reaproveita o layout/menu de `inicio.css`; estilos próprios em
  `static/css/usuarios.css`. Sem bibliotecas externas.

## Componente reutilizável de modal (janela suspensa)

- Os estilos genéricos do modal (`.modal-overlay`, `.modal-caixa`, `.modal-topo`, `.modal-titulo`,
  `.modal-fechar`, `.modal-corpo`, `body.modal-aberto`, animação e tela cheia no celular) ficam em
  `static/css/base.css` (compartilhados). O CSS da página só acrescenta o conteúdo específico.
- Estrutura HTML padrão: `<div class="modal-overlay" id="..." hidden>` › `.modal-caixa[role=dialog]`
  › `.modal-topo` (`.modal-titulo` + `.modal-fechar`) › `.modal-corpo`.
- Comportamento (JS puro): abre exibindo (`hidden=false`) e trava o scroll (`body.modal-aberto`);
  fecha no botão **X**, ao **clicar no fundo** e com **Esc**. Colocar o modal **fora** de
  `.conteudo-interno` para não conflitar com o accordion de `inicio.js`.
- **Fechar no fundo com cuidado**: só fechar quando o **mousedown E o click** ocorreram no próprio
  overlay (rastrear um flag no `mousedown`). Sem isso, arrastar para **selecionar texto** de dentro do
  modal e soltar o mouse fora fecha o modal indevidamente.

## Formatação de valores (moeda)

- Valores monetários usam o filtro `moeda` (`core/templatetags/formato.py`): `{% load formato %}` e
  `{{ valor|moeda }}` → formato brasileiro `1.500,00` (ponto de milhar, vírgula decimal). Prefixar com
  `R$ ` no template. Não usar `floatformat` para dinheiro (não coloca separador de milhar em pt-BR).
- **Reexibir número em `<input type="number">` cru**: passar **string com ponto** (ex.: `str(v.valor)`)
  ou usar `unlocalize`. Um `Decimal`/`float`/`int` grande é **localizado** no template em pt-BR (vírgula
  decimal / ponto de milhar) e o `type="number"` **rejeita** esse formato, deixando o campo **vazio**.
  Já mordeu na edição de produto da lojinha (preço/estoque não vinham).

## Padrão da tela "Eventos"

- **Rotas** `core:eventos` (`/eventos/`) e `core:evento_novo` (`/eventos/novo/`), ambas
  `@diretor_required`. Item de menu "Eventos" só para o diretor (`{% if is_diretor %}`).
- **Criar evento**: um único botão "Criar evento" abre o **modal** de escolha de tipo com dois cards —
  "Evento simples" (link para `core:evento_novo`) e "Evento com inscrição" (desabilitado, "Em breve").
- **Tipos**: `Evento.tipo` = `simples` | `inscricao`. Só o `simples` é cadastrável hoje; o `inscricao`
  (inscrição pública, pagamento, custos, presença, descontos) virá depois.
- **Recadastro rápido**: cada evento tem **Duplicar** (`?duplicar=<id>`), que pré-preenche o formulário
  com os dados daquele evento (a view monta o `initial`); o usuário ajusta a data/horário e salva.
- **Excluir evento** (`core:evento_excluir`, POST, `@diretor_required` + `@require_POST`): só é permitido
  quando o evento está **vazio** — **sem nenhuma inscrição e sem nenhum pedido**. Isso protege dados de
  pessoas/vendas (nunca apagar por data: um evento futuro pode já ter inscritos/pedidos). O botão
  **Excluir** só aparece nos eventos vazios (`e.pode_excluir`, calculado na view), e a **view revalida a
  regra** no servidor. Ações destrutivas pedem confirmação via `<form data-confirmar="...">` (guarda em
  `static/js/eventos.js` que chama `confirm()` no submit) — reutilizar esse padrão para novas exclusões.
- **Formulário**: `EventoForm` (ModelForm) reaproveita o parcial `_campo.html`; os campos são
  estilizados em `eventos.css` escopados por `.evento-form` (sem carregar `cadastro.css`, que tem
  `body {}` global e conflitaria com o layout interno). `tipo` e `criado_por` são definidos no servidor.
- **Reuso visual**: telas de evento usam o layout/menu de `inicio.css`, o modal de `base.css` e estilos
  próprios em `static/css/eventos.css`. Sem bibliotecas externas.

### Evento complexo (com inscrição) — em fases

- É um **mini-sistema por evento**, construído em fases. O plano completo (todas as fases, módulos e a
  referência do sistema antigo) está em `docs/PLANEJAMENTO_EVENTO_COMPLEXO.md` — **consultar antes de
  evoluir** e manter atualizado a cada fase concluída.
- Reaproveita o modelo `Evento` (`tipo=inscricao`) como base; módulos entram como modelos relacionados
  por FK ao `Evento` (ex.: `CustoEvento`). O evento complexo tem `data_fim` (eventos de vários dias).
- Abre num **painel dedicado** (`core:evento_painel`, `/eventos/<id>/`) com **abas** (Resumo,
  Inscrições, Lojinha, Custos, Financeiro) trocadas no cliente (`static/js/evento_painel.js`); abas de
  fases futuras ficam como "em breve". Ações que gravam (ex.: custos) são POST e redirecionam para o
  painel com a hash da aba (ex.: `#custos`).
- **Sub-abas** (abas DENTRO de uma seção; ex.: Inscrições → Lista/Configuração/Faixas/Formulário): usar
  o padrão `.sub-abas` > `.sub-aba[data-sub]` + `.sub-secao[data-subsecao]` (a inicial visível, as demais
  com `hidden`). O JS em `evento_painel.js` é **genérico e escopado** à `.painel-secao` pai (cada barra
  só mexe nas próprias sub-seções) — reutilizar para novas seções (ex.: Lojinha → Produtos/Pedidos).
- **A janela extra da diretoria não é anunciada em tela pública** (`Evento.inscricao_limite_diretoria`).
  Passado o **prazo comum**, a página do evento diz apenas "Inscrições encerradas", **o botão de inscrever
  some para todo mundo** e o erro de POST fora do prazo é **genérico** — quem é recusado não fica sabendo
  que existe janela extra. A diretoria entra pelo **link direto** de `/eventos/<id>/inscrever/`, que a view
  continua abrindo pelo prazo mais generoso; a regra de verdade é a **validação do POST** pela composição
  real da inscrição, com a trava final no model. O **menu do Responsável** segue o mesmo prazo comum
  (`_eventos_menu(user, perfil)` em `core/context_processors.py` filtra por `inscricoes_abertas()` no perfil
  **Responsável**) — e com o item de menu some também o caminho dele para a **lojinha** daquele
  evento. `tem_prazo_diretoria` e `so_diretoria_pode_inscrever` são **estado interno**: só o **painel do
  Diretor** os exibe. **Tela pública nova de evento segue o prazo comum.**
- **Pagamentos ficam simulados** até a fase específica; nunca integrar gateway sem autorização.
- Fase 1 (feita): base + painel/resumo (indicadores) + Custos (com comprovante). Próximas: Inscrições,
  Página pública, Lojinha, Financeiro/gráficos; depois, pagamentos reais e mapa.

#### Financeiro × Resumo (dashboard) — divisão de responsabilidades

- **Aba Financeiro = o extrato/contabilidade** (números precisos): resultado (Entradas − Saídas),
  resumos em cards (por fonte, por forma de pagamento, por canal, saídas), "vendidos por produto" e o
  **extrato** cronológico de todos os lançamentos. Dados montados em `_montar_financeiro` (`views.py`).
- **Aba Resumo = o dashboard visual**: KPIs de topo + **gráficos** (a fazer em CSS/SVG puro, sem libs).
- **Regra anti-duplicação**: **número/tabela mora no Financeiro; gráfico mora no Resumo.** O único
  indicador repetido de propósito é o **Resultado**. Não colocar a mesma tabela nas duas abas.
- **Totais**: só entram lançamentos **confirmados**; **cancelados** aparecem no extrato (riscados, para
  auditoria) mas ficam **fora** dos totais. **Cortesia** conta como transação com valor **R$ 0**.
- **Custos** continuam sendo **cadastrados na aba Custos** (com comprovante); o Financeiro só
  **consolida** (não duplicar o CRUD de custos).
- **Entrada é o que ENTROU, não o que foi vendido.** Uma inscrição pode valer mais do que já foi recebido
  (parcelamento do valor da diretoria), então **toda soma de caixa de inscrição usa
  `Inscricao.valor_no_caixa`** (`valor_total` − parcelas em aberto), nunca `valor_total`. Já aplicado em
  `evento_painel_view`, `_montar_financeiro` e `financeiro_view` — **soma nova precisa fazer o mesmo**.
- **No extrato, cada lançamento vale o que caiu naquela data.** A linha da inscrição usa `valor_no_ato` (o
  total menos todas as parcelas que **não** foram cobradas no ato) e **cada parcela paga vira um lançamento
  próprio**, na data do pagamento. Usar `valor_no_caixa` na linha da inscrição contaria a parcela **duas
  vezes** (uma na inscrição, outra no lançamento dela). Há teste que soma o extrato e compara com a
  arrecadação — mantê-lo passando é a garantia dessa regra.
- **Quem separa as duas coisas é `ParcelaInscricao.no_ato`, NUNCA o número da parcela.** Desde que a 1ª
  parcela pode ser jogada para o mês seguinte, "parcela 1" não quer mais dizer "parcela cobrada no ato": num
  evento com a 1ª diferida **nenhuma** parcela entrou no caixa no dia da inscrição, e a 1ª paga depois é
  lançamento próprio como qualquer outra. Filtro novo de extrato/caixa usa a flag; voltar a filtrar por
  `numero == 1` faz a 1ª parcela diferida ser contada duas vezes.
- **1ª parcela da diretoria: cobrar na inscrição ou jogar para o mês seguinte** é opção **por evento**
  (`Evento.parcelas_diretoria_primeira`; `primeira_parcela_no_ato()`). Jogando para o mês seguinte, ela vence
  no dia **`DIA_VENCIMENTO_PARCELA` (10)** do mês que vem — **dia fixo, que não depende do dia da inscrição**
  (é o que a família consegue guardar) — e a parte da diretoria **inteira** sai da cobrança do ato: numa
  inscrição só de diretoria **não há cobrança nenhuma** e a inscrição é criada na hora, sem passar pela tela
  de pagamento. O que os outros participantes devem e a lojinha **continuam integrais no ato**. Por isso o
  fluxo da inscrição decide o parcelamento **antes** de falar com o gateway e só cobra quando
  `a_pagar_agora > 0`: cobrança de R$ 0,00 não existe. E o `primeira_no_ato` viaja **no payload** do
  pagamento — entre o POST e a aprovação do Pix a configuração do evento pode mudar, e vale a regra que a
  pessoa viu na tela.
- **Dinheiro a receber não é dinheiro fora do caixa.** São dois controles diferentes, com cards separados:
  **"Fora do caixa"** = pago direto ao evento, o clube **nunca** recebe (âmbar); **"Parcelas da diretoria"**
  = é do clube, só **ainda não chegou** (azul). Não juntar os dois nem somar o "a receber" nas entradas.

##### Gráficos e dashboard (Resumo) — regras

- **Sem biblioteca de gráficos** (nada de Chart.js/D3/etc.): tudo em **CSS/SVG puro**. Barras =
  `div` com `width: %` (percentual calculado **na view**); donut = `<svg>` com `pathLength="100"` +
  `stroke-dasharray="<pct> 100"` (o `pct` já vem pronto do backend).
- **Cor pela função, com rótulo sempre**: magnitude (mesma medida entre categorias) usa **um tom só**
  (azul); status usa **verde** (positivo/receita/presente) e **vermelho** (negativo/custo). **A cor
  nunca é a única pista** — todo valor tem rótulo em texto (ex.: barras verde/vermelho de receitas×custos
  vêm rotuladas). Não criar paleta categórica de muitas cores.
- **Cobertura do clube por nome (melhor esforço)**: como a inscrição guarda o nome do participante como
  **texto livre** (sem vínculo com `Aventureiro`), a cobertura casa por **conjunto de nomes** — tokens
  sem acento/caixa e **sem conectores** (`_tokens_nome`): o participante casa quando **todos os nomes
  digitados ⊆ nome cadastrado** **e** o resultado é **único** (senão vira "a conferir", nunca casa
  errado). É referência, não verdade absoluta — deixar claro na tela. O **vínculo exato** (selecionar o
  aventureiro na inscrição, dentre os do próprio responsável logado) é o caminho definitivo (a fazer).
- **Busca em tempo real** reaproveita o padrão do `usuarios.js` (helper `ligarBusca` em
  `evento_painel.js`): normaliza (sem acento/caixa) e filtra por `data-busca`. **Esconder itens com a
  classe `.busca-oculto` (`display:none !important`), NUNCA com o atributo `hidden`** — itens com
  `display:flex`/`grid` ignoram o `[hidden]` do UA stylesheet e não somem. Mostra "nada encontrado"
  quando zera. Sem AJAX.
- **Regra geral desse mesmo tropeço** (já custou duas vezes): um elemento com `display:flex`/`grid`
  **não desaparece** com o atributo `hidden` — a declaração da classe ganha do `[hidden]` do UA
  stylesheet. Ao esconder um bloco flex/grid pelo `hidden` (padrão de "só aparece quando o JS decide",
  ex.: `.insc-parcelar` do parcelamento), **escreva também `.classe[hidden] { display: none; }`**.
  Nenhum teste Python pega isso: só se vê renderizando — conferir com a sonda do Chrome headless,
  medindo `getBoundingClientRect().height` do bloco que deveria estar escondido.

### Pagamentos (simulados) — lojinha pública

- A compra pela **página pública** da lojinha (`core:evento_loja`) tem um **passo de pagamento**
  (`core:evento_pagamento`, `/eventos/<id>/loja/pagamento/`) antes de confirmar. Formas **online**:
  **Pix** e **Cartão de crédito** (constante `FORMAS_PAGAMENTO_ONLINE` em `views.py`); dinheiro e
  cortesia continuam só no **PDV/balcão**.
- **O pedido só é criado no banco APÓS a aprovação** do pagamento. Enquanto pendente, os dados ficam
  na **sessão** (`request.session["loja_checkout"]` = itens + comprador + forma). Assim não há pedido
  "pendente" no banco nem estoque reservado por carrinho abandonado. A **baixa de estoque** (revalidada
  com `_erros_estoque`) e a criação do `PedidoLoja` (via `_criar_pedido`, `origem="online"`) acontecem
  só na aprovação. Após aprovar, limpar `loja_checkout` da sessão.
- **Pagamento é SIMULADO** por ora: a tela mostra o processo (Pix com **QR Code decorativo** — helpers
  `_pseudo_qr`/`_qr_svg` — e **código "copia e cola" fictício** — `_pix_copia_cola`; cartão com aviso de
  **redirecionamento ao Mercado Pago**) e um botão **"Simular pagamento aprovado"**. O QR e o payload
  Pix **não são reais/escaneáveis** e são gerados **sem biblioteca externa** (regra do projeto). O
  pagamento real (Pix/BR Code real e API do Mercado Pago) fica para a integração do gateway — **nunca
  integrar gateway sem autorização**.
- **WhatsApp obrigatório** (e-mail opcional) nos dados do comprador da loja pública. Os dados do
  comprador são lembrados no **localStorage** do aparelho (`static/js/loja_comprador.js`) e
  autopreenchidos em pedidos seguintes — sem back-end, funciona logado ou anônimo.

## Módulo WhatsApp (W-API)

- **Rotas** `core:whatsapp` (`/whatsapp/`), `core:whatsapp_config` e `core:whatsapp_enviar`, todas
  `@diretor_required`. Item de menu **WhatsApp** (💬) só para o diretor (`{% if is_diretor %}`).
- **Configuração** em `WhatsappConfig` (**singleton**, `get_solo()`): `instance_id`, `token`, `base_url`.
  **Nunca exibir o token inteiro** — só `token_mascarado` (últimos 4 dígitos). Ao salvar, **token vazio
  não sobrescreve** o guardado (permite editar o resto sem redigitar o token).
- **Envio**: `POST {base_url}/message/send-text?instanceId=<id>`, header `Authorization: Bearer <token>`,
  body JSON `{"phone","message"}` (docs W-API). Feito com **urllib** da stdlib — **não** adicionar
  `requests` nem outra dependência.
- **Normalização do telefone** (`normalizar_telefone` em `views.py`) é a fonte da verdade (aceita
  espaços/traços/parênteses/`+55`/`00…` → DDI 55 + dígitos). O JS só **espelha** essa lógica para a
  **prévia ao vivo**; a validação real é no back-end. Envio é **AJAX** e usa o **toast padrão**
  (`window.mostrarToast`).
- **Mensagem longa é dividida, nunca cortada**: `_partir_texto_whatsapp` (usado dentro do
  `_notificar_whatsapp`) quebra o texto que passa de `LIMITE_MSG_WHATSAPP` em **partes numeradas**, cortando
  só em quebra de linha. Ao montar mensagem que cresce com o tempo (ex.: lista de inscritos de um evento),
  **não invente um teto que descarta conteúdo** — numa lista de pessoas, o que "não cabe" é gente.
- **Não enviar mensagens reais em testes automatizados** nem versionar tokens/IDs reais.

## Recuperação de senha pelo WhatsApp

- Fluxo **público** em 3 etapas (`/recuperar-senha/`, `.../codigo/`, `.../nova-senha/`), estado na
  **sessão** (`request.session["recup"]`). Etapas com guarda: código exige sessão; nova senha exige
  `validado=True`. Já logado → redireciona para `/inicio/`.
- **Identificação por CPF em DOIS lugares** (`_conta_por_cpf`): o **responsável legal** de um aventureiro
  (`Aventureiro.resp_cpf`) **e** a **ficha de diretoria** (`MembroDiretoria.cpf`), comparando **só dígitos**
  (`_so_digitos`) e ignorando `demo`. Prefere conta **ativa**. Procurar só no `resp_cpf` deixava **quem é da
  diretoria e não tem filho no clube sem nenhum caminho** de recuperação — se aparecer um cadastro novo com
  CPF (ex.: professor, ajudante), **acrescente-o aqui também**. O helper devolve `(usuario, via_diretoria)`.
- **Destino do código** (`_whatsapp_recuperacao`), nesta ordem: **escolha do Diretor** (WhatsApp principal,
  `PerfilUsuario.whatsapp_principal_origem`) > **WhatsApp da ficha de diretoria**, quando o CPF veio dela >
  **responsável legal** (`_whatsapp_principal`) > ficha de diretoria como **fallback**. O caso do meio é a
  regra que importa: quem pediu com o próprio CPF **recebe no próprio número** — mandar para o cônjuge
  (responsável legal do aventureiro) deixa a pessoa sem o código. **Não** resolver o destino por
  `_numeros_conta` sozinho: ele lê só pai/mãe/responsável **dos aventureiros**, e devolve vazio numa conta que
  só tem ficha de diretoria (era o segundo bloqueio do mesmo bug).
- **A tela do código mostra o usuário de acesso** da conta encontrada (card `.recup-usuario`), e a mensagem
  do WhatsApp leva o login junto do código — o esquecimento comum é o **usuário**, não a senha. O login é
  guardado na sessão do fluxo (`recup["usuario"]`) por quem gera o código, para o **reenvio** repetir sem
  consulta extra. **Consequência aceita:** quem souber o CPF de um responsável descobre o login sem ter o
  celular da família — por isso a etapa 1 **nunca** pode revelar nada quando o CPF não existe, e um
  **throttle** aqui é ainda mais necessário (cada POST válido dispara um WhatsApp real).
- **Código de 4 dígitos** gerado com `secrets.randbelow`, guardado **com hash** na sessão (`make_password`
  /`check_password`) — **nunca** em texto puro. Constantes: `RECUP_TTL_MIN=10`, `RECUP_MAX_TENTATIVAS=5`,
  `RECUP_REENVIO_ESPERA=60`. Número exibido sempre **mascarado** (`_mascara_telefone`).
- Reaproveita `normalizar_telefone` + `_enviar_whatsapp` do módulo WhatsApp (sem novas dependências).
- **WhatsApp principal**: só o Diretor define hoje (`/usuarios/conta/<id>/principal/`), no detalhe do
  responsável em Usuários; guarda a **origem** (pai/mãe/resp) e o número é resolvido ao vivo. O bloco só
  aparece quando o CPF do responsável liga a **exatamente uma** conta.
- Feedback usa o **toast padrão** do sistema (framework de `messages` → `.mensagens`/`.mensagem`), igual
  ao resto. As telas públicas carregam `inicio.js` (o módulo de toasts é seguro em qualquer página) e o
  **CSS do toast fica no `base.css`** (componente reutilizável, com fallback de cores) — não no `inicio.css`.
- **Envio por AJAX** (`static/js/ajax_form.js`, `form[data-ajax-toast]`): erro **repete o toast sem
  recarregar** a página; sucesso navega. Contrato JSON quando `X-Requested-With: XMLHttpRequest`:
  `{"redirect": url}` (JS navega) ou `{"msg","tipo"}` (só toast). Helpers `_eh_ajax`, `_ajax_redirect`,
  `_ajax_toast`. Sem JS, POST normal (fallback com `messages`). **Componente genérico**: o **login**
  também usa (senha errada só repete o toast, sem recarregar) — ver regra de Login.
- **Cuidado com vazamento de `messages`**: mensagem enfileirada antes de um `redirect` só é consumida se
  a página de **destino renderizar `{% for m in messages %}`**. Por isso o **login também renderiza
  messages** (mostra "Senha redefinida…" e não deixa a mensagem sobrar para telas seguintes).


## Edição na tela de Mensalidades: voltar para onde a pessoa estava

- **Ação de card devolve o card, não o topo da tela.** Isenção/desconto, ✏️ editar o mês e "Gerar {ano}" são
  POST + redirect; o redirect passa por **`_volta_mensalidades(request, ano, av_id)`**, que remonta `aba`,
  `ano`, `av`, `q` e `deve`. Redirecionar só para `?ano=` devolve o painel na aba **Resumo** (o padrão), com o
  card fechado e a busca apagada — e isentar o ano de uma criança é **mês a mês**. Ação nova nesse card usa o
  mesmo helper.
- **O aventureiro sai do SERVIDOR** (`m.aventureiro_id`, `av.id`): o card certo reabre **mesmo sem JS**, e um
  destino vindo do formulário seria uma forma de mandar o usuário para outro lugar. **Só estado de tela**
  viaja em campo oculto (busca, "só quem deve" e a aba, em `templates/core/_mens_volta.html`, nos formulários
  com `data-volta`) — é o que o servidor não tem como adivinhar.
- **O card que volta aberto escapa do "só quem deve"** até a pessoa mexer no filtro: isentar zera a dívida, e
  ver o card sumir logo depois de salvar parece que a edição falhou.
- **Não transformar essas ações em AJAX sem pensar duas vezes.** A isenção recalcula **todos** os meses em
  aberto do ano; atualizar isso no navegador significa repetir em JS o desenho das linhas de mês. "Marcar
  pago" é AJAX porque mexe em **uma** linha e devolve o resumo pronto (`mensalidade_pagar_view`).
- **`av` inválido na URL não é 404** — é um card a menos aberto. A URL é colável e editável.

## Parcelamento lançado pelo clube (Mensalidades → Parcelas)

Lançamento **manual** de parcelas para uma conta (família ou diretoria), dividido no dia
`DIA_VENCIMENTO_PARCELA` mês a mês. Não confundir com `ParcelaInscricao`, que é o parcelamento do valor da
**diretoria dentro da inscrição** de evento e nasce sozinho no ato.

- **O vínculo é com a CONTA** (`ParcelamentoClube.usuario`), não com o aventureiro. É isso que faz o mesmo
  lançamento servir para família e para **diretoria sem filho no clube**. `aventureiro` é opcional (diz *por
  quem* é o acerto) e `evento` é opcional (diz *de onde* veio a dívida).
- **O seletor "para quem" tem TRÊS grupos** (`_alvos_parcelamento`): Aventureiros (`av:<id>`, ativos),
  **Responsáveis** (`resp:<av_id>:<papel>`, a família pelos adultos da ficha — **pai, mãe e responsável
  legal**, uma opção cada, em `_alvos_responsaveis`; quem acumula papéis vira uma opção só) e Diretoria
  (`conta:<id>`). Os três levam à **mesma conta**. A conta que já está em Diretoria **não** se repete em
  Responsáveis, e esse grupo **não filtra `ativo`** — é a exceção do parcelamento (dívida combinada continua
  devida), então a família cujo aventureiro saiu ainda precisa ser alcançável. `demo` fica fora dos três.
- **Escolher uma PESSOA e guardar só a CONTA perde a escolha.** Pai, mãe e responsável legal dividem a
  mesma conta: enquanto as três opções mandavam `conta:<id>` puro, o nome escolhido morria no POST e
  `pessoa_nome` o recalculava pelo `resp_nome` — **o acerto combinado com o pai reaparecia no nome da
  responsável legal**, no painel, no resumo copiado, nos dois extratos, na aba de cobrança e na saudação da
  página pública. Foi bug real. Por isso o alvo carrega o **papel** e `_resolver_alvo` devolve
  `(usuario, aventureiro, pessoa)`, com o nome lido **da ficha, no servidor** — rótulo que o navegador
  mandasse não é fonte de verdade. **Opção de seletor que o usuário distingue pelo nome precisa gravar esse
  nome**; se o alvo não o carrega, ele se perde.
- **`ParcelamentoClube.pessoa` é snapshot** (mig. **0074**), como os outros nomes do sistema: corrigir a
  ficha depois não reescreve o que foi combinado. Vem **antes** da ficha em `pessoa_nome` e **depois** do
  aventureiro (escolher a criança deixa `pessoa` vazia, então não há disputa). Lançamento anterior à
  migration tem o campo vazio e continua caindo nos degraus de baixo — a escolha daquele dia não foi
  gravada e não há como recuperá-la.
- **Mensagem para a CONTA só chama alguém pelo nome quando a conta tem um dono só.**
  `_nome_da_conta(usuario, lancamentos)` usa a `pessoa` apenas se **todos** os lançamentos apontam para ela;
  com adultos diferentes na mesma conta, volta ao responsável da família. Errar o nome de quem recebe a
  cobrança é pior do que usar o nome genérico.
- **Id vindo do POST passa por `isdigit` antes do `filter`** (`_aventureiro_do_alvo`). Um alvo forjado
  (`av:abc`) estoura `ValueError` dentro do ORM e vira **500 de HTML** numa view cuja recusa é uma mensagem
  na tela — a mesma lição de `minutos`/`quantos` no leilão.
- **`_numeros_conta` NÃO basta para achar o WhatsApp de uma conta** — ele lê só os **aventureiros**, então
  numa conta de **diretoria sem filho no clube** devolve lista vazia. A cobrança dizia "sem WhatsApp
  cadastrado" (com o botão de enviar desabilitado) para quem tem o número gravado na ficha; havia até um
  `if not numero: numero = _whatsapp_familia(u)` que **não resolvia nada**, porque o helper refazia a mesma
  conta. O degrau que falta é sempre **`_whatsapp_diretoria(usuario)`**, como a recuperação de senha já
  fazia. Quem for buscar o número de uma conta: `_whatsapp_familia` (que agora já cai na ficha) ou
  `numero or _whatsapp_diretoria(u)`.
- **Sem escolha e sem responsável legal, `_resolver_origem_numero` usa o primeiro número que existir.**
  Antes ele só olhava `resp` e desistia: a ficha preenchida apenas com o WhatsApp do pai ou o da mãe
  aparecia como "sem número". Dizer que não há número quando há é pior do que escolher um.
- **Virar diretoria numa conta que já existe passa por `/meus-dados/diretoria/`, nunca pelo
  `/cadastro/diretoria/`.** Aquele **cria conta** (`User.objects.create_user`) — usá-lo para quem já tem login
  parte a família em dois cadastros. O caminho novo tem três donos: o **Diretor** libera a conta em Usuários
  (`PerfilUsuario.liberacao_diretoria_em`), a **pessoa** preenche e assina, e o **Diretor** define o papel em
  `/usuarios/diretoria/`. A gravação é a mesma nos dois caminhos (`_gravar_ficha_diretoria`) — mexeu num,
  conferiu o outro.
- **A liberação é consumida e conferida na view.** Ao gravar a ficha, `liberacao_diretoria_em` volta a vazio:
  liberação não é permissão permanente. E `pode_cadastrar_diretoria` é checado no **GET e no POST** — esconder
  o botão no HTML não barra envio forjado.
- **Definir o papel SUBSTITUI o grupo "Diretoria"** (`diretoria_papel_view` remove todos e aplica um). Quem
  escrever regra por perfil não pode assumir que o professor também está em "Diretoria" — ele **não está**.
- **Quem é só diretoria não tem tela de mensalidade.** Por isso o que ela deve aparece no card **Minhas
  parcelas** de "Meus Dados" (`_minhas_parcelas`), que cobre as **duas** origens (`ParcelaClube`, presa à
  conta, e `ParcelaInscricao`, presa à inscrição) e **reaproveita as páginas públicas por token** para pagar —
  não crie um segundo fluxo de pagamento logado.
- **Mudar o TEXTO PADRÃO de uma mensagem é mudar o `default` de um campo — e isso exige migration.** As
  mensagens/prompts padrão (`MENSAGEM_*_PADRAO`, `PROMPT_*_PADRAO`) são `default=` de campos do
  `ConfigMensalidade`: editar a constante muda o estado do model. O deploy roda `makemigrations --check` e
  **recusa** sem a migration (já aconteceu: o deploy caiu no rollback e o site ficou **502 por ~2 min**, porque
  o rollback do script **não refaz o `chown root:www-data`** do código). Rode `makemigrations` sempre que mexer
  numa dessas constantes; é só `AlterField`, nenhum dado muda e quem já salvou a própria mensagem continua com
  ela.
- **Copiar texto para o clipboard é UM arquivo: `copiar_texto.js`.** O texto vem **pronto do servidor** numa
  `<textarea class="copiar-fonte">` (fora da tela, nunca `hidden`: a cópia de reserva precisa de `select()` num
  campo que exista) e o botão `.btn-copiar-lista` aponta para ela por `data-fonte`. Já serve o painel do evento
  e a aba Parcelas; ao criar uma terceira tela, **ligue o mesmo arquivo** em vez de copiar o bloco.
- **O resumo copiável conta como os KPIs**: `_export_parcelamentos` deixa o lançamento **cancelado de fora**
  (só um contador no fim), porque os KPIs da aba somam só os ativos — dois números diferentes na mesma tela
  parecem erro. E **leva nomes**: é texto para a diretoria, não para grupo aberto.
- **Marcador de mensagem pode ser OPCIONAL** (`_aplicar_marcadores`, hoje `{evento}`/`{link_evento}` na cobrança
  de parcelas): quando vem vazio, a **linha inteira** que o usa é removida e o buraco de linhas em branco é
  fechado. Duas razões: a mensagem é escrita **uma vez** para todo mundo, e no **prompt da IA** um rótulo sem
  valor ("Evento: ") faz a IA inventar o que falta. Consequência a documentar na tela: marcador opcional vai em
  **linha própria**. Marcador obrigatório ({nome}/{itens}/{total}/{link}) não entra nessa regra.
- **Link só de página que abre**: `{link_evento}` sai apenas de evento **de inscrição e ativo** — a página
  pública do inativo é bloqueada (e a do evento simples não existe). Mandar link que não abre é pior do que
  não mandar.
- **Lançamento numa conta sem aventureiro precisa de um nome legível**: `pessoa_nome` tenta, nesta ordem,
  aventureiro → **`pessoa` escolhida no seletor** → ficha de diretoria → **`resp_nome` da família** →
  `get_full_name()`/username. Sem o último degrau útil a lista de parcelas mostrava o **nome de acesso** da
  conta; sem o segundo, mostrava o adulto errado da mesma família.
- **Não vire uma `Mensalidade`.** Ela é **uma por (aventureiro, ano, mês)** — colidiria com a mensalidade do
  mês —, não tem vencimento nem descrição, e é amarrada ao `Aventureiro`. E não vire uma `ParcelaInscricao`:
  ela exige uma `Inscricao` e o dinheiro dela entra no caixa **pelo evento**.
- **O lançamento nasce 100% a receber.** Nada é cobrado no ato, então **só a parcela PAGA é entrada** — em
  qualquer soma de caixa (Financeiro do clube, painel do evento) e no **extrato**, que leva **uma linha por
  parcela paga**. Lançar não move caixa nenhum. (Por isso aqui não existe a flag `no_ato` das parcelas de
  inscrição: nenhuma parcela é cobrada junto de outra coisa.)
- **A fonte do dinheiro é decidida pelo `evento`**: com evento, a parcela paga conta em **Eventos** (e no
  painel daquele evento, no canal próprio "Parcelamento do clube"); sem evento, na fonte **Parcelamentos**.
  Nunca nas duas — há teste.
- **A divisão do valor é a `dividir_em_parcelas`** (função de módulo em `models.py`), compartilhada com o
  parcelamento de evento: a sobra dos centavos vai na **1ª** parcela. Ela **cai para 1 parcela** quando o
  valor não dá R$ 0,01 por parcela (cobrança de zero não existe no gateway) — quem exige um número de
  parcelas **precisa conferir o tamanho da lista** e recusar, como faz o lançamento manual.
- **A regra "aventureiro inativo não é cobrado" NÃO vale aqui.** Ela é da cobrança **recorrente** de quem saiu
  do clube; um parcelamento é dívida **combinada** e continua devida, como as parcelas de inscrição. Há teste
  documentando a diferença — não "conserte" isso adicionando `aventureiro__ativo=True`.
- **A cobrança leva só o que VENCEU e o que vence DENTRO do mês** (`_q_parcelas_cobraveis`, em
  `_cobrancas_parcelas_familias`). Filtrar só por `status="aberta"` põe na mensagem o parcelamento
  **inteiro** — um acerto em 10x com as 10 parcelas e um `{total}` que a pessoa não deve hoje — e, pior,
  mantém na lista **quem já pagou a parcela do mês**, porque sobrou parcela futura em aberto. É a mesma
  regra do `_q_mens_vencidas()` das mensalidades, pelo mesmo motivo. Parcela **sem vencimento** entra:
  dívida sem data é dívida de agora. A **página pública é o contrário** (`_parcelas_abertas_conta` mostra o
  lançamento inteiro, porque lá a pessoa pode **adiantar** parcela) — não "uniformize" as duas; há teste
  para cada uma. O envio monta os destinatários pela **mesma função**, então a trava vale também para
  `usuario_id` forjado no POST.
- **A cobrança tem aba, mensagem e histórico PRÓPRIOS** (`CobrancaParcelaEnviada`). Contar junto com a
  mensalidade faria "já cobrei este mês" de uma **silenciar** a outra — é o mesmo motivo pelo qual o canal faz
  parte da identidade do registro. Mantenha o padrão de lote: **1 por request + 10s no front**.
- **Cancelar** um lançamento cancela **só as parcelas em aberto**; as pagas continuam no caixa e no extrato.
  A baixa manual **entra** no caixa (diferente da baixa do "pago direto ao evento"), e **reabrir solta o
  `pagamento`** para a taxa do gateway não ficar presa a uma parcela em aberto.
- **`demo` fica fora**: use o helper `_q_parcelamentos_clube()` (exclui aventureiro/evento fictícios) em
  **toda** estatística nova.
- **O link público aceita DOIS tokens** (`_lancamentos_por_token`): o de **um lançamento** (é o que o painel
  do Diretor mostra, para tratar de um acerto específico) e o da **conta** (`PerfilUsuario.token_acerto`, o
  mesmo do acerto de mensalidades), que abre **todos** os lançamentos ativos da pessoa. A **cobrança manda o
  token da conta** de propósito: a mensagem lista as parcelas de todos os lançamentos, então um link que
  mostrasse só um deles contradiria a própria mensagem. A página é uma **lista de blocos**, um por
  lançamento, e cada bloco posta no **seu** token — a cobrança é sempre de uma parcela de um lançamento.
- **Pagamento online**: uma cobrança **por parcela** (`tipo="parcela_clube"`), finalizada por
  `_finalizar_parcela_clube` — **idempotente**, porque o webhook do MP repete o aviso. A página pública
  `/parcelas/<token>/` é sem login, pelo mesmo motivo do acerto de mensalidades: quem recebe a cobrança pode
  não ter o login.
- **JS**: `mensalidade_cobranca.js` é **um arquivo para as duas abas** de cobrança (painel + prefixo de ids
  por parâmetro). Ao criar uma terceira, ligue-o de novo — não duplique. O clique do envio individual é
  ouvido **no painel**, não no `document`: no document, as duas instâncias respondem ao mesmo clique e a
  cobrança sai duas vezes.
- **Abas**: o trilho `.mens-abas` agora tem **5** pílulas e usa `flex-wrap` com `flex-basis: auto` — em
  telas estreitas as pílulas descem de linha em vez de empurrar a página. Ao acrescentar aba, confira a
  rolagem horizontal com a sonda (`scrollWidth` × `clientWidth`).

## Módulo de Leilão (`/leilao/`) — regras próprias

O leilão é **outra aplicação Django** na mesma base de código (settings, URLs, banco, cookies e serviço
próprios). Antes de mexer nele, ler `docs/PLANEJAMENTO_LEILAO.md`.

- **UM worker uvicorn, sempre.** O hub de eventos (`leilao/hub.py`) e o laço central vivem **na
  memória do processo**. Dois workers = dois hubs, e metade das pessoas vendo um pregão e metade
  vendo outro. Se um dia precisar escalar, o caminho é trocar o hub
  em memória por Redis pub/sub — **só isso** muda.
- **O leilão não pode morar no serviço do clube.** Ele usa **SSE**, que segura a conexão aberta; em
  worker **síncrono** (o do clube é gunicorn sync) cada participante prenderia um worker inteiro e
  derrubaria o site do clube junto.
- **`transaction_mode: IMMEDIATE` no SQLite não é detalhe.** Com o `BEGIN DEFERRED` padrão, uma
  transação que **lê e depois escreve** — que é **todo lance** — recebe `SQLITE_BUSY` na hora, **sem**
  respeitar o `busy_timeout`: o SQLite recusa em vez de arriscar um impasse. O resultado seria lance
  perdido no meio do pregão. "Um escritor só" vale para **processos**; dentro do processo, as views
  síncronas rodam num pool de **threads**, cada uma com a sua conexão.
- **O banco de teste do leilão é em ARQUIVO** (`TEST: {"NAME": ...}`), não em memória. O padrão do Django
  para SQLite é `:memory:` com *shared cache*, onde o `busy_timeout` não vale e duas threads escrevendo
  dão `database table is locked` — o que **esconderia** justamente o problema que o teste de lances
  simultâneos existe para pegar.
- **`get_solo()` de configuração NÃO escreve.** Era `get_or_create`, e ele é chamado pelo context
  processor a **cada página** e por uma thread de fundo a cada item vendido: toda leitura virava
  tentativa de escrita, disputando a trava com quem estava dando lance. Sem linha salva, devolve
  instância em memória.
- **O relógio é do servidor.** Não há cronômetro (o martelo é do locutor, e `Lote.fecha_em` está
  dormente), mas todo estado leva `servidor_em`: o navegador calcula a diferença uma vez e aplica, e é
  isso que mantém certo o contador "sem lance há…" da mesa num computador com a hora errada.
  **Nunca** mandar "faltam N segundos" e deixar o cliente contar sozinho.
- **O broadcast só leva o que pode ser dito em voz alta**: nome curto e valor. **Código Pix, telefone e
  endereço nunca entram no stream** — saem por `GET` próprio, autenticado pela sessão. Há teste.
- **Reconexão manda o estado inteiro**, nunca uma repetição de eventos perdidos. É o que dispensa lógica
  de replay: quem reconecta está sempre correto. Evento novo no stream? Mande o suficiente para a tela se
  redesenhar sozinha.
- **Lance é `POST`, não stream.** O SSE é de mão única (servidor → cliente), e é isso que o faz barato.
- **Corrida de lance**: cadeado por lote + `UPDATE` conferindo **o valor que o cliente viu**. Se subiu
  mais de **um** degrau desde que a tela desenhou o botão, recusar e pedir confirmação — aceitar calado
  faria alguém pagar mais do que pretendia. E o **freio de repetição vem depois** das recusas que têm
  explicação própria, senão quem toca duas vezes ouve "Calma!" quando a resposta certa era "você já está
  ganhando".
- **Lances são por RODADA** (`Lote.lances_da_rodada()`): um item pode voltar para a fila — hoje só
  pelo **↩️ Voltar ao leilão** do caixa (mig. 0012), ou quando o locutor abre outro com este sem
  lance —, e os lances da rodada anulada não podem aparecer na tela.
- **Não há "desfazer lance"**, e a decisão é do clube. `Lance.cancelado` é coluna dormente — não religue
  por conta própria. `SemDesfazerLanceTests` guarda a porta.
- **Chamada externa lenta sai do caminho crítico.** O Pix é gerado numa thread **depois** de publicar o
  "vendido" — ninguém espera o Mercado Pago com a tela parada. Sem credencial, o leilão **não para**: o
  locutor dá baixa manual. Thread de fundo **fecha a conexão** no fim (`connections.close_all()`).
- **Sem biblioteca externa, aqui também.** WebRTC é API nativa (`RTCPeerConnection` + `fetch` do SDP, ~40
  linhas); o QR vem pronto em base64 do Mercado Pago; o som de lance/arremate é **arquivo do clube**
  baixado na entrada, com o **sintetizado em WebAudio** de reserva (nenhuma biblioteca); confete é canvas escrito à mão. A única dependência nova é o **uvicorn**,
  isolada em `requirements-leilao.txt`.
- **`leilao/tests.py` se auto-pula** quando o app não está instalado (`apps.is_installed`). O
  `manage.py test` do clube varre o diretório inteiro e encontraria o arquivo; sem a guarda, ele vira um
  erro de importação na suíte do clube. **Teste novo em app com settings próprias precisa da mesma
  guarda.**
- **A caixa de áudio é plugável de propósito**: se o teste de carga do WebRTC reprovar no VPS
  compartilhado, basta preencher "link de live externa" na configuração — a tela passa a apontar para lá
  sem tocar no resto.
- **Teste de carga antes do evento, de outra máquina** (`leilao_carga`). Medir de dentro do VPS esconde
  exatamente o que o teste procura.

### Papéis da equipe do leilão

- **São três áreas, não um "admin"**: `preparacao` (itens e configurações), `locutor` (o pregão) e
  `caixa` (pagamentos e entrega); `diretor` vê as três. Ficam em `leilao/papeis.py`, como **grupos
  nativos do Django** no banco do leilão — mesma ideia do `core/menus.py`, sem model novo.
- **`is_staff` sozinho não dá acesso a nada.** Sem papel, a pessoa entra e não vê tela. É o que impede
  uma conta esquecida de virar acesso total no dia do evento.
- **Papéis acumulam** e quem tem **uma** área só pula o hub e cai direto no trabalho — no dia do evento
  ninguém quer um menu entre o login e a tela.
- **Quem protege é a view, nunca o menu.** Toda tela da equipe usa `@papeis.exige(...)`, e o POST único
  (`/equipe/acao/`) confere a área **por ação**, no mapa `ACOES_AREAS`. Ação nova entra nesse mapa —
  ação fora dele é recusada por padrão, que é o lado seguro.
- **O locutor não dá baixa de pagamento.** Quem bate o martelo não confirma o recebimento. Ao mexer
  nisso, lembre que a tela do locutor **não tem** aba de pagamentos de propósito.
- **Só se entrega o que foi PAGO** (`Arremate.a_entregar`), e a regra mora no **servidor**, não na
  tela. Ela ficou *mais* importante desde que o prazo de pagamento saiu: hoje ninguém é marcado como
  pago por decurso de tempo, então quem não acertou continua devendo — e continua fora da entrega.
- **Tela que trabalha sobre um leilão recebe o id na URL.** O cadastro de item adivinhava ("o que está
  ao vivo, ou o mais recente") e, com um pregão rolando, jogava item novo **dentro dele**. Rota nova que
  mexa em leilão/lote segue o mesmo padrão: `/preparacao/<id>/…`.
- **"Ninguém cobre o próprio lance" compara PESSOA, não registro.** A entrada cria um `Participante`
  novo a cada vez, então a mesma pessoa no celular e no computador são dois registros; pelo id, ela
  daria lance contra si mesma. Use `servicos._mesma_pessoa` (id **ou** `telefone_normalizado`). O que
  vai no broadcast é a `chave_pessoa` — um **hash** —, nunca o telefone: aquele estado é transmitido
  para 100 pessoas. E **não** "resolva" isso reaproveitando o cadastro de quem tem o mesmo número:
  quem soubesse o seu WhatsApp tomaria a sua sessão, seus arremates e seu código Pix.
- **Bloqueio segue a pessoa.** Cadastro novo de quem está bloqueado já nasce bloqueado
  (`pessoa_bloqueada`), e bloquear pela tela alcança todos os cadastros dela (`bloquear_pessoa`) —
  senão o bloqueio se desfaz com dois toques na tela de entrada.

### O dinheiro quando o Pix é refeito

- **A âncora é a `referencia`, não a FK.** `Arremate.pagamento` aponta para UMA cobrança e é trocado
  ao refazer o Pix (hoje, "vai pagar depois"); a anterior fica órfã — e é ela que está **na tela da
  pessoa** naquele instante. Pagar aquele código e ninguém ser marcado como pago já foi bug real. Os
  dois caminhos (`_arremates_do_pagamento` no webhook, `cobrancas_do_arremate` na consulta de reforço)
  recuperam o arremate pela referência. **Formato atual**:
  `LEILAOC-<participante>-<leilao>[-R<ts>]`, a conta inteira da pessoa; o antigo por item
  (`LEILAO-<arremate>`) **continua sendo lido**, porque aquelas cobranças existem e ainda podem ser
  pagas.
- **Sem `site_url` não existe webhook**, e a consulta de reforço vira o único caminho do dinheiro. Ela
  precisa olhar **todas** as cobranças do arremate, não só a última.
- **Confira o id, não o prefixo**: `startswith("LEILAO-1")` pesca `LEILAO-12`.
- **`marcar_pago` aponta para a cobrança que foi paga**, mesmo que não seja a última: é dela que sai a
  taxa e é ela que o extrato explica.
- **Ação que muda estado e continua visível precisa ser idempotente.** O botão sobrevive na tela até a
  recarga: `marcar_combinado` chamado duas vezes emitia dois Pix vivos do mesmo item.

### A mesa do caixa

- **Pagamento aparece sozinho.** `caixa.js` ouve o `/stream/`: a linha muda na hora e **pisca**. A tela
  era estática de propósito e isso virou gente apertando F5 para saber se o Pix caiu — ou cobrando quem
  já havia pagado.
- **Recarga automática cede a quem está trabalhando.** Ela é necessária (totais, aba "A entregar"), mas
  **nunca** com um campo em foco ou o modal aberto: apagaria o "quem recebeu" no meio da frase. Não
  dando, aparece o botão 🔄. Ao ligar atualização automática em tela nova, repita a guarda.
- **Não existe "esticar prazo", porque não existe prazo.** `estender_prazo` foi removido junto com o
  pagamento por item (21/09) — o dinheiro fecha no fim, numa cobrança só. Fica a lição de então, para
  quem for criar qualquer botão que mexa em cobrança: **refazer a validade obriga a refazer o Pix**,
  porque o código nasce com ela e vence junto; esticar só a data entrega à pessoa um copia e cola que
  o banco recusa.
- **"Vai pagar depois" precisa entregar o Pix.** Sem o código na mão do caixa, o botão só tira o item
  da lista e a cobrança some do mapa. O código do combinado vale **7 dias**
  (`MINUTOS_PIX_COMBINADO`) — é o caixa quem vai cobrar, e isso leva dias, não minutos.
- **Mensagem com código Pix termina NO código.** É assim que a pessoa segura o dedo em cima e copia no
  celular; texto depois dele atrapalha a seleção.
- **Falar com a pessoa é um toque** (`Participante.whatsapp_link`, com o `55` acrescentado no servidor).
  Digitar número de celular com o leilão rolando é onde a conversa morre.
- **A divisão das entregas continua sendo um botão que alguém aperta**, depois do leilão: só entra o que
  **já foi pago**, e durante o pregão a lista ainda cresce. Automatizar dividiria uma lista pela metade.

### A tela de quem chega

- **Antes do primeiro item não é intervalo, é chegada.** `Leilao.ja_comecou()` separa as duas; "Intervalo"
  para quem acabou de entrar dá a impressão de que ela perdeu o começo.
- **O texto é do clube, não do sistema** (`boas_vindas_titulo`/`boas_vindas_texto`, uma informação por
  linha) e é editável **com o leilão no ar** — quem conduz muda de ideia durante o evento. Salvar publica
  o `estado`: as telas abertas se redesenham sozinhas. O servidor manda **linhas**, nunca HTML.
- **"0 pessoa(s)" não vai para a tela.** Frase montada no cliente, com plural certo — é a primeira coisa
  que a pessoa vê do clube.
- **Os emojis não podem cobrir controle nenhum.** A coluna de reações mora à direita, onde fica o ➤ do
  chat; com o chat aberto (`body.chat-aberto`) os dois trocam de lado. Controle novo no canto inferior
  direito precisa considerar isso.

### A ordem de importância do dia

- **Voz ao vivo e lance são o leilão; chat, emoji e enfeite vêm depois.** Não é opinião: o áudio precisa
  entregar um pacote a cada 20 ms e o lance é o que a pessoa foi lá fazer. Recurso novo que gere tráfego
  **entra abaixo dessa linha** e precisa poder ser descartado.
- **Enfeite se descarta CALADO.** Erro visível em cima de enfeite faz o celular tentar de novo — mais
  tráfego exatamente quando há menos CPU. A reação descartada responde 200.
- **O servidor não acredita no cliente para ritmo.** O `reacoes.js` manda 2 por segundo; um `fetch` num
  console manda 200. Todo caminho de escrita chamado por JS precisa do freio **no servidor**
  (`reacoes.aceitar`, `INTERVALO_MIN_LANCE`, `equipe.login_barrado`).
- **Freio de enfeite e freio de pregão são contadores separados.** Se dividissem, encher a tela de emoji
  recusaria lance — o oposto do que se quer. Há teste.
- **Teto por segundo, nunca fila.** Reação atrasada não é reação: o excedente é jogado fora.
- **O teste de carga do dia é COMBINADO**: SSE + lances + `--reacoes`, com o MediaMTX no ar. Medir uma
  coisa de cada vez esconde justamente a disputa de CPU que o evento tem.

### As reações (emoji)

- **Mais emoji na tela não pode virar mais requisição.** Cada toque solta uma **rajada**
  (`EMOJIS_POR_TOQUE`), e o que viaja continua sendo a **contagem** dentro do resumo de 0,5 s. Se um dia
  quiserem "mais emoji ainda", mexa nesse número — nunca na frequência de envio.
- **A multiplicação é do SERVIDOR.** O cliente manda **toques** (teto de 10 por requisição); o
  `data-rajada` existe só para a tela descontar o que já desenhou. Se o cliente mandasse o total, um toque
  forjado encheria a tela de todo mundo.
- **O resumo volta para quem mandou** (é broadcast — o servidor não sabe, nem deve saber, quem tocou o
  quê). Por isso a tela credita o que envia e desconta do próximo resumo; sem isso, quem toca vê em dobro.
  O crédito **expira**: requisição perdida deixaria um crédito pendurado comendo os emojis dos outros.
- **O teto do despejo é do RESUMO INTEIRO, não de cada emoji.** Por emoji parecia igual e não era: são
  seis, então o resumo podia pedir 240 desenhos a um celular que mostra 30. Ele é repartido na proporção
  dos toques, com **pelo menos 1 por emoji** — a tela tem de mostrar que a sala mandou coisas diferentes.
- **No cliente, o teto é o ESPAÇO LIVRE** (`TETO_NA_TELA - vivos`), e `receber` reparte esse espaço entre
  os emojis do resumo: sem isso o primeiro da lista toma a tela e os outros não aparecem, e agendam-se
  centenas de relógios que só descobrem que não há lugar.
- **Se a rajada apertar o servidor, o número a mexer NÃO é `EMOJIS_POR_TOQUE`** — ele não muda quantas
  requisições chegam. Quem controla a pressão é o `INTERVALO_ENVIO` do `reacoes.js`.
- **A rajada de emoji é o pior caso de requisições por segundo do módulo** (o lance é raro; o emoji não).
  Está no `leilao_carga --reacoes` — rode junto do resto, de outra máquina, antes do evento.
- **Os dois tetos são a proteção final** (`TETO_POR_DESPEJO` no servidor, `TETO_NA_TELA` no cliente), e
  saturar é o comportamento certo — reação atrasada não é reação, então o excedente é **descartado**, não
  enfileirado.

### Contagem de gente × teto de conexões

- **São números diferentes e não podem virar um só.** `HUB.conectados` conta o **público** (é por ele que
  o locutor decide a hora de começar); `HUB.total` conta tudo e é o que o teto limita. As telas da equipe
  assinam com `?equipe=1` (`HUB.assinar(publico=False)`) — sem isso, três voluntários com a mesa aberta
  viram três pessoas esperando. Tela nova da equipe que ouça o stream **passa `?equipe=1`**.

### Contas da equipe e a senha padrão

- **A senha `1234` é um bilhete, não um segredo.** Ela existe para ser dita em voz alta numa mesa de
  evento e digitada no celular em três segundos. O que a torna segura é **valer uma entrada só**: enquanto
  `ContaEquipe.senha_provisoria` for verdadeiro, a única tela que abre é `/equipe/senha/`.
- **A guarda está em quatro lugares, e todos são necessários**: `papeis.exige`, `papeis.exige_diretor`,
  o `equipe_view` (que usa `login_required` puro) e o **POST único da equipe** (`/equipe/acao/`, que
  devolve 403). Esconder a tela não protege nada se o botão continua respondendo por `fetch` — é a mesma
  lição do mapa `ACOES_AREAS`. Rota nova da equipe **repete a checagem**.
- **A senha nova pode ser fraca, e isso é decisão do clube.** `validate_password` fica **de fora de
  propósito**: quem digita é um voluntário, no celular, no meio de um evento, numa conta que abre telas de
  leilão. Exigir oito caracteres com número e símbolo ali produz senha anotada em papel — que é pior. Não
  "conserte" isso ligando os validadores. A **única** senha recusada é a própria padrão: aceitá-la faria a
  troca não trocar nada.
- **A trava é um campo, não o `last_login`.** O Django preenche `last_login` **no momento do login**,
  antes da troca: quem entrasse e fechasse o navegador no meio ficaria com a senha padrão para sempre, e o
  sistema acharia que estava resolvido.
- **Conta sem registro em `ContaEquipe` não é cobrada.** As contas antigas e as do `leilao_papel` (que
  sorteia senha forte) nunca tiveram senha padrão; forçá-las a trocar seria inventar um problema no dia do
  evento.
- **`update_session_auth_hash` depois de trocar a senha.** Sem ele o Django invalida a sessão e a pessoa
  cai no login logo depois de fazer o que o sistema exigiu. Há teste.
- **Usuários não é uma área, é o que o diretor faz por ser diretor.** Não entra em `AREAS` (ninguém é "o
  usuário de usuários"): é `ITEM_USUARIOS` no menu + `exige_diretor`. O template continua **iterando o
  menu** — nada de `{% if %}` por papel chumbado no HTML.
- **Duas travas contra o diretor se trancar do lado de fora**, as duas no servidor: ninguém desliga a
  própria conta, ninguém tira a própria função de diretor. E **conta de superusuário só é alterada por
  superusuário** — um diretor voluntário não reseta a senha de quem administra o sistema.
- **Cadastro sem função é recusado.** Conta sem papel entra e não vê tela nenhuma: seria uma armadilha
  para descobrir no dia do evento, não um cadastro.
- **A senha padrão tem freio de tentativas** (`equipe.login_barrado`: 10 erros por IP em 5 min, memória
  do processo, zerado no acerto). Sem ele dava para varrer `maria/1234` da internet — e o dano não é só
  entrar: quem acertasse **primeiro** trocaria a senha e trancaria a voluntária de verdade do lado de fora.
- **O `/admin/` do serviço do leilão é só de superusuário** (`config/urls_leilao.py`). O Django abre o
  admin para qualquer `is_staff`, e `is_staff` é exatamente o que toda conta da equipe tem: seria uma porta
  que nenhuma tela mostra e que a troca obrigatória de senha não protege.
- **Recado de acesso não promete senha que não vale**: `recado_de_acesso` só inclui a padrão enquanto a
  conta está com `senha_provisoria`.
- **Entrada da internet não vai direto para `int()`** (`minutos`, `quantos`): view cujas recusas são JSON
  não pode devolver um 500 de HTML no meio do evento.
- **A tela desliga a conta, não exclui.** Desligar é reversível e preserva quem deu baixa de pagamento e
  quem entregou item.

### A tela de entrada

- **Ela é preenchida com pressa, com o pregão já rolando.** Campo que não ajuda
  a entregar o item só produz desistência: pedem-se nome, WhatsApp, rua, número,
  complemento (opcional), bairro e cidade — **CEP e UF não**. Antes de acrescentar
  campo aqui, pergunte se ele muda a entrega.
- **Tirar da tela não é apagar o dado.** A UF virou campo **oculto** com
  `UF_PADRAO` (`leilao/forms.py`), porque o roteiro de entrega é endereço de
  verdade; o CEP continua no model, em branco. Campo oculto é editável por quem
  quiser, então o `clean` volta ao padrão quando vier vazio — a decisão é do
  servidor, como sempre.

### A divisão das entregas

- **O sistema NÃO consulta mapa, e a tela diz isso.** Não há coordenada no cadastro, e buscar uma seria
  dependência externa nova. A divisão é por **bairro** e equilibra o número de paradas. Declarar o limite é
  parte do recurso: precisão inventada é pior do que limite declarado, porque a equipe confia nela.
- **A divisão automática é PONTO DE PARTIDA; a palavra final é do quadro** (`/caixa/entregas/`). Sem mapa, o
  servidor compara **nomes** de bairro — ele nunca vai saber que um bairro é perto do outro, nem juntar
  "Jd. Exemplo" com "Jardim Exemplo". Quem sabe isso é a equipe, e o quadro é onde ela arrasta. Não tente
  fazer o algoritmo adivinhar proximidade: ou se compra mapa (dependência nova, chamada por endereço na noite
  do evento) ou se aceita que a decisão é humana.
- **O quadro nasce preenchido e só semeia UMA vez** (`_semear_quadro`): parada que aparecer depois (quem pagou
  mais tarde) cai em "a distribuir". Resemear por cima apagaria o trabalho manual, que é o que o quadro existe
  para guardar. O botão "refazer por bairro" apaga de propósito — e pergunta antes.
- **Cada arrastada salva na hora**, e se o servidor recusar a tela **desfaz**. A divisão que está na tela é a
  que vira a mensagem mandada ao voluntário: uma tela que mostre o que o banco não tem manda o voluntário para
  a casa errada.
- **A unidade do quadro é a mesma da divisão: a PESSOA** (`AtribuicaoEntrega.participante`). Arrastar leva
  tudo o que ela arrematou junto.
- **Diminuir o número de colunas não apaga atribuição**: a parada volta para "a distribuir" (quem faz isso é
  `entregas.quadro`, ignorando número que não existe mais). Apagar faria a equipe perder trabalho por um
  clique de configuração.
- **UM rótulo por região** (`_uniformizar_rotulos`). Agrupar pela chave normalizada resolve a divisão, mas o
  rótulo é a grafia de quem cadastrou: sem uniformizar, a rota impressa abre um cabeçalho de região por
  variação ("Centro", "centro", "CENTRO") e quem entrega lê três regiões. Vence a mais usada; no empate, a
  escrita como nome próprio.
- **A unidade da divisão é a PESSOA, não o item.** Dois itens da mesma casa são uma visita só; contar itens
  faria um entregador parecer sobrecarregado sem estar.
- **Bairro nunca é partido** entre dois entregadores — é exatamente o que a divisão existe para evitar.
- **A chave da região é normalizada** (sem acento, sem caixa, espaços colapsados): cada pessoa digita o
  bairro de um jeito, e o mesmo bairro escrito de duas formas viraria duas regiões.
- **A divisão é determinística.** A equipe reabre a tela, manda o link para outra pessoa da mesa e precisa
  ver o mesmo resultado; por isso o empate desempata pelo índice e o parâmetro vive no GET.
- **Não peça "rastreio" na entrega.** É voluntário levando na casa da pessoa: não existe código para anotar,
  e o campo pedindo um só fazia hesitar quem preenchia com pressa.

### Peso e dimensões do item

- **São obrigatórios no `LoteForm`, NÃO no model.** No banco os quatro campos aceitam vazio de propósito:
  os itens cadastrados antes da migration **0010** existem e continuam válidos. Gravar `0` neles seria
  inventar um dado — e quem lê a medida é quem vai **dirigir até a casa da pessoa**. A tela desses itens
  antigos diz "—" (e, na lista da preparação, "sem peso/medidas — completar ao editar", que é onde se
  descobre o que falta antes da noite da entrega).
- **"Obrigatório" que aceita zero não obriga nada.** `0 kg` e `0 cm` são campo vazio disfarçado e chegam na
  entrega valendo o mesmo que em branco — por isso os `MinValueValidator` no model e a recusa no form.
- **O peso aceita vírgula E ponto** (`forms.peso_para_decimal`), e é por isso que ele é `CharField` no form
  em vez de `DecimalField` com `localize=True`: em pt-BR o Django lê `"1.5"` como **separador de milhar** e
  devolve **15** — um item de 1,5 kg vira um de 15 kg sem avisar ninguém. O clube não leiloa nada de mil
  quilos; trocar essa hipótese impossível por um erro real de peso não vale a pena. Há teste.
  A **máscara `moeda_br.js` não entra aqui**: ela é de valor em R$ (regra do projeto) e leria "40" como
  R$ 0,40. Centímetro é inteiro e usa `NumberInput` com `min="1"`.
- **Há teto, e ele não é regra de negócio: é o freio do dígito a mais.** `Lote.MAX_PESO_KG` (1.000 kg) e
  `Lote.MAX_LADO_CM` (1.000 cm = 10 m). Sem eles o campo aceitava `999999999999`, e uma medida dessas
  **quebra a tela do pregão para as 100 pessoas** que estão olhando. Nenhum item de leilão de clube chega
  perto do teto; o que chega perto é o dedo escorregando no teclado do celular. O mínimo `1` é declarado
  **no form também**: o `PositiveIntegerField` entrega o campo com `min_value=0` e é esse validador que
  responde primeiro ao negativo, dizendo "maior ou igual a 0" quando o mínimo de verdade é 1.
- **Na edição, o campo volta com a vírgula** (`Lote.peso_numero` → `"1,5"`), não com o `Decimal` cru do banco
  (`1.50`): é o mesmo texto que a pessoa digitou.
- **O texto é montado num lugar só** — `Lote.medidas_texto` (`"1,5 kg · 40 × 30 × 25 cm"`), que vale para
  **todas** as telas: cadastro, lista da preparação, pregão público, mesa do locutor, caixa e roteiro de
  entrega. Formatar no template ou no JS faria a mesma medida aparecer de jeitos diferentes, e a equipe
  desconfia do número quando ele muda de cara. **Tela nova usa a property**, não os quatro campos.
- **Meia dimensão não vira texto**: `40 × ? × 25` parece defeito do sistema, não item incompleto. `dimensoes`
  só devolve algo com os **três** lados preenchidos, e `peso_texto` corta os zeros à direita parando no ponto
  decimal (`10,00` → `10 kg`, nunca `1`).
- **Vai no broadcast** (`estado.lote_publico`, chave `medidas`) porque é o **tamanho do que está à venda** —
  pode ser dito em voz alta, ao contrário de Pix, telefone e endereço. Vai o **texto pronto**, não os quatro
  números: o broadcast é lido por 100 celulares e o formato já foi decidido no servidor.
- **O motivo de tudo isso é a ENTREGA**, que acontece depois e longe: o voluntário escolhe o carro antes de
  sair de casa, e descobrir na porta que o item não cabe custa a viagem inteira. Por isso a medida aparece
  também no roteiro copiável (linha recuada sob o item) e no cartão do quadro.

### A foto do item

- **Nem `capture`, nem a falta dele: são DOIS inputs.** Com `capture="environment"` o celular abre a câmera
  e **esconde a galeria**; sem `capture`, o **Android 13+** abre o **seletor de fotos do sistema**, que
  **não tem câmera**. Os dois caminhos foram tentados em produção, nesta ordem, e **cada um perdeu metade
  do problema**. O que aparece varia por aparelho e por versão, então não dá para confiar no menu do
  sistema para oferecer as duas coisas.
- **A escolha vem para a tela**: dois botões (📷 Tirar foto · 🖼️ Escolher arquivo) e dois
  `<input type="file">`, um com `capture` e outro sem. Guarda: `FotoDoItemCameraOuArquivoTests`.
- **Só o input do formulário tem `name`.** O da câmera não é enviado — se tivesse `name="foto"`, os dois
  iriam no POST e o vazio poderia sobrescrever a foto escolhida. O arquivo da câmera é copiado para o campo
  de verdade com **`DataTransfer`**, que é a única forma de escrever em `input.files`.
- **É melhoria progressiva, e isso não é enfeite.** Os botões nascem `hidden` e só aparecem se houver JS
  **e** `DataTransfer`. Sem isso o seletor nativo continua visível e funcionando: um cadastro que depende de
  JS para aceitar foto deixaria alguém sem conseguir cadastrar, e descobriríamos na véspera do evento.
- **Escondeu o input nativo, escondeu o nome do arquivo junto.** Quem escolhe da galeria precisa conferir
  que pegou a foto certa — daí o `#fotoNome` ao lado da prévia. Ao trocar um controle nativo por um próprio,
  liste o que o nativo dava de graça.
- **Atributo que fecha uma porta precisa de motivo forte.** `capture` não decide melhor que a pessoa com o
  celular na mão: ela sabe se a foto já existe.

### Verificar layout com sonda: não injete no `<body>`

- **`body` pode ser um contêiner flex** (`tela-entrada` é), e todo elemento que a sonda acrescenta ao
  `<body>` vira **irmão flex**: o card real foi espremido de 411px para 147px e empurrado para fora da tela,
  e a captura saiu "vazia". Perdeu-se tempo procurando um defeito de layout que era **da bancada**.
- **A sonda reporta sem tocar no DOM** — escreva em `document.title` e leia do `--dump-dom`. Se precisar
  mesmo de um elemento, use `position: fixed`, que o tira do fluxo.
- **Confirme a geometria, não só a captura**: `getBoundingClientRect()` dos elementos que interessam
  (largura, x, y) prova que estão na tela e do tamanho certo. Imagem vazia não distingue "não renderizou" de
  "renderizou fora da vista".

### O número do item

- **É a etiqueta do objeto físico, não a posição na fila.** `Lote.numero` nasce sozinho e **não muda
  nunca**; `Lote.ordem` é a fila e muda a cada reorganização. Trocar um pelo outro faz a caixa na
  prateleira apontar para outro item, e o erro só aparece na hora de entregar.
- **O contador fica no leilão (`Leilao.ultimo_numero_item`) e só sobe.** Numerar pelo `Max()` do que
  existe parece igual e não é: apagando o último item, o próximo cadastro repete um número que talvez já
  esteja colado numa caixa. Há teste.
- **Item que volta para a fila mantém o número.** Não reetiquete nada, e não "corrija" isso.
- **O número NÃO vai no broadcast.** "Item nº 12" conta ao público que existem pelo menos 12 itens, e
  quantos faltam é justamente o que ele não pode saber. Vai pelo `/locutor/dados/`, o caminho autenticado
  que a fila já usa.

### Sem cronômetro, sem pausa

- **Nada fecha sozinho.** Quem bate o martelo é o locutor — é o momento que mais importa para ele, e
  tirá-lo descaracteriza o leilão. Não recrie contagem regressiva, "fecha sozinho" nem "+tempo": são
  colunas dormentes (`segundos_por_lote`, `segundos_extra`, `reiniciar_cronometro`,
  `fechamento_automatico`, `Lote.fecha_em`, `pausado_restante`) e nada as lê.
- **Também não há "pausar".** Para segurar o pregão, o locutor não abre o próximo item. Pausar só
  valia durante um item já aberto, e mesmo aí a saída é bater o martelo ou deixar rolar.
- **O relógio da mesa conta para CIMA**, não para baixo: mostra há quanto tempo ninguém dá lance. É o que
  ajuda a decidir o martelo — e é sugestão, nunca fechamento.
- **`servidor_em` continua obrigatório no estado.** Sem cronômetro ele ainda é o que faz a mesa calcular o
  silêncio pelo relógio do SERVIDOR; pelo do aparelho, quem estivesse com a hora errada veria outro número.

### Remover código JS tem DOIS lados

- **Tirou a função, tire as chamadas.** `ReferenceError` mata o arquivo inteiro: o script morre naquela
  linha e **nada depois é ligado**. A tela abre bonita, o item novo não aparece, o lance não desenha — e
  quem está no evento descreve isso como *"o sistema está com atraso"*, que manda você investigar a rede e
  o SSE em vez do JS. Já aconteceu com `atualizarTempoChat` ao remover a contagem do chat.
- **São duas guardas, e as duas são necessárias**: `BotoesQueOJsProcuraExistemTests` (id que o JS procura e
  o template não tem) e `FuncaoQueOJsCHAMAExisteTests` (nome chamado que não está declarado no arquivo).
  Uma não pega o que a outra pega.
- **Comentário conta como texto, não como código.** As duas varreduras leem o arquivo cru; a segunda tira
  comentários e strings antes justamente porque um comentário citando a função removida daria falso
  positivo — e a primeira já deu, com `$("id")` escrito dentro de um comentário.
- **Para achar esse tipo de erro em minutos**: renderize a tela pelo test client, injete
  `window.addEventListener("error", …)` **antes** dos scripts da página e leia o resultado pelo
  `document.title`. Não escreva a sonda no DOM — `body` pode ser flex e a sonda desmonta o layout.

### O dinheiro fecha no FIM (não item a item)

- **Ninguém sai do leilão para pagar.** Os arremates se acumulam na conta da pessoa e ela paga **tudo num
  Pix só**, quando o locutor libera. O prazo de 15 minutos existia para evitar isso e provocava exatamente
  isso — e ainda devolvia o item à fila de quem estava sem o celular na mão. Não recrie prazo, contagem
  regressiva nem devolução automática: `minutos_para_pagar` e `Arremate.expira_em` são **dormentes**, e
  `expirar_arremate`/`estender_prazo` **não existem mais**.
- **Quem não paga fica devendo**, e quem cobra é o caixa (WhatsApp e Pix estão lá). O item **não volta para
  a fila** sozinho.
- **Liberar é do LOCUTOR e é um botão só** (`liberar` em `ACOES_AREAS`): é ele quem sabe que o último item
  foi batido. É **alavanca** — apertar antes da hora acontece, e desfazer sai mais barato que explicar.
- **A trava é do SERVIDOR.** Esconder o botão não impede um POST forjado: pedir o Pix antes da liberação
  leva 409. Gerar cobrança antes da hora encheria a noite de códigos vivos do mesmo dinheiro.
- **A âncora continua sendo a REFERÊNCIA, não a FK** — a lição não mudou, só o formato:
  `LEILAOC-<participante>-<leilao>[-R<ts>]`. `Arremate.pagamento` é trocado quando o Pix é refeito e a
  cobrança anterior fica órfã **na tela da pessoa**; `_arremates_do_pagamento` a reencontra pela
  referência. O formato antigo (`LEILAO-<arremate>`) **continua sendo lido**: aquelas cobranças existem e
  ainda podem ser pagas.
- **Uma cobrança viva por pessoa.** `cobranca_do_participante` devolve a que já existe em vez de criar
  outra — vários códigos vivos do mesmo dinheiro deixam o caixa sem saber qual foi pago.
- **O escopo da conta é o cadastro da SESSÃO.** Juntar os arremates de quem tem o mesmo telefone parece
  certo (celular + computador) e é o que a regra dos lances já proíbe: quem soubesse o seu WhatsApp veria
  os seus itens e o seu código Pix.

### O chat não tem relógio

- **Aberto enquanto o leilão está no ar, e só isso.** `Leilao.chat_aberto` é **uma expressão**
  (`status == "ao_vivo"`), que é a MESMA que o servidor usa para aceitar mensagem — a divergência entre o
  que a tela mostra e o que o servidor aceita deixou de ser possível por construção, e era ela o bug
  antigo. Não recrie `chat_segundos`/`chat_aberto_ate`: são dormentes.
- **O fio é um só a noite inteira.** O corte por rodada (`chat_aberto_em`) existia porque o chat era "do
  intervalo"; sem intervalo, o que limita a tela é o teto das 40 últimas, que sempre existiu.

### Nada flutuante em cima de controle

- **Os botões de reagir moram no FLUXO da página.** Eram `position: fixed` no canto e cobriam o envio do
  chat. A correção de então — trocar de lado quando o chat abrisse — dependia de *"com o chat aberto o
  botão de lance não está na tela"*, e caiu no dia em que o chat passou a ficar aberto o leilão inteiro.
  **Elemento que não flutua não cobre nada**: é a única solução que não volta a quebrar na próxima mudança
  de tela. Controle novo segue a mesma regra; só o **trilho** dos emojis é fixo, e ele é
  `pointer-events: none`.

### Conexão que o navegador derruba, alguém tem de trazer de volta

- **`visibilitychange` não é capricho, é obrigatório** — vale para o áudio como já valia para a Screen Wake
  Lock. O navegador derruba a conexão WebRTC quando a aba sai da frente e **não a devolve**: quem voltava ao
  leilão ficava sem ouvir e só resolvia fechando o navegador, que ninguém adivinha. O módulo escuta o evento
  **ele mesmo**, em vez de confiar que cada tela lembre de chamá-lo.
- **Desistir de reconectar não pode ser definitivo.** O freio contra martelar o servidor com 50
  celulares é o **intervalo** (até 20 s, sorteado), não um teto de tentativas — desde 24/09 não existe
  mais desistência (ver "Áudio ao vivo: o que quebra é o que NÃO avisa"). Voltar para a tela continua
  sendo sinal novo: zera o contador e tenta na hora.
- **O `<audio>` volta PAUSADO mesmo com a conexão de pé.** Reconectar sem mandar tocar deixa a pessoa
  olhando um leilão mudo com tudo aparentemente funcionando.
- **Handler de `RTCPeerConnection` fica amarrado à conexão que o criou.** `pc.close()` dispara
  `connectionState = "closed"`, e um handler que não confere qual conexão disparou faz a reconexão contar
  tentativa contra si mesma — uma religada legítima virava duas.

### O incremento é fixo

- **R$ 5, e ponto** (`INCREMENTO_PADRAO`). Configurar por leilão e por item existia e saiu: no pregão ao
  vivo o locutor anuncia "de cinco em cinco" uma vez e ninguém confere tabela — incremento variável só
  criava a chance de um item sair com regra diferente da que foi dita em voz alta. `incremento_efetivo`
  devolve a constante e **não consulta o banco**; as duas colunas são dormentes.

### O pregão morre com o leilão

- **Leilão fora do ar não tem item em pregão.** `mudar_status` fecha o chat **e** devolve o lote aberto para
  a fila (`_devolver_lotes_abertos`). Sem isso a linha fica `status="aberto"` para sempre — e como a mesa do
  locutor **cai para o leilão mais recente** quando não há nada no ar, ela passa a mostrar "item em pregão,
  sala calada" com o leilão encerrado há dias. Foi bug real, visto na produção.
- **A guarda é do ESTADO, não de quem chama.** `estado_publico` dizia `ativo: True` para qualquer leilão
  não-nulo e confiava no chamador. A tela pública acertava **por acidente** (passa `Leilao.ao_vivo()`, que é
  `None`); qualquer outro chamador recebia um pregão inventado. Agora ele mesmo exige `status == "ao_vivo"`,
  como o `Leilao.chat_aberto` já fazia. **Estado que pode ser pedido para um objeto errado se defende
  sozinho** — esconder o problema no chamador é esperar que todos os chamadores futuros acertem.
- **O item volta LIMPO para a fila**, não "vendido" nem "sem lance": ninguém arrematou, então ele fica
  disponível de novo (decisão do clube). Zera `valor_atual` e `lider` — item na fila exibindo líder e valor de
  uma disputa abandonada é pior que item sem nada. Os lances ficam no banco como histórico, e
  `lances_da_rodada()` já ignora a rodada anulada. Vale também para o leilão que sai do ar **para dar lugar a
  outro**, que é o caminho por onde o órfão nasceu.

### O lance tem de se fazer notar

- **O nome de quem assume a ponta CRESCE e acende** (`assume-a-ponta`), não desliza discretamente. Quem está
  olhando o botão precisa perceber, sem ler, que a liderança trocou — é a única informação que ele usa para
  decidir cobrir. A classe entra **só quando o líder muda dentro do mesmo item** (o `trocouLote` segura a
  troca de item), senão piscaria a cada item que abre.
- **`transform: scale` não empurra o layout, mas conta para a área rolável.** Escalar o nome criava
  **rolagem horizontal na página inteira** quando o nome era comprido — a mesma armadilha do `minmax(0, 1fr)`,
  por outro caminho. A trava é `overflow-x: clip` + `overflow-clip-margin` no card: **`clip`, não `hidden`**,
  porque `hidden` cria caixa de rolagem; a margem deixa o brilho vazar sem que nada role. Efeito novo que
  escale alguma coisa **passa pela sonda headless** antes de subir — o olho não vê 27px de estouro.

### Centralizar na vertical corta o que não cabe

- **`align-items: center` num container da altura da janela esconde o topo do que é maior que ela** —
  e esconde **para sempre**: o que fica em coordenada negativa o navegador não rola. Aconteceu no
  `body.tela-entrada` do leilão (`html, body { height: 100% }`), com o cadastro de item: 997px de
  card, 260px sumidos numa janela de 540, o `<h1>` fora da tela.
- **O disfarce é a página rolar para baixo**: chega-se ao botão de salvar e nunca ao título, então o
  relato vem como "a tela fica cortada", não como "não consigo rolar".
- **Quem centraliza é `margin: auto` no filho.** Ela centraliza quando há espaço e vira **zero**
  quando o espaço é negativo — o card começa no topo e a página rola. Preferida a
  `align-items: safe center`, que resolve o mesmo mas é keyword nova, de suporte irregular.
- **Corrija no CONTAINER, não na tela que estourou primeiro.** Encolher o formulário mais alto
  resolve um caso e deixa a armadilha para a próxima tela que crescer.
- **Captura de tela com animação de entrada engana.** A `sobe` desloca o card enquanto roda, e a
  imagem sai com ele em outro lugar. Meça `getBoundingClientRect()` com a sonda.

### Devolver ao leilão um item já arrematado

- **O motivo é obrigatório, e quem exige é o SERVIDOR.** Um item reaparecendo na fila depois de
  batido é a coisa mais estranha que pode acontecer num leilão: quem abrir a lista amanhã precisa
  saber por quê sem ter de perguntar. `required` no HTML não barra POST forjado.
- **Devolver é do CAIXA** (`ACOES_AREAS`), não do locutor: é lá que se vê quem não pagou, e com o
  pagamento no fim a devolução quase sempre acontece **depois** do leilão.
- **Item PAGO pode voltar, e isso não é estorno.** O caso é a pessoa **doar o item de volta** para o
  clube leiloar outra vez: o arremate continua `pago`, o dinheiro entrou e é do clube, e a
  arrecadação **não muda**. Quem **não** pagou vira `cancelado` — cobrar por um item que ela não vai
  receber seria errado.
- **Quem devolveu sai da ENTREGA** (`a_entregar` confere o `devolvido_em`), pago ou não. Sem isso um
  voluntário sai para levar na casa da pessoa um objeto que está de volta na prateleira.
- **O item volta limpo e o NÚMERO não muda**: sem líder e sem valor (item na fila exibindo a disputa
  anterior é pior que item sem nada), `voltas` sobe, e o número é a etiqueta colada na caixa.
- **Item em pregão AGORA não é devolvido**, e a ação é **idempotente** — o botão sobrevive na tela
  até a página se refazer, e o segundo clique não pode somar outra volta.

### A tela de equipe trabalha sobre o leilão da URL — todas elas

- **A regra já valia para o cadastro de item e agora vale para mesa, caixa e entregas.** Adivinhar
  ("o que está no ar, ou o mais recente") fazia o locutor **abrir a mesa sem saber qual leilão estava
  conduzindo**, e não havia como olhar o caixa da noite passada sem colocá-la no ar de novo.
- **A URL sem id não some: ela REDIRECIONA** para a URL com id (link antigo, favorito, atalho do
  hub). E o redirect **preserva a query string** — o `?entregadores=2` do quadro viaja no GET, e
  redirecionar seco o descartava.
- **Teste que batia na URL sem id precisa de `follow`**, e `302` deixou de distinguir "não tem
  acesso" de "vá para a URL do leilão": quem testa acesso confere **onde a pessoa termina**.
- **Cuidado com o laço de redirect**: quem tem UMA área só é mandado direto para ela pelo hub, e a
  área sem leilão nenhum manda de volta — página que nunca carrega. O hub só pula para a área quando
  há o que mostrar lá.

### Áudio ao vivo: o que quebra é o que NÃO avisa

- **Reconexão de áudio não pode desistir de vez.** O freio contra martelar o servidor é o
  **intervalo** (até 20 s), nunca um teto de tentativas: o caso real é o locutor sair do ar e voltar
  minutos depois, com a pessoa olhando a tela o tempo todo — a aba nunca sai da frente, então nada
  dispara o `retomar()`, e a desistência vira silêncio definitivo até reiniciar o aparelho.
- **Pedido explícito zera o contador.** Tocar o 🔊 é um começo do zero; sem isso, depois de uma
  sequência ruim cada clique vale uma tentativa que **nasce estourada** — e foi por isso que nem
  clicando o som voltava.
- **"Conectado" não quer dizer "com som".** Quando a fonte some, o ICE não cai e o
  `connectionState` não muda: nada dispara. Ouça a **faixa** (`onmute`/`onended`) e, porque nem todo
  navegador a avisa, tenha um segundo vigia lendo `bytesReceived` do `getStats()`.
- **O vigia de bytes espera 15 s, não 5.** O locutor faz pausas ao falar e o RTP continua mandando
  mesmo em silêncio; o que para de crescer é quando a **fonte** some, não quando ele respira.
- **Limpe o `srcObject` antes de reatribuir.** O elemento segurando a stream anterior é um dos
  jeitos de o celular travar o áudio de vez — o caso em que nem desligar e ligar o som resolve.
- **Espera de reconexão é SORTEADA, nunca fixa.** Cem celulares percebem a mesma queda no mesmo
  instante, então espera fixa os mantém **sincronizados a noite inteira**: 100 pedidos no mesmo
  segundo em vez de espalhados. E a rajada cai no pior momento — o da volta, quando as negociações
  acontecem todas juntas. Sorteie **na detecção** (é ela que resolve) e também no intervalo.
  Medido: pico de 73 para 49 com 100 aparelhos, com a média igual — dispersão **achata o pico**,
  não reduz a carga.
- **Simulação com hipótese errada mente com confiança.** A primeira medição espalhava a detecção
  entre 3 e 15 s e concluiu que a dispersão era inútil; esse espalhamento não existe na vida real.
  Antes de acreditar num número, confira se o **cenário** simulado é o que acontece.
- **Relógio de vigia morre com a conexão que o criou.** Um `setInterval` sobrevivente religa uma
  conexão já substituída, e a reconexão legítima vira duas. Mesma disciplina dos handlers de
  `RTCPeerConnection`.

### Som do leilão: arquivo do clube, com três amarras

- **A regra era "nenhum arquivo de áudio", e caiu** em 24/09, quando o clube trouxe os próprios
  arquivos. O que **não** caiu foram os três motivos dela — download, latência e binário versionado
  —, e é por isso que a troca tem amarras em vez de ser um `src` solto.
- **O arquivo baixa na ENTRADA, nunca no pregão.** A carga acontece no `ativar()`, quando a pessoa
  toca "Entrar com som" e está parada lendo a tela. Buscar no primeiro lance atrasaria justamente o
  som que precisa sair no instante do evento, e poria tráfego na hora de maior disputa.
- **O sintetizado continua existindo como RESERVA.** Rede ruim, formato que aquele navegador não
  decodifica, arquivo trocado por engano: o leilão não pode ficar mudo por causa de um download.
  `tocarArquivo` devolve `false` quando o buffer não chegou, e é esse `false` que aciona a reserva.
- **Teto de 500 kB por arquivo**, com teste. Efeito de leilão não precisa de taxa de música.
- **O caminho vem do servidor** (`data-som-*` no template), nunca escrito no JS: em produção o
  `static` acrescenta o hash do conteúdo, e um caminho chumbado apontaria para a versão antiga
  depois do primeiro deploy.
- **Licença: confira a procedência antes de subir áudio.** O repositório é **público** e o site
  também, então um arquivo tirado de vídeo alheio passa a ser distribuído pelo clube. Áudio novo só
  entra sendo gravação própria, material livre de direitos ou coisa licenciada — e **na dúvida,
  sintetize**, que é o caminho que o módulo já tem pronto e que não depende de licença nenhuma.
- **Como se sintetiza o que o clube costuma pedir**: palma é uma rajada de ~30 ms de ruído filtrado
  em banda alta, e uma plateia é dezenas delas em instantes diferentes com a densidade **caindo**
  (aplauso de verdade termina rareando; espalhado por igual soa como chuva). Torcida é ruído de
  banda média com a frequência subindo e caindo. Sino metálico são duas parciais **desafinadas
  entre si** — afinadas, soam musicais em vez de metálicas.
- **O ruído é gerado UMA vez e reaproveitado.** Gerar dois segundos de ruído a cada palma é trabalho
  de CPU no meio do pregão, justamente quando ela falta.
- **Som que toca a cada lance é curto** (~0,35 s). Som que toca uma vez por item pode ser longo e
  caro — é a mesma regra de prioridade do módulo: o que se repete não pode pesar.

### A tela "show" do pregão: um motor, duas telas

- **A "show" é a padrão (`/`) e a clássica é o backup (`/classico/`)** — decisão do clube, aprovada
  em 24/09 depois do teste em `/nova/` (que agora só redireciona para `/`). Quem abre `/classico/`
  sem cadastro passa pela porta e **volta para ela** (`views.CHAVE_TELA` na sessão); abrir `/` apaga
  a marca. A clássica **continua recebendo** o que mudar no motor — não a deixe apodrecer: ela é a
  saída de emergência se a show der problema num evento.
- **Não existe segundo motor.** Lance, chat, Pix, som, porta e tela acesa são do `leilao.js`, para as
  duas telas. Ele só **emite avisos** (`emitir` → `CustomEvent` `leilao:estado|lance|lote_aberto|
  vendido|chat|toque_lance`) e o `palco_show.js` enfeita em cima. O `emitir` tem `try/catch`: um
  enfeite que quebre não derruba o pregão. Duplicar a lógica de lance numa tela nova é o jeito certo
  de as duas passarem a discordar sobre quem está ganhando.
- **Todo id que o motor procura existe nos DOIS templates** (há teste para a nova). O `.pregao` é a
  classe que o motor liga em `eu-ganhando`/`superado` — o placar da nova a carrega por isso.
- **O botão de lance da nova mora fora do bloco do item** (os emojis e o chat ficam entre eles),
  então o motor não o esconde no intervalo: quem esconde é o `palco_show.js` (`#showAcao`).
- **A foto nunca some e nunca é cortada**: ela fica com o espaço que sobra, com piso de altura
  (`--foto-min`), em `object-fit: contain` sobre um borrão da própria foto. Janela baixa demais faz a
  página **rolar** — nada de `overflow: hidden` no palco, que cortaria o botão.
- **O chat não ocupa a tela**: no celular, duas bolhas que somem sozinhas (ticker); tocar abre a
  **folha** com o `#chat` de sempre. A folha cobre o placar com o teclado aberto, então o topo dela
  tem um **mini placar** ao vivo — o "te superaram" não se esconde de quem conversa. Na tela larga
  (900px+) o ticker vira a conversa inteira na coluna da direita.
- **Efeito é enfeite, e enfeite se descarta primeiro**: só `transform`/`opacity`; camadas de efeito
  com `pointer-events: none`; **um** canvas de partículas cujo laço só roda com partícula viva e cujo
  **teto cai pela metade** depois de 20 quadros lentos seguidos; `prefers-reduced-motion` desliga
  tudo. O `palco_show.js` **não faz requisição nenhuma** — o termômetro 🔥 conta os lances que já
  chegam pelo stream (há teste).
- **O "cassino" tem limite**: da interação de jogo vem a graça (contador que rola, moedas, combo,
  coroa, jackpot no martelo), **nunca** a pressão — nada de contagem regressiva (o martelo é do
  locutor), lance ou gente falsa, "quase ganhou". É dinheiro de verdade num leilão beneficente.
- **O público continua sem saber quantos itens faltam**: o carimbo diz "NOVO ITEM!", nunca o número.
- **Animação com relógio usa SÓ o carimbo do `requestAnimationFrame`**. Misturar com
  `performance.now()` deu tempo negativo e a festa contou "R$ -6,17"; e contagem de valor tem
  **garantia do valor final** por `setTimeout` — aba no fundo para de dar quadros.
- **Verificação**: a sonda headless mede posição, estouro e o dígito final de cada fita; a captura
  **congela animação no meio** (nome do líder "sumido", contador entre dois números) — não é defeito.

### O que a revisão geral de 24/09 fixou (dinheiro, conexão, leilão da tela)

- **A cobrança grava QUAIS itens cobre** (`PagamentoLeilao.cobre`, mig. **0014**), na criação, e nunca
  mais muda. É a resposta do webhook para "quem esta cobrança quita" — não a FK (trocada quando o Pix é
  refeito) e não "tudo o que a pessoa tem em aberto hoje" (que fazia um Pix antigo de R$ 10 quitar um
  item novo de R$ 100). Cobrança anterior à 0014 sem lista só quita pelo palpite se o **valor bater**.
- **Reaproveitar o Pix exige a MESMA lista e o MESMO valor** (`servicos.cobranca_viva`). Bastar "os
  itens apontam para ela" devolvia o Pix de R$ 80 depois de o caixa dar baixa num item de R$ 50.
- **Pagamento só quita item AINDA EM ABERTO** (`aguardando`/`combinado`, sem `devolvido_em`). Dinheiro
  por item já pago ou devolvido vira `logger.error` para o caixa acertar — nunca ressuscita um
  arremate cancelado. **Estorno** (`estornado`) devolve a dívida de quem foi pago POR AQUELA cobrança
  (a baixa manual não é tocada).
- **A conta é de UM leilão** (`servicos.conta_aberta`: o do item mais antigo em aberto). A sessão dura
  30 dias; somar dois leilões mostrava um total que nenhum Pix cobria.
- **Depois de ENCERRADO, paga-se sempre** (`servicos.pagamento_aberto_para`). Antes o Pix exigia leilão
  ao vivo e liberado, e quem não tinha aberto o próprio Pix na noite ficava sem jeito de pagar. O
  **📋 Pix do caixa GERA a cobrança** (antes só lia a pendurada no 1º item).
- **Item devolvido/cancelado fica fora da conta**: `pago`, `combinado` e `entregue` são recusados no
  servidor (outro terminal do caixa ainda tem o botão).
- **Toda tela da equipe manda o leilão dela** (`data-leilao` → `corpo.leilao`; `?leilao=` nos dados da
  mesa; campo oculto no "Refazer por bairro"). O servidor usa `_leilao_da_tela` e só cai no palpite
  antigo sem id. Ação nova da equipe: **mande o leilão**.
- **A mesa só abre item da FILA num leilão NO AR**, e o lance recusa leilão fora do ar. Abrir e VENDIDO
  ficam travados durante o POST (toque duplo abria dois itens), e o ▶ da fila passa pela mesma
  confirmação de "está em disputa".
- **Mudar o nº de entregadores é POST** (cria e apaga colunas; por GET, um prefetch apagava).
- **Conexão ao vivo não desiste** (`fonte_viva.js`, nas telas do público, mesa e caixa): o
  `EventSource` desiste de vez ao pegar um 502/503 na reconexão (todo reinício do serviço), e a tela
  congelava sem aviso. A `FonteViva` reabre com espera crescente e **sorteada** e religa os ouvintes.
- **Resposta do POST do lance não sobrescreve lance mais novo** (`respostaAindaVale`): o stream do lance
  de outra pessoa pode chegar antes da resposta do meu.
- **Item aberto é rodada nova mesmo com o mesmo id** (devolvido ao leilão): o `lote_aberto` zera o
  estado por item e fecha a gaveta que cobriria o botão.
- **Peso em gramas**: `12.500` é ponto de milhar (12,5 kg); vírgula/ponto decimal é recusado com
  explicação — antes virava 10 g calado. **Foto** só é reprocessada quando muda; limpar tira a
  miniatura. **Editar item** grava só os campos do formulário.
- **O IP do freio de login é o ÚLTIMO do `X-Forwarded-For`** (o que o nosso Nginx acrescenta); o
  primeiro é escrito pelo cliente.

### O que a segunda conferência de 24/09 fixou

- **`chave_pessoa` é HMAC com a `SECRET_KEY`**, nunca hash puro do telefone: celulares de um DDD
  são 10⁸ números, e o `sha256` do telefone se revertia em menos de um minuto — quem estava no
  stream tirava o WhatsApp de quem dava lance ou escrevia no chat. Qualquer identificador derivado
  de dado pessoal que vá para o broadcast: **com segredo do servidor**.
- **A configuração do Mercado Pago (e do áudio) é SÓ do Diretor** (`config_view` com
  `exige_diretor`). Quem a edita decide para qual conta vai o Pix de todo mundo.
- **"Pago" é a conta inteira quitada, não "alguma cobrança aprovada"**: o `conferir_pagamento`
  responde se ESTE item foi pago, e a view só diz "pago" quando todos os itens que estavam abertos
  estão. Cobrança `finalizado` ou que não cobre nada em aberto não é consultada no Mercado Pago.
- **Todo `estado` publicado é o do leilão NO AR** (`servicos.publicar_estado`). O stream é um só;
  publicar o de outro leilão mandava "sem leilão" para a sala.
- **Referência de Pix refeito em milissegundos, com laço até achar a livre**; o `IntegrityError`
  só devolve a outra cobrança se ela cobrir exatamente esta conta.
- **O stream do público exige cadastro** e tem **teto de 6 conexões por pessoa**; `?equipe=1` só
  vale com login de equipe, e a equipe **não entra no teto** (a mesa nunca é barrada).
- **Contagens do hub percorrem uma cópia** (`list(...)`): rodam em threads enquanto o laço de
  eventos mexe no dicionário.
- **`leilao_demo` recusa rodar sem DEBUG** (em produção encerrava o leilão no ar) e nunca reescreve
  a senha de um `locutor` que já existe.
- **Freio de login com duas chaves**: `IP|usuário` (10) e `IP` (30). Acertar a própria senha zera só
  a própria chave; o Wi-Fi do evento não tranca a equipe inteira.
- **Foto com nome sorteado** (`lote-<id>-<hex>.jpg`) — a pasta é pública e o nome sequencial
  mostrava a fila; o **original sai** depois de reduzido (tinha EXIF/GPS); **mais de 60 Mpx é
  recusado** antes de decodificar (`imagens.MAX_PIXELS`).
- **Não se exclui item em pregão**; excluir leva as fotos junto. **Leilão não volta a rascunho.**
  **Item sem lance pode ser aberto de novo** (▶ na aba Itens).
- **Estorno de quem pagou em dobro** não volta a dívida: o item passa a apontar para a outra
  cobrança aprovada. O QR aberto se refaz quando um item da conta é quitado.
- **Uvicorn com `--timeout-graceful-shutdown 3`**: sem ele, o reinício com público conectado
  esperava o stream fechar (nunca fecha) e o leilão ficava **90 s** fora do ar.

### Voz ao vivo: pausar é MUDO, e a volta é avisada

- **Mudo desliga a faixa (`track.enabled = false`), não a transmissão.** A conexão de todos os
  ouvintes continua de pé e o som volta no mesmo instante. Parar/voltar derruba e refaz as
  negociações de todo mundo — medido: 4,9 s sem aviso, até ~20 s numa pausa longa.
- **"A voz voltou" é avisado pelo servidor** (ação `voz` → evento SSE `voz`), e o ouvinte pula a
  espera (`AudioLeilao.vozVoltou`), sorteando até 4 s por celular para 100 negociações não caírem
  no mesmo instante. Medido: 0,7 s. Quem entrou sem som ou desligou o som não é religado.
- **A transmissão do locutor tem vigia próprio** (`AudioFalar.aoCair`: `failed`, ou `disconnected`
  por 4 s) e a mesa **religa sozinha** com espera crescente. Parar durante uma religação pendente
  não pode religar a voz (`if (ok && !querNoAr)`).
- **A tentativa agendada do ouvinte é cancelável** (`relogioReligar`): sem isso, a reconexão pedida
  na hora era seguida pela agendada, e a conexão recém-aberta caía.
- **Laboratório de áudio**: MediaMTX da mesma versão da produção + dois Chrome headless
  (`--use-fake-device-for-media-stream`, `--allow-loopback-in-peer-connection`,
  `--disable-features=WebRtcHideLocalIpsWithMdns`) comandados por CDP a partir do Node. É o que
  prova o comportamento que os testes Python só guardam na estrutura.

### O martelo em três tempos: dou-lhe uma, dou-lhe duas, VENDIDO (desde 26/09)

- **"Dou-lhe" é anúncio, não cronômetro.** `servicos.dou_lhe` só publica `dou_lhe` no broadcast
  (`vez`, `lote`, `valor`, `lider` — tudo que se diz em voz alta); não grava nada e **não fecha o
  item**. O martelo continua sendo o VENDIDO, apertado pelo locutor. Nada de fechar sozinho depois do
  "duas".
- **Só com lance, e só para o item que a mesa mostra**: a mesa manda o `lote` que está na tela e o
  servidor recusa (409) se o pregão já trocou — senão o "duas" do item anterior cairia no novo.
- **Lance novo, item novo ou martelo zeram o tempo** na mesa. O estado do martelo vem do **stream**
  (não da resposta do clique), para duas telas de mesa ficarem no mesmo tempo.
- **O VENDIDO só pula a confirmação depois do "dou-lhe duas" sem lance novo** — é o terceiro tempo
  natural. Fora da sequência, a pergunta continua (mexe em dinheiro).

### O som da SALA é sempre ligado (desde 26/09)

- **Não há mais interruptor.** Decisão do clube: o leilão soa sempre. Os botões "🔔 Lance" e
  "🔔 Arremate" saíram da mesa, a ação `som` saiu do `ACOES_AREAS` (POST com ela é 400) e a chave
  saiu do broadcast. As colunas `som_lance`/`som_arremate` ficaram **dormentes** — não religue.
- Quem não quiser som em casa usa o 🔊 da própria tela, que é preferência do aparelho dela.

### (Histórico) Quem controlava o som da SALA era o locutor

- **Esses efeitos tocam na tela de quem assiste, não na mesa.** Então "mutar" não é preferência
  local: é decisão de quem conduz, e vale para todo mundo. A chave viaja no **broadcast**, como o
  `pagamentos_liberados`, e as telas emudecem sem ninguém recarregar nada.
- **Um interruptor por efeito**, não um geral: eles incomodam de formas diferentes (a caixa
  registradora toca a cada lance; a comemoração, uma vez por item e alto). Um botão só obrigaria a
  sacrificar os dois juntos.
- **O aviso de "te superaram" fica de fora.** É o alerta pessoal de quem perdeu a ponta — o som mais
  útil da tela para quem está disputando —, não parte da festa. A tela **diz isso** ao lado dos
  botões, para a escolha não parecer esquecimento.
- **`qual` vindo da internet não vira `setattr`**: a lista de sons válidos é branca, e fora dela é
  400. É a mesma lição de `minutos`/`quantos`.

### Quem está online é informação da EQUIPE

- **O nome de quem está conectado sai só pelo `/locutor/dados/`**, que é autenticado. Nunca pelo
  broadcast: o estado público é lido por todos os celulares da sala — mesma regra que mantém Pix,
  telefone e endereço fora do stream.
- **A mesma pessoa em duas abas é UMA entrada** (celular + computador), com selo de quantas telas.
  Como o contador conta **conexões**, a lista pode ser menor que ele: diga isso na tela, senão
  parece que o número mente. Quem ainda está na tela de entrada conta e não tem nome.

### Foto de item: o gargalo é o UPLOAD, e o EXIF é a armadilha

- **O que demora ao cadastrar item não é o servidor.** O `preparar_foto` leva décimos de segundo; a
  foto do celular tem 2 a 5 MB e sobe inteira. Reduzir **no navegador** antes de enviar é o ganho
  grande — o servidor guarda no máximo 1280 px de largura de qualquer jeito.
- **Desenhar num canvas APAGA o EXIF.** Se a rotação não tiver sido aplicada na leitura, a foto sobe
  deitada e o servidor não tem mais como consertar. Não basta pedir
  `imageOrientation: "from-image"`: **confira** comparando com as dimensões que o elemento de imagem
  reporta (ele orienta pelo EXIF desde sempre) e, divergindo, **pule a redução**. Item deitado no
  pregão é pior do que cadastro lento.
- **Redução no cliente é melhoria progressiva**, nunca a garantia do tamanho: sem JS ou sem suporte,
  o original sobe inteiro e o servidor reduz como sempre.
- **No servidor, não decodifique o que vai jogar fora**: `img.draft("RGB", (largura, largura))` antes
  de carregar deixa o próprio JPEG entregar a imagem reduzida, e a miniatura sai da **grande**, não
  da original. Medido: 433 ms para 177 ms, mesmo arquivo final.

### Unidade de campo: a que a pessoa usa para pensar

- **Peso de item é digitado em GRAMAS**, e o banco guarda quilos. Pedir "0,35" para uma caneca é
  convidar ao erro de vírgula — e no celular a vírgula é a tecla que o teclado numérico de muitos
  aparelhos não mostra. Em grama o campo é **inteiro**: não há separador para errar.
- **Trocar a unidade de ENTRADA não precisa trocar a de ARMAZENAMENTO.** Converter no `clean` deixou
  os itens já cadastrados válidos e nenhuma tela que lê `peso_kg` precisou mudar — sem migration.
- **O texto de saída segue o tamanho da coisa**: abaixo de 1 kg em gramas, acima em quilos. Quem
  digitou 350 quer ler "350 g"; "0,35 kg" faz o voluntário parar para converter, e ele está
  decidindo se o item cabe no carro.
- **Recuse o que não cabe na precisão, não arredonde para zero**: 5 g em duas casas de quilo vira
  0,00, que é peso vazio disfarçado — exatamente o que os validadores existem para impedir.

### A cobrança é da PESSOA — o botão também

- **Um Pix por pessoa, pelo total**, desde que o pagamento passou para o fim. Botão de cobrança por
  **item** não é só repetição: os vários botões devolvem o **mesmo** código (a cobrança é uma só) e
  cada um anuncia o valor do seu item — o caixa diz "é R$ 10" com um código que cobra R$ 20.
- **O rótulo do botão leva o VALOR** (`📋 Pix de R$ x`). É o que faz o erro aparecer na hora, se um
  dia o que se cobra divergir do que está escrito ao lado.
- **A mensagem pronta lista o que está sendo cobrado**: todos os itens e o total. Com um item só,
  nomeia o item e não repete o total — listar "1 item" e somar embaixo é burocracia. O código Pix
  continua na **última linha**, para a pessoa copiar segurando o dedo.
- **"Marcar pago" continua por item**, e isso não é incoerência: o caixa recebe em dinheiro por uma
  coisa e não por outra, e o pagamento parcial precisa caber.

### Modal do leilão herda um card BRANCO — cuidado ao clonar markup escuro

- **O `.modal-caixa` do `base.css` é branco**, porque nasceu para o sistema do clube, que é claro. As
  telas de equipe do leilão são **escuras**. Clonar conteúdo da mesa para dentro de um modal leva
  junto o `--palco-texto` (#eaf3fb) e dá **letra clara em fundo branco** — ilegível. Aconteceu na
  janela da conta do caixa.
- **Escureça o modal ESPECÍFICO, nunca `body.tela-locutor .modal-caixa`.** O modal do Pix, na mesma
  tela, usa as cores do tema claro **de propósito** e está correto sobre o branco: a regra ampla
  resolveria um e quebraria o outro.
- **Fundo opaco** (`--palco-fundo-2`), não `--palco-card`: este é `rgba(255,255,255,0.06)` e deixa o
  branco de baixo atravessar.
- **Contraste se MEDE, não se avalia a olho.** A sonda calcula a razão pela fórmula do WCAG, subindo
  a árvore até achar o fundo realmente opaco (o `background` do próprio elemento costuma ser
  transparente). Mínimo 4,5; acima de 7 é o nível mais exigente.

### Modais do leilão: o comportamento mora no `modal.js`

- **Um arquivo só** (`static/leilao/js/modal.js`), e não uma cópia por tela. O que se repetia não era
  o desenho (esse vem do `base.css`) e sim o comportamento — e com ele a regra que é fácil esquecer
  ao reescrever: **fecha no fundo só quando o `mousedown` E o `click` foram no fundo**, senão quem
  arrasta para selecionar um texto de dentro e solta fora vê a janela fechar na cara.
- **Carregue o `modal.js` ANTES** do script da tela que o usa. Sem ele, `window.ModalLeilao` não
  existe e o botão simplesmente não abre nada — sem erro visível.
- **Formulário em modal volta ABERTO quando o POST dá erro**, com o que a pessoa digitou. Fechado,
  ela redigita tudo sem nem ver o que estava errado.

### Plural de "item" em português

- **`pluralize:"ns"` sobre "item" rende "itemns".** O filtro anexa; ele não troca o fim da palavra.
  O certo é `ite{{ n|pluralize:"m,ns" }}` → *item* / *itens*. Estava errado em três lugares do
  leilão, e passa despercebido porque não quebra nada — só fica escrito errado na tela.

### A mesa do locutor: o que se anuncia é o que é grande

- **Lista dentro de card de linha PRECISA de teto e rolagem.** Os cards de uma linha têm a altura do
  mais alto, então uma lista sem `max-height` cresce e leva os outros dois junto — a mesa sai da
  tela. Medido: 20 mensagens levavam o chat a 1093px e a página a 1576px. Teto de **320px** nas duas
  listas (lances e chat), para as colunas terem o mesmo corpo.
- **Rolagem em item flex quebra de DOIS jeitos**, e os dois são necessários: sem `max-height` a
  lista cresce; **sem `min-height: 0`** um item flex não encolhe abaixo do conteúdo e o
  `overflow-y: auto` nunca entra em ação. Guarda nova de rolagem cobre os dois.
- **Rodapé de card usa `margin-top: auto`**, não só `flex: 1` na lista acima: quando a lista bate no
  teto e sobra espaço, o auto é o que segura o campo no pé em vez de deixá-lo boiando.
- **Tamanho de letra segue o que o locutor ANUNCIA**: "Valor atual" e "Ganhando" grandes, na linha
  de cima; "Próximo lance" menor, embaixo (é o valor atual mais cinco — ele já sabe).
- **Nome é menor que valor, sempre.** Valor em reais tem tamanho previsível; nome não. Na mesma
  letra, dois sobrenomes longos viram quatro linhas e o card empurra o ▶ Abrir e o 🔨 VENDIDO para
  fora da tela. E **encolher é melhor do que cortar**: nome com reticências é justo o que ele tem de
  ler em voz alta. Vale para qualquer campo de texto livre exibido em destaque.
- **Guarda que lê CSS por `index` do seletor pega o seletor AGRUPADO.** `.chat-mesa` aparece antes
  dentro de `.historico, .fila, …, .chat-mesa`, e o corpo daquele é outro — a guarda caiu nisso na
  primeira execução. Procure a regra por **regex** (`\.classe\s*\{[^}]*propriedade`).

### A mesa do locutor: nenhuma célula vazia

- **A grade do pregão é de duas colunas, e três cards não cabem nela.** Foi assim que nasceu a
  "faixa": a bilheteria entrou como terceiro card, o microfone caiu sozinho na segunda linha e
  sobrou uma **célula vazia** de 353 × 119 px, que o clube viu e perguntou o que era. **Card novo
  não pode deixar célula vazia em NENHUMA largura** — ou entra de três em três, ou faz como o
  **"Online agora"** (24/09, 4º card da linha de cima): em três colunas (1000–1279px) ele ocupa a
  **linha inteira** (`grid-column: 1 / -1`, nomes lado a lado) e só a partir de **1280px** vira a
  quarta coluna. Há teste para as duas faixas.
- **"Online agora" é a mesma lista da janela do 👥**, desenhada pela mesma função
  (`desenharQuemChegou`), vinda do `/locutor/dados/` autenticado — **nunca** do broadcast. Ela se
  atualiza no evento `online` (entrou/saiu alguém) pela `recarregarDados`, que já junta rajadas em
  700 ms; não crie um segundo fetch nem um timer próprio para ela.
- **A ordem é o USO, não a simetria.** Linha de cima: **item em pregão · lances · chat · online agora**, que é o
  que o locutor acompanha ao mesmo tempo enquanto conduz. Linha de baixo: **fila · sua voz ·
  pagamentos**, que se usam uma vez por noite. Quem separa isso por "tamanho de card" acaba
  mandando o locutor procurar informação em dois cantos da tela no meio do pregão.
- **Abaixo de 1000px as duas grades empilham** (`grid-template-columns: minmax(0, 1fr)`). Sem essa
  regra elas herdam o `2fr 1fr` da base e a célula vazia volta pela porta dos fundos, numa largura
  de laptop — a `.tres` carregava esse buraco latente desde sempre.
- **Card com campo no rodapé precisa ser coluna flex.** Os três cards da linha esticam até a altura
  do mais alto, então o espaço que sobra aparece **embaixo** do conteúdo: o campo de falar do chat
  boiava no meio. Lista com `flex: 1`, campo colado no pé.
- **Guarda que procura o TEXTO de um bug tem de tirar os comentários antes.** O comentário que
  explica a correção cita o texto (`"fecha em NaN:NaN"`), e sem a limpeza o teste acusa a própria
  documentação dele. É a mesma armadilha do scanner de funções, e mordeu de novo.

### A mesa do locutor sente a sala

- **Quem conduz não LÊ a mesa.** Ele está falando, de olho no microfone e na lista; o que chega até
  ele é **movimento**. Informação nova na mesa que só troque uma palavra de lugar não é vista — e
  duas coisas que ele precisa saber (a ponta trocou, a sala reagiu) são exatamente disso.
- **O nome de quem está ganhando acende a cada LANCE** (`acende-o-nome`), não a cada troca de nome.
  Na tela do público a classe entra quando o líder muda; aqui o que interessa é *entrou lance
  agora*, que é o que o locutor repete em voz alta. Hoje as duas coisas coincidem (ninguém cobre o
  próprio lance) — `acenderLider` compara **também o valor** justamente para não depender disso.
- **Item novo não acende.** Abrir o próximo é ação da própria mesa, o locutor acabou de clicar, e
  ainda não há lance nenhum. A guarda é comparar o **id do lote** antes de animar.
- **O mesmo cuidado de rolagem do card do pregão vale aqui**: `transform` não empurra o layout mas
  **conta para a área rolável**, então o nome comprido no pico estoura a coluna. A trava é
  `overflow-x: clip` + `overflow-clip-margin` no `.numero` (**`clip`, não `hidden`**) e
  `transform-origin: left center` — crescendo do meio, o nome invade a coluna vizinha da grade.
  Efeito novo que escale alguma coisa **passa pela sonda headless** antes de subir.
- **As reações do público sobem na mesa também, e a mesa só OUVE.** Não há botão de reagir ali:
  quem reage é o público. Isso **não custa requisição nenhuma** — o evento `reacoes` já chegava à
  conexão da mesa (o hub entrega tudo a todos) e ela o jogava fora.
- **Um jeito só de desenhar emoji**: mesmo `reacoes.js`, mesma classe de trilho, mesmo CSS do
  público. Tela nova que queira mostrar reação liga o mesmo módulo — não duplique o desenho.
- **Cor dentro de `@keyframes` vai por extenso.** `inherit` num keyframe é pedir para o navegador
  adivinhar; escreva o valor de ida e o de volta (aqui, `--palco-texto` → `--ouro` → `--palco-texto`).
### O chat do intervalo

- **Estado do chat e estado do leilão têm de concordar.** `chat_aberto_ate` é uma hora futura no banco e
  **não sabe que o leilão acabou**: sozinha, ela deixava a caixa de conversa de pé numa tela cujo envio o
  servidor recusava com "nenhum leilão ao vivo". `Leilao.chat_aberto` exige `status == "ao_vivo"`, e
  `mudar_status` fecha o chat ao sair do ar — inclusive o do leilão encerrado para dar lugar a outro (o
  `update` em massa também limpa `chat_aberto_ate`).
- **Toda porta que a tela abre, o servidor tem de aceitar.** Mostrar um campo que o servidor vai recusar é
  pior do que não mostrar: a pessoa digita, envia e não entende. Ao criar controle novo, confira que a
  condição que o EXIBE é a mesma que o servidor usa para ACEITAR.
- **Mensagem de recusa é lida por quem está na tela**, não pelo servidor: "nenhum leilão ao vivo" era
  verdade internamente e mentira para quem estava olhando o leilão. Diga o que aconteceu.

### Som, música e a tela do celular

- **A porta de entrada tem um caminho só: "Entrar com som".** O botão "entrar sem som" foi removido e
  não deve voltar: quem errava o toque caía num leilão mudo e concluía que o site estava quebrado — não
  há como a pessoa adivinhar que o silêncio foi escolha dela. A saída continua no 🔇 do topo, onde ela
  sabe o que está desligando. Esse toque é também o **gesto** que o navegador exige para liberar áudio;
  sem ele nada toca, e foi assim que o aviso de lance ficou mudo a primeira vez.
- **Lance e arremate tocam os arquivos do clube** (`static/leilao/som/`, desde 24/09), baixados na
  entrada e com o **sintetizado em WebAudio como reserva** (`som.js`); superado e demais efeitos seguem
  sintetizados. As três amarras estão em "Som do leilão: arquivo do clube, com três amarras".
- **Não há música de fundo, e isso foi decidido de ouvido.** Existiu, pronta e funcionando, e o clube
  ouviu e não quis. Sobraram colunas dormentes (`Leilao.musica_ligada`, `musica_volume`,
  `ConfigLeilao.musica`) que **nada lê**. Não religue por conta própria — é o tipo de decisão que só quem
  vai conduzir o evento pode tomar. `SemMusicaDeFundoTests` guarda a porta.
- **A tela do celular não pode apagar** (`tela_acesa.js`). Entre um lance e outro ninguém toca em nada;
  para o sistema é aparelho ocioso e o protetor entra em 30 s, fazendo a pessoa perder item por
  economizador de bateria. Três coisas, ao mexer nisso:
  - **`visibilitychange` é obrigatório.** O sistema derruba o bloqueio toda vez que a aba sai da frente
    e **não o devolve**. Sem repor, quem atende uma ligação volta com a tela apagando — e parece que a
    proteção nunca existiu.
  - **Só funciona em HTTPS.** Em `http://` o navegador nem expõe a API; no `runserver` a ausência é
    normal e não é bug.
  - **O vídeo do plano B (iOS < 16.4) fica visível** — 1px, `opacity: .01`. Com `display:none` ou
    `hidden` o navegador o pausa e ele não segura tela nenhuma.
- **`$("id").metodo` com `id` inexistente mata o arquivo de JS inteiro**: é `TypeError` em cima de
  `null`, o script morre naquela linha e **nada depois é ligado** — a tela abre bonita e nenhum botão
  funciona. Ao remover um elemento do template, remova o listener junto. Há teste
  (`BotoesQueOJsProcuraExistemTests`) varrendo os dois pares template/JS.
