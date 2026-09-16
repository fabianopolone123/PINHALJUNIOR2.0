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


## Parcelamento lançado pelo clube (Mensalidades → Parcelas)

Lançamento **manual** de parcelas para uma conta (família ou diretoria), dividido no dia
`DIA_VENCIMENTO_PARCELA` mês a mês. Não confundir com `ParcelaInscricao`, que é o parcelamento do valor da
**diretoria dentro da inscrição** de evento e nasce sozinho no ato.

- **O vínculo é com a CONTA** (`ParcelamentoClube.usuario`), não com o aventureiro. É isso que faz o mesmo
  lançamento servir para família e para **diretoria sem filho no clube**. `aventureiro` é opcional (diz *por
  quem* é o acerto) e `evento` é opcional (diz *de onde* veio a dívida).
- **O seletor "para quem" tem TRÊS grupos** (`_alvos_parcelamento`): Aventureiros (`av:<id>`, ativos),
  **Responsáveis** (`conta:<id>`, a família pelos adultos da ficha — **pai, mãe e responsável legal**, uma
  opção cada, em `_alvos_responsaveis`; quem acumula papéis vira uma opção só) e Diretoria
  (`conta:<id>`). Os dois últimos produzem o **mesmo** alvo: o grupo novo é só outro caminho para a mesma
  conta, e por isso `_resolver_alvo` não mudou. A conta que já está em Diretoria **não** se repete em
  Responsáveis, e esse grupo **não filtra `ativo`** — é a exceção do parcelamento (dívida combinada continua
  devida), então a família cujo aventureiro saiu ainda precisa ser alcançável. `demo` fica fora dos três.
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
  aventureiro → ficha de diretoria → **`resp_nome` da família** → `get_full_name()`/username. Sem o penúltimo
  degrau a lista de parcelas mostrava o **nome de acesso** da conta.
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

- **UM worker uvicorn, sempre.** O hub de eventos (`leilao/hub.py`) e o relógio do pregão vivem **na
  memória do processo**. Dois workers = dois leilões paralelos, cada um com o seu cronômetro, e metade
  das pessoas vendo um pregão e metade vendo outro. Se um dia precisar escalar, o caminho é trocar o hub
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
- **O relógio é do servidor.** `Lote.fecha_em` é data/hora **absoluta** e todo estado leva `servidor_em`;
  o navegador calcula a diferença uma vez e aplica. Celular com a hora errada (tem muitos) vê o mesmo
  cronômetro. **Nunca** mandar "faltam N segundos" e deixar o cliente contar sozinho.
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
- **Lances são por RODADA** (`Lote.lances_da_rodada()`): um item volta para a fila quando o arrematante
  não paga, e os lances da rodada anulada não podem aparecer na tela.
- **Não há "desfazer lance"**, e a decisão é do clube. `Lance.cancelado` é coluna dormente — não religue
  por conta própria. `SemDesfazerLanceTests` guarda a porta.
- **Chamada externa lenta sai do caminho crítico.** O Pix é gerado numa thread **depois** de publicar o
  "vendido" — ninguém espera o Mercado Pago com a tela parada. Sem credencial, o leilão **não para**: o
  locutor dá baixa manual. Thread de fundo **fecha a conexão** no fim (`connections.close_all()`).
- **Sem biblioteca externa, aqui também.** WebRTC é API nativa (`RTCPeerConnection` + `fetch` do SDP, ~40
  linhas); o QR vem pronto em base64 do Mercado Pago; o som é **sintetizado em WebAudio** (zero arquivo
  para baixar, zero latência); confete é canvas escrito à mão. A única dependência nova é o **uvicorn**,
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
- **Só se entrega o que foi PAGO** (`Arremate.a_entregar`). Mandar o item antes de o dinheiro cair é o
  erro que o prazo de 15 minutos existe para evitar — e a regra mora no servidor, não na tela.
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

- **A âncora é a `referencia`, não a FK.** `Arremate.pagamento` aponta para UMA cobrança e é trocado ao
  refazer o Pix; a anterior fica órfã — e é ela que está **na tela da pessoa** no instante em que o caixa
  aperta "+15 min" ou "vai pagar depois". Pagar aquele código e ninguém ser marcado como pago já foi bug
  real. Os dois caminhos (`_arremates_do_pagamento` no webhook, `cobrancas_do_arremate` na consulta de
  reforço) recuperam o arremate de `LEILAO-<id>` / `LEILAO-<id>-R<timestamp>`.
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
- **Esticar prazo refaz o Pix** (`estender_prazo`). O código nasce com a validade do prazo e vence junto:
  esticar só o `expira_em` entrega à pessoa mais tempo na tela e um copia e cola que o banco recusa. E
  soma **a partir de agora** — o caso real é o prazo prestes a vencer, e somar ao passado daria nada.
- **Esticar prazo é do CAIXA** (`ACOES_AREAS`), não do locutor: é conversa de quem cuida do dinheiro.
- **"Vai pagar depois" precisa entregar o Pix.** Sem o código na mão do caixa, o botão só tira o item da
  fila e a cobrança some do mapa. O código do combinado vale **7 dias**: 15 minutos é o prazo que aquele
  botão acabou de dispensar.
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
- **A unidade da divisão é a PESSOA, não o item.** Dois itens da mesma casa são uma visita só; contar itens
  faria um entregador parecer sobrecarregado sem estar.
- **Bairro nunca é partido** entre dois entregadores — é exatamente o que a divisão existe para evitar.
- **A chave da região é normalizada** (sem acento, sem caixa, espaços colapsados): cada pessoa digita o
  bairro de um jeito, e o mesmo bairro escrito de duas formas viraria duas regiões.
- **A divisão é determinística.** A equipe reabre a tela, manda o link para outra pessoa da mesa e precisa
  ver o mesmo resultado; por isso o empate desempata pelo índice e o parâmetro vive no GET.
- **Não peça "rastreio" na entrega.** É voluntário levando na casa da pessoa: não existe código para anotar,
  e o campo pedindo um só fazia hesitar quem preenchia com pressa.

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
- **Os efeitos sonoros são sintetizados, sem arquivo nenhum** (`som.js`). Zero download, zero
  licenciamento e nada de binário no repositório.
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
