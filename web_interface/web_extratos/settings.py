"""
Django settings for web_extratos project.
"""
import os
from pathlib import Path
from decouple import Config, RepositoryEnv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file from parent directory (project root)
ENV_FILE = BASE_DIR.parent / '.env'

# Configure decouple to use the specific .env file
if ENV_FILE.exists():
    config = Config(RepositoryEnv(str(ENV_FILE)))
else:
    from decouple import config

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-your-secret-key-here')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

# Hosts permitidos
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '.render.com',
    os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')
]

# Remover hosts vazios
ALLOWED_HOSTS = [host for host in ALLOWED_HOSTS if host]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'extratos_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'extratos_app.middleware.cleanup_middleware.PeriodicFileCleanupMiddleware',
]

ROOT_URLCONF = 'web_extratos.urls'

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

WSGI_APPLICATION = 'web_extratos.wsgi.application'

# Database
if os.environ.get('DATABASE_URL'):
    # Produção (Render) - PostgreSQL
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(os.environ.get('DATABASE_URL'))
    }
else:
    # Desenvolvimento - SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configurações de segurança básicas
SECURE_CONTENT_TYPE_NOSNIFF = config('SECURE_CONTENT_TYPE_NOSNIFF', default=True, cast=bool)
SECURE_BROWSER_XSS_FILTER = config('SECURE_BROWSER_XSS_FILTER', default=True, cast=bool)
SECURE_REFERRER_POLICY = config('SECURE_REFERRER_POLICY', default='strict-origin-when-cross-origin')

# Configurações de cookies (padrões para PRODUÇÃO)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
SESSION_COOKIE_HTTPONLY = config('SESSION_COOKIE_HTTPONLY', default=True, cast=bool)
SESSION_COOKIE_SAMESITE = config('SESSION_COOKIE_SAMESITE', default='Strict')
SESSION_COOKIE_AGE = 3600  # 1 hora

CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=True, cast=bool)
CSRF_COOKIE_HTTPONLY = config('CSRF_COOKIE_HTTPONLY', default=True, cast=bool)
CSRF_COOKIE_SAMESITE = config('CSRF_COOKIE_SAMESITE', default='Strict')

# X-Frame-Options
X_FRAME_OPTIONS = config('X_FRAME_OPTIONS', default='DENY')

# Configurações de sessão
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Configurações de upload
FILE_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024  # 25MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024  # 25MB
MAX_UPLOAD_SIZE = 25 * 1024 * 1024  # 25MB

# Configurações de logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'extratos_app': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Configurações específicas da aplicação
BACKUP_ENABLED = False
BACKUP_INTERVAL = 86400  # 24 horas
BACKUP_RETENTION_DAYS = 7

# Configurações de auditoria
AUDIT_LOG_ENABLED = True
AUDIT_LOG_FILE = os.path.join(BASE_DIR, 'logs', 'audit.log')

# Criar diretório de logs se não existir
os.makedirs(os.path.dirname(AUDIT_LOG_FILE), exist_ok=True)
