from .base import *

DEBUG = False

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

# 배포 환경용 CORS 및 CSRF 신뢰 오리진 환경변수 엄격 통제
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

# HTTPS 프로토콜 보안 강화 강제
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# 리버스 프록시(Nginx/ALB)의 SSL Termination 세션 쿠키 붕괴 방지용 보안 헤더 신뢰 설정
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
