import os
import time
import uuid
from django.db import models

def generate_uuidv7() -> uuid.UUID:
    """
    [CRITICAL HELP] 
    RFC 9562 표준 규격에 부합하는 UUIDv7(시간 기반 고유 식별자)을 생성합니다.
    - 상위 48비트: 현재의 Unix Timestamp Milliseconds
    - 4비트 버전: 0111 (Version 7)
    - 2비트 배리언트: 10 (RFC 4122 Variant)
    - 나머지 비트: 암호학적 난수(os.urandom)로 채워 분산 환경 난수 충돌률을 0%에 수렴시킵니다.
    """
    nanoseconds = time.time_ns()
    milliseconds = nanoseconds // 1_000_000
    
    timestamp_bytes = milliseconds.to_bytes(6, byteorder='big')
    rand_bytes = os.urandom(10)
    
    byte_list = bytearray(16)
    byte_list[0:6] = timestamp_bytes
    byte_list[6] = (rand_bytes[0] & 0x0F) | 0x70  # Version 7 (0111)
    byte_list[7] = rand_bytes[1]
    byte_list[8] = (rand_bytes[2] & 0x3F) | 0x80  # Variant 10 (RFC 4122)
    byte_list[9:16] = rand_bytes[3:10]
    
    return uuid.UUID(bytes=bytes(byte_list))


class User(models.Model):
    """
    [T004] User 데이터 모델
    - 가입 회원 계정 정보 관리 및 메일 인바운드 수집 시 스팸 차단을 위한 
      이메일 화이트리스트 주소 매핑 필드(최대 3개)를 갖춥니다.
    """
    id = models.UUIDField(primary_key=True, default=generate_uuidv7, editable=False, db_index=True)
    email = models.EmailField(unique=True, max_length=254)
    
    # 헌법 IV조 준수: 사용자당 최대 3개의 SPF/DKIM 검증 통과 화이트리스트 메일 발송인 관리
    registered_forward_email_1 = models.EmailField(null=True, blank=True, max_length=254)
    registered_forward_email_2 = models.EmailField(null=True, blank=True, max_length=254)
    registered_forward_email_3 = models.EmailField(null=True, blank=True, max_length=254)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def __str__(self):
        return self.email


class UserPushSubscription(models.Model):
    """
    [T005] UserPushSubscription 데이터 모델
    - PWA 클라이언트 기기로 VAPID v2 표준 웹 푸시 알림을 즉각 디스패치하기 위해
      브라우저의 푸시 구독 엔드포인트 세부 명세 정보를 영구 보존합니다.
    """
    id = models.UUIDField(primary_key=True, default=generate_uuidv7, editable=False, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_subscriptions')
    
    # 푸시 게이트웨이 엔드포인트 URL은 매우 길어질 수 있으므로 max_length=2000 이상 보장
    endpoint = models.URLField(unique=True, max_length=2000)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_push_subscriptions'
        verbose_name = 'user_push_subscription'
        verbose_name_plural = 'user_push_subscriptions'

    def __str__(self):
        return f"PushSubscription for {self.user.email} ({self.id})"
