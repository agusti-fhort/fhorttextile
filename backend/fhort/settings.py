"""
Django settings for fhort project.

Multitenant SaaS PLM (django-tenants, schema-per-tenant).
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


SECRET_KEY = os.environ['SECRET_KEY']

DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# ALLOWED_HOSTS es llegeix del .env i sempre inclou els hosts de producció
# com a fallback per evitar 400 si el .env queda mal configurat.
_env_hosts = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', '').split(',') if h.strip()]
_prod_hosts = ['fhorttextile.tech', '.fhorttextile.tech', '178.105.217.125']
ALLOWED_HOSTS = list(dict.fromkeys(_env_hosts + _prod_hosts))

# CSRF: confiem origens HTTPS del domini propi i subdominis de tenant.
CSRF_TRUSTED_ORIGINS = [
    'https://fhorttextile.tech',
    'https://*.fhorttextile.tech',
]


# Apps compartides (esquema 'public'): tot el que és cross-tenant.
SHARED_APPS = [
    'django_tenants',
    'fhort.tenants',

    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',

    # Third-party (sense models propis o amb models opcionals no usats).
    'corsheaders',
    'rest_framework',
    'django_filters',
    'drf_spectacular',

    # 'pom' viu en SHARED i TENANT: els models *Global viuen a 'public'
    # i la resta es repliquen a cada tenant per a FKs cross-schema.
    'fhort.pom',

    # Backoffice: capa de control de negoci. NOMÉS public (mai a TENANT_APPS).
    'fhort.backoffice',
]

# Apps per-tenant: viuen dins de l'esquema de cada client.
TENANT_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',

    'fhort.accounts',
    'fhort.models_app',
    'fhort.pom',
    'fhort.fitting',
    'fhort.tasks',
    'fhort.files',
    'fhort.planning',
]

INSTALLED_APPS = list(SHARED_APPS) + [a for a in TENANT_APPS if a not in SHARED_APPS]

TENANT_MODEL = 'tenants.Client'
TENANT_DOMAIN_MODEL = 'tenants.Domain'


MIDDLEWARE = [
    # CORS ha d'anar abans del tenant middleware perquè les preflight OPTIONS
    # des de frontends en domini diferent no es bloquegin per host no resolt.
    'corsheaders.middleware.CorsMiddleware',
    'django_tenants.middleware.main.TenantMainMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'fhort.urls'
PUBLIC_SCHEMA_URLCONF = 'fhort.urls_public'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'fhort.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

DATABASE_ROUTERS = ['django_tenants.routers.TenantSyncRouter']


# Anthropic Claude API — usat per extraction_service.py (sprint 6)
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'ca'
TIME_ZONE = 'Europe/Madrid'
USE_I18N = True
USE_TZ = True


STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ─────────────────────────────────────────────────────────────
# Django REST Framework
# ─────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'fhort.pagination.DefaultPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# ─────────────────────────────────────────────────────────────
# SimpleJWT
# ─────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'UPDATE_LAST_LOGIN': True,
}

# ─────────────────────────────────────────────────────────────
# drf-spectacular (OpenAPI)
# ─────────────────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    'TITLE': 'FHORT Textile Tech API',
    'DESCRIPTION': 'SaaS PLM tècnic per a moda — multitenant (django-tenants).',
    'VERSION': '0.1.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/',
}

# ─────────────────────────────────────────────────────────────
# CORS
# ─────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:3000',
    'https://fhorttextile.tech',
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^https://[a-z0-9-]+\.fhorttextile\.tech$',
]
CORS_ALLOW_CREDENTIALS = True
