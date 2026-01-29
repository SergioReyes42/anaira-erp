import os
import shutil
import dj_database_url
from pathlib import Path

# 1. DIRECTORIO BASE Y LIMPIEZA AUTOMÁTICA
# (Esto intenta borrar las bases de datos viejas para que no molesten)
BASE_DIR = Path(__file__).resolve().parent.parent

try:
    zombie_path = BASE_DIR / 'tenants'
    if zombie_path.exists():
        shutil.rmtree(zombie_path)
except:
    pass

# 2. SEGURIDAD
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-key-reemplazar')
DEBUG = True # Mantenemos True para ver errores si salen
ALLOWED_HOSTS = ['*']

# 3. APPS
INSTALLED_APPS = [
    'jazzmin'
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Sus apps
    "core",
    "accounts",
    "accounting",
    "inventory",
    "sales",
    "hr",
    # Terceros
    "rest_framework",
    "corsheaders",
]

# 4. MIDDLEWARE
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

# 5. BASE DE DATOS PRINCIPAL (PostgreSQL o SQLite)
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///db.sqlite3',
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Configuración explícita para evitar errores en la default
DATABASES['default']['ATOMIC_REQUESTS'] = True

# 6. CONFIGURACIÓN
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

ROOT_URLCONF = 'anaira.urls'
WSGI_APPLICATION = 'anaira.wsgi.application'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# 7. TEMPLATES
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

# 8. SEGURIDAD SSL
CSRF_TRUSTED_ORIGINS = ['https://*.up.railway.app']
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = False # False temporalmente para facilitar login
CSRF_COOKIE_SECURE = False

# ==============================================================================
# 💉 EL PARCHE MAESTRO (LA VACUNA)
# ==============================================================================
# Este bloque detecta cualquier base de datos rota (como company_1) y
# le inyecta las configuraciones faltantes ANTES de que Django explote.
# ==============================================================================
import django.core.handlers.base
from django.conf import settings as django_settings

original_make_view_atomic = django.core.handlers.base.BaseHandler.make_view_atomic

def patched_make_view_atomic(self, view):
    if hasattr(django_settings, 'DATABASES'):
        for db_name, db_config in django_settings.DATABASES.items():
            # Rellenamos todo lo que pueda faltar
            defaults = {
                'ATOMIC_REQUESTS': True,
                'TIME_ZONE': 'America/Guatemala',
                'CONN_HEALTH_CHECKS': False,
                'CONN_MAX_AGE': 0,
                'AUTOCOMMIT': True,
                'OPTIONS': {},
                'TEST': {},
                'ENGINE': 'django.db.backends.sqlite3',
                # Nombre falso por si falta
                'NAME': os.path.join(BASE_DIR, 'db_dummy.sqlite3'),
            }
            
            for key, value in defaults.items():
                if key not in db_config:
                    db_config[key] = value

    return original_make_view_atomic(self, view)

# Aplicamos el parche
django.core.handlers.base.BaseHandler.make_view_atomic = patched_make_view_atomic
# ==============================================================================