from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']

# 1. 로컬 개발 시 CORS 제한 전격 전체 허용
CORS_ALLOW_ALL_ORIGINS = True

# 2. 로컬 개발 오리진 신뢰 처리 (CORS 전격 전체 허용과 동기화)
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])
