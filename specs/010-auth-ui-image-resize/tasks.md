# Tasks: Frontend Authentication and Client-side Image Resizing

**Input**: Design documents from `/specs/010-auth-ui-image-resize/`

**Prerequisites**: [plan.md](file:///D:/Projects/Private/ai-ledger-automation/specs/010-auth-ui-image-resize/plan.md) (required), [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/010-auth-ui-image-resize/spec.md) (required for user stories), [research.md](file:///D:/Projects/Private/ai-ledger-automation/specs/010-auth-ui-image-resize/research.md), [data-model.md](file:///D:/Projects/Private/ai-ledger-automation/specs/010-auth-ui-image-resize/data-model.md), [auth-api.md](file:///D:/Projects/Private/ai-ledger-automation/specs/010-auth-ui-image-resize/contracts/auth-api.md)

**Tests**: TDD 방식이 명시적으로 요구되었으므로, 각 사용자 스토리의 구현부 작성 이전에 테스트 코드 구현 태스크를 반드시 먼저 수행하여 Fails 상태를 확인한 뒤 개발을 진행합니다.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/` (Based on plan.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 frontend/package.json 경로에 vue-router@4 의존성 패키지 설치
- [X] T002 frontend/package.json 경로의 scripts 항목에 "test": "vitest" 스크립트 명령어 등록
- [X] T003 [P] frontend/src/router/ 및 frontend/src/utils/ 디렉토리 구조 준비

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] 백엔드 JWT 인증 API 정합성을 검증하기 위해 backend/tests/accounts/test_account_views.py 경로에 회원가입 및 로그인 기본 E2E 통합 테스트 작성 및 pytest 통과 검증
- [X] T005 백엔드 DB 마이그레이션 최신화 및 로컬 PostgreSQL 개발 DB 환경 구동 확인

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - 사용자 로그인 및 회원가입 UI (Priority: P1) 🎯 MVP

**Goal**: 이메일, 패스워드와 함께 사용자의 이름(닉네임)을 수집하여 회원가입을 수행하고 로그인 후 발급받은 JWT 토큰을 로컬스토리지에 저장하는 프론트엔드 UI 및 API 연동 모듈을 구현합니다.

**Independent Test**: Mock API 또는 백엔드 API를 로컬 기동하고, 회원가입 화면에서 필수 정보를 입력하여 가입 성공 후, 로그인 화면에서 자격 증명을 전송하여 로컬스토리지에 토큰 세션이 생성됨을 확인합니다.

### Tests for User Story 1 (TDD) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T006 [P] [US1] frontend/src/__tests__/components/auth/RegisterView.spec.js 경로에 이름(닉네임), 이메일, 패스워드 입력 폼 렌더링 및 유효성 검사 TDD 테스트 구현
- [X] T007 [P] [US1] frontend/src/__tests__/components/auth/LoginView.spec.js 경로에 이메일 및 패스워드 입력 폼 렌더링과 전송 이벤트 TDD 테스트 구현

### Implementation for User Story 1

- [X] T008 [P] [US1] frontend/src/services/authService.js 경로에 Axios/Fetch 기반 회원가입/로그인 API 호출 및 LocalStorage 토큰 보존 관리 로직 구현
- [X] T009 [US1] frontend/src/components/auth/RegisterView.vue 경로에 이름(닉네임) 입력을 필수로 포함하는 회원가입 마크업 및 유효성 검사 컴포넌트 구현 (Tailwind CSS 적용)
- [X] T010 [US1] frontend/src/components/auth/LoginView.vue 경로에 이메일 및 비밀번호를 기반으로 API 통신을 수행하는 로그인 컴포넌트 구현 (Tailwind CSS 적용)
- [X] T011 [US1] RegisterView.spec.js 및 LoginView.spec.js Vitest 테스트를 가동하여 100% 통과 완료 증명

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - 인증 토큰 기반 라우터 가드 및 상태 체크 (Priority: P2)

**Goal**: 라우터 가드를 구현하여 로그인 상태를 실시간 체크하고, 비인가 사용자의 대시보드 진입 차단 및 로그인 완료된 사용자의 로그인/회원가입 폼 역접근을 완벽히 방제합니다.

**Independent Test**: 토큰이 없는 상태에서 주소창에 `/dashboard`를 입력하여 로그인 화면으로 강제 이동하고, 토큰이 있는 상태에서 `/login` 접근 시 `/dashboard`로 즉시 튕겨 나가는지 확인합니다.

### Tests for User Story 2 (TDD) ⚠️

- [X] T012 [P] [US2] frontend/src/__tests__/router/index.spec.js 경로에 로그인 인증 세션 유무 및 토큰 수명에 따른 라우터 리다이렉트 가드 TDD 테스트 구현

### Implementation for User Story 2

- [X] T013 [US2] frontend/src/router/index.js 경로에 라우트 경로 정의 및 beforeEach 네비게이션 가드 구현
- [X] T014 [US2] frontend/src/components/DashboardView.vue 경로에 로그인한 사용자 닉네임 환영사 표시 및 로컬 토큰 세션을 안전하게 폐기(LocalStorage 클리어)하고 로그아웃을 처리하는 대시보드 메인 UI 및 로그아웃 버튼 구현 (Tailwind CSS 적용)
- [X] T015 [US2] frontend/src/main.js 및 frontend/src/App.vue 경로에 라우터 결합 및 라우트 뷰 마운트 통합
- [X] T016 [US2] index.spec.js Vitest 라우터 가드 테스트를 가동하여 100% 통과 완료 증명

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - 모바일 사용자 전용 클라이언트 사이드 이미지 리사이징 (Priority: P3)

**Goal**: HTML5 Canvas API를 내장하여 이미지 업로드 API 발송 직전에 긴 축을 1000px로 축소하고 JPEG 80% 압축 처리를 실행하여 무선 네트워크 트래픽을 90% 이상 절감합니다.

**Independent Test**: 5MB 크기의 고해상도 이미지를 업로드 영역에 드롭했을 때, 서버 API 전송 전용 바이너리 폼 데이터의 긴 축 해상도가 1000px로 스케일다운되고 용량이 500KB 이하로 감소함을 확인합니다.

### Tests for User Story 3 (TDD) ⚠️

- [X] T017 [P] [US3] frontend/src/__tests__/utils/imageResizer.spec.js 경로에 긴 축 1000px 초과 이미지 스케일다운 비율 검증, JPEG 일괄 변환 및 80% 퀄리티 압축 검증, 1000px 이하 저해상도 이미지 원본 크기 바이패스 검증 TDD 테스트 구현

### Implementation for User Story 3

- [X] T018 [P] [US3] frontend/src/utils/imageResizer.js 경로에 HTML5 Canvas API 및 FileReader 기반의 이미지 리사이징 및 JPEG 80% 인코딩 압축 유틸리티 구현
- [X] T019 [US3] frontend/src/components/DashboardView.vue 경로(또는 기존 영수증 업로드 컴포넌트)의 파일 수집 핸들러 초입에 imageResizer 전처리 모듈을 통합하여 API 전송 직전에 스케일다운된 JPEG 파일 객체로 교체하도록 통합
- [X] T020 [US3] imageResizer.spec.js Vitest 이미지 처리 유틸 테스트를 가동하여 100% 통과 완료 증명

**Checkpoint**: All user stories should now be independently functional

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T021 [P] frontend 디렉토리 소스 코드 린팅 및 스타일 가이드 정합성 검증
- [X] T022 docs/project_plan.md 및 README.md 경로에 로그인 라우터 가드 및 모바일 이미지 압축 기능 탑재 관련 명세서 업데이트
- [X] T023 모바일 화면 뷰포트에서 최종 통합 UI 상태 점검 및 예외적인 업로드 중단 복구 팝업 확인

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- TDD 방식에 따라 테스트 명세 구현이 개발부 구현보다 무조건 선행되어 통과 실패(Fail)를 보장해야 합니다.
- API 통신 서비스 로직이 화면 UI 뷰 로직보다 먼저 구현 및 검증되어야 합니다.

### Parallel Opportunities

- Setup 페이즈의 [P] 표시 작업들은 병렬 가동이 가능합니다.
- Foundational 페이즈가 마감되면 US1, US2, US3 각 페이즈는 완벽히 다른 파일들을 편집하므로 병렬 개발을 즉시 개시할 수 있습니다.

---

## Parallel Example: User Story 1

```bash
# Launch User Story 1 Test Tasks in parallel:
Task: frontend/src/__tests__/components/auth/RegisterView.spec.js 테스트 구현
Task: frontend/src/__tests__/components/auth/LoginView.spec.js 테스트 구현

# Launch User Story 1 Implementation Tasks in parallel:
Task: frontend/src/services/authService.js API 연동 서비스 구현
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Setup 단계 완료 (T001 ~ T003)
2. Foundational 인프라 유효성 체크 완료 (T004 ~ T005)
3. User Story 1 TDD 테스트 빌드 후 실패 확인 (T006 ~ T007)
4. User Story 1 비즈니스 로직 및 컴포넌트 렌더링 완료 (T008 ~ T010)
5. **STOP and VALIDATE**: T011 테스트 수행으로 유효성 증명 및 MVP 1단계 배포

---

## Notes

- [P] 표시가 부여된 태스크는 파일 충돌이 발생하지 않고 종속성이 없어 독립 개발이 가능함을 보장합니다.
- 각 사용자 스토리 페이즈 완료 시점마다 주도적으로 독립 테스트 시나리오를 활용해 동작의 무결성을 검증하고 커밋을 완료하십시오.
