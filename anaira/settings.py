import os
import shutil
import dj_database_url # type: ignore
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
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'cloudinary', # <- Y AGREGA ESTA TAMBIÉN

    # --- HERRAMIENTAS EXTRAS ---
    'django.contrib.humanize',  # <--- AGREGUE ESTA LÍNEA
    'widget_tweaks',            # (Si ya lo tenía)
    
    # Sus apps
    "core",
    "accounts",
    "accounting",
    "inventory",
    "sales",
    "hr",
    'imports',
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
    # 'anaira.middleware.ActiveUserMiddleware',
    'anaira.middleware.ActiveCompanyMiddleware', # <--- TU NUEVO GUARDIAN DE EMPRESA ACTIVA
]

# 5. BASE DE DATOS PRINCIPAL (PostgreSQL o SQLite)
# 🛡️ BLINDAJE EXTREMO APLICADO AQUÍ
db_url = os.environ.get('DATABASE_URL', '').strip()

if db_url:
    DATABASES = {
        'default': dj_database_url.parse(db_url, conn_max_age=600, conn_health_checks=True)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Configuración explícita para evitar errores en la default
DATABASES['default']['ATOMIC_REQUESTS'] = True


# 6. CONFIGURACIÓN
AUTH_USER_MODEL = "accounts.User"
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Guatemala'
USE_I18N = True
USE_L10N = True

USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = ','
DECIMAL_SEPARATOR = '.'
NUMBER_GROUPING = 3  # Agrupa de 3 en 3 (ej: 1,000,000)

DECIMAL_SEPARATOR_INPUT = ['.']
THOUSAND_SEPARATOR_INPUT = [',']

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

ROOT_URLCONF = 'anaira.urls'
WSGI_APPLICATION = 'anaira.wsgi.application'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_REDIRECT_URL = 'core:select_company' # Ajusta 'core' al nombre de tu app
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
                'core.context_processors.global_info',  # <--- AGREGA ESTA LÍNEA
                'accounting.context_processors.expense_notifications',
            ],
        },
    },
]

# 8. SEGURIDAD SSL Y DOMINIOS
CSRF_TRUSTED_ORIGINS = [
    'https://anaira-erp-production.up.railway.app', 
    'https://*.railway.app' 
]
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

# Configuración de Inteligencia Artificial (Google Gemini)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# ==============================================================================
# ☁️ CONFIGURACIÓN DE ARCHIVOS Y NUBE (Cloudinary y WhiteNoise)
# ==============================================================================
# IMPORTANTE: Busca correctamente la variable de entorno
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')

if CLOUDINARY_URL:
    # Si estamos en Railway (Producción), usamos Cloudinary
    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
else:
    # Si estás probando en tu computadora local, sigue guardando en carpetas
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }