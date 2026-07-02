# Estado Atual do Sistema

> Resumo rápido do estado atual. Atualize este arquivo após qualquer alteração.

**Última atualização:** 2026-07-02 (fluxo para cadastrar múltiplos aventureiros na mesma conta)

## Nome do sistema
Clube de Aventureiros Pinhal Júnior

## Objetivo do sistema
Sistema web do clube. No momento possui apenas a tela inicial de login (visual),
servindo de base para o desenvolvimento futuro.

## Funcionalidades prontas
- Estrutura inicial do Django funcionando.
- Tela de login visual e responsiva (mobile first) na rota `/`, com visual moderno.
- Logo do clube exibido no topo da tela de login (com fallback "CA" caso não carregue).
- Formulário visual: campos "Usuário" e "Senha", botão "Entrar", link "Esqueci minha senha".
- Tela inicial interna (área logada) na rota `/inicio/`, com menu lateral fixo (desktop)
  e menu recolhível/gaveta (mobile), item "Meus Dados" ativo e cards visuais.
- Botão "Entrar" da tela de login navega (apenas visualmente) para `/inicio/`, sem autenticação.
- Fluxo de cadastro de aventureiro em `/cadastro/`: wizard de 7 etapas (conta, ficha de inscrição,
  responsáveis, ficha médica, declaração médica, autorização de imagem, revisão), com barra de
  progresso, campos condicionais, upload/preview de foto e tela de sucesso em `/cadastro/sucesso/`.
- Link "Cadastre-se" na tela de login (entre "Entrar" e "Esqueci minha senha"), em estilo
  discreto de link de texto (levemente maior que "Esqueci minha senha").
- Ao finalizar o cadastro, cria o `User` do Django e salva Aventureiro + FichaMedica + AutorizacaoImagem.
- Cadastro de **múltiplos aventureiros na mesma conta**: a tela de sucesso mostra o nome cadastrado e
  oferece "Cadastrar outro aventureiro" e "Ir para a tela inicial". A opção leva a
  `/cadastro/novo-aventureiro/` (wizard de 6 etapas, sem "Conta de acesso"), que vincula o novo
  aventureiro ao mesmo usuário — identificado temporariamente pela sessão (`cadastro_usuario_id`),
  já que ainda não há login real. Sem usuário na sessão, essa rota redireciona para `/cadastro/`.
- Nesse fluxo, é possível reaproveitar os dados de pai, mãe e responsável legal do último cadastro
  marcando uma opção; os campos são preenchidos automaticamente e podem ser editados antes de finalizar.

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
- Área principal com cabeçalho de boas-vindas, card em destaque "Meus Dados" e cards
  ilustrativos (Cadastro, Atividades, Conquistas), com sombras suaves e hover.
- Fundo claro com detalhes decorativos radiais suaves; animação de entrada do conteúdo.
- Suporte a `prefers-reduced-motion`. Testado em mobile (390px, sem overflow) e desktop (1280px).

## Models existentes
- `Aventureiro` — ficha de inscrição + dados dos responsáveis (pai, mãe, responsável legal);
  FK `usuario` (um usuário pode ter vários aventureiros); `data_inscricao` e `criado_em` automáticos.
- `FichaMedica` — OneToOne com `Aventureiro` (plano de saúde, doenças, alergias, condições, tipo sanguíneo).
- `AutorizacaoImagem` — OneToOne com `Aventureiro` (dados do menor e do responsável para o termo).

## Funcionalidades incompletas / não implementadas
- Autenticação real (login/logout) — NÃO implementada (o cadastro cria o `User`, mas não faz login).
  O usuário atual é mantido apenas por sessão (`cadastro_usuario_id`), de forma **temporária**.
- Link "Esqueci minha senha" — sem funcionalidade (aponta para `#`).
- Página real de "Meus Dados" e listagem de aventureiros — NÃO criadas.
- Permissões / perfis de usuário — NÃO implementados.
- Validação avançada de CPF — NÃO implementada (deixada para o futuro).
- Envio de e-mail — NÃO implementado.

## Próximas etapas previstas
- (A definir) Implementar autenticação de usuários (login/logout) usando o `User` criado no cadastro
  e substituir a identificação temporária por sessão (`cadastro_usuario_id`) por `request.user`.
- (A definir) Criar a página real de "Meus Dados" e a listagem de aventureiros do responsável.
- (A definir) Implementar o fluxo de "Esqueci minha senha".

## Apps existentes
- `config` — projeto Django (settings, urls, wsgi, asgi).
- `core` — app principal (views de login, tela inicial e cadastro; models de aventureiro).

## Templates existentes
- `templates/core/login.html`
- `templates/core/inicio.html`
- `templates/core/cadastro.html` (wizard de cadastro)
- `templates/core/cadastro_sucesso.html`
- `templates/core/_campo.html` e `templates/core/_campo_check.html` (parciais de campo reutilizáveis)

## Arquivos CSS existentes
- `static/css/login.css`
- `static/css/inicio.css`
- `static/css/cadastro.css`

## Arquivos JavaScript existentes
- `static/js/cadastro.js` — wizard de etapas (numeração e índices calculados dinamicamente, servindo
  tanto ao cadastro de 7 etapas quanto ao de 6 etapas), barra de progresso, campos condicionais,
  preview da foto, atalhos (copiar pai/mãe para responsável legal), reaproveitamento dos dados dos
  responsáveis no cadastro de novo aventureiro, revisão e validação dos aceites.
- Scripts inline em `login.html` (redireciona para `/inicio/`) e em `inicio.html` (menu recolhível).

## Rotas existentes
- `/` — tela de login (`core.views.login_view`, nome `core:login`).
- `/inicio/` — tela inicial interna (`core.views.inicio_view`, nome `core:inicio`).
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
