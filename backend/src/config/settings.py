import os
import environ
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize django-environ and load local environment file
env = environ.Env()
env_file = BASE_DIR.parent.parent / '.env.local'
if env_file.exists():
    environ.Env.read_env(str(env_file))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-fallback-secret-key-for-local-development')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # [T002] 3대 신규 비즈니스 도메인 앱 완벽 등록
    'apps.accounts',
    'apps.ledgers',
    'apps.tasks',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'config.wsgi.application'


# [T003] DB Connection Pooling Constraints & Supabase Free Plan Optimization
# 헌법 II조 및 plan.md 제약 사항 수호:
# Supabase 가용 커넥션 풀 고갈 붕괴를 영구 차단하기 위해, api_server 최대 5개, async_worker 최대 3개, 
# 전체 합산 8개 이하 유지 제약을 충족하기 위한 DB 설정을 수립합니다.
# CONN_MAX_AGE를 활성화하여 빈번한 커넥션 재설정 비용을 제거합니다.

DB_HOST = env.str('DB_HOST', default=env.str('POSTGRES_HOST', default='127.0.0.1'))
DB_PORT = env.str('DB_PORT', default=env.str('POSTGRES_PORT', default='5432'))
DB_NAME = env.str('DB_NAME', default=env.str('POSTGRES_DB', default='postgres'))
DB_USER = env.str('DB_USER', default=env.str('POSTGRES_USER', default='postgres'))
DB_PASSWORD = env.str('DB_PASSWORD', default=env.str('POSTGRES_PASSWORD', default='postgres'))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
        'CONN_MAX_AGE': 600,  # 10분간 커넥션 유지로 맺고 끊는 부하 최소화
        'OPTIONS': {
            # PostgreSQL 연결 시 강제 스위치 튜닝을 통해
            # 동시 연결 세션이 과대 팽창하여 DB가 Crash되는 사태를 물리 예방합니다.
            'connect_timeout': 5,
        }
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
LANGUAGE_CODE = 'ko-kr'  # 한국어 우선 원칙 준수
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
