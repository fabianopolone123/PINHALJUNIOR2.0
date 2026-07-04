"""
Configurações do projeto Django.

Clube de Aventureiros Pinhal Júnior
"""

from pathlib import Path

# Diretório base do projeto (a pasta que contém o manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent

# ATENÇÃO: mantenha a chave secreta em segredo em produção!
SECRET_KEY = "django-insecure-troque-esta-chave-em-producao"

# ATENÇÃO: não deixe DEBUG=True em produção!
DEBUG = True

ALLOWED_HOSTS = []


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
        "NAME": BASE_DIR / "db.sqlite3",
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
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Arquivos de mídia (uploads dos usuários, ex.: foto 3x4 do aventureiro)
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Tipo de chave primária padrão
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
