# API Contracts: User Authentication & Token Session

본 문서는 프론트엔드 PWA 클라이언트와 백엔드 Django REST Framework(SimpleJWT) 서버 간의 HTTP API 통신 계약 명세서입니다.

---

## 1. 회원가입 API (User Registration)

- **HTTP Method & URL**: `POST /api/auth/register/`
- **인증 제한**: `AllowAny` (인증 불필요)

### Request Payload

```json
{
  "username": "user_nickname",
  "password": "secure_password123",
  "email": "user@example.com"
}
```

| 필드명 | 타입 | 필수 여부 | 제약 조건 및 설명 |
| :--- | :--- | :--- | :--- |
| `username` | String | 필수 | 중복 불가능. 가계부 및 화면 상에 노출될 식별 이름. |
| `password` | String | 필수 | 최소 8자 이상, 해싱 저장 처리됨. |
| `email` | String | 선택 | 가입 시 이메일 유효성 검사 적용. 메일 인바운드 수집에 연동 가능. |

### Response Payload

#### 성공 (201 Created)
```json
{
  "id": "01900000-0000-7000-8000-000000000001",
  "username": "user_nickname",
  "email": "user@example.com",
  "date_joined": "2026-06-05T10:15:00Z"
}
```

#### 실패 (400 Bad Request)
- **아이디 중복 에러**:
  ```json
  {
    "username": [
      "이미 가입된 아이디(username)입니다."
    ]
  }
  ```
- **필드 누락 또는 형식 유효성 에러**:
  ```json
  {
    "password": [
      "이 필드는 필수 항목입니다."
    ]
  }
  ```

---

## 2. 로그인 API (User Login & Token Issue)

- **HTTP Method & URL**: `POST /api/auth/login/`
- **인증 제한**: `AllowAny` (인증 불필요)

### Request Payload

```json
{
  "username": "user_nickname",
  "password": "secure_password123"
}
```

### Response Payload

#### 성공 (200 OK)
로그인 성공 시 SimpleJWT 표준 규격에 따라 단기 엑세스 토큰 및 리프레시 토큰 쌍을 반환합니다.
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMDE5MDAwMDAtMDAwMC03MDAwLTgwMDAtMDAwMDAwMDAwMDAxIiwiZXhwIjoxNzE4MDAzNjAwfQ...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMDE5MDAwMDAtMDAwMC03MDAwLTgwMDAtMDAwMDAwMDAwMDAxIiwiZXhwIjoxNzE4MDg2NDAwfQ..."
}
```

#### 실패 (401 Unauthorized)
```json
{
  "detail": "No active account found with the given credentials"
}
```

---

## 3. 로그아웃 API (User Logout)

- **HTTP Method & URL**: `POST /api/auth/logout/`
- **인증 제한**: `AllowAny` (인증 무력화 후 블랙리스트 기재)

### Request Payload

```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Response Payload

#### 성공 (205 Reset Content)
- 응답 본문 없음. 클라이언트는 보관하고 있던 LocalStorage의 토큰 세션을 일괄 삭제 및 초기화 처리합니다.

#### 실패 (400 Bad Request - 토큰 누락 또는 이미 만료됨)
```json
{
  "detail": "Token is invalid or expired"
}
```
