import os
import dj_database_url
from pathlib import Path

# 1. RUTAS BÁSICAS
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. SEGURIDAD
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-insecure-secret-key-change-me')
DEBUG = True
ALLOWED_HOSTS = ['*']

# 3. APLICACIONES
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
    # 'core.middleware.CompanyRoutingMiddleware', # Router desactivado por seguridad
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# 5. CONFIGURACIÓN DE BASE DE DATOS LIMPIA
# Primero borramos cualquier rastro anterior
DATABASES = {}

if 'DATABASE_URL' in os.environ:
    # Producción (Railway)
    DATABASES['default'] = dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
else:
    # Local
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }

# 6. ROUTER (Vacío para evitar desvíos)
DATABASE_ROUTERS = []

# 7. OTRAS CONFIGURACIONES
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
STATICFILES_DIRS = [BASE_DIR / 'static']
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

# Seguridad SSL
CSRF_TRUSTED_ORIGINS = ['https://anaira-erp.up.railway.app']
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# ==============================================================================
# 🛑 EL VACUNADOR: SOLUCIÓN FINAL AL KEYERROR
# ==============================================================================
# Este bloque revisa CADA base de datos que Django haya detectado (incluso las fantasmas
# como company_1) y les inyecta la llave 'ATOMIC_REQUESTS' a la fuerza.
# ==============================================================================
if 'DATABASES' in locals():
    for db_name in DATABASES:
        DATABASES[db_name]['ATOMIC_REQUESTS'] = True
# ==============================================================================