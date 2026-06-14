# API Contract: 사용자 타임존 환경설정 변경 API

본 문서는 사용자의 선호 타임존 설정을 동적으로 업데이트하기 위한 백엔드 엔드포인트 계약 사양을 정의합니다.

---

## 1. 엔드포인트 명세 (Endpoint Details)

* **HTTP Method**: `PATCH`
* **URL**: `/api/v1/accounts/timezone/`
* **Authentication**: `Bearer JWT Token` (sessionStorage 내 Access Token 필요)
* **Content-Type**: `application/json`

---

## 2. 요청 스키마 (Request Schema)

### Request Payload

```json
{
  "timezone": "America/New_York"
}
```

### 파라미터 제약 조건
* **`timezone`**: 
  * 데이터 타입: `String`
  * 필수 여부: 필수
  * 유효성 검사: IANA 타임존 데이터베이스 표준 명칭 포맷을 충족해야 함. (예: `Asia/Seoul`, `America/New_York`, `UTC`, `Europe/London` 등)

---

## 3. 응답 스키마 (Response Schema)

### 성공 응답 (HTTP 200 OK)

요청된 타임존이 유효하고 정상적으로 데이터베이스에 갱신 및 저장된 경우 반환됩니다.

```json
{
  "status": "success",
  "data": {
    "timezone": "America/New_York",
    "updated_at": "2026-06-14T07:00:00Z"
  }
}
```

### 실패 응답: 무효한 타임존 명칭 (HTTP 400 Bad Request)

전송된 타임존 명칭이 IANA 표준에 존재하지 않거나 알 수 없는 포맷인 경우 반환됩니다.

```json
{
  "status": "error",
  "code": "INVALID_TIMEZONE",
  "message": "제시된 타임존 명칭이 표준 IANA 규격에 유효하지 않습니다."
}
```

### 실패 응답: 인증 누락 (HTTP 401 Unauthorized)

JWT 인증 헤더가 누락되었거나 만료된 토큰인 경우 반환됩니다.

```json
{
  "status": "error",
  "code": "UNAUTHORIZED",
  "message": "인증 자격 증명이 제공되지 않았거나 유효하지 않습니다."
}
```
