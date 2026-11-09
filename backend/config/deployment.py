from .settings import *

import os
from pathlib import Path
DEBUG = False
DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': os.environ['POSTGRES_DB'], 'USER': os.environ['POSTGRES_USER'], 'PASSWORD': os.environ['POSTGRES_PASSWORD'], 'HOST': 'db', 'PORT': '5432', 'CONN_MAX_AGE': 60}}
STATIC_ROOT = Path('/data/static')
STATIC_URL = '/static/'
MEDIA_ROOT = Path('/data/media')
MEDIA_URL = '/media/'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS = ['http://' + os.environ['SITE_DOMAIN'], 'https://' + os.environ['SITE_DOMAIN']]
HTTPS_ENABLED = os.environ.get('HTTPS_ENABLED') == '1'
SECURE_SSL_REDIRECT = HTTPS_ENABLED
SESSION_COOKIE_SECURE = HTTPS_ENABLED
CSRF_COOKIE_SECURE = HTTPS_ENABLED
SECURE_HSTS_SECONDS = 0

PUBLIC_DEMO = True
EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"
MIDDLEWARE.insert(1, "config.demo_middleware.PublicDemoInputMiddleware")
LOCAL_DEVELOPMENT = True  # Provider simulation only; secrets were already loaded from env.
