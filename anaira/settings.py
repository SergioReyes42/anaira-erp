import os
import shutil  # Para borrar carpetas
import sys
import dj_database_url
from pathlib import Path

# 1. DIRECTORIO BASE
BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================================================================
# 🧹 FASE 1: EL EXORCISMO (ELIMINAR ARCHIVOS ZOMBIES)
# ==============================================================================
# Buscamos la carpeta 'tenants' que está causando el problema y la borramos.
zombie_path = BASE_DIR / 'tenants'
if zombie_path.exists():
    try:
        shutil.rmtree(zombie_path)
        print("💥 ZOMBIE ELIMINADO: Carpeta /tenants/ borrada correctamente.")
    except Exception as e:
        print(f"⚠️ No se pudo borrar carpeta tenants: {e}")

# También borramos cualquier sqlite suelto que no sea el principal
for db_file in BASE_DIR.glob("*.sqlite3"):
    if db_file.name != "db.sqlite3": # Respetamos solo la base local default
        try:
            os.remove(db_file)
            print(f"💥 ZOMBIE ELIMINADO: {db_file.name}")
        except:
            pass
# ==============================================================================

# 2. SEGURIDAD
SECRET_KEY = os.environ.get('SECRET_KEY', 'llave-maestra-anti-zombies')
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

# 4. MIDDLEWARE (SIN ROUTERS)
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

# 5. BASE DE DATOS (CONFIGURACIÓN ESTRICTA)
DATABASES = {}

if 'DATABASE_URL' in os.environ:
    # Railway (PostgreSQL)
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

# ==============================================================================
# 🛡️ FASE 2: EL BLINDAJE (PURGA DE MEMORIA)
# ==============================================================================
# Aquí revisamos si algún código "travieso" metió bases de datos extras (como company_1)
# y las borramos de la memoria a la fuerza.

# 1. Obtenemos las llaves actuales (ej: 'default', 'company_1')
db_keys = list(DATABASES.keys())

# 2. Recorremos y eliminamos a los intrusos
for alias in db_keys:
    if alias != 'default':
        del DATABASES[alias] # ¡Adiós company_1!
        print(f"🚫 Base de datos intrusa '{alias}' eliminada de la configuración.")

# 3. A la única sobreviviente (default), le ponemos la vacuna ATOMIC
DATABASES['default']['ATOMIC_REQUESTS'] = True

# Aseguramos el motor (parche extra)
if not DATABASES['default'].get('ENGINE'):
    DATABASES['default']['ENGINE'] = 'django.db.backends.sqlite3'
# ==============================================================================

# 6. ROUTER (APAGADO)
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

# 8. VARIOS
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

# 9. SEGURIDAD HTTPS RELAJADA
CSRF_TRUSTED_ORIGINS = ['https://anaira-erp.up.railway.app']
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False