# Developer Quickstart Guide

**Feature**: Dashboard Ledger List and Detail Accordion Component

본 퀵스타트 가이드는 로컬 개발 환경에서 백엔드 API 서버와 프론트엔드 Vue.js 앱을 구동하고 연동을 검증하는 단계를 명세합니다.

## 1. Prerequisites (환경 준비)

프로젝트 루트에서 `uv` 패키지 관리자와 `Docker` 인프라를 사용해 의존성을 설치하고 데이터베이스를 기동합니다.

```bash
# 1. 백엔드 가상 환경 패키지 격리 동기화 (헌법 VII조 준수)
uv sync

# 2. 로컬 PostgreSQL 및 Redis 컨테이너 통합 인프라 기동
docker compose -f docker-compose.db.yml up -d
```

---

## 2. Backend Server Execution (백엔드 서버 가동)

백엔드 Django 개발 서버를 `8080` 포트로 기동합니다.

```bash
# 1. Django 마이그레이션 적용 (테이블 스키마 최신화)
uv run python backend/src/manage.py migrate

# 2. 로컬 API 개발 서버 가동
uv run python backend/src/manage.py runserver 0.0.0.0:8080
```

---

## 3. Frontend Application Execution (프론트엔드 앱 가동)

프론트엔드 개발 서버를 가동합니다.

```bash
# 1. 프론트엔드 경로 진입 및 패키지 설치
cd frontend
npm install

# 2. Vite 로컬 개발 서버 기동
npm run dev
```
브라우저에서 `http://localhost:5173` 등으로 접속하여 10일차 로그인 인터페이스를 통해 로그인 후 대시보드 리스트를 조회할 수 있습니다.

---

## 4. Run Tests (기계적 검증 및 테스트 실행)

헌법 제VIII조(하이브리드 테스트 수호)에 따라 백엔드 데이터베이스 격리 유닛 테스트는 `pytest` 및 장고의 `TestCase` 조합을 활용해 초고속 피드백 루프로 검증됩니다.

```bash
# 백엔드 테스트 디렉토리 내에서 pytest 러너 실행
cd backend
uv run pytest
```
* **테스트 격리 규약**:
  * DB 결합이 필요한 뷰/직렬화기 테스트: `django.test.TestCase` 상속 및 `setUpTestData(cls)`를 통해 최초 테스트 셋업 오버헤드를 극소화하여 작성.
  * 순수 유틸리티 테스트: `unittest.TestCase` 상속으로 장고 부트스트랩 없이 밀리초 단위 속도로 수행.
