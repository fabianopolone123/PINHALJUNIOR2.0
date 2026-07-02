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
