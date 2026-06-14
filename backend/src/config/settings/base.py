from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# settings/base.py의 위치에 의거한 정확한 디렉토리 명세 보정
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/src
BACKEND_DIR = BASE_DIR.parent  # backend

# Initialize django-environ and load local environment file
env = environ.Env()
# backend/.env 로딩 지원
env_file = BACKEND_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party Apps
    "rest_framework",
    "corsheaders",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    # 신규 비즈니스 도메인 앱
    "apps.accounts",
    "apps.ledgers",
    "apps.tasks",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.accounts.middleware.TimezoneMiddleware",  # 사용자 타임존 동적 전환 미들웨어
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# DB Connection Pooling Constraints & Supabase Free Plan Optimization (Django 5.1+ Native Pool)
import sys

IS_CELERY_WORKER = "celery" in sys.argv[0] or any("celery" in arg for arg in sys.argv)

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"
DATABASES["default"]["CONN_MAX_AGE"] = 0  # Native pooling requires CONN_MAX_AGE=0
DATABASES["default"]["OPTIONS"] = {
    "connect_timeout": 5,
    "pool": {
        "min_size": 1,
        "max_size": 3 if IS_CELERY_WORKER else 5,  # api_server <= 5, celery_worker <= 3
        "timeout": 10,
    },
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS & CSRF 신뢰 오리진 기본 공통 설정
CORS_ALLOWED_ORIGINS = []
CSRF_TRUSTED_ORIGINS = []

AUTH_USER_MODEL = "accounts.User"

# 글로벌 REST API 보안 및 권한 정책
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
}

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=30)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=14)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# AI 분석 엔진 (LiteLLM / Gemini / Ollama) 설정
GEMINI_ENABLED = env.bool("GEMINI_ENABLED", default=False)
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
GEMINI_MODEL = env("GEMINI_MODEL", default="gemini-2.5-flash")

OLLAMA_MODEL = env("OLLAMA_MODEL", default="gemma4:e4b")
OLLAMA_API_BASE = env("OLLAMA_API_BASE", default="http://localhost:11434")

# =========================================================================
# Celery & Redis Infrastructure Configuration (헌법 제II조 수호)
# =========================================================================
# - 메시지 브로커 및 결과 백엔드로 Redis 고속 메모리 스토어 연동.
# - AWS/Supabase 무료 DB 커넥션 제한(최대 8개)을 준수하기 위해
#   서버당 가용한 커넥션 풀을 api_server <= 5, Celery 워커 <= 3으로 격리 통제.
# =========================================================================
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 태스크 타임아웃 30분 제한

# Django/pytest 테스트 구동 시 Celery 태스크를 Eager(동기) 모드로 실행하여 테스트 격리 및 외부 Redis 의존성 차단
import sys

if "test" in sys.argv or "pytest" in sys.argv or any("pytest" in arg for arg in sys.argv):
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = False
