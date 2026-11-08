import json
import os
import secrets
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
LOCAL_DEVELOPMENT = DEBUG and os.environ.get("LOCAL_DEVELOPMENT", "1") == "1"
if LOCAL_DEVELOPMENT:
    local = BASE_DIR / ".local"
    local.mkdir(mode=0o700, exist_ok=True)
    keyfile = local / "keys.json"
    if not keyfile.exists():
        from cryptography.fernet import Fernet

        with keyfile.open("x", encoding="utf-8") as f:
            json.dump(
                {
                    "django": secrets.token_urlsafe(64),
                    "encryption": Fernet.generate_key().decode(),
                },
                f,
            )
        keyfile.chmod(0o600)
        if os.name == "nt":
            import subprocess

            identity = f"{os.environ.get('USERDOMAIN', '')}\\{os.environ['USERNAME']}"
            subprocess.run(
                [
                    "icacls",
                    str(local),
                    "/inheritance:r",
                    "/grant:r",
                    identity + ":(OI)(CI)F",
                    "SYSTEM:(OI)(CI)F",
                ],
                check=True,
                capture_output=True,
            )
    keys = json.loads(keyfile.read_text(encoding="utf-8"))
    SECRET_KEY = keys["django"]
    ENCRYPTION_KEY = keys["encryption"]
else:
    SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")
    if not SECRET_KEY or not ENCRYPTION_KEY:
        raise ImproperlyConfigured("Задайте DJANGO_SECRET_KEY и ENCRYPTION_KEY.")
ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver"
).split(",")
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "core.apps.CoreConfig",
    "catalog.apps.CatalogConfig",
    "integrations.apps.IntegrationsConfig",
    "orders.apps.OrdersConfig",
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
                "core.context_processors.admin_mode",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {"timeout": 30},
    }
}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
PRIVATE_IMPORT_ROOT = BASE_DIR / ".local" / "imports"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS", "http://localhost:5177,http://127.0.0.1:5177"
).split(",")
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "240/min",
        "checkout": "15/min",
        "payment": "30/min",
    },
}
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
