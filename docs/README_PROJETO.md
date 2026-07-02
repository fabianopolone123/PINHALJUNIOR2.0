# Clube de Aventureiros Pinhal Júnior

## Nome do projeto

Clube de Aventureiros Pinhal Júnior

## Objetivo geral do sistema

Sistema web para o Clube de Aventureiros Pinhal Júnior. O projeto já possui
autenticação real (login/logout), cadastro de conta e de aventureiros (com ficha
médica e autorização de imagem) e uma área interna "Meus Dados" que exibe os dados
da conta e dos aventureiros do usuário logado.

O foco continua sendo uma interface bonita, moderna e **responsiva (mobile first)**,
com CSS próprio (sem frameworks externos).

## Stack usada

- **Django** (5.2.x) — framework web principal
- **Python** (3.10+)
- **HTML** — templates
- **CSS** — estilos próprios, sem frameworks externos
- **JavaScript** — puro, sem frameworks (wizard do cadastro em `static/js/cadastro.js` + scripts inline)
- **Pillow** — necessário para o `ImageField` (upload da foto 3x4)
- **Banco de dados**: SQLite (padrão do Django), com os models de cadastro migrados

## Estado atual do sistema

- Estrutura inicial do Django criada e funcionando.
- Tela de login visual acessível na rota principal `/` (com link "Cadastre-se").
- Tela inicial interna (área logada) acessível em `/inicio/`, com menu lateral e o item "Meus Dados".
- Fluxo de cadastro de aventureiro em `/cadastro/` (wizard de 7 etapas) que cria o `User` e salva
  a ficha de inscrição, a ficha médica e a autorização de imagem; confirmação em `/cadastro/sucesso/`.
- Cadastro de outro aventureiro na mesma conta em `/cadastro/novo-aventureiro/` (wizard de 6 etapas,
  sem "Conta de acesso"), com opção de reaproveitar os dados dos responsáveis do último cadastro.
- Models de cadastro criados e migrados (`Aventureiro`, `FichaMedica`, `AutorizacaoImagem`).
- Logo do clube exibido no login, no menu lateral e no cadastro.
- **Autenticação real implementada** (login por username/senha, logout e `@login_required` na área interna).
- Tela "Meus Dados" funcional: card do **Responsável** no topo (com edição) e os aventureiros
  do usuário logado em cards clicáveis com detalhes por seção.
- **Sem controle de permissões / perfis** (preparado para o futuro).

## Como rodar o projeto localmente

Pré-requisitos: Python 3.10+ e Django instalado (ver `requirements.txt`).

```bash
# (opcional) criar e ativar ambiente virtual
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# instalar dependências
pip install -r requirements.txt

# rodar o servidor de desenvolvimento
python manage.py runserver
```

Depois, acesse no navegador: http://127.0.0.1:8000/

Observação: ao rodar, o Django pode exibir um aviso sobre migrações pendentes
das apps internas (admin, auth, sessions). Isso é normal e não afeta a tela de
login. Se quiser remover o aviso, rode `python manage.py migrate`.

### Popular o banco com dados de teste

Para validar rapidamente uma conta com 2 aventureiros já cadastrados, use o
comando de gerenciamento que gera dados fictícios (sem pessoas nem imagens reais):

```bash
python manage.py criar_dados_teste
```

Ele cria (ou atualiza, se já existirem) o usuário `teste_responsavel` (senha `123456`)
com 2 aventureiros completos — ficha de inscrição, ficha médica, autorização de imagem
e fotos 3x4 fictícias geradas com Pillow em `media/aventureiros/fotos_teste/`
(`lucas_teste.png` e `ana_teste.png`). O comando é seguro para rodar mais de uma vez
(usa `get_or_create`/`update_or_create` e não apaga dados de outros usuários). As fotos só
são regeradas quando estão faltando ou apontando para um arquivo inexistente; se já
estiverem corretas, são mantidas (o comando informa "foto mantida" ou "foto gerada").

### Como testar o login e a tela "Meus Dados"

1. Rode `python manage.py criar_dados_teste` (se ainda não rodou).
2. Acesse `http://127.0.0.1:8000/` e faça login com **usuário `teste_responsavel`** e
   **senha `123456`** — você será levado a `/inicio/`.
3. Em "Meus Dados" aparecem os dados da conta e os 2 aventureiros de teste (com foto,
   ficha médica e autorização de imagem em seções recolhíveis).
4. Para sair, use o botão **Sair** no menu lateral (volta ao login). Depois disso,
   acessar `/inicio/` diretamente redireciona para a tela de login.

## Estrutura geral de pastas

```
PINHALJUNIOR2.0/
├── CODEX.md                  # Guia rápido para o Codex
├── manage.py                 # Utilitário de linha de comando do Django
├── requirements.txt          # Dependências do projeto
├── .gitignore
├── db.sqlite3                # Banco SQLite (vazio / padrão)
├── config/                   # Configuração do projeto Django
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── core/                     # App principal
│   ├── __init__.py
│   ├── admin.py              # Models registrados no admin
│   ├── apps.py
│   ├── models.py             # Aventureiro, FichaMedica, AutorizacaoImagem
│   ├── forms.py              # Formulários do cadastro
│   ├── urls.py
│   ├── views.py
│   └── migrations/
│       ├── __init__.py
│       └── 0001_initial.py
├── templates/
│   └── core/
│       ├── login.html            # Tela de login
│       ├── inicio.html           # Tela inicial interna
│       ├── cadastro.html         # Wizard de cadastro (7 etapas)
│       ├── cadastro_sucesso.html # Confirmação do cadastro
│       ├── _campo.html           # Parcial de campo (label + widget)
│       └── _campo_check.html     # Parcial de campo checkbox
├── static/
│   ├── css/
│   │   ├── login.css
│   │   ├── inicio.css
│   │   └── cadastro.css
│   ├── js/
│   │   └── cadastro.js       # Wizard, condicionais, preview de foto
│   └── img/
│       ├── logo.png
│       ├── logo_original_backup.png
│       └── LEIA-ME.txt
├── media/                    # Uploads dos usuários (ex.: fotos) — não versionado
└── docs/                     # Documentação interna (este diretório)
    ├── README_PROJETO.md
    ├── REGRAS_CODEX.md
    ├── ESTADO_ATUAL.md
    └── HISTORICO_ALTERACOES.md
```

## Apps existentes

- **config**: projeto Django (settings, urls, wsgi, asgi). Não é um app de negócio.
- **core**: app principal. Views de login, tela inicial e cadastro; models de aventureiro.

## Rotas existentes

- `/` — tela de login com autenticação real (view `core.views.login_view`, nome `core:login`).
- `/sair/` — logout (POST); encerra a sessão e volta ao login (view `core.views.sair_view`, nome `core:sair`).
- `/inicio/` — área logada "Meus Dados", protegida por `@login_required` (view `core.views.inicio_view`, nome `core:inicio`).
- `/meus-dados/responsavel/editar/` — edição dos dados do responsável legal, protegida por login (view `core.views.editar_responsavel_view`, nome `core:editar_responsavel`).
- `/cadastro/` — cadastro inicial: cria a conta + o primeiro aventureiro (view `core.views.cadastro_view`, nome `core:cadastro`).
- `/cadastro/novo-aventureiro/` — cadastra outro aventureiro na mesma conta, sem etapa de conta (view `core.views.cadastro_novo_aventureiro_view`, nome `core:cadastro_novo_aventureiro`).
- `/cadastro/sucesso/` — confirmação, com opções "Cadastrar outro aventureiro" e "Ir para a tela inicial" (view `core.views.cadastro_sucesso_view`, nome `core:cadastro_sucesso`).
- `/admin/` — Django admin (models de cadastro registrados).
- `/media/...` — arquivos de mídia (uploads), servidos pelo Django em DEBUG.

## Models existentes

- **Aventureiro** — ficha de inscrição + dados dos responsáveis; FK `usuario` (um usuário pode ter vários).
- **FichaMedica** — OneToOne com Aventureiro (dados médicos).
- **AutorizacaoImagem** — OneToOne com Aventureiro (dados do termo de imagem).

## Templates existentes

- `templates/core/login.html` — tela de login (com link "Cadastre-se").
- `templates/core/inicio.html` — tela inicial interna.
- `templates/core/cadastro.html` — wizard de cadastro (7 etapas).
- `templates/core/cadastro_sucesso.html` — confirmação do cadastro.
- `templates/core/_campo.html` e `_campo_check.html` — parciais reutilizáveis de campo.

## Arquivos estáticos existentes

- `static/css/login.css`, `static/css/inicio.css`, `static/css/cadastro.css` — estilos por tela.
- `static/js/cadastro.js` — wizard do cadastro (etapas, progresso, condicionais, preview de foto, atalhos, revisão).
- `static/img/logo.png` — logo do clube (usado no login, no menu lateral e no cadastro).
- `static/img/logo_original_backup.png` — backup do logo original recebido.
- `static/img/LEIA-ME.txt` — instruções sobre o logo.

Outros scripts inline: em `login.html` (redireciona para `/inicio/`) e em `inicio.html`
(abre/fecha o menu recolhível no celular).

## Funcionalidades existentes

- Tela de login visual e responsiva na rota `/`, com link "Cadastre-se".
- Tela inicial interna em `/inicio/` com menu lateral (desktop) / gaveta (mobile) e cards.
- Navegação de teste: o botão "Entrar" leva para `/inicio/` (sem autenticação real).
- Cadastro de aventureiro em `/cadastro/` (wizard de 7 etapas): conta de acesso, ficha de inscrição,
  responsáveis, ficha médica, declaração médica, autorização de imagem e revisão. Ao finalizar, cria
  o `User` e salva Aventureiro + FichaMedica + AutorizacaoImagem; confirma em `/cadastro/sucesso/`.
- Cadastro de **múltiplos aventureiros na mesma conta**: a tela de sucesso oferece "Cadastrar outro
  aventureiro", que leva a `/cadastro/novo-aventureiro/` (wizard de 6 etapas, sem "Conta de acesso").
  Esse fluxo reaproveita o mesmo usuário (identificado por sessão, temporariamente) e permite preencher
  automaticamente os dados de pai/mãe/responsável legal com base no último cadastro.

## Funcionalidades ainda NÃO implementadas

- Funcionalidade do link "Esqueci minha senha" (hoje aponta para `#`).
- Edição dos dados do aventureiro pela área logada (hoje é somente visualização).
- Controle de permissões / perfis de usuário.
- Validação avançada de CPF e envio de e-mail.

## Observações importantes para futuros desenvolvimentos

- **Não usar** Bootstrap, Tailwind ou frameworks visuais externos (CSS é próprio).
- Manter o foco em **responsividade mobile first**.
- Preservar o padrão visual já criado (paleta azul/verde inspirada no logo).
- A `SECRET_KEY` em `config/settings.py` é de desenvolvimento; trocar em produção.
- `DEBUG = True` e `ALLOWED_HOSTS = []` são configurações de desenvolvimento.
- Ao criar models, lembrar de gerar as migrations correspondentes.
- Sempre atualizar a documentação em `docs/` após qualquer alteração
  (ver `CODEX.md` e `docs/REGRAS_CODEX.md`).
