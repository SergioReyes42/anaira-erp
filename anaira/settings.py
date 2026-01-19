import os
import dj_database_url # <--- AGREGUE ESTO
import glob
from pathlib import Path
from datetime import timedelta
from django.utils.translation import gettext_lazy as _

# 1. RUTAS BÁSICAS
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. SEGURIDAD
SECRET_KEY = 'dev-insecure-secret-key-change-me'
DEBUG = True

# Permitir acceso desde cualquier lugar (PC, Celular, Ngrok)
ALLOWED_HOSTS = ['*'] 

CSRF_TRUSTED_ORIGINS = [
    'https://refreshful-asthmatically-mackenzie.ngrok-free.dev',
]

# 3. CONFIGURACIÓN DE BASES DE DATOS (ARQUITECTURA MULTI-TENANT)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        # AQUÍ APUNTAMOS A LA "RECEPCIÓN" (Donde viven los usuarios y lista de empresas)
        'NAME': BASE_DIR / 'db_main.sqlite3',
    }
}

# Auto-detección de bases de datos de empresas (db_empresa_X.sqlite3)
db_files = glob.glob(os.path.join(BASE_DIR, "db_empresa_*.sqlite3"))
for db_file in db_files:
    # Extraemos el nombre (ej: empresa_1)
    db_id = os.path.basename(db_file).replace('db_', '').replace('.sqlite3', '')
    
    DATABASES[db_id] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': Path(db_file),
        'TIME_ZONE': 'America/Guatemala',
        'ATOMIC_REQUESTS': False,
        'AUTOCOMMIT': True,
        'CONN_MAX_AGE': 0,
        
        'ATOMIC_REQUESTS': True,  # <--- ESTA LÍNEA ES LA CLAVE (No la borres)

    }

# 4. APLICACIONES
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    # Apps del ERP
    "core.apps.CoreConfig",
    "accounts.apps.AccountsConfig",
    "accounting.apps.AccountingConfig",
    "inventory.apps.InventoryConfig",
    "sales.apps.SalesConfig",
    'hr',  # <--- AGREGAR ESTA LÍNEA
    
    # Terceros
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",
    "corsheaders",
]

# 5. MIDDLEWARE
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # <--- AGREGUE ESTA LÍNEA EXACTA
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware', # Agregado para evitar bloqueos
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.CompanyRoutingMiddleware', # TU SELECTOR DE EMPRESA
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# 6. ROUTER DE BASE DE DATOS
DATABASE_ROUTERS = ['anaira.router.CompanyRouter']

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

# 8. CONFIGURACIÓN DE LOGIN
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/select-company/'
LOGOUT_REDIRECT_URL = '/login/'

# 9. INTERNACIONALIZACIÓN
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Guatemala'
USE_I18N = True
USE_TZ = True

# 10. ARCHIVOS ESTÁTICOS Y MEDIA
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 11. OTRAS CONFIGURACIONES
ROOT_URLCONF = 'anaira.urls'
WSGI_APPLICATION = 'anaira.wsgi.application'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# API REST
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# CONFIGURACIÓN DE ARCHIVOS MULTIMEDIA (LOGOS, EVIDENCIAS)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

CSRF_TRUSTED_ORIGINS = [
    'https://anaira-erp.up.railway.app'
]
# --- AGREGAR AL FINAL DE SETTINGS.PY ---

# Configuración vital para que el Login funcione en Railway (HTTPS)
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')