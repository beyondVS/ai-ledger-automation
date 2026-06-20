# API Contracts: VAPID V2 웹 푸시 발송 큐 파이프라인

**Feature Branch**: `026-vapid-push-queue`
**Phase**: Phase 1 — Design & Contracts
**Date**: 2026-06-20

---

## 백엔드 REST API 엔드포인트

### 기본 URL 접두사
`/api/v1/notifications/`

---

### 1. 구독 등록 (POST)

**URL**: `POST /api/v1/notifications/subscriptions/`

**인증**: Bearer JWT (필수)

**요청 본문**:
```json
{
  "endpoint": "https://fcm.googleapis.com/fcm/send/xxx...",
  "keys": {
    "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtazy...",
    "auth":   "tBHItJI5svbpez7KI4CCXg=="
  }
}
```

**응답 (201 Created)**:
```json
{
  "id": "018f4d3e-...",
  "endpoint": "https://fcm.googleapis.com/fcm/send/xxx...",
  "device_hint": "FCM",
  "is_active": true,
  "created_at": "2026-06-20T15:00:00Z"
}
```

**응답 (200 OK)**: 이미 등록된 구독의 경우 (동일 endpoint) 기존 구독 정보 반환 및 활성화.

**오류**:
| 코드 | 상황 |
|------|------|
| 400 | endpoint, p256dh, auth 필드 누락 또는 유효하지 않은 URL |
| 401 | 인증 실패 |

---

### 2. 구독 비활성화 (DELETE)

**URL**: `DELETE /api/v1/notifications/subscriptions/{id}/`

**인증**: Bearer JWT (필수, 본인 구독만 삭제 가능)

**응답 (204 No Content)**

**오류**:
| 코드 | 상황 |
|------|------|
| 403 | 다른 사용자의 구독에 접근 시도 |
| 404 | 존재하지 않는 구독 ID |

---

### 3. 내 구독 목록 조회 (GET)

**URL**: `GET /api/v1/notifications/subscriptions/`

**인증**: Bearer JWT (필수)

**응답 (200 OK)**:
```json
[
  {
    "id": "018f4d3e-...",
    "device_hint": "FCM",
    "is_active": true,
    "created_at": "2026-06-20T15:00:00Z"
  }
]
```

> endpoint, p256dh, auth 등 민감 정보는 목록 조회 응답에서 제외.

---

### 4. 테스트 알림 발송 (POST, 디버그용)

**URL**: `POST /api/v1/notifications/test-push/`

**인증**: Bearer JWT (필수), `is_staff=True` 권한 필요

**요청 본문**:
```json
{
  "user_id": "018f4d3e-...",
  "title": "테스트 알림",
  "body": "이것은 테스트 알림입니다."
}
```

**응답 (202 Accepted)**:
```json
{
  "message": "테스트 알림이 큐에 적재되었습니다.",
  "queued_count": 2
}
```

---

### 5. 알림 발송 이력 조회 (GET, 운영자 전용)

**URL**: `GET /api/v1/notifications/logs/`

**인증**: Bearer JWT (필수), `is_staff=True` 권한 필요

**쿼리 파라미터**:
| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| `user_id` | 특정 사용자 필터 | — |
| `event_type` | 이벤트 유형 필터 | — |
| `is_success` | 성공/실패 필터 (`true`/`false`) | — |
| `start_date` | 조회 시작일 (ISO 8601) | 30일 전 |
| `end_date` | 조회 종료일 (ISO 8601) | 현재 |

**응답 (200 OK)**:
```json
{
  "count": 42,
  "results": [
    {
      "id": "...",
      "task_id": "...",
      "user_id": "...",
      "channel": "FCM",
      "http_status_code": 200,
      "is_success": true,
      "created_at": "2026-06-20T15:00:00Z"
    }
  ]
}
```

---

### 6. VAPID 공개키 조회 (GET, 인증 불필요)

**URL**: `GET /api/v1/notifications/vapid-public-key/`

**인증**: 불필요 (프론트엔드 구독 등록 전 공개키 획득 목적)

**응답 (200 OK)**:
```json
{
  "public_key": "BNcRdreALRFXTkOOUHK1EtK2..."
}
```

---

## 프론트엔드 → 백엔드 이벤트 트리거 (내부 계약)

### 트리거 1: 영수증 처리 완료

**발생 위치**: `apps/ledgers/tasks.py` → `extract_receipt_task` 완료 시

```python
# 영수증 처리 완료 후 알림 큐 적재
from apps.notifications.services import enqueue_receipt_notification

enqueue_receipt_notification(
    user_id=str(user.id),
    ledger_id=str(ledger.id),
    vendor_name=ledger.vendor_name,
    total_amount=str(ledger.total_amount),
)
```

**알림 페이로드**:
```json
{
  "title": "영수증 처리 완료",
  "body": "{vendor_name}에서 {total_amount}원 결제가 등록되었습니다.",
  "action_url": "/dashboard"
}
```

**멱등성 키**: `"RECEIPT_PROCESSED:{user_id}:{ledger_id}"`

---

### 트리거 2: 월별 예산 임계 초과

**발생 위치**: `apps/ledgers/views.py` 또는 `apps/ledgers/services.py` → 월별 집계 후 임계값 비교

```python
from apps.notifications.services import enqueue_budget_alert_notification

enqueue_budget_alert_notification(
    user_id=str(user.id),
    year=year,
    month=month,
    spent_amount=spent,
    budget_amount=budget,
    threshold_percent=80,
)
```

**알림 페이로드**:
```json
{
  "title": "월별 지출 경보",
  "body": "이번 달 예산의 80%를 초과했습니다. ({spent}원 / {budget}원)",
  "action_url": "/dashboard"
}
```

**멱등성 키**: `"BUDGET_THRESHOLD_ALERT:{user_id}:{year}-{month}"`

---

## 서비스 워커 계약 (frontend/public/sw.js)

### push 이벤트 핸들러 추가

```javascript
self.addEventListener("push", (event) => {
  if (!event.data) return;

  const data = event.data.json();
  const options = {
    body: data.body,
    icon: "/icons/icon-192x192.png",
    badge: "/icons/badge-72x72.png",
    data: { actionUrl: data.action_url || "/" },
    requireInteraction: false,
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});
```

### notificationclick 이벤트 핸들러 추가

```javascript
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const actionUrl = event.notification.data?.actionUrl || "/";

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true })
      .then((clientList) => {
        for (const client of clientList) {
          if (client.url.includes(actionUrl) && "focus" in client) {
            return client.focus();
          }
        }
        if (clients.openWindow) {
          return clients.openWindow(actionUrl);
        }
      })
  );
});
```

---

## Celery 태스크 계약 (apps/notifications/tasks.py)

### send_push_notification_task

```python
@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    queue="notifications",
    name="apps.notifications.tasks.send_push_notification",
)
def send_push_notification_task(
    self,
    notification_task_id: str,
) -> dict:
    """
    단일 구독에 대한 Web Push 발송 태스크.
    - 지수 백오프: 5s → 10s → 20s (max_retries=3)
    - 410 Gone 수신 시 구독 자동 비활성화 (FR-006)
    - 성공/실패 여부 NotificationLog에 영속화
    """
    ...

# 반환 형식
{
  "status": "SUCCESS" | "FAILED",
  "notification_task_id": "...",
  "channel": "FCM" | "APPLE_VAPID" | "GENERIC_VAPID",
  "http_status_code": 201,
}
```

### dispatch_user_notifications_task

```python
@shared_task(queue="notifications")
def dispatch_user_notifications_task(
    user_id: str,
    event_type: str,
    payload: dict,
    idempotency_key: str,
) -> dict:
    """
    사용자의 모든 활성 구독에 send_push_notification_task를 병렬 발송.
    - 멱등성 체크: Redis 락 (5분 TTL) + DB 60초 윈도우
    - 한 사용자가 복수 기기 구독 시 모든 구독에 병렬 발송
    """
    ...
```

---

## 알림 페이로드 크기 제한 계약

- 전체 JSON 직렬화 페이로드: **≤ 4,096 bytes** (FCM 기준 상한선)
- `title`: ≤ 255 bytes
- `body`: 나머지 공간에서 최대화, 초과 시 잘라내기 처리
- 초과 시 `PushPayloadTooLargeError` 예외 발생 → 400 응답
