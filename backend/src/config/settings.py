import os
import environ
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# settings.py의 위치(backend/src/config/settings.py)에 의거한 정확한 디렉토리 명세
BASE_DIR = Path(__file__).resolve().parent.parent  # backend/src
BACKEND_DIR = BASE_DIR.parent  # backend

# Initialize django-environ and load local environment file
env = environ.Env()
# backend/.env 또는 프로젝트 루트의 .env.local 로딩 우선순위 지원 (T004)
env_file = BACKEND_DIR / '.env'
if not env_file.exists():
    env_file = BACKEND_DIR.parent / '.env.local'
if env_file.exists():
    environ.Env.read_env(str(env_file))

# SECURITY WARNING: keep the secret key used in production secret!
# 절대 보안 수호: 하드코딩 폴백 배제 및 환경 변수 강제 로딩 (T004)
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DEBUG', default=False)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party Apps (T006)
    'rest_framework',
    'corsheaders',
    
    # 3대 신규 비즈니스 도메인 앱 완벽 등록
    'apps.accounts',
    'apps.ledgers',
    'apps.tasks',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS 미들웨어 탑재 (T006)
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


# [T005] DB Connection Pooling Constraints & Supabase Free Plan Optimization
# 헌법 II조 및 plan.md 제약 사항 수호:
# DATABASE_URL은 필수 정보이며 하드코딩 폴백 자격 증명을 전면 배제합니다.
# api_server 컨테이너 최대 5개 커넥션 한도를 넘지 않도록 WAS 멀티프로세스 제한(Gunicorn worker=2, thread=2 등)과 연동 통제합니다.
DATABASES = {
    'default': env.db('DATABASE_URL')
}
# psycopg3 연동 엔진 설정
DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql'
# Supabase 자원 병목 방지를 위한 CONN_MAX_AGE 동적 오버라이드 지원 (기본 60초)
DATABASES['default']['CONN_MAX_AGE'] = env.int('DATABASE_CONN_MAX_AGE', default=60)
DATABASES['default']['OPTIONS'] = {
    # 연결 타임아웃 세션 물리 제한
    'connect_timeout': 5,
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

# [T006] CORS Allowed Origins 명세
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])

# [T006] 글로벌 REST API 보안 및 권한 정책 락 (Secure by Default)
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
}
