# Implementation Plan: 가계부 UI 고도화 2단계 및 사용자 타임존 설정 변경 기능

**Branch**: `021-ledger-calendar-timezone` | **Date**: 2026-06-14 | **Spec**: [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/021-ledger-calendar-timezone/spec.md)

**Input**: Feature specification from `/specs/021-ledger-calendar-timezone/spec.md`

## Summary

* **주요 요구사항**: 
  * 사용자 고유 타임존 변경 API(`PATCH /api/v1/accounts/timezone/`) 및 프론트엔드 환경설정 탭 UI 구축
  * 영수증 결제일시 적재 및 조회 시 사용자 설정 타임존 기준 글로벌 정합성 연동 파이프라인 연계
  * 일자별 지출 요약을 시각적으로 제공하는 가로 폭 반응형 Grid 기반 캘린더 뷰(Calendar View) 모드 추가
  * 상호명, 카테고리(체크박스/칩 다중 선택 - OR 조건), 기간, 금액 대역별 복합 쿼리 다차원 검색/필터링 패널 연동
* **기술적 접근**:
  * 백엔드에서는 Django의 `timezone.activate()`를 요청 라이프사이클에 동적으로 연동하여, 조회 시 DB의 UTC 타임스탬프를 사용자 선호 시간대로 직렬화하고, API 파라미터 유효성(IANA 표준)을 검증함.
  * 프론트엔드에서는 외부 라이브러리 의존 없이 Vue 3 + Tailwind CSS를 활용한 Vanilla CSS Grid 방식의 고성능 캘린더 UI를 작성하여, 복합 필터 갱신 시 실시간 반응형 데이터 바인딩을 지원함.

## Technical Context

**Language/Version**: Python 3.13 (Backend) / Vue.js 3 & Vite & JavaScript/TypeScript (Frontend)

**Primary Dependencies**: Django, Django REST Framework, zoneinfo, Django-Filter (Backend) / Tailwind CSS (Frontend)

**Storage**: PostgreSQL v18+ (JSONB 및 timestamp with time zone 지원)

**Testing**: pytest & Django TestCase 하이브리드 테스트 (setUpTestData 기반 DB 결합 API 테스트 및 unittest 기반 무장고 유틸리티 테스트)

**Target Platform**: Web Browser PWA (Docker Compose 배포 인프라)

**Project Type**: web-service (Django API Server + Vue.js Frontend Client)

**Performance Goals**: 당월 지출 조회 응답 및 렌더링 < 1초, 모드 전환 렌더링 < 200ms, 복합 필터 검색 쿼리 응답 < 500ms, 타임존 API 변경 < 500ms

**Constraints**: Supabase 무료 등급 한계를 감안하여 최대 DB 커넥션 풀 크기 api_server 5개, Celery 3개, 전체 합산 8개 이하 제약 준수

**Scale/Scope**: 10만 건 이상의 가계부 데이터 셋 및 수십 개 타임존을 포괄하는 스케일 지원

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

* **데이터 무결성 및 원자성 트랜잭션 최우선 (Principle I)**:
  * 타임존 정보 유입 검증 및 영수증 결제일시 타임스탬프 보정 과정은 Django ORM의 단일 트랜잭션 블록(`transaction.atomic()`)과 연계되어 오차 및 Dirty State 없이 원자적으로 완결되어야 함. (**통과**)
* **비동기 큐 전환 및 자원 점유 최적화 (Principle II)**:
  * 타임존 설정 변경 시 기존 데이터 소급 렌더링은 동적 타임존 팩토리 변환을 거치므로 CPU 오버헤드를 극소화하는 방식으로 쿼리 설계. 최대 데이터베이스 커넥션 제한(8개) 수호. (**통과**)
* **크로스 플랫폼 대칭 툴링 및 문서 동기화 수호 (Principle VI)**:
  * 신규 빌드 스크립트 작성 시 Windows/Bash 대칭 구조 유지 및 `scripts/` 배치 규정 준수. (**통과**)
* **pytest 및 Django TestCase 하이브리드 테스트 수호 (Principle VIII)**:
  * 타임존 보정 API 및 다차원 필터링 ORM 연동 테스트는 `django.test.TestCase`를 상속하고 `setUpTestData`를 통해 DB 가동 오버헤드를 극소화. 순수 타임존 문자열 유효성 검사 등은 `unittest.TestCase` 상속으로 장고 부트스트랩을 우회하여 초고속 피드백 실현. (**통과**)

## Project Structure

### Documentation (this feature)

```text
specs/021-ledger-calendar-timezone/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/           # Phase 1 output
    ├── accounts-timezone-contract.md
    └── ledgers-query-contract.md
```

### Source Code (repository root)

```text
backend/
├── accounts/
│   ├── models.py        # UserAccount(User) timezone 필드 추가
│   └── views.py         # PATCH /api/v1/accounts/timezone/ API 엔드포인트
├── ledgers/
│   ├── views.py         # GET /api/v1/ledgers/ (다차원 필터), GET /api/v1/ledgers/calendar/ (달력 요약)
│   ├── filters.py       # Django-Filter 다차원 복합 필터 조건 설정
│   └── services.py      # 결제일시 파이프라인 타임존 보정 로직
└── tests/               # pytest 기반 하이브리드 테스트 스위트

frontend/
├── src/
│   ├── components/
│   │   ├── CalendarView.vue      # Vanilla CSS Grid 기반 월별 달력 컴포넌트
│   │   └── FilterPanel.vue       # 상호/카테고리/기간/금액 복합 검색 패널
│   ├── pages/
│   │   ├── Dashboard.vue         # 목록/캘린더 토글 스위처 및 바인딩 페이지
│   │   └── Settings.vue          # 사용자 프로필 설정 탭 및 타임존 변경 UI
│   └── services/
│       ├── accountService.js     # 타임존 PATCH API 연동
│       └── ledgerService.js      # 다차원 필터 및 캘린더 요약 API 연동
```

**Structure Decision**: 
본 프로젝트는 백엔드(Python/Django)와 프론트엔드(Vue.js)가 분리 구동되는 도커 기반 웹 애플리케이션 구조(Option 2)를 따릅니다. 백엔드의 `accounts` 및 `ledgers` 앱 하위에 타임존 처리와 다차원 조회를 배치하고, 프론트엔드의 `src/components/`와 `src/pages/` 하위에 관련 UI 요소를 격리 작성합니다.

## Complexity Tracking

*정당화가 필요한 헌법 위반 사항이 존재하지 않습니다.*
