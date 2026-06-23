# Interface & API Contracts: Production SSL & E2E Notification Release

**Feature**: `029-prod-ssl-nginx-push`

## 1. REST API Specification

웹푸시 알림 수명 주기 관리를 위해 프론트엔드 클라이언트(PWA)와 백엔드 API 간에 체결된 엔드포인트 규격입니다.

### 1.1 `POST /api/v1/notifications/subscribe/` (푸시 구독 등록)
브라우저 단말의 웹푸시 구독(VAPID) 상태를 서버에 전송하여 활성화합니다.

- **Request Body (JSON)**:
  ```json
  {
    "endpoint": "https://fcm.googleapis.com/fcm/send/f-xxxx...",
    "p256dh": "BBAx...",
    "auth": "Axx..."
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "status": "SUCCESS",
    "message": "Push subscription registered and activated."
  }
  ```
- **Error Response (400 Bad Request)**:
  ```json
  {
    "error": "MISSING_FIELDS",
    "message": "Required fields (endpoint, p256dh, auth) are missing."
  }
  ```

### 1.2 `POST /api/v1/notifications/unsubscribe/` (푸시 구독 해제)
특정 단말의 푸시 구독을 비활성화하여 알림 대상에서 제외합니다.

- **Request Body (JSON)**:
  ```json
  {
    "endpoint": "https://fcm.googleapis.com/fcm/send/f-xxxx..."
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "status": "SUCCESS",
    "message": "Push subscription deactivated."
  }
  ```

### 1.3 `POST /api/v1/notifications/ack/` (푸시 수신 확인)
백그라운드에서 푸시 알림 수신 성공 시 클라이언트가 서버로 송신하여 로그 상태를 갱신합니다.

- **Request Body (JSON)**:
  ```json
  {
    "notification_id": "019047b2-3b54-7bb0-a67f-5d85787a3ecd"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "status": "SUCCESS",
    "notification_id": "019047b2-3b54-7bb0-a67f-5d85787a3ecd",
    "state": "DELIVERED"
  }
  ```

### 1.4 `GET /api/v1/notifications/sync/` (오프라인 델타 동기화)
단말이 오프라인에서 온라인 상태로 전환될 시, 마지막 동기화 일시 이후 발생한 전송 실패 혹은 미수신 알림 내역을 조회합니다.

- **Query Parameters**:
  - `last_sync`: `ISO 8601 DateTime` (예: `2026-06-23T22:00:00Z`)
- **Response (200 OK - JSON Array)**:
  ```json
  [
    {
      "id": "019047b2-3b54-7bb0-a67f-5d85787a3ecd",
      "type": "RECEIPT_SUCCESS",
      "title": "영수증 분석 완료",
      "message": "스타벅스 영수증 파싱이 완료되어 12,500원이 가계부에 적재되었습니다.",
      "created_at": "2026-06-23T22:15:00Z"
    }
  ]
  ```

---

## 2. Infrastructure Configuration Contracts (Nginx & Docker Compose)

실서버 인프라의 단일 게이트웨이 유지를 위한 역방향 프록시 통신 규격 계약입니다.

### 2.1 Nginx Ingress Configuration Contract
- Nginx는 호스트 포트 80(HTTP) 및 443(HTTPS)을 수신하며, 모든 HTTP 트래픽은 HTTPS로 `301 Moved Permanently` 리다이렉트 처리합니다.
- 외부 SSL Offloading을 이용하므로 Nginx 자체는 HTTP 포트 80만 오픈하고, 헤더의 `X-Forwarded-Proto`가 `https`로 유입됨을 감지하여 안전하게 리다이렉션을 우회/중계합니다.

```nginx
server {
    listen 80;
    server_name example.com;

    # 외부 SSL 오프로딩 검증 및 강제 HTTPS 리다이렉트
    if ($http_x_forwarded_proto != "https") {
        return 301 https://$host$request_uri;
    }

    # Frontend SPA 정적 파일 서빙 계약
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    # Backend API 리버스 프록시 중계 계약
    location /api/ {
        proxy_pass http://api-server:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
    }
}
```

### 2.2 Docker Compose Production Isolation
- `postgres-db` 및 `redis-broker` 컨테이너는 어떠한 경우에도 외부 호스트 포트 바인딩(예: `5432:5432`)을 노출하지 않습니다.
- 오직 `prod-bridge` 내부 격리 네트워크 안에서만 `api-server` 및 `async-worker`와의 TCP/IP 연결을 유지합니다.
