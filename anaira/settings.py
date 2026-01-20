import os
import shutil
import dj_database_url
from pathlib import Path

# 1. DIRECTORIO BASE Y LIMPIEZA PREVENTIVA
BASE_DIR = Path(__file__).resolve().parent.parent

# Intentamos borrar basura vieja
zombie_path = BASE_DIR / 'tenants'
if zombie_path.exists():
    try:
        shutil.rmtree(zombie_path)
    except:
        pass

# 2. SEGURIDAD
SECRET_KEY = os.environ.get('SECRET_KEY', 'hack-patch-key-123')
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

# Aseguramos la llave en la default
DATABASES['default']['ATOMIC_REQUESTS'] = True

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
LOGIN_REDIRECT_URL = '/select-company/' # Importante: Redirigir aquí tras login
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

# 9. SEGURIDAD RELAJADA
CSRF_TRUSTED_ORIGINS = ['https://anaira-erp.up.railway.app']
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# ==============================================================================
# 💉 EL PARCHE MAESTRO (MONKEY PATCH) - LA SOLUCIÓN FINAL
# ==============================================================================
# "Hackeamos" la función interna de Django que causa el error.
# Le decimos: "Antes de revisar las bases de datos, asegúrate de que TODAS
# tengan la llave ATOMIC_REQUESTS, si no la tienen, pónsela tú mismo".
# ==============================================================================
import django.core.handlers.base
from django.conf import settings as django_settings

# Guardamos la función original
original_make_view_atomic = django.core.handlers.base.BaseHandler.make_view_atomic

def patched_make_view_atomic(self, view):
    # Justo antes de que Django revise, arreglamos cualquier base de datos rota
    if hasattr(django_settings, 'DATABASES'):
        for db_name, db_config in django_settings.DATABASES.items():
            if 'ATOMIC_REQUESTS' not in db_config:
                # ¡Aquí está la magia! Le inyectamos la llave faltante
                db_config['ATOMIC_REQUESTS'] = True 
    
    # Ejecutamos la función original como si nada hubiera pasado
    return original_make_view_atomic(self, view)

# Aplicamos el parche
django.core.handlers.base.BaseHandler.make_view_atomic = patched_make_view_atomic
# ==============================================================================