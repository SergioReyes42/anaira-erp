import os
import dj_database_url
from pathlib import Path
from django.utils.translation import gettext_lazy as _

# 1. RUTAS BÁSICAS
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. SEGURIDAD
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-insecure-secret-key-change-me')
DEBUG = True
ALLOWED_HOSTS = ['*'] 

# 3. CONFIGURACIÓN DE BASE DE DATOS (INTELIGENTE)
# Esta configuración detecta si está en Railway o en su PC
if 'DATABASE_URL' in os.environ:
    # --- MODO PRODUCCIÓN (RAILWAY) ---
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
    # ESTO SOLUCIONA EL ERROR KeyError: 'ATOMIC_REQUESTS'
    DATABASES['default']['ATOMIC_REQUESTS'] = True
    
else:
    # --- MODO LOCAL (PC) ---
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'ATOMIC_REQUESTS': True, 
        }
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
    'hr',
    
    # Terceros
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",
    "corsheaders",
]

# 5. MIDDLEWARE
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.CompanyRoutingMiddleware',
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

# 12. SEGURIDAD Y DOMINIOS (SOLUCIÓN LOGIN PARPADEANTE)

# Lista de dominios permitidos
CSRF_TRUSTED_ORIGINS = [
    'https://anaira-erp.up.railway.app',
    'https://refreshful-asthmatically-mackenzie.ngrok-free.dev',
]

# Configuración SSL para Railway
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# IMPORTANTE: Dejamos esto en False para GARANTIZAR que pueda entrar hoy.
# (Más adelante, cuando todo funcione perfecto, podemos pasarlo a True)
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False