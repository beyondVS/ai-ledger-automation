import os

from django.core.asgi import get_asgi_application

# Django 설정 모듈 기본 바인딩
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

# ASGI 비동기 어플리케이션 인터페이스 획득
application = get_asgi_application()
