# Estado Atual do Sistema

> Resumo rápido do estado atual. Atualize este arquivo após qualquer alteração.

**Última atualização:** 2026-07-02 ("Meus Dados" reorganizado: card do responsável (com edição) + aventureiros clicáveis)

## Nome do sistema
Clube de Aventureiros Pinhal Júnior

## Objetivo do sistema
Sistema web do clube com autenticação real, cadastro de conta e de aventureiros e
área interna "Meus Dados" que exibe os dados do usuário logado e de seus aventureiros.

## Funcionalidades prontas
- Estrutura inicial do Django funcionando.
- Tela de login responsiva (mobile first) na rota `/`, com visual moderno.
- **Autenticação real**: login por username/senha (`authenticate` + `login`), com mensagem
  "Usuário ou senha inválidos." em caso de erro; após logar, vai para `/inicio/`.
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
    todos os dados em seções recolhíveis: Dados pessoais, Endereço, Pai, Mãe, Responsável legal,
    Ficha médica e Autorização de imagem. Botão "Editar dados do aventureiro" ainda desabilitado
    (edição completa prevista para depois).
  - Botão "Cadastrar outro aventureiro" e estado vazio amigável quando não há aventureiros.
- Edição do responsável em `/meus-dados/responsavel/editar/` (form `ResponsavelLegalForm`): altera
  nome, parentesco, CPF, e-mail e WhatsApp de todos os aventureiros do usuário com o mesmo CPF de
  responsável (ou apenas o mais recente, se nenhum coincidir); volta a `/inicio/` com mensagem de sucesso.
- Menu lateral fixo (desktop) e recolhível/gaveta (mobile), com nome do usuário e botão "Sair".
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
- Mensagens de feedback (sucesso/erro) via framework de messages do Django.
- Fundo claro com detalhes decorativos radiais suaves; animação de entrada dos cards.
- Suporte a `prefers-reduced-motion`. Layout responsivo (mobile first): cards empilhados no
  celular e em grade de 2 colunas em telas largas; sem overflow horizontal (validado).

## Models existentes
- `Aventureiro` — ficha de inscrição + dados dos responsáveis (pai, mãe, responsável legal);
  FK `usuario` (um usuário pode ter vários aventureiros); `data_inscricao` e `criado_em` automáticos.
- `FichaMedica` — OneToOne com `Aventureiro` (plano de saúde, doenças, alergias, condições, tipo sanguíneo).
- `AutorizacaoImagem` — OneToOne com `Aventureiro` (dados do menor e do responsável para o termo).

## Funcionalidades incompletas / não implementadas
- Link "Esqueci minha senha" — sem funcionalidade (aponta para `#`).
- Edição dos dados do aventureiro pela área logada — hoje "Meus Dados" é somente visualização.
- Permissões / perfis de usuário — NÃO implementados.
- Validação avançada de CPF — NÃO implementada (deixada para o futuro).
- Envio de e-mail — NÃO implementado.

## Próximas etapas previstas
- (A definir) Permitir editar os dados do aventureiro pela área logada.
- (A definir) Implementar o fluxo de "Esqueci minha senha".
- (A definir) Novos itens de menu e controle de permissões/perfis.

## Apps existentes
- `config` — projeto Django (settings, urls, wsgi, asgi).
- `core` — app principal (views de login, tela inicial e cadastro; models de aventureiro).

## Templates existentes
- `templates/core/login.html` (login real, com mensagem de erro)
- `templates/core/inicio.html` (área "Meus Dados": card do responsável + cards clicáveis dos aventureiros)
- `templates/core/editar_responsavel.html` (edição do responsável legal)
- `templates/core/cadastro.html` (wizard de cadastro)
- `templates/core/cadastro_sucesso.html`
- `templates/core/_campo.html` e `templates/core/_campo_check.html` (parciais de campo reutilizáveis)
- `templates/core/_dado.html` (parcial rótulo+valor usada em "Meus Dados")

## Arquivos CSS existentes
- `static/css/login.css`
- `static/css/inicio.css`
- `static/css/cadastro.css`

## Arquivos JavaScript existentes
- `static/js/cadastro.js` — wizard de etapas (numeração e índices calculados dinamicamente, servindo
  tanto ao cadastro de 7 etapas quanto ao de 6 etapas), barra de progresso, campos condicionais,
  preview da foto, atalhos (copiar pai/mãe para responsável legal), reaproveitamento dos dados dos
  responsáveis no cadastro de novo aventureiro, revisão e validação dos aceites.
- `static/js/inicio.js` — menu recolhível no celular (as seções de detalhes usam `<details>` nativo,
  sem JS). Substitui o script inline anterior de `inicio.html`.

## Rotas existentes
- `/` — tela de login com autenticação real (`core.views.login_view`, nome `core:login`).
- `/sair/` — logout (POST) (`core.views.sair_view`, nome `core:sair`).
- `/inicio/` — área "Meus Dados", protegida por `@login_required` (`core.views.inicio_view`, nome `core:inicio`).
- `/meus-dados/responsavel/editar/` — edição do responsável, protegida por login (`core.views.editar_responsavel_view`, nome `core:editar_responsavel`).
- `/cadastro/` — cadastro inicial: conta + primeiro aventureiro (`core.views.cadastro_view`, nome `core:cadastro`).
- `/cadastro/novo-aventureiro/` — outro aventureiro na mesma conta (`core.views.cadastro_novo_aventureiro_view`, nome `core:cadastro_novo_aventureiro`).
- `/cadastro/sucesso/` — confirmação (`core.views.cadastro_sucesso_view`, nome `core:cadastro_sucesso`).
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
- Requer `Pillow` (já instalado) para o `ImageField` da foto.

## Versionamento (Git)
- Repositório Git inicializado; branch principal: `main`.
- Remoto `origin`: https://github.com/fabianopolone123/PINHALJUNIOR2.0.git
- `.gitignore` configurado para Python/Django (ignora `.env`, `*.sqlite3`, ambientes virtuais, cache, `staticfiles/`, `media/`, etc.).
- `README.md` na raiz com descrição básica e apontando para a pasta `docs/`.
- Regra obrigatória: após qualquer alteração, rodar `git add .`, criar commit descritivo em
  português do Brasil e fazer `git push` (ver `CODEX.md` e `docs/REGRAS_CODEX.md`).

## Observações importantes para continuação
- Não usar Bootstrap, Tailwind ou frameworks visuais externos (CSS é próprio).
- Manter responsividade mobile first e o padrão visual azul/verde já criado.
- Ao criar models, gerar as migrations correspondentes.
- Sempre atualizar `docs/ESTADO_ATUAL.md` e `docs/HISTORICO_ALTERACOES.md` após qualquer alteração.
- Ao final de cada alteração, versionar no Git (commit + push) conforme o fluxo obrigatório.
