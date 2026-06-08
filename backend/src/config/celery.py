import os

from celery import Celery

# Django 설정을 Celery의 기본 설정 모듈로 지정합니다.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("ai_ledger_backend")

# Celery 설정을 Django settings.py에 정의하고, 접두사는 'CELERY_'로 통일합니다.
app.config_from_object("django.conf:settings", namespace="CELERY")

# 각 장고 앱 디렉토리 내에 정의된 tasks.py 모듈을 자동 탐색하여 등록합니다.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """
    Celery 연동 유무 확인을 위한 테스트 디버그 태스크
    """
    print(f"Request: {self.request!r}")
