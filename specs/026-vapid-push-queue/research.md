# Research: VAPID V2 웹 푸시 발송 큐 파이프라인

**Feature Branch**: `026-vapid-push-queue`
**Phase**: Phase 0 — Outline & Research
**Date**: 2026-06-20

---

## 1. Python VAPID V2 라이브러리 선택

### 결정사항
`pywebpush>=2.0` + `py-vapid>=1.9` 두 패키지를 함께 사용.

- `py-vapid`: VAPID 키 생성 및 JWT 헤더 유틸리티 전담 (RFC 8292)
- `pywebpush`: 페이로드 암호화(aes128gcm, RFC 8291) + Push Service로의 HTTP 요청 전송

```toml
# backend/pyproject.toml 추가
"pywebpush>=2.0",
"py-vapid>=1.9",
```

### 타당성
- 두 라이브러리는 경쟁 관계가 아닌 상호보완 관계: `py-vapid`가 보안/키 레이어, `pywebpush`가 메시지 전송/암호화 레이어.
- `pywebpush`는 `aud` 클레임을 구독 endpoint로부터 자동 추론 → 구현 단순화.
- 2024~2026년 기준 프로덕션 검증 옵션으로 MDN, Twilio 등에서 표준 참조.
- 직접 구현(`cryptography` + `PyJWT`) 대비 RFC 8291 암호화(HKDF, ECE) 구현 난이도 대폭 감소.

### 고려된 대안
| 대안 | 탈락 이유 |
|------|----------|
| `webpush` (신규 PyPI 패키지) | 생태계 미성숙, 참조 문서 부족 |
| 직접 구현 (`cryptography` + `PyJWT`) | RFC 8291 암호화 구현 난이도 매우 높음, 유지보수 부담 큼 |
| `py-vapid` 단독 | 암호화(RFC 8291) 미지원 → 별도 구현 필요 |

---

## 2. FCM HTTP v1 API 통합 방식

### 결정사항
`google-auth` 라이브러리(`google-auth>=2.0`)를 사용하여 서비스 계정 JSON으로 OAuth 2.0 Bearer 토큰을 동적 생성하고, `httpx`로 FCM v1 REST API를 직접 호출.

```python
import os, json
from google.oauth2 import service_account

key_dict = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
credentials = service_account.Credentials.from_service_account_info(
    key_dict,
    scopes=["https://www.googleapis.com/auth/firebase.messaging"]
)
```

**FCM 엔드포인트 판별 전략** — 브라우저 구독 endpoint URL 패턴으로 채널 식별:
```python
def detect_push_channel(endpoint: str) -> str:
    if "fcm.googleapis.com" in endpoint:
        return "fcm"           # Chrome/Android/Firefox
    elif "web.push.apple.com" in endpoint:
        return "apple_vapid"   # Safari/iOS PWA → VAPID 표준으로 처리 가능
    else:
        return "generic_vapid" # 기타 표준 VAPID
```

> **중요**: 브라우저가 `pushManager.subscribe()` 시 반환하는 endpoint(`/fcm/send/xxx` 경로)를 백엔드가 v1 형식으로 임의 변환하지 않도록 주의. 백엔드가 FCM v1 API로 "발송하는 URL"과 구독 endpoint는 별개.

### 타당성
- `GOOGLE_APPLICATION_CREDENTIALS` 환경 변수는 파일 경로만 지원 → Docker/컨테이너에서 JSON 문자열 주입 시 `from_service_account_info()` 패턴이 필수 (spec.md Assumption 명시 준수).
- `firebase-admin` SDK 불필요 — 과대 의존성. 기존 `google-genai` 의존성 체인에 `google-auth`가 포함되어 있을 가능성 높음.

### 고려된 대안
| 대안 | 탈락 이유 |
|------|----------|
| `firebase-admin` SDK | 불필요한 의존성 추가, 컨테이너 이미지 비대화 |
| FCM Legacy API (`/fcm/send`) | Google 공식 Deprecated (2024년 이후 지원 종료) |
| 파일 볼륨 마운트 방식 | 컨테이너 이식성 저하, spec.md 명시 방향과 상이 |

---

## 3. APNs / Safari iOS 연동 방식

### 결정사항
**iOS Safari PWA의 Web Push는 VAPID 표준(pywebpush)으로 통일 처리**. 별도 APNs SDK 불필요.

iOS 16.4+ PWA 구독 endpoint는 `https://web.push.apple.com/...` 형식이며, 이는 W3C Web Push Protocol을 따르는 표준 VAPID 처리로 동작함.

```python
def send_notification(subscription: dict, payload: dict, vapid_claims: dict):
    endpoint = subscription["endpoint"]
    channel = detect_push_channel(endpoint)

    # FCM과 Apple Web Push 모두 pywebpush로 통일 처리
    webpush(
        subscription_info=subscription,
        data=json.dumps(payload),
        vapid_private_key=settings.VAPID_PRIVATE_KEY,
        vapid_claims=vapid_claims,
    )
```

**만약 네이티브 iOS 앱(비 PWA) 연동이 필요한 경우** (현 범위 외):
- `PyJWT>=2.8` + `httpx[http2]>=0.27`로 직접 APNs JWT 생성 및 HTTP/2 전송 가능
- APNs JWT 유효기간 1시간 제한 → 캐싱 필수

### 타당성
- 이 프로젝트 범위는 PWA 웹 푸시 → iOS 16.4+ Web Push는 표준 VAPID 지원 확인됨.
- `api.push.apple.com` (네이티브 APNs)은 PWA가 아닌 iOS 네이티브 앱 전용 → 현 범위 외.
- 단일 `pywebpush` 코드 경로로 Chrome/Firefox/Safari 모두 처리 → 유지보수 단순화.

### 고려된 대안
| 대안 | 탈락 이유 |
|------|----------|
| `apns2` 라이브러리 | 유지보수 종료, Python 3.12+ 미지원 |
| `aioapns` | asyncio 전용 → Celery 동기 태스크와 충돌 |
| APNs 직접 구현 | PWA 범위에서 불필요, 복잡도만 증가 |

---

## 4. Celery 알림 전용 큐 분리 방식

### 결정사항
`CELERY_TASK_ROUTES`로 `apps.notifications.tasks.*`를 `notifications` 큐로 라우팅하고, Docker Compose에 `notification_worker` 컨테이너를 추가하여 `-Q notifications -c 2`로 분리 기동.

```python
# config/settings/base.py
CELERY_TASK_ROUTES = {
    "apps.notifications.tasks.*": {"queue": "notifications"},
    "apps.ledgers.tasks.*": {"queue": "celery"},
}
```

```yaml
# docker-compose.yml 추가
notification_worker:
  build: ./backend
  command: /venv/bin/celery -A config worker --loglevel=info -Q notifications -c 2
  # concurrency=2로 제한 → 헌법 II조 커넥션 풀 8개 상한 준수
```

### 타당성
- 영수증 파싱 워커(CPU/메모리 부하)와 알림 발송 워커(I/O 대기)를 격리 → 상호 지연 오염 방지.
- SC-001(30초 이내 도달) 달성을 위해 독립 큐 필수.
- `concurrency=2` 제한으로 기존 커넥션 풀 상한(합산 8개) 초과 방지.

### 고려된 대안
| 대안 | 탈락 이유 |
|------|----------|
| 기존 `async_worker` 큐 공유 | 영수증 파싱 부하로 알림 지연 가능, SC-001 위반 리스크 |
| Django Channels (WebSocket) | 서비스 워커 Web Push와 이중화, 복잡도 과다 |
| Priority Queue | 브로커 설정 복잡도 증가, 단순 큐 분리가 더 명확 |

---

## 5. 멱등성 보장 전략 (이중 방어)

### 결정사항
**단계별 이중 방어** 전략 채택:

**① 큐 제출 단계: Redis 분산 락 (커스텀 구현)**
```python
import redis
from django.conf import settings

def submit_notification_task(user_id, event_type, idempotency_key):
    lock_key = f"push_lock:{event_type}:{user_id}:{idempotency_key}"
    r = redis.from_url(settings.CELERY_BROKER_URL)
    if r.set(lock_key, "1", nx=True, ex=300):  # 5분 TTL
        send_push_notification_task.apply_async(
            args=[user_id, event_type, idempotency_key]
        )
```

**② 실행 단계: DB NotificationLog 시간 윈도우 체크**
```python
from django.utils import timezone
from datetime import timedelta

def is_duplicate_notification(user_id, event_type, window_seconds=60):
    cutoff = timezone.now() - timedelta(seconds=window_seconds)
    return NotificationLog.objects.filter(
        user_id=user_id,
        event_type=event_type,
        created_at__gte=cutoff
    ).exists()
```

> **중요**: `task_id` 고정 방식은 Celery 공식 문서에서 중복 방지를 보장하지 않음(undefined behavior). Redis 락 + DB 체크 이중 방어 필수.

### 타당성
- Celery의 기본 배달 모델은 "at-least-once" → 단일 방어로 충분하지 않음.
- 기존 프로젝트의 "60초 임계창 방어" 패턴(AGENTS.md 명시)과 일관성 유지.
- Redis는 이미 Celery 브로커로 사용 중 → 추가 인프라 불필요.

### 고려된 대안
| 대안 | 탈락 이유 |
|------|----------|
| `task_id` 고정 단독 | Celery가 deduplication 보장하지 않음 (undefined behavior) |
| `celery-singleton` 라이브러리 | 추가 의존성, 직접 구현으로 충분 |
| DB `unique_together` 제약 단독 | 실행 후 체크만 가능, 큐 제출 단계 중복 방지 불가 |

---

## 6. 알림 이력 30일 자동 정리

### 결정사항
`CELERY_BEAT_SCHEDULE` + 매일 새벽 2시 실행 태스크로 30일 초과 `NotificationLog` 레코드 자동 삭제.

```python
# apps/notifications/tasks.py
@shared_task(name="apps.notifications.tasks.cleanup_old_notification_logs")
def cleanup_old_notification_logs():
    cutoff = timezone.now() - timedelta(days=30)
    deleted_count, _ = NotificationLog.objects.filter(
        created_at__lt=cutoff
    ).delete()
    return f"Deleted {deleted_count} old notification logs"

# config/settings/base.py
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    "cleanup-old-notification-logs": {
        "task": "apps.notifications.tasks.cleanup_old_notification_logs",
        "schedule": crontab(hour=2, minute=0),  # 새벽 2시 (트래픽 최소)
        "options": {"queue": "notifications"},
    },
}
```

### 타당성
- 기존 Celery 인프라에 `CELERY_BEAT_SCHEDULE` 설정만 추가 → 별도 인프라 불필요.
- 새벽 2시는 트래픽 최소 시간대 → DB 부하 최소화.
- `options.queue = "notifications"` 로 알림 워커에서 처리 → 큐 격리 일관성 유지.

### 고려된 대안
| 대안 | 탈락 이유 |
|------|----------|
| PostgreSQL `pg_cron` | Docker 환경 설정 복잡도 높음 |
| 별도 cron job 컨테이너 | 인프라 추가, Celery 통합 단일화 원칙 위배 |
| `CELERY_RESULT_EXPIRES` 설정 | Celery result backend 전용, ORM 모델에 적용 불가 |

---

## 7. VAPID 키 쌍 관리 전략

### 결정사항
VAPID 공개키/비밀키는 최초 1회 `vapid --gen` CLI로 생성 후, Base64url 인코딩하여 환경 변수로 영구 관리.

```ini
# backend/.env
VAPID_PRIVATE_KEY=<Base64url-encoded private key>
VAPID_PUBLIC_KEY=<Base64url-encoded public key>
VAPID_CLAIMS_EMAIL=mailto:admin@example.com
```

```ini
# frontend/.env (Vite용)
VITE_VAPID_PUBLIC_KEY=<VAPID 공개키 (동일 값)>
```

키 교체 절차는 `docs/vapid-key-rotation.md`에 문서화 (운영 중 동적 교체는 v2 백로그).

### 타당성
- spec.md Assumption 명시: "VAPID 키 쌍은 최초 1회 생성 후 환경 변수(.env)로 관리".
- 프론트엔드에서 구독 시 VAPID 공개키가 필요 → Vite의 `VITE_` 접두사로 안전하게 빌드 시 주입.

---

## 8. Django 앱 구조 결정

### 결정사항
`apps/notifications/` 신규 Django 앱 생성. `UserPushSubscription` 모델은 **현행 `apps/accounts/models.py` 위치 유지**.

### 타당성
- `UserPushSubscription`이 이미 `apps/accounts/models.py`에 정의되어 있음을 코드베이스에서 확인.
- 이관 시 마이그레이션 의존성 충돌 발생 위험 → 불필요한 위험 감수 배제.
- `NotificationTask`, `NotificationLog` 모델만 `apps/notifications/` 앱에 신설하고, `accounts.UserPushSubscription`을 ForeignKey로 참조.

---

## 요약 결정 테이블

| 항목 | 결정 | 신규 패키지 |
|------|------|------------|
| VAPID 서명 | `py-vapid>=1.9` | `py-vapid` |
| VAPID 암호화+전송 | `pywebpush>=2.0` | `pywebpush` |
| FCM v1 API 인증 | `google-auth` (기존 의존성 가능성) | 없거나 `google-auth` |
| APNs/Safari PWA | `pywebpush`로 통일 처리 (VAPID 표준) | 없음 |
| Celery 큐 분리 | `notifications` 전용 큐 + Docker 컨테이너 분리 | 없음 |
| 멱등성 | Redis 락(5분 TTL) + DB 60초 윈도우 이중 방어 | 없음 |
| 30일 자동 정리 | Celery Beat crontab (새벽 2시) | 없음 |
| 키 관리 | `.env` 환경 변수 1회 생성 고정 | 없음 |
| 앱 구조 | `apps/notifications/` 신설, UserPushSubscription은 accounts 유지 | 없음 |
