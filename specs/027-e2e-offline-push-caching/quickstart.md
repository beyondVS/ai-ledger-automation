# Quickstart Guide: E2E Offline Push & Caching

이 문서는 오프라인 웹 푸시 알림 수신 및 디바이스 캐싱 데이터 무결성 검증을 위한 로컬 개발 환경 구성 및 테스트 실행 방법을 안내합니다.

---

## 1. 사전 요구사항 (Prerequisites)

- 로컬 개발 장비에 `Docker Desktop` 및 `uv`, `Node.js (v18+)`가 설치되어 있어야 합니다.
- Git 피처 브랜치 `027-e2e-offline-push-caching` 상에서 작업을 진행합니다.

---

## 2. 개발 인프라 기동 (Local Infrastructure)

데이터베이스(PostgreSQL v18) 및 Redis 브로커를 컨테이너로 기동합니다.

```bash
# PostgreSQL 및 Redis 단독 백그라운드 기동
docker compose -f docker-compose.db.yml up -d
```

---

## 3. 백엔드 및 프론트엔드 빌드/구동 (Development Run)

### 3.1 백엔드 API & Celery Worker 구동
백엔드 가상 환경을 동기화하고 API 서버 및 워커를 띄웁니다.

```bash
# 1. 의존성 패키지 동기화 및 락 파일 갱신
uv sync

# 2. 데이터베이스 마이그레이션 실행
uv run python backend/src/manage.py migrate

# 3. 개발 API 서버 기동 (기본 포트 8000)
uv run python backend/src/manage.py runserver 0.0.0.0:8000

# 4. Celery 비동기 워커 구동 (별도 터미널)
uv run celery -A backend.src.celery_app worker -Q notifications --loglevel=info
```

### 3.2 프론트엔드 웹 앱 구동
프론트엔드 의존성 패키지를 설치하고 개발용 Vite 서버를 일반 HTTP로 가동합니다. (localhost 도메인은 보안 컨텍스트 규격 상 PWA와 카메라 capture, 서비스 워커를 정상 지원합니다.)

```bash
# 1. frontend 디렉토리로 이동하여 npm 패키지 설치
cd frontend
npm install

# 2. Vite 개발 서버 가동
npm run dev
```

---

## 4. Playwright E2E 자동화 테스트 실행 (Offline Test)

오프라인 상태와 서비스 워커 가로채기, IndexedDB 캐싱 연동 E2E 시나리오를 Playwright로 기계적 검증합니다.

```bash
# 1. Playwright 실행을 위한 브라우저 바이너리 설치 (최초 1회)
npx playwright install chromium

# 2. 오프라인 웹 푸시 무결성 E2E 테스트 실행
npx playwright test frontend/tests/e2e/offline-push.spec.js --headed
```

### E2E 테스트 내부 가상 시나리오
1. Playwright가 브라우저를 켜고 로그인 및 알림 수신 동의(`Granted`)를 수립합니다.
2. `context.setOffline(true)`를 가동해 브라우저 상태를 즉시 오프라인으로 전환합니다.
3. 백엔드 API 서버를 모의(Mocking)하여 Celery 비동기 워커가 푸시 메시지를 중개 서버로 발송하도록 이벤트를 트리거합니다.
4. 브라우저의 오프라인 네트워크 차단을 복구(`context.setOffline(false)`)합니다.
5. 브라우저 푸시 서비스(Mock Push Server)가 지연 대기 중이던 푸시 이벤트를 서비스 워커(`sw.js`)로 전송합니다.
6. 서비스 워커가 이벤트를 가로채 단말의 로컬 IndexedDB에 `CachedNotification`을 생성(30일/100개 기준 및 멱등성 유지)하는지 검증합니다.
7. IndexedDB에 적재된 데이터의 UUIDv7 ID 및 title, body 필드 무결성을 대조 확인하고 성공 상태를 반환합니다.
