# Quickstart: 개발 및 검증 퀵스타트 가이드

본 문서는 가계부 UI 고도화 2단계 및 사용자 타임존 환경설정 변경 기능을 로컬 셋업하고 E2E로 빠르게 기동 및 검증하기 위한 가이드를 제공합니다.

---

## 1. 백엔드 가동 및 데이터베이스 마이그레이션

### 1.1 데이터베이스 및 백그라운드 인프라 기동
먼저 Docker Compose를 사용하여 로컬 PostgreSQL v18 데이터베이스 및 Redis 브로커를 백그라운드로 실행합니다.

```bash
docker compose -f docker-compose.db.yml up -d
```

### 1.2 선언적 패키지 동기화 및 락 갱신
프로젝트 헌법(Principle VII)에 따라, 파이썬 의존성 환경을 격리 동기화합니다.

```bash
uv sync
```

### 1.3 장고 마이그레이션 실행
사용자 타임존 필드 추가 및 복합 인덱스 생성을 위해 마이그레이션 스크립트를 빌드하고 반영합니다.

```bash
# 백엔드 디렉토리 또는 루트 uv 컨텍스트에서 실행
uv run python backend/manage.py makemigrations
uv run python backend/manage.py migrate
```

### 1.4 백엔드 API 서버 로컬 구동
```bash
uv run python backend/manage.py runserver 0.0.0.0:8000
```

---

## 2. API 엔드포인트 검증 (Curl Command)

### 2.1 사용자 타임존 변경 API 테스트
임의의 테스트 유저 자격증명(JWT)을 통해 사용자의 타임존 설정을 뉴욕 시간대로 변경합니다.

```bash
curl -X PATCH http://localhost:8000/api/v1/accounts/timezone/ \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"timezone": "America/New_York"}'
```

**예상 성공 응답**:
```json
{"status":"success","data":{"timezone":"America/New_York"}}
```

### 2.2 다차원 복합 필터링 목록 조회 테스트
상호명에 '스타벅스'가 들어가고 식비 카테고리(예: `c12a7bd8-5e8c-8bd9-9002-df6e297d297b`), 금액 1만원~5만원 사이인 지출 내역을 검색합니다.

```bash
curl -X GET "http://localhost:8000/api/v1/ledgers/?q=스타벅스&categories=c12a7bd8-5e8c-8bd9-9002-df6e297d297b&min_amount=10000&max_amount=50000" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```

### 2.3 캘린더 요약 집계 API 테스트
```bash
curl -X GET "http://localhost:8000/api/v1/ledgers/calendar/?year=2026&month=6&q=스타벅스" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```

---

## 3. 프론트엔드 클라이언트 구동

### 3.1 의존성 설치 및 로컬 서버 실행
```bash
cd frontend
npm install
npm run dev
```

### 3.2 로컬 브라우저 디버깅
* 브라우저에서 `http://localhost:5173`에 접속합니다.
* **설정(Settings)** 페이지로 이동하여 새로 추가된 **타임존 설정 탭**에서 타임존을 선택 및 변경 저장합니다.
* **대시보드(Dashboard)** 페이지로 돌아와 상단의 **캘린더 뷰** 토글 버튼을 작동하여 일자별 합산 지출이 올바르게 요약 렌더링되는지 확인하고, 필터 패널에서 복합 검색을 수행하여 렌더링 속도와 정합성을 체감 테스트합니다.
