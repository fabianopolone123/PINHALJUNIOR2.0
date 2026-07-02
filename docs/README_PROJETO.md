# Clube de Aventureiros Pinhal Júnior

## Nome do projeto

Clube de Aventureiros Pinhal Júnior

## Objetivo geral do sistema

Sistema web para o Clube de Aventureiros Pinhal Júnior. No momento, o projeto
possui apenas a **tela inicial de login** (visual), servindo de base para o
desenvolvimento futuro (autenticação, área interna, cadastros, etc.).

O foco atual é ter uma interface bonita, moderna e **responsiva (mobile first)**,
sem ainda implementar lógica de autenticação ou banco de usuários.

## Stack usada

- **Django** (5.2.x) — framework web principal
- **Python** (3.10+)
- **HTML** — templates
- **CSS** — estilos próprios, sem frameworks externos
- **JavaScript** — apenas o mínimo necessário (pequeno script inline na tela de login)
- **Banco de dados**: SQLite (padrão do Django, ainda não utilizado para dados do sistema)

## Estado atual do sistema

- Estrutura inicial do Django criada e funcionando.
- Tela de login visual acessível na rota principal `/`.
- Tela inicial interna (área logada) acessível em `/inicio/`, com menu lateral e o item "Meus Dados".
- Logo do clube exibido na tela de login e no menu lateral.
- **Autenticação ainda NÃO implementada** (o botão "Entrar" apenas redireciona para `/inicio/`).
- **Sem controle de permissões / perfis** (menu preparado para isso futuramente).
- **Sem models / sem cadastro de usuários próprios.**

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
│   ├── admin.py
│   ├── apps.py
│   ├── models.py             # Sem models por enquanto
│   ├── urls.py
│   ├── views.py
│   └── migrations/
│       └── __init__.py
├── templates/
│   └── core/
│       ├── login.html        # Template da tela de login
│       └── inicio.html       # Template da tela inicial interna
├── static/
│   ├── css/
│   │   ├── login.css         # Estilos da tela de login
│   │   └── inicio.css        # Estilos da tela inicial interna
│   └── img/
│       ├── logo.png                  # Logo do clube (usado na tela de login)
│       ├── logo_original_backup.png  # Backup do logo original (antes do recorte)
│       └── LEIA-ME.txt               # Instruções sobre o logo
└── docs/                     # Documentação interna (este diretório)
    ├── README_PROJETO.md
    ├── REGRAS_CODEX.md
    ├── ESTADO_ATUAL.md
    └── HISTORICO_ALTERACOES.md
```

## Apps existentes

- **config**: projeto Django (settings, urls, wsgi, asgi). Não é um app de negócio.
- **core**: app principal. Contém as views da tela de login e da tela inicial interna.

## Rotas existentes

- `/` — tela de login (view `core.views.login_view`, nome de rota `core:login`).
- `/inicio/` — tela inicial interna / área logada (view `core.views.inicio_view`, nome `core:inicio`).
- `/admin/` — Django admin padrão (habilitado por padrão, sem uso específico do projeto).

## Templates existentes

- `templates/core/login.html` — tela de login (logo, título, campos usuário/senha,
  botão "Entrar" e link "Esqueci minha senha").
- `templates/core/inicio.html` — tela inicial interna (menu lateral com "Meus Dados",
  cabeçalho de boas-vindas e cards visuais).

## Arquivos estáticos existentes

- `static/css/login.css` — estilos da tela de login (mobile first, gradiente, card, etc.).
- `static/css/inicio.css` — estilos da tela inicial interna (menu lateral, gaveta mobile, cards).
- `static/img/logo.png` — logo do clube (usado na tela de login e no menu lateral; fundo transparente).
- `static/img/logo_original_backup.png` — backup do logo original recebido.
- `static/img/LEIA-ME.txt` — instruções sobre onde colocar / nomear o logo.

JavaScript: não há arquivo `.js` separado. Existem apenas pequenos scripts inline:
em `login.html` (redireciona para `/inicio/` ao enviar, sem autenticar) e em
`inicio.html` (abre/fecha o menu recolhível no celular).

## Funcionalidades existentes

- Tela de login visual e responsiva na rota `/`.
- Exibição do logo no topo, com fallback visual ("CA") caso a imagem não carregue.
- Formulário com campos "Usuário" e "Senha", botão "Entrar" e link "Esqueci minha senha".
- Tela inicial interna em `/inicio/` com menu lateral fixo (desktop) / gaveta (mobile),
  item "Meus Dados" ativo, cabeçalho de boas-vindas e cards visuais.
- Navegação de teste: o botão "Entrar" leva para `/inicio/` (sem autenticação real).

## Funcionalidades ainda NÃO implementadas

- Autenticação real (login/logout).
- Cadastro / banco de usuários do sistema.
- Funcionalidade do link "Esqueci minha senha" (hoje aponta para `#`).
- Página real de "Meus Dados" (visualizar/editar dados pessoais).
- Controle de permissões / perfis de usuário (menu já preparado para isso).
- Models e migrations de negócio (o app `core` não possui models).

## Observações importantes para futuros desenvolvimentos

- **Não usar** Bootstrap, Tailwind ou frameworks visuais externos (CSS é próprio).
- Manter o foco em **responsividade mobile first**.
- Preservar o padrão visual já criado (paleta azul/verde inspirada no logo).
- A `SECRET_KEY` em `config/settings.py` é de desenvolvimento; trocar em produção.
- `DEBUG = True` e `ALLOWED_HOSTS = []` são configurações de desenvolvimento.
- Ao criar models, lembrar de gerar as migrations correspondentes.
- Sempre atualizar a documentação em `docs/` após qualquer alteração
  (ver `CODEX.md` e `docs/REGRAS_CODEX.md`).
