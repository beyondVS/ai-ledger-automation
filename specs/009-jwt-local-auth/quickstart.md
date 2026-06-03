# Quickstart Guide: Setup Local Authentication with JWT

이 가이드는 로컬 개발 환경에서 가입 및 JWT 로그인 기능을 구동하고, 테스트 및 동작을 확인하는 과정을 안내합니다.

---

## 1. 개발 환경 인프라 기동

로컬 PostgreSQL 데이터베이스 및 Redis 브로커를 포함한 컨테이너 인프라를 구동합니다.

```bash
# Docker Compose 기반 통합 로컬 개발 컨테이너 기동
docker compose up -d --build
```

---

## 2. 데이터베이스 마이그레이션 적용

Custom User 모델 및 `simplejwt` 관련 DB 테이블을 생성하기 위해 백엔드 컨테이너 내부에서 장고 마이그레이션을 실행합니다.

```bash
# 1. 마이그레이션 파일 생성 상태 확인 및 생성
docker compose exec api_server python manage.py makemigrations accounts

# 2. 데이터베이스 테이블 생성
docker compose exec api_server python manage.py migrate
```

---

## 3. 기계적 테스트 검증 (Linter / Formatter / Tests)

헌법에 규정된 pytest 러너 및 하이브리드 테스트 스위트를 구동하여 기계적으로 검증합니다.

```bash
# 전체 테스트 실행 (pytest 실행기 활용)
docker compose exec api_server pytest

# 특정 인증 앱 테스트 개별 실행
docker compose exec api_server pytest tests/accounts/
```

---

## 4. API 수동 작동성 테스트 예시 (E2E)

로컬에서 `curl` 또는 API 클라이언트 도구를 사용하여 가입 및 로그인이 정상적으로 JWT를 발급하는지 검증합니다.

### 4.1. 회원가입 (POST `/api/auth/register/`)

```bash
curl -X POST http://localhost:8080/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "secure_password_123"
  }'
```

* **예상 응답 (201 Created):**
  ```json
  {
    "id": "01900c71-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "email": "testuser@example.com",
    "provider": "local",
    "date_joined": "2026-06-03T23:00:00Z"
  }
  ```

### 4.2. 로그인 및 JWT 토큰 발급 (POST `/api/auth/login/`)

```bash
curl -X POST http://localhost:8080/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "secure_password_123"
  }'
```

* **예상 응답 (200 OK):**
  ```json
  {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```

### 4.3. 인증 인가 식별 API 테스트 (가계부 조회 요청 헤더 바인딩)

```bash
curl -X GET http://localhost:8080/api/ledgers/ \
  -H "Authorization: Bearer <획득한_Access_Token_문자열>"
```
