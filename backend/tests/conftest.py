import os
import sys
from pathlib import Path

import django

# backend/src/ 경로를 최상위 sys.path 검색 경로로 정밀 등록
BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = os.path.join(BASE_DIR, "src")
sys.path.insert(0, SRC_DIR)

# Django 설정 인프라 로드
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# django.setup() 기동을 통한 모델 정보 안전 인스톨
django.setup()


import pytest
from apps.accounts.models import User, UserPushSubscription


@pytest.fixture
def test_user(db):
    """테스트용 회원 계정을 생성하는 피스처"""
    user = User.objects.create_user(username="testuser", email="testuser@example.com", password="test_secure_password")
    return user


@pytest.fixture
def test_subscription(test_user):
    """테스트용 푸시 알림 구독 레코드를 생성하는 피스처"""
    sub = UserPushSubscription.objects.create(
        user=test_user,
        endpoint="https://fcm.googleapis.com/fcm/send/mock_endpoint_token",
        p256dh="mock_p256dh_key",
        auth="mock_auth_secret",
        device_hint="FCM",
    )
    return sub
