import os
import dj_database_url
from pathlib import Path
import sys

# 1. DEFINICIONES BÁSICAS
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-zombie-killer')
DEBUG = True
ALLOWED_HOSTS = ['*']

# 2. APLICACIONES
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "accounts",
    "accounting",
    "inventory",
    "sales",
    "hr",
    "rest_framework",
    "corsheaders",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'anaira.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'anaira.wsgi.application'

# ==============================================================================
# 🛑 ZONA DE BASE DE DATOS (LA SOLUCIÓN NUCLEAR)
# ==============================================================================

# 1. Reiniciamos la variable para que no quede basura anterior
DATABASES = {}

# 2. Definimos ÚNICAMENTE la base de datos principal
if 'DATABASE_URL' in os.environ:
    # Producción (Railway)
    DATABASES['default'] = dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
else:
    # Local (SQLite)
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }

# 3. EL GUARDIÁN: Eliminamos cualquier intruso y forzamos la llave
print("--- 🛡️ INICIO DE DEPURACIÓN DE DATABASES ---")
for alias in list(DATABASES.keys()):
    # Si encontramos una base de datos que NO es 'default', la borramos del mapa
    if alias != 'default':
        print(f"👻 FANTASMA DETECTADO Y ELIMINADO: {alias}")
        del DATABASES[alias]
    else:
        # A la base de datos legal, le ponemos la vacuna
        DATABASES[alias]['ATOMIC_REQUESTS'] = True
        print(f"✅ DB '{alias}' configurada y BLINDADA con ATOMIC_REQUESTS.")

print("--- 🛡️ FIN DE DEPURACIÓN ---")
# ==============================================================================

# 4. ROUTER DESACTIVADO (Crucial para que no busque zombies)
DATABASE_ROUTERS = []

# 5. OTRAS CONFIGURACIONES
AUTH_USER_MODEL = "accounts.User"
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Guatemala'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 6. SEGURIDAD (ANTI-PARPADEO)
CSRF_TRUSTED_ORIGINS = ['https://anaira-erp.up.railway.app']
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False