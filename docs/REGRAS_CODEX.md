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
- Item de menu ativo recebe a classe `ativo` (destaque em verde).
- Cada tela interna deve ter seu próprio CSS (não misturar com `login.css`), reaproveitando a paleta.
- Novos itens de menu devem ser adicionados no `<nav class="menu">`, no ponto marcado por comentário.
- O menu foi preparado para permissões futuras: exibir/ocultar itens conforme o perfil do usuário
  (ex.: envolver o item em `{% if ... %}`), quando a autenticação for implementada.
- Ícones podem ser emoji, caractere ou SVG inline — nunca biblioteca externa.

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
  se chamam `usuario` e `senha`. Em erro, mostra "Usuário ou senha inválidos." (classe `.aviso-login`).
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

## Padrão da tela "Usuários" (vínculos familiares)

- **Rota** `core:usuarios` (`/usuarios/`), com `@login_required`. Qualquer usuário autenticado
  acessa; FUTURO: poderá ser restrito por perfil (documentar quando implementar permissões).
- **Agrupamento de responsáveis** (helpers em `core/views.py`): para cada aventureiro considerar
  pai, mãe e responsável legal; a chave de deduplicação é `_chave_responsavel` — CPF, senão
  nome+WhatsApp, senão nome normalizado (`_normaliza` remove acentos/caixa); responsáveis sem nome
  são ignorados. A mesma pessoa em papéis diferentes aparece uma única vez, com os papéis juntos.
- **Vínculos**: por responsável, listar os aventureiros ligados (nome, idade e papéis do vínculo).
  Contadores: Responsáveis (pessoas únicas), Aventureiros (total), Vínculos (total de relações
  papel×aventureiro).
- **Somente resumo — NUNCA dados sensíveis** nesta tela: proibido CPF, RG, certidão, endereço,
  e-mail, telefone/WhatsApp, ficha médica, autorização de imagem e foto.
- **Pesquisa**: filtro no front-end (`static/js/usuarios.js`) sobre o texto dos cards, ignorando
  caixa e acentos; mensagem "Nenhum vínculo encontrado para essa pesquisa." quando não houver
  resultado. Sem AJAX nesta etapa.
- **Reuso visual**: a tela reaproveita o layout/menu de `inicio.css`; estilos próprios em
  `static/css/usuarios.css`. Sem bibliotecas externas.
