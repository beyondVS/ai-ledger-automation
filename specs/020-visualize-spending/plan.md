# Implementation Plan: 소비 시각화 차트 및 예산 게이지 (가계부 UI 고도화 1단계)

**Branch**: `020-visualize-spending` | **Date**: 2026-06-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/020-visualize-spending/spec.md`

## Summary
* **주요 요건**: 카테고리별 소비 분포(원형 차트), 최근 월별 지출 추이(막대 차트, 3/6/12개월 필터), 당월 예산 소진 속도(게이지 바, 인라인/모달 실시간 수정), 당월 지출 TOP 3 가맹점 요약 카드를 포함한 직관적인 모바일 PWA 반응형 소비 대시보드를 구축합니다.
* **기술적 접근**:
  * **프론트엔드**: 가벼운 캔버스 기반 렌더링 성능을 보장하는 `Chart.js` & `vue-chartjs`를 탑재하여 Vue 3 데이터 반응성 및 Tailwind CSS 반응형 레이아웃과 유기적으로 바인딩합니다.
  * **백엔드**: `MonthlyBudget` 독립 모델을 신설하여 월별 예산을 영속화하고, 대시보드 렌더링에 필요한 모든 지표를 단 한 번의 요청으로 반환하는 `/api/ledgers/dashboard/` 전용 통합 통계 DTO API를 구축합니다.
  * **성능 및 캐싱**: 지출 데이터 인덱스 최적화 및 당월 외의 과거 월 데이터는 Redis/로컬 캐시를 조회하게 설계하여 쿼리 응답 시간을 상시 **100ms 이내**로 강력하게 방어합니다.

## Technical Context

**Language/Version**: Python 3.13 (백엔드) & JavaScript / Vue.js 3 (프론트엔드)

**Primary Dependencies**: Django REST Framework (백엔드) & Vite, Vue 3, Chart.js (v4+), vue-chartjs (v5+), Tailwind CSS (프론트엔드)

**Storage**: PostgreSQL v18+ (ACID 정합성 보장, `MonthlyBudget` 모델 및 복합 인덱스 신설), Redis (지출 통계 캐싱 병용)

**Testing**: pytest & Django `TestCase` 하이브리드 테스트 (DB 결합 테스트는 `setUpTestData` 활용)

**Target Platform**: Docker Compose 통합 가상화 환경 (api_server, postgres_db, redis_broker, async_worker)

**Project Type**: Web application (Frontend + Backend 모노레포)

**Performance Goals**: 대시보드 API 쿼리 응답 시간 **100ms 이내** 방어, 최초 렌더링 1.5초 이내 완료

**Constraints**: DB 커넥션 풀 크기 제약 (api_server 5개, Celery worker 3개, 전체 합산 8개 이하), JWT httpOnly 이중 토큰 인증(Refresh 쿠키, sessionStorage Access Token staff 권한 payload 검증), PWA 모바일 반응형 2-3열 그리드 레이아웃.

**Scale/Scope**: 당월 지출 실시간 및 과거 월 통계 집계.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

* **I. 데이터 무결성 및 원자성 트랜잭션 최우선**: 예산 설정 및 변경 API(`/api/budgets/`) 가동 시 `MonthlyBudget` 레코드 저장 연산은 DB의 `UNIQUE (user_id, budget_month)` 제약조건에 종속되어 중복 생성이 차단되며 정합성이 보장됩니다. -> **PASS**
* **II. 비동기 큐 전환 및 자원 점유 최적화**: 대시보드 조회 및 예산 갱신 연산은 최대 8개 이하의 DB 커넥션 풀 제약을 철저히 준수합니다. -> **PASS**
* **V. Vision-First PWA & HTTPS/JWT 보안 환경 강제**: 대시보드는 데스크톱 브레이크포인트에 맞춘 반응형 2열 분할 그리드를 지원하고 모바일 뷰포트 정합성을 100% 준수합니다. JWT httpOnly 이중 토큰 인증 사양을 준수하며 Access Token staff payload 검증을 준수합니다. -> **PASS**
* **VI. 크로스 플랫폼 대칭 툴링 및 문서 동기화 수호**: 이번 피처에서 쉘 스크립트 수정은 발생하지 않으며, 에이전트 설계 계획이 완성됨에 따라 `AGENTS.md` 내의 계획 가이드 포인터를 `020-visualize-spending`으로 유기적으로 자동 갱신합니다. -> **PASS**
* **VIII. pytest 및 Django TestCase 하이브리드 테스트 수호**: API 뷰 및 ORM 쿼리 검증 테스트는 `django.test.TestCase` 및 `setUpTestData(cls)`를 사용하여 가동 속도를 최적화합니다. -> **PASS**

## Project Structure

### Documentation (this feature)

```text
specs/020-visualize-spending/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── budget-api.md
│   └── dashboard-api.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── backend/
│   ├── settings.py
│   └── urls.py
├── ledgers/
│   ├── models.py        # MonthlyBudget 모델 추가
│   ├── views.py         # dashboard, budget API 뷰 추가
│   ├── serializers.py   # MonthlyBudgetSerializer, DashboardSerializer 추가
│   └── urls.py          # 라우팅 추가
└── tests/
    └── test_dashboard_api.py # pytest API 테스트 코드 추가

frontend/
├── package.json         # chart.js, vue-chartjs 패키지 추가
├── src/
│   ├── components/      # PieChart.vue, BarChart.vue, BudgetGauge.vue 추가
│   ├── pages/           # Dashboard.vue 고도화 및 컴포넌트 마운트
│   └── services/        # budgetService, dashboardService API 연동 코드 추가
└── tests/
```

**Structure Decision**: 프론트엔드(Vue.js)와 백엔드(Django REST Framework)가 분리된 모노레포 구조이므로 Option 2(Web application) 구조를 적용하여 각각 `backend/`와 `frontend/` 디렉토리 하위에 수술적 편집을 진행합니다.
