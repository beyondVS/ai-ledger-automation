# Quickstart Guide: Cost Control Engine Core Implementation

본 가이드는 비용 통제 엔진 핵심 기능의 작동 유무를 로컬 개발 환경에서 빠르게 기계적으로 검증하고 하이브리드 테스트 아키텍처를 가동하기 위한 요약 매뉴얼입니다.

## 1. 개발 환경 초기화 및 인프라 기동

프로젝트 루트에서 `uv` 패키지 동기화 및 Docker DB/Redis 컨테이너 인프라를 백그라운드로 실행합니다.

```powershell
# 1. 파이썬 가상환경 의존성 동기화
uv sync

# 2. 로컬 PostgreSQL 및 Redis 브로커 컨테이너 기동
docker compose -f docker-compose.db.yml up -d

# 3. 데이터베이스 신규 마이그레이션 적용 (MerchantTemplate 테이블 생성 등)
uv run python backend/manage.py migrate
```

---

## 2. 하이브리드 테스트 구동 (헌법 제VIII조 준수)

본 피처는 데이터베이스 및 Django ORM 연동을 수행하는 통합 테스트와 독립 유틸리티로 구성된 파서 단위 테스트가 혼합된 하이브리드 구조를 가집니다. pytest 러너를 통해 테스트 피드백 루프를 수호합니다.

### 2.1 DB 결합형 통합 테스트 (`django.test.TestCase` 상속)
* 대상: `MerchantTemplate` 영속성, `is_verified` 필터 기반 우회/LLM 폴백 처리, DRF API 뷰 동작 검증
* 특징: `setUpTestData(cls)`를 활용하여 초기 DB 오버헤드 최소화

```powershell
uv run pytest backend/tests/integration/test_cost_control_parser.py
```

### 2.2 순수 유틸리티성 정적 파서 테스트 (`unittest.TestCase` 상속)
* 대상: 정적 정규식 규칙 매칭 알고리즘 단독 유닛 테스트
* 특징: Django 부트스트랩 기동을 완전히 우회하여 밀리초 단위 속도로 초고속 실행

```powershell
uv run pytest backend/tests/unit/test_regex_parser.py
```

---

## 3. 시나리오 E2E 수동 검증 흐름

로컬 개발 서버를 기동한 뒤 아래의 3단계 흐름을 따라 E2E 동작을 수동 기계적으로 추적합니다.

```powershell
# 백엔드 API 서버 및 Celery 비동기 워커 기동
uv run python backend/manage.py runserver
uv run celery -A src.config worker -l info
```

### 1단계: 신규 가맹점 적재 및 자가 학습 트리거
* **동작**: 시스템에 템플릿이 없는 신규 가맹점 영수증을 분석 API(`POST /api/ledgers/upload/`)로 제출합니다.
* **검증**: `202 Accepted` 응답을 획득하고, 비동기 처리가 끝나면 LLM이 파싱한 정보에 기반하여 정규식 타당성 임시 테스트가 자동 통과되어 `MerchantTemplate` 테이블에 `is_verified: false` 상태로 임시 레코드가 자동 등록되는지 확인합니다.

### 2단계: 어드민 수동 승인 적용
* **동작**: 어드민 API(`POST /api/admin/merchant-templates/<uuid>/verify/`)를 호출하여 해당 템플릿을 승인 처리합니다.
* **검증**: 데이터베이스 내 해당 가맹점의 `is_verified` 값이 `true`로 갱신되었는지 검증합니다.

### 3단계: 동일 가맹점 영수증 유입 시 LLM 우회(Bypass) 및 즉시 응답 검증
* **동작**: 1단계와 동일한 가맹점의 영수증을 다시 API로 전송합니다.
* **검증**: `201 Created` 응답과 함께 LLM API 호출(LiteLLM) 횟수가 0회인 채로, 100ms 이내에 즉시 가계부 마스터 및 품목 레코드가 동기식으로 생성 완료되는지 검증합니다.
