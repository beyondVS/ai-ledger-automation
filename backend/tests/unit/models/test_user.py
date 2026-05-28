import time
import pytest
from django.db import IntegrityError
from apps.accounts.models import User, UserPushSubscription, generate_uuidv7

@pytest.mark.django_db
def test_generate_uuidv7_uniqueness_and_version():
    """
    generate_uuidv7() 헬퍼 함수가 고유한 식별자를 생성하며,
    RFC 9562 Version 7 규격을 충족하는지 검증합니다.
    """
    uuid1 = generate_uuidv7()
    time.sleep(0.005)  # 5밀리초 대기를 두어 시계열 순서 차이 보장
    uuid2 = generate_uuidv7()
    
    assert uuid1 != uuid2
    assert uuid1.version == 7
    assert uuid2.version == 7
    # 시간 순서 정렬이 성립해야 함
    assert str(uuid1) < str(uuid2)


@pytest.mark.django_db
def test_create_user_with_whitelist_emails():
    """
    이메일 화이트리스트 주소 매핑 필드(registered_forward_email 1, 2, 3)를 장착한
    User 모델의 정상 생성 및 필드 유입 상태를 검증합니다.
    """
    user = User.objects.create(
        email="owner@example.com",
        registered_forward_email_1="whitelist1@example.com",
        registered_forward_email_2="whitelist2@example.com",
        registered_forward_email_3="whitelist3@example.com"
    )
    
    assert user.id is not None
    assert user.email == "owner@example.com"
    assert user.registered_forward_email_1 == "whitelist1@example.com"
    assert user.registered_forward_email_2 == "whitelist2@example.com"
    assert user.registered_forward_email_3 == "whitelist3@example.com"


@pytest.mark.django_db
def test_user_push_subscription_uniqueness():
    """
    VAPID 표준 웹 푸시 구독 엔드포인트의 고유성(Unique)을 검증합니다.
    """
    user = User.objects.create(email="push_uniq_user@example.com")
    
    UserPushSubscription.objects.create(
        user=user,
        endpoint="https://fcm.googleapis.com/fcm/send/token_uniq",
        p256dh="p256dh_public_key_string",
        auth="auth_secret_string"
    )
    
    # 중복 엔드포인트 생성 시 고유성 위배(IntegrityError)가 발생하는지 검증
    with pytest.raises(IntegrityError):
        UserPushSubscription.objects.create(
            user=user,
            endpoint="https://fcm.googleapis.com/fcm/send/token_uniq",  # 중복
            p256dh="another_key",
            auth="another_auth"
        )


@pytest.mark.django_db
def test_user_push_subscription_cascade():
    """
    User 레코드 삭제 시 연관된 구독 정보까지 동시 소멸하는 CASCADE 정합성을 검증합니다.
    """
    user = User.objects.create(email="push_cascade_user@example.com")
    
    subscription = UserPushSubscription.objects.create(
        user=user,
        endpoint="https://fcm.googleapis.com/fcm/send/token_cascade",
        p256dh="p256dh_public_key_string",
        auth="auth_secret_string"
    )
    
    assert subscription.id is not None
    assert subscription.user == user
    
    user_id = user.id
    user.delete()
    
    assert not UserPushSubscription.objects.filter(user_id=user_id).exists()
