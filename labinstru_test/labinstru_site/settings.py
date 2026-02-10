from pathlib import Path
import os

# dotenv (não quebra produção se não existir)
try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

# =======================================================
# Caminhos básicos
# =======================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega .env local (opcional). No Render você usa Environment Variables.
if load_dotenv:
    load_dotenv(BASE_DIR / ".env")

# =======================================================
# Segurança / Debug
# =======================================================
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-please-change")

# No Render, defina DEBUG=False em Environment
DEBUG = os.getenv("DEBUG", "False") == "True"

# Render / Produção
ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    ".onrender.com",  # aceita qualquer subdomínio do Render
    "labinstru2026-10.onrender.com",  # opcional (pode deixar)
]

# Recomendado para HTTPS atrás de proxy (Render/Cloudflare)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# =======================================================
# Aplicativos
# =======================================================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "siteapp",
]

# =======================================================
# Middleware (ordem correta + sem duplicar)
# =======================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Evita loops em rotas técnicas /embed/, /api/, etc.
LANGUAGE_IGNORE_PATHS = [
    r"^embed/",
    r"^api/",
    r"^media/",
]

ROOT_URLCONF = "labinstru_site.urls"

# =======================================================
# Templates
# =======================================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "siteapp" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "labinstru_site.wsgi.application"

# =======================================================
# Banco de Dados (SQLite ok para teste; em produção use Postgres)
# =======================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# =======================================================
# Idiomas e Localização
# =======================================================
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Manaus"
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ("pt", "Português"),
    ("en", "English"),
    ("es", "Español"),
]

LANGUAGE_COOKIE_NAME = "django_language"
LANGUAGE_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 dias
LOCALE_PATHS = [BASE_DIR / "locale"]

# =======================================================
# Arquivos Estáticos e de Mídia
# =======================================================
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise (boa prática)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =======================================================
# Configurações do ZEUS / IA / APIs
# =======================================================
PURPLEAIR_API_KEY = os.getenv("PURPLEAIR_API_KEY", "")

CSE_API_KEY = os.getenv("CSE_API_KEY", "")
CSE_CX = os.getenv("CSE_CX", "")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

ZEUS_MAX_WEB_SOURCES = int(os.getenv("ZEUS_MAX_WEB_SOURCES", "3"))

ZEUS_LOCAL_SOURCES = [
    {
        "title": "LabInstru — Resumo (PDF)",
        "type": "pdf",
        "path": BASE_DIR / "media" / "LabInstru-resumo.pdf",
    }
]

# =======================================================
# Outros padrões Django
# =======================================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
