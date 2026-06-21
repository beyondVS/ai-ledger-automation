# Interface Contracts: Notification Acknowledgment & Sync API

이 문서는 웹 푸시 수신 시 단말이 발송하는 수신 확인(Acknowledgment) API와 포그라운드 진입 시 호출되는 동기화(Sync) API에 대한 데이터 구조 및 인터페이스 규약을 정의합니다.

---

## 1. Acknowledgment API (수신 확인)

단말의 서비스 워커(Service Worker)가 푸시 메시지를 최종 수신 및 캐싱 완료한 시점에 백엔드에 도달 상태를 보고하기 위해 호출하는 비동기 API입니다.

- **URL**: `/api/v1/notifications/<uuid:id>/acknowledge/`
- **Method**: `POST`
- **Authentication**: JWT (Access Token 필수, 서비스 워커 요청 시 헤더 주입)
- **Headers**:
  - `Content-Type: application/json`

### 1.1 Request Payload
```json
{
  "status": "DELIVERED",
  "delivered_at": "2026-06-21T01:20:00Z"
}
```

- **필드 명세**:
  - `status` (String, Required): 반드시 `"DELIVERED"` 값이어야 함.
  - `delivered_at` (String, Required): 단말 기기 기준 알림 도달 로컬 시각을 ISO-8601 UTC 규격으로 변환한 문자열.

### 1.2 Response Payload
#### 성공 (200 OK)
```json
{
  "success": true,
  "id": "019036c3-1a2b-7f3e-8c9d-a1b2c3d4e5f6",
  "status": "DELIVERED"
}
```

#### 실패 (400 Bad Request - 유효하지 않은 상태 값 또는 Payload 누락)
```json
{
  "detail": "Invalid status value. Only 'DELIVERED' status update is permitted via this endpoint."
}
```

#### 실패 (404 Not Found - 존재하지 않거나 권한이 없는 알림 ID)
```json
{
  "detail": "Notification log record not found."
}
```

---

## 2. Sync API (상태 동기화)

사용자가 앱 화면을 포그라운드로 활성화(Document Focus 진입)했을 때, 단말의 IndexedDB 로컬 캐시와 백엔드 상태를 대조하여 읽음 상태 등을 보정하기 위해 호출하는 델타 동기화 API입니다.

- **URL**: `/api/v1/notifications/sync/`
- **Method**: `GET`
- **Authentication**: JWT (Access Token 필수)
- **Query Parameters**:
  - `last_synced_at` (String, Optional): 단말이 기억하고 있는 최종 동기화 타임스탬프 (ISO-8601 UTC). 미전송 시 최근 30일 이내의 미삭제 알림 전체 목록(최대 100개)을 반환합니다.

### 2.1 Response Payload
#### 성공 (200 OK)
```json
{
  "synced_at": "2026-06-21T01:21:00Z",
  "notifications": [
    {
      "id": "019036c3-1a2b-7f3e-8c9d-a1b2c3d4e5f6",
      "title": "6월 예산 알림",
      "body": "6월 가계부 예산 소진율이 80%를 초과하였습니다.",
      "status": "READ",
      "created_at": "2026-06-21T01:10:00Z"
    },
    {
      "id": "019036c3-9f8e-7d6c-5b4a-3b2c1d0e9f8a",
      "title": "영수증 분석 완료",
      "body": "스타벅스 역삼역점 결제 영수증 분석이 정상 완료되었습니다.",
      "status": "UNREAD",
      "created_at": "2026-06-21T01:15:00Z"
    }
  ]
}
```

- **필드 명세**:
  - `synced_at`: 이번 동기화가 이루어진 서버 기준 시각 (다음 동기화의 `last_synced_at` 파라미터로 사용).
  - `notifications`: 델타 또는 전체 알림 목록 배열. 각 항목은 IndexedDB 스크립트에서 upsert(고유 `id` 기준 덮어쓰기)하여 캐시를 보정합니다.
