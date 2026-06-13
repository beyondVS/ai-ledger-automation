# Tasks: Template Promotion & Self-Healing

**Input**: Design documents from `/specs/019-auto-promote-template/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/admin_api.md

**Tests**: TDD (Test-Driven Development)가 적용되어, 각 사용자 스토리의 구현 작업 전에 해당 동작을 검증하기 위한 테스트 코드를 먼저 작성하고 실패함을 확인해야 합니다.

**Organization**: 각 사용자 스토리별로 태스크가 그룹화되어 있어, 독립적인 구현과 테스트가 가능합니다.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 프로젝트 구조 초기화 및 테스트 패키지 동기화

- [X] T001 `backend/src/` 및 `frontend/src/` 하위에 템플릿 관리 피처를 위한 기본 디렉토리 구조 검증 및 생성
- [X] T002 `backend/pyproject.toml` 설정 파일 내 신규 검증 및 API 모킹을 위한 테스트 패키지 의존성 확인 및 `uv sync` 동기화
- [X] T003 [P] `pre-commit` 린터 및 포매터 환경 작동 검증 및 활성화 상태 확인

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 본격적인 비즈니스 로직 작성 전에 구현 완료되어야 하는 데이터베이스 마이그레이션 및 서비스 뼈대 구성

**⚠️ CRITICAL**: 이 페이즈가 완료되기 전까지는 어떠한 사용자 스토리 작업도 시작할 수 없습니다.

- [X] T004 `backend/src/models/template.py` 경로의 기존 `MerchantTemplate` 모델에 `consistency_count`, `self_healing_attempts`, `is_blacklisted`, `last_healing_at` 필드를 추가하는 Django Migration 파일 생성 및 DB 마이그레이션 실행
- [X] T005 [P] `backend/src/models/template.py` 경로에 신규 실행 로그 모델 `TemplateExecutionHistory` 데이터 스키마 및 UUIDv7 PK 정의 마이그레이션 파일 생성 및 DB 마이그레이션 실행
- [X] T006 [P] `backend/src/services/promotion.py` 경로에 템플릿 승격/강등 및 자가치유를 전담 처리할 Base 서비스 인터페이스 뼈대 구성
- [X] T007 `backend/src/api/admin_views.py` 경로에 어드민 템플릿 관리 조회를 수행할 백엔드 API 라우터 뼈대 구성 및 URL 맵핑 설정

**Checkpoint**: Foundational 페이즈 완료 - 데이터 모델 및 API 뼈대가 준비되어 사용자 스토리 구현 단계로 병렬 진입 가능

---

## Phase 3: User Story 1 - Automatic Promotion of Merchant Template (Priority: P1) 🎯 MVP

**Goal**: 동일 템플릿 파싱 패턴이 3회 연속 일치 시 `is_verified: true`로 자동 승격

**Independent Test**: 동일 영수증을 3회 업로드 시 `is_verified`가 자동으로 `True`로 승격되고 4회차부터 LLM API 우회 여부 검증

### Tests for User Story 1 (TDD - Write FIRST) ⚠️

- [X] T008 [P] [US1] `backend/tests/test_template_promotion.py` 경로에 자동 승인(consistency_count 카운팅 및 3회 도달 시 is_verified: true) 조건 검증 실패 테스트 코드 우선 작성

### Implementation for User Story 1

- [X] T009 [US1] `backend/src/services/promotion.py` 경로에 템플릿 일치성을 평가하고 카운팅을 처리하여 3회차에 승격시키는 `promote_template_if_consistent` 서비스 로직 구현
- [X] T010 [US1] `backend/src/services/parser.py` 경로의 BypassParser 캐시 조회 블록에 자동 승격 플래그(`is_verified`) 상태를 검사하여 LLM 호출을 건너뛰는 바이패스 파서 연동 구현
- [X] T011 [US1] `backend/tests/test_template_promotion.py` 내 작성된 테스트 코드를 실행하여 자동 승격 기능의 무결성 증명
- [X] T012 [P] [US1] `frontend/src/pages/admin/TemplateList.vue` 경로에 가맹점 템플릿 목록 및 승격 상태(`is_verified`)를 보여주는 UI 컴포넌트 마크업 및 어드민 API 연동
- [X] T013 [US1] `frontend/src/components/admin/TemplateListItem.vue` 경로에 목록 내 개별 템플릿 행(Row) 및 뱃지 스타일 렌더링 구현

**Checkpoint**: 이 시점에서 User Story 1이 완전하게 독자 작동하며 테스트 검증을 통과해야 합니다.

---

## Phase 4: User Story 2 - Template Demotion & Self-Healing upon Correction or Error (Priority: P2)

**Goal**: 에러나 사용자 정정 발생 시 즉각 강등 및 자가 치유(정규식 재생성)

**Independent Test**: 승인된 템플릿에 정정 API가 전송되었을 때 `is_verified: false`로 강등되고 백그라운드 Celery 자가치유 태스크를 통해 새 정규식 규칙이 갱신 적재되는지 검증

### Tests for User Story 2 (TDD - Write FIRST) ⚠️

- [X] T014 [P] [US2] `backend/tests/test_template_self_healing.py` 경로에 파싱 에러 발생 또는 사용자 수동 정정 이벤트 수신 시 즉각 강등(`is_verified: false`) 처리 및 자가 치유 Celery 태스크 트리거 동작을 검증하는 실패 테스트 코드 우선 작성

### Implementation for User Story 2

- [X] T015 [US2] `backend/src/services/promotion.py` 경로에 예외 또는 정정 감지 시 즉각 강등 처리하고 `TemplateExecutionHistory`에 Diff 데이터를 로깅하는 `demote_template` 서비스 로직 구현
- [X] T016 [US2] `backend/src/tasks/template_tasks.py` 경로에 수동 정정 데이터(Ground Truth)를 피딩하여 Gemini API를 통해 최적화된 새로운 정규식을 재생성하는 Celery 비동기 태스크 `self_heal_template_task` 구현
- [X] T017 [US2] `backend/src/tasks/template_tasks.py` 내의 `self_heal_template_task` 로직에 갱신 횟수 누적(`self_healing_attempts`) 및 3회 초과 실패 시 블랙리스트 (`is_blacklisted: true`)로 격리하는 예외 제한 가드 로직 추가 구현
- [X] T018 [US2] `backend/src/services/parser.py` 경로의 파서 실행 제어 블록에 템플릿 에러 발생 시의 `demote_template` 호출 예외 처리 핸들러 통합 구현
- [X] T019 [US2] `backend/tests/test_template_self_healing.py` 내 작성된 테스트 코드를 실행하여 자동 강등 및 자가치유 비동기 파이프라인의 무결성 증명
- [X] T020 [P] [US2] `frontend/src/pages/admin/TemplateDetail.vue` 경로에 특정 가맹점 템플릿의 자가 치유 이력 및 사용자 정정 Diff 데이터 로그를 시간순으로 조회하는 UI 상세 조회 페이지 구현 및 통합
- [X] T021 [US2] `frontend/src/pages/admin/TemplateDetail.vue` 경로에 블랙리스트 상태 해제(`reset-healing`) 및 수동 정규식 조율 API 액션 버튼 및 모달 UI 구현

**Checkpoint**: 이 시점에서 User Story 1과 2가 모두 독자적으로 통합 작동하며 테스트를 통과해야 합니다.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: 문서 최신화 및 최종 멱등성 검증

- [ ] T022 [P] `docs/project_plan.md` 경로에 개발 일정 및 아키텍처 개정 사항 문서 최신화 반영
- [ ] T023 `backend/tests/` 디렉토리 내 전체 테스트 묶음을 pytest CLI로 일괄 수행하여 기존 결합 테스트 하위 호환성 및 신규 템플릿 로직 정합성 최종 교차 검증
- [ ] T024 `scripts/local-db-controller.ps1` (및 `.sh` 대칭 스크립트)를 사용해 DB 초기화 후 E2E 마이그레이션이 깔끔하게 재구동되는지 멱등성 검증

---

## Dependencies & Execution Order

### Phase Dependencies

* **Setup (Phase 1)**: 의존성 없음 - 즉시 시작 가능.
* **Foundational (Phase 2)**: Setup 완료 후 시작 가능 - **모든 사용자 스토리(US1, US2) 구현을 블로킹**합니다.
* **User Stories (Phase 3 & 4)**: Foundational 완료 후 시작 가능. US1과 US2는 각각 독립적으로 구성되어 있어 병렬 개발이 가능합니다.
* **Polish (Phase 5)**: 모든 사용자 스토리가 완료된 후 최종 다듬기 및 테스트를 위해 수행합니다.

### Within Each User Story
* TDD 지침에 따라 테스트 사양을 먼저 작성하여 **실패(FAIL)**함을 확인한 뒤 실제 모델, 서비스, API 뷰 구현에 진입합니다.
* 백엔드 API 서비스와 검증이 완료된 후에 프론트엔드 어드민 뷰 화면 UI 통합에 들어갑니다.

---

## Parallel Example: User Story 1 & 2

```bash
# User Story 1과 User Story 2의 테스트 코드는 병렬로 작성할 수 있습니다:
Task: "backend/tests/test_template_promotion.py 경로에 자동 승인 검증 실패 테스트 코드 우선 작성"
Task: "backend/tests/test_template_self_healing.py 경로에 자동 강등 검증 실패 테스트 코드 우선 작성"

# 어드민 UI 컴포넌트 마크업과 상세 조회 페이지 또한 병렬 개발이 가능합니다:
Task: "frontend/src/pages/admin/TemplateList.vue 경로에 가맹점 템플릿 목록 UI 및 API 연동"
Task: "frontend/src/pages/admin/TemplateDetail.vue 경로에 자가치유 이력 및 Diff 조회 UI 구현"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Phase 1: Setup 완료.
2. Phase 2: Foundational 구현 (블로킹 인프라 구축).
3. Phase 3: User Story 1 완료.
4. **STOP and VALIDATE**: 3회 연속 동일 패턴 인입 시 LLM 우회가 정상 작동하는지 E2E로 독립 검증 및 평가.

### Incremental Delivery
1. Setup + Foundation 완료 -> 인프라 준비.
2. User Story 1 (자동 승격) 추가 및 테스트 통과 -> MVP 배포 가능.
3. User Story 2 (강등 및 자가치유) 추가 및 테스트 통과 -> 비용 통제 자율 진화 엔진 완결.
4. 각 스토리는 이전 기능의 가동성을 깨뜨리지 않고 점진적으로 가치를 더합니다.
