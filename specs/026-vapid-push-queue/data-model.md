# Data Model: VAPID V2 웹 푸시 발송 큐 파이프라인

**Feature Branch**: `026-vapid-push-queue`
**Phase**: Phase 1 — Design & Contracts
**Date**: 2026-06-20

---

## 기존 모델 (변경 없음)

### accounts.UserPushSubscription (기존 유지)

`apps/accounts/models.py`에 이미 정의되어 있으며, **이관하지 않고 현행 위치를 유지**한다.

```python
class UserPushSubscription(models.Model):
    id         : UUIDField (PK, UUIDv7, auto)
    user       : ForeignKey → accounts.User (CASCADE)
    endpoint   : URLField (max_length=2000)   # 브라우저 구독 엔드포인트 URL
    p256dh     : CharField (max_length=255)   # 공개키 (Base64url)
    auth       : CharField (max_length=255)   # 인증 시크릿 (Base64url)
    is_active  : BooleanField (default=True)  # 410 Gone 수신 시 False 전환
    device_hint: CharField (max_length=20, choices=[FCM|APPLE|GENERIC], 신규 추가)
    created_at : DateTimeField (auto_now_add)

    Meta:
        db_table = "user_push_subscriptions"
        constraints:
            UniqueConstraint(fields=["user", "endpoint"])
```

> **신규 필드 추가 (마이그레이션 필요)**:
> - `is_active`: 구독 비활성화 상태 추적 (FR-006: 410 Gone 자동 처리)
> - `device_hint`: 채널 식별 캐시 (`FCM`, `APPLE`, `GENERIC`). endpoint URL 패턴 분석 결과 저장.

---

## 신규 모델 (apps/notifications/models.py)

### NotificationTask (알림 발송 태스크)

큐에 적재되는 알림 작업 단위. Celery 태스크와 1:1 대응.

```python
class NotificationTask(models.Model):
    """
    알림 발송 큐 태스크 레코드.
    - 멱등성 보장: idempotency_key로 동일 이벤트 중복 발송 차단.
    - 상태 전이: PENDING → PROCESSING → SUCCESS | FAILED
    """
    STATUS_CHOICES = [
        ("PENDING",    "대기 중"),
        ("PROCESSING", "처리 중"),
        ("SUCCESS",    "성공"),
        ("FAILED",     "실패"),
    ]

    EVENT_TYPE_CHOICES = [
        ("RECEIPT_PROCESSED",      "영수증 처리 완료"),
        ("BUDGET_THRESHOLD_ALERT", "월별 예산 임계 초과"),
    ]

    id               : UUIDField (PK, UUIDv7, auto)
    user             : ForeignKey → accounts.User (CASCADE)
    subscription     : ForeignKey → accounts.UserPushSubscription (SET_NULL, null=True)
                       # 발송 당시 대상 구독. 구독 삭제 시 이력 보존을 위해 SET_NULL.
    event_type       : CharField (max_length=50, choices=EVENT_TYPE_CHOICES)
    idempotency_key  : CharField (max_length=255, db_index=True)
                       # 형식: "{event_type}:{user_id}:{unique_identifier}"
                       # 예: "RECEIPT_PROCESSED:{user_id}:{ledger_id}"
                       # 예: "BUDGET_THRESHOLD_ALERT:{user_id}:{year}-{month}"
    title            : CharField (max_length=255)
    body             : TextField
    action_url       : URLField (null=True, blank=True)
    status           : CharField (max_length=20, choices=STATUS_CHOICES, default="PENDING")
    retry_count      : PositiveSmallIntegerField (default=0)
    last_attempted_at: DateTimeField (null=True, blank=True)
    created_at       : DateTimeField (auto_now_add)
    updated_at       : DateTimeField (auto_now)

    Meta:
        db_table = "notification_tasks"
        constraints:
            UniqueConstraint(
                fields=["idempotency_key", "subscription"],
                name="unique_notification_task_idempotency"
            )
        indexes:
            Index(fields=["user", "status", "created_at"])
            Index(fields=["idempotency_key"])
```

**상태 전이 다이어그램**:
```
PENDING ──[Celery Worker 소비]──► PROCESSING
    ├── [발송 성공] ──────────────► SUCCESS
    ├── [일시적 실패 + retry_count < 3] ──► PENDING (재시도)
    └── [최대 재시도 초과 / 영구 실패] ──► FAILED
```

---

### NotificationLog (발송 이력 감사 로그)

완료된 발송의 감사 기록. 30일 보존 후 자동 정리.

```python
class NotificationLog(models.Model):
    """
    알림 발송 감사 이력.
    - 보존 기간: 30일 (Celery Beat 자동 정리)
    - 조회 대상: 운영자 어드민 전용 (최종 사용자 미노출)
    """
    CHANNEL_CHOICES = [
        ("FCM",          "Firebase Cloud Messaging"),
        ("APPLE_VAPID",  "Apple Web Push (VAPID)"),
        ("GENERIC_VAPID","Generic Web Push (VAPID)"),
    ]

    id              : UUIDField (PK, UUIDv7, auto)
    task            : ForeignKey → NotificationTask (CASCADE)
    user            : ForeignKey → accounts.User (SET_NULL, null=True)
    channel         : CharField (max_length=20, choices=CHANNEL_CHOICES)
    endpoint_hint   : CharField (max_length=255)  # 발송 당시 endpoint URL (앞 255자, 감사용)
    http_status_code: PositiveSmallIntegerField (null=True)
    response_body   : TextField (null=True, blank=True, max_length=2000)  # 에러 응답 요약
    is_success      : BooleanField (db_index=True)
    created_at      : DateTimeField (auto_now_add, db_index=True)

    Meta:
        db_table = "notification_logs"
        indexes:
            Index(fields=["user", "is_success", "created_at"])
            Index(fields=["created_at"])  # 30일 정리 배치 쿼리 최적화
```

---

## 유효성 검사 규칙

| 모델 | 필드 | 규칙 |
|------|------|------|
| UserPushSubscription | `endpoint` | 유효한 URL, max_length=2000 |
| UserPushSubscription | `p256dh`, `auth` | 비어있지 않은 문자열 |
| NotificationTask | `title` | max_length=255 (페이로드 4KB 상한 준수) |
| NotificationTask | `body` | 전체 페이로드(JSON 직렬화) ≤ 4096 bytes 검증 |
| NotificationTask | `idempotency_key` | max_length=255, 고유성 보장 |
| NotificationLog | `response_body` | max_length=2000 (잘라내기 저장) |

---

## 마이그레이션 계획

### apps/accounts (기존 앱 마이그레이션)
- `UserPushSubscription`에 `is_active` (BooleanField, default=True) 추가
- `UserPushSubscription`에 `device_hint` (CharField, max_length=20, blank=True) 추가
- 마이그레이션 파일: `accounts/migrations/00XX_add_push_subscription_active_device_hint.py`

### apps/notifications (신규 앱 마이그레이션)
- `apps.notifications` INSTALLED_APPS 등록
- `NotificationTask`, `NotificationLog` 초기 마이그레이션 생성
- 마이그레이션 파일: `notifications/migrations/0001_initial.py`

---

## 엔티티 관계 다이어그램

```
accounts.User
    │ 1
    │
    ├─ * accounts.UserPushSubscription
    │       │ 1
    │       │
    │       └─ * notifications.NotificationTask
    │                   │ 1
    │                   │
    │                   └─ * notifications.NotificationLog
    │
    └─ * notifications.NotificationTask (user FK, 직접 참조)
    └─ * notifications.NotificationLog  (user FK, 직접 참조)
```

---

## 신규 환경 변수

```ini
# backend/.env 추가 항목
VAPID_PRIVATE_KEY=<Base64url-encoded ECDSA private key>
VAPID_PUBLIC_KEY=<Base64url-encoded ECDSA public key>
VAPID_CLAIMS_EMAIL=mailto:admin@example.com

# FCM 서비스 계정 (JSON 문자열 전체)
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}

# (옵션) 알림 예산 임계값 (기본 80%)
BUDGET_ALERT_THRESHOLD_PERCENT=80

# frontend/.env 추가 항목
VITE_VAPID_PUBLIC_KEY=<VAPID 공개키 (동일 값)>
```
