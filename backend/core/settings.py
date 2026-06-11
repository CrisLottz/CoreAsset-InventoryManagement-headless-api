from pathlib import Path
import os
from django.core.exceptions import ImproperlyConfigured

def get_env_variable(var_name, default=None):
    """Obtiene la variable de entorno o falla de forma ruidosa si no existe (Fail-Fast)"""
    try:
        return os.environ[var_name]
    except KeyError:
        if default is not None:
            return default
        raise ImproperlyConfigured(f"Falla de seguridad: La variable de entorno {var_name} no está definida.")

def parse_env_list(var_name, default_val):
    raw_val = os.environ.get(var_name, default_val)
    return [item.strip() for item in raw_val.split(',') if item.strip()]

BASE_DIR = Path(__file__).resolve().parent.parent

# SEGURIDAD CORE
SECRET_KEY = get_env_variable('SECRET_KEY')
DEBUG = get_env_variable('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = parse_env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'corsheaders',
    'users',
    'rbac',
    'audit',
    'assets',
    'employees'
]

AUTH_USER_MODEL = 'users.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'audit.middleware.AuditMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# BASE DE DATOS BLINDADA
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': get_env_variable('POSTGRES_DB', 'coreasset'),
        'USER': get_env_variable('POSTGRES_USER', 'postgres'),
        'PASSWORD': get_env_variable('POSTGRES_PASSWORD', 'postgres'),
        'HOST': get_env_variable('POSTGRES_HOST', 'db'),
        'PORT': get_env_variable('POSTGRES_PORT', '5432'),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": get_env_variable("REDIS_URL", "redis://127.0.0.1:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SERIALIZER": "django_redis.serializers.pickle.PickleSerializer",
        }
    }
}

CACHE_TTL = 60 * 15

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

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

CORS_ALLOWED_ORIGINS = parse_env_list('CORS_ALLOWED_ORIGINS', 'http://localhost:4321')
CSRF_TRUSTED_ORIGINS = parse_env_list('CSRF_TRUSTED_ORIGINS', 'http://localhost:4321')

CORS_ALLOW_CREDENTIALS = True

SPECTACULAR_SETTINGS = {
    'TITLE': 'CoreAsset Inventory & IAM Engine',
    'DESCRIPTION': 'Headless API para gestión de activos, auditoría y control de acceso.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'EXCLUDE_PATHS': ['/admin/'],
}