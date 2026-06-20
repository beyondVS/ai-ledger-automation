# Quickstart: VAPID V2 웹 푸시 파이프라인 개발 가이드

**Feature Branch**: `026-vapid-push-queue`
**Date**: 2026-06-20

---

## 1. VAPID 키 쌍 생성 (최초 1회)

```bash
# py-vapid CLI로 키 생성
uv run vapid --gen
# → private_key.pem, public_key.pem 파일 생성됨
# → 터미널에 Base64url 인코딩된 공개키/비밀키가 출력됨

# 또는 Python으로 직접 생성
uv run python -c "
from py_vapid import Vapid
v = Vapid()
v.generate_keys()
print('Private:', v.private_key)
print('Public:', v.public_key)
"
```

생성된 키를 환경 변수에 등록:
```ini
# backend/.env
VAPID_PRIVATE_KEY=<출력된 비밀키 Base64url>
VAPID_PUBLIC_KEY=<출력된 공개키 Base64url>
VAPID_CLAIMS_EMAIL=mailto:admin@yourdomain.com
```

```ini
# frontend/.env
VITE_VAPID_PUBLIC_KEY=<동일한 공개키>
```

---

## 2. 신규 의존성 설치

```bash
# backend/pyproject.toml 수정 후
uv add pywebpush "py-vapid>=1.9" "httpx[http2]"
uv sync
```

---

## 3. 마이그레이션 실행

```bash
# accounts 앱 (is_active, device_hint 필드 추가)
uv run python src/manage.py makemigrations accounts

# notifications 앱 (신규 앱 생성 후)
uv run python src/manage.py makemigrations notifications

# 마이그레이션 적용
uv run python src/manage.py migrate
```

---

## 4. Docker 환경 기동

```bash
# 전체 서비스 기동 (notification_worker 컨테이너 포함)
docker compose up -d

# notification_worker 로그 확인
docker compose logs -f notification_worker

# Flower 대시보드에서 notifications 큐 확인
# http://localhost:5555
```

---

## 5. 브라우저 푸시 알림 테스트

```javascript
// 브라우저 개발자 도구 콘솔에서 실행
const vapidPublicKey = import.meta.env.VITE_VAPID_PUBLIC_KEY;
const reg = await navigator.serviceWorker.ready;

const subscription = await reg.pushManager.subscribe({
  userVisibleOnly: true,
  applicationServerKey: vapidPublicKey
});

console.log(JSON.stringify(subscription));
// → 이 JSON을 POST /api/v1/notifications/subscriptions/로 전송
```

---

## 6. 테스트 알림 발송 (어드민 전용)

```bash
# Django 쉘에서 테스트 발송
uv run python src/manage.py shell
```

```python
from apps.notifications.services import enqueue_receipt_notification

enqueue_receipt_notification(
    user_id="<테스트 사용자 UUID>",
    ledger_id="<테스트 가계부 UUID>",
    vendor_name="테스트 가맹점",
    total_amount="15000",
)
```

또는 어드민 API 사용:
```bash
curl -X POST http://localhost:8000/api/v1/notifications/test-push/ \
  -H "Authorization: Bearer <staff JWT>" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "<UUID>", "title": "테스트", "body": "안녕하세요!"}'
```

---

## 7. 로컬 HTTPS 없이 개발하기

서비스 워커의 push 이벤트는 HTTPS 또는 `localhost`에서만 동작합니다.
이 프로젝트는 `localhost:5173`에서 일반 HTTP로 기동하므로 **추가 설정 없이 개발 가능**합니다.

> 헌법 V조 명시: `localhost` 도메인은 안전한 보안 컨텍스트(Secure Context)로 브라우저가 인정하므로 PWA 설치 및 디바이스 카메라 연동, 서비스 워커 push 이벤트가 정상 작동합니다.

---

## 8. 주요 파일 위치

| 파일 | 용도 |
|------|------|
| `backend/src/apps/notifications/` | 신규 Django 앱 루트 |
| `backend/src/apps/notifications/models.py` | NotificationTask, NotificationLog |
| `backend/src/apps/notifications/tasks.py` | Celery 발송 태스크 |
| `backend/src/apps/notifications/services.py` | 큐 적재 서비스 (트리거 진입점) |
| `backend/src/apps/notifications/views.py` | REST API 뷰 |
| `backend/src/apps/notifications/urls.py` | URL 라우팅 |
| `backend/src/apps/notifications/sender.py` | VAPID/FCM/APPLE 발송 모듈 |
| `frontend/public/sw.js` | 서비스 워커 (push 핸들러 추가) |
| `frontend/src/pages/Settings.vue` | 알림 On/Off 토글 UI 섹션 추가 |
| `frontend/src/services/notificationService.js` | 구독 등록/해제 API 연동 |
