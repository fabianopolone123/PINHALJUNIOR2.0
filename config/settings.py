"""
Configurações do projeto Django.

Clube de Aventureiros Pinhal Júnior
"""

import os
from pathlib import Path

# Diretório base do projeto (a pasta que contém o manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent

# ATENÇÃO: mantenha a chave secreta em segredo em produção!
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-troque-esta-chave-em-producao",
)

# ATENÇÃO: não deixe DEBUG=True em produção!
# Se DJANGO_DEBUG for definido, ele manda. Se NÃO for definido, o padrão é seguro:
# liga DEBUG só quando não há ALLOWED_HOSTS configurado (= desenvolvimento local).
# Em produção (ALLOWED_HOSTS setado) fica DEBUG=False mesmo que esqueçam a variável.
_debug_env = os.environ.get("DJANGO_DEBUG")
if _debug_env is None:
    DEBUG = not os.environ.get("DJANGO_ALLOWED_HOSTS", "").strip()
else:
    DEBUG = _debug_env.lower() in {"1", "true", "yes", "on"}

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# O sistema roda no MESMO domínio do sistema antigo (sob /sistema-novo/ no VPS).
# Se os dois apps Django usarem o mesmo nome de cookie ("sessionid"/"csrftoken"),
# um sobrescreve o cookie do outro no navegador e derruba o login ("deslogou
# sozinho"). Nomes de cookie DISTINTOS isolam os dois apps.
SESSION_COOKIE_NAME = os.environ.get(
    "DJANGO_SESSION_COOKIE_NAME", "pinhaljunior2_sessionid"
)
CSRF_COOKIE_NAME = os.environ.get(
    "DJANGO_CSRF_COOKIE_NAME", "pinhaljunior2_csrftoken"
)


# Aplicações instaladas
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.TrocaSenhaObrigatoriaMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
                "core.context_processors.perfis",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Autenticação: para onde redirecionar em login/logout.
LOGIN_URL = "core:login"            # @login_required manda para cá quando não autenticado
LOGIN_REDIRECT_URL = "core:inicio"  # destino padrão após o login
LOGOUT_REDIRECT_URL = "core:login"  # destino após o logout


# Banco de dados (padrão SQLite)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DJANGO_SQLITE_PATH", BASE_DIR / "db.sqlite3"),
    }
}


# Validação de senha
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internacionalização
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True


# Arquivos estáticos (CSS, JavaScript, Imagens)
FORCE_SCRIPT_NAME = os.environ.get("DJANGO_FORCE_SCRIPT_NAME") or None
_url_prefix = FORCE_SCRIPT_NAME.rstrip("/") if FORCE_SCRIPT_NAME else ""

STATIC_URL = os.environ.get("DJANGO_STATIC_URL", f"{_url_prefix}/static/")
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = os.environ.get("DJANGO_STATIC_ROOT", BASE_DIR / "staticfiles")

# Cache-busting dos estáticos em produção: o ManifestStaticFilesStorage renomeia
# cada arquivo com um hash do conteúdo (ex.: mensalidades.abc123.js), então o
# navegador SEMPRE baixa a versão nova a cada deploy (sem ficar preso a JS/CSS
# antigo em cache). Em desenvolvimento (DEBUG) fica o storage simples, para não
# depender de `collectstatic`.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "core.storages.CacheBustingStaticFilesStorage"
        ),
    },
}

# Arquivos de mídia (uploads dos usuários, ex.: foto 3x4 do aventureiro)
MEDIA_URL = os.environ.get("DJANGO_MEDIA_URL", f"{_url_prefix}/media/")
MEDIA_ROOT = os.environ.get("DJANGO_MEDIA_ROOT", BASE_DIR / "media")

# Tipo de chave primária padrão
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
