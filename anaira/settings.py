import os
import shutil
import dj_database_url
from pathlib import Path

# 1. DIRECTORIO BASE Y LIMPIEZA
BASE_DIR = Path(__file__).resolve().parent.parent

# Limpieza preventiva de carpetas viejas
zombie_path = BASE_DIR / 'tenants'
if zombie_path.exists():
    try:
        shutil.rmtree(zombie_path)
    except:
        pass

# 2. SEGURIDAD
SECRET_KEY = os.environ.get('SECRET_KEY', 'hack-patch-key-ultimate-v3')
DEBUG = True
ALLOWED_HOSTS = ['*']

# 3. APPS
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core.apps.CoreConfig",
    "accounts.apps.AccountsConfig",
    "accounting.apps.AccountingConfig",
    "inventory.apps.InventoryConfig",
    "sales.apps.SalesConfig",
    'hr',
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",
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

# 5. BASE DE DATOS
DATABASES = {}

if 'DATABASE_URL' in os.environ:
    DATABASES['default'] = dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
else:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }

# Configuración inicial segura para default
DATABASES['default']['ATOMIC_REQUESTS'] = True
DATABASES['default']['CONN_HEALTH_CHECKS'] = False

# 6. ROUTER (OFF)
DATABASE_ROUTERS = []

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

# 8. GENERALES
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/select-company/'
LOGOUT_REDIRECT_URL = '/login/'

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
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
}

# 9. SEGURIDAD
CSRF_TRUSTED_ORIGINS = ['https://anaira-erp.up.railway.app']
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# ==============================================================================
# 💉 EL PARCHE MAESTRO v3.0 (COBERTURA TOTAL)
# ==============================================================================
import django.core.handlers.base
from django.conf import settings as django_settings

original_make_view_atomic = django.core.handlers.base.BaseHandler.make_view_atomic

def patched_make_view_atomic(self, view):
    if hasattr(django_settings, 'DATABASES'):
        for db_name, db_config in django_settings.DATABASES.items():
            # Inyectamos TODAS las llaves que Django 6.0 pueda pedir
            # para evitar KeyErrors en cadena.
            
            defaults = {
                'ATOMIC_REQUESTS': True,
                'TIME_ZONE': 'America/Guatemala',
                'CONN_HEALTH_CHECKS': False,  # <--- ¡AQUÍ ESTÁ LA QUE FALTABA!
                'CONN_MAX_AGE': 0,
                'AUTOCOMMIT': True,
                'OPTIONS': {},
                'TEST': {},
                'ENGINE': 'django.db.backends.sqlite3' # Fallback por si falta engine
            }

            for key, value in defaults.items():
                if key not in db_config:
                    db_config[key] = value

    return original_make_view_atomic(self, view)

# Aplicamos el parche
django.core.handlers.base.BaseHandler.make_view_atomic = patched_make_view_atomic
# ==============================================================================