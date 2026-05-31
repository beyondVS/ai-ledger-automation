# Interface Contract: Local Health Check API

본 문서는 Python 및 Django 보일러플레이트 셋업 단계에서 웹 프레임워크의 정상 구동 및 PostgreSQL v18+ 데이터베이스와의 실시간 핸드셰이크 상태를 E2E로 진단하기 위한 로컬 헬스 체크 API 규격을 명세합니다.

---

## 1. Endpoint 명세 및 접근 권한

| 구분 | 내용 |
| :--- | :--- |
| **HTTP Method** | `GET` |
| **URI Path** | `/api/health/` |
| **Access Permission** | `AllowAny` (글로벌 `IsAuthenticated` 잠금 정책의 유일한 화이트리스트 예외 우회 대역) |
| **Content-Type** | `application/json; charset=utf-8` |

---

## 2. API Request

별도의 Request Parameter, Body Payload, 또는 인증 토큰 헤더를 요구하지 않습니다. (비인증 익명 호출 가능)

---

## 3. API Response

### 3.1 성공 응답 (HTTP 200 OK)
Django 코어 프레임워크가 정상 기동 중이고, PostgreSQL v18+ 데이터베이스와의 단순 조회 쿼리 핸드셰이크(e.g., `SELECT 1`)가 성공적으로 끝났을 때의 응답 규격입니다.

```json
{
  "status": "healthy",
  "timestamp": "2026-05-31T15:43:00+09:00",
  "services": {
    "django": "up",
    "database": "up"
  }
}
```

### 3.2 데이터베이스 오프라인 또는 연결 지연 장해 (HTTP 503 Service Unavailable)
Django 웹 프레임워크는 가동 중이나, PostgreSQL DBMS 서버가 중지되었거나 자격 증명 오타 등으로 연결을 수립하지 못했을 때 반환하는 응답 규격입니다.

```json
{
  "status": "unhealthy",
  "timestamp": "2026-05-31T15:43:00+09:00",
  "services": {
    "django": "up",
    "database": "down"
  },
  "error": "Database connection failed: OperationalError"
}
```

---

## 4. 기계적 인수 기준 (Acceptance Criteria)

- **AC-001 (보안 예외 검증)**: 별도의 인증(Session/Token) 없이 `/api/health/`에 익명 GET 요청 시, 401/403 권한 거부 코드 대신 반드시 `200 OK` 혹은 `503 Service Unavailable`이 성공 반환되어야 한다.
- **AC-002 (DB 격리 진단)**: 데이터베이스 인프라 컨테이너를 일시 중지시킨 뒤 호출 시, 500 Internal Server Error로 충돌 Crash를 내며 멈추지 않고, 계약에 맞춘 `503 Service Unavailable` JSON 및 에러 문구를 정상 응답해야 한다.
