"""Configurações do **serviço do leilão** (`/leilao/`).

Herda tudo do `settings.py` do clube e troca o que precisa ser diferente. São
duas aplicações Django na mesma base de código, rodando como **dois serviços**:

    pinhaljunior.com.br/sistema-novo/  → gunicorn síncrono   → db.sqlite3
    pinhaljunior.com.br/leilao/        → uvicorn (1 worker)  → leilao.sqlite3

Por que separado (resumo; o inteiro está em `docs/PLANEJAMENTO_LEILAO.md`):

- O leilão usa **SSE**, que segura a conexão aberta. Num worker **síncrono**,
  cada participante prenderia um worker inteiro e derrubaria o site do clube.
- **Um worker só, de propósito**: o hub de eventos vive na memória do processo
  (sem Redis), há **um escritor só** no SQLite e o cronômetro roda num laço
  `asyncio` único (sem cron).
- Banco próprio: 50 pessoas martelando lance não encostam no banco que roda
  mensalidades, eventos e loja.

Uso:

    DJANGO_SETTINGS_MODULE=config.settings_leilao python manage.py migrate
    uvicorn config.asgi_leilao:application --port 8011
"""

import os

from .settings import *  # noqa: F401,F403  (herda o do clube e sobrescreve abaixo)
from .settings import BASE_DIR

# ---------------------------------------------------------------------------
# Apps e middleware
# ---------------------------------------------------------------------------
# O app `core` fica **de fora**: o leilão não importa model do clube. O que ele
# reaproveita é `core/mercadopago.py`, que é biblioteca pura (só `urllib`) e
# recebe o objeto de configuração de quem chama — funciona sem o app instalado.
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "leilao",
]

# Sem o middleware de troca de senha obrigatória (é do fluxo de operadores do clube).
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls_leilao"
ASGI_APPLICATION = "config.asgi_leilao.application"
WSGI_APPLICATION = None  # este serviço é ASGI; não existe modo WSGI para ele.

# O context processor `perfis` é do `core` (menu/permissões do clube) — não existe aqui.
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "leilao.context_processors.leilao_base",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Banco (próprio)
# ---------------------------------------------------------------------------
# WAL é o que permite ler enquanto se escreve — num leilão, todo mundo lê o
# tempo todo e o lance escreve no meio. `busy_timeout` evita "database is
# locked" em pico. `synchronous=NORMAL` troca um fsync por lance por
# desempenho; o risco é perder o último lance num corte de energia do servidor,
# o que é aceitável aqui (e o WAL continua garantindo banco íntegro).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DJANGO_LEILAO_SQLITE_PATH", BASE_DIR / "leilao.sqlite3"),
        "OPTIONS": {
            "init_command": (
                "PRAGMA journal_mode=WAL;"
                "PRAGMA synchronous=NORMAL;"
                "PRAGMA busy_timeout=5000;"
            ),
            # ISTO NÃO É DETALHE — é o que impede "database is locked" no meio do
            # pregão. Com o `BEGIN DEFERRED` padrão, uma transação que LÊ e depois
            # ESCREVE (todo lance é assim) recebe SQLITE_BUSY na hora, **sem**
            # respeitar o `busy_timeout`: o SQLite recusa em vez de arriscar um
            # impasse com quem já está escrevendo. Com `IMMEDIATE`, a trava de
            # escrita é pedida no começo da transação, então as conexões
            # **esperam a vez** (até os 5 s acima) em vez de falhar.
            #
            # Faz falta porque um worker só ainda atende várias requisições em
            # THREADS (as views síncronas rodam num pool), e cada thread tem a
            # sua conexão. "Um escritor só" vale para processos, não para threads.
            "transaction_mode": "IMMEDIATE",
        },
        # Banco de teste em ARQUIVO, não em memória. O padrão do Django para
        # SQLite é `:memory:` com *shared cache*, e lá o `busy_timeout` não vale:
        # duas threads escrevendo dão `database table is locked` na hora. Como o
        # teste mais importante deste módulo é justamente o de **lances
        # simultâneos**, o banco de teste precisa se comportar como o de
        # produção — arquivo com WAL. O arquivo é descartado ao fim da suíte.
        "TEST": {"NAME": BASE_DIR / "test_leilao.sqlite3"},
    }
}

# ---------------------------------------------------------------------------
# Cookies: nomes PRÓPRIOS
# ---------------------------------------------------------------------------
# Mesmo domínio do sistema do clube. Repetir o nome do cookie faz um app
# derrubar a sessão do outro no navegador ("deslogou sozinho") — armadilha que o
# settings do clube já documenta e que aqui vale igual.
SESSION_COOKIE_NAME = os.environ.get("DJANGO_LEILAO_SESSION_COOKIE", "leilao_sessionid")
CSRF_COOKIE_NAME = os.environ.get("DJANGO_LEILAO_CSRF_COOKIE", "leilao_csrftoken")

# O participante entra por um link e volta depois; sessão curta o expulsaria no
# meio do pregão. 30 dias, renovando a cada visita.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
SESSION_SAVE_EVERY_REQUEST = False

# ---------------------------------------------------------------------------
# URLs, estáticos e mídia
# ---------------------------------------------------------------------------
FORCE_SCRIPT_NAME = os.environ.get("DJANGO_LEILAO_SCRIPT_NAME") or None
_prefixo = FORCE_SCRIPT_NAME.rstrip("/") if FORCE_SCRIPT_NAME else ""

STATIC_URL = os.environ.get("DJANGO_LEILAO_STATIC_URL", f"{_prefixo}/static/")
STATIC_ROOT = os.environ.get("DJANGO_LEILAO_STATIC_ROOT", BASE_DIR / "staticfiles_leilao")
STATICFILES_DIRS = [BASE_DIR / "static"]

# Mídia própria: as fotos dos lotes não se misturam com as do clube (que têm
# foto de criança e nunca podem ser servidas por outro caminho).
MEDIA_URL = os.environ.get("DJANGO_LEILAO_MEDIA_URL", f"{_prefixo}/media/")
MEDIA_ROOT = os.environ.get("DJANGO_LEILAO_MEDIA_ROOT", BASE_DIR / "media_leilao")

# ---------------------------------------------------------------------------
# Autenticação (só o locutor/administração do leilão)
# ---------------------------------------------------------------------------
LOGIN_URL = "leilao:entrar_equipe"
LOGIN_REDIRECT_URL = "leilao:equipe"
LOGOUT_REDIRECT_URL = "leilao:entrar_equipe"

# ---------------------------------------------------------------------------
# Ajustes do próprio leilão
# ---------------------------------------------------------------------------
# Teto de conexões SSE simultâneas. Não é capacidade do servidor — é um freio
# de segurança para um script não abrir mil conexões e derrubar o pregão.
LEILAO_MAX_CONEXOES = int(os.environ.get("DJANGO_LEILAO_MAX_CONEXOES", "300"))

# De quanto em quanto tempo o laço central confere cronômetro e prazo de pagamento.
LEILAO_TICK_SEGUNDOS = float(os.environ.get("DJANGO_LEILAO_TICK", "1"))

# Batimento do SSE: sem tráfego, o Nginx fecha a conexão ociosa.
LEILAO_PING_SEGUNDOS = int(os.environ.get("DJANGO_LEILAO_PING", "15"))
