# Tasks: PWA Install Banner & iOS A2HS Tooltip

**Input**: Design documents from `/specs/025-pwa-install-banner/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/ui-contracts.md, quickstart.md

**Tests**: TDD (Test-Driven Development) is requested. Unit tests using Vitest must be implemented FIRST and verified to fail before the corresponding component logic is coded.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure creation

- [ ] T001 `frontend/src/components/PwaInstallBanner.vue` 경로에 신규 PWA 설치 유도 제어 컴포넌트 기본 스켈레톤 파일 생성
- [ ] T002 [P] `frontend/src/__tests__/PwaInstallBanner.spec.js` 경로에 Vitest 유닛 테스트용 테스트 스켈레톤 파일 생성

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Helper utility logic for platform detection and storage check

- [ ] T003 `frontend/src/utils/pwa-helper.js` 경로에 PWA 브라우저 환경 판단, Standalone 모드 식별, LocalStorage 쿨다운 확인을 전담할 유틸리티 파일 생성
- [ ] T004 [P] `frontend/public/sw.js` 및 `frontend/src/registerServiceWorker.js`를 확인하여 PWA 웹 앱의 설치 조건 충족에 필요한 매니페스트와 서비스 워커 세팅 상태 점검

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Android 및 지원 브라우저용 커스텀 설치 배너 제어 (Priority: P1) 🎯 MVP

**Goal**: Android/Chromium 환경에서 beforeinstallprompt 이벤트를 차단하고 3초 지연 후 커스텀 하단 배너를 노출하여 설치를 유도하며, 닫기 시 7일간 노출 차단

**Independent Test**: Android Chrome 환경을 모의하여 접속 시 브라우저 기본 설치 팝업이 차단되고 3초 후 하단 배너 노출 검증. 설치 클릭 시 브라우저 기본 설치 창 노출, 닫기 시 7일 차단 검증.

### Tests for User Story 1 (TDD - Required First) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T005 [P] [US1] `frontend/src/__tests__/PwaInstallBanner.spec.js` 경로에 `beforeinstallprompt` 이벤트 가로채기(preventDefault) 및 커스텀 배너 노출 플래그 동작을 검증하는 실패하는 단위 테스트 작성
- [ ] T006 [P] [US1] `frontend/src/__tests__/PwaInstallBanner.spec.js` 경로에 "설치" 버튼 클릭 시 캡처된 프롬프트 API(.prompt())가 호출되는지 및 "닫기" 클릭 시 로컬 저장소 쿨다운(7일) 상태가 기록되는지 검증하는 실패하는 단위 테스트 작성

### Implementation for User Story 1

- [ ] T007 [P] [US1] `frontend/src/utils/pwa-helper.js` 경로에 beforeinstallprompt 지원 여부 및 LocalStorage 쿨다운 만료(7일 차이 대조) 판별 헬퍼 함수 구현 (T005, T006 테스트 대상)
- [ ] T008 [US1] `frontend/src/components/PwaInstallBanner.vue` 경로에 Android용 하단 고정식 가로 배너 UI(앱 타이틀, 설치 권장 문구, "설치하기" 버튼, "닫기" X 아이콘) 마크업 및 3초 지연 타이머(`setTimeout`) 연동 구현
- [ ] T009 [US1] `frontend/src/components/PwaInstallBanner.vue` 경로에 beforeinstallprompt 이벤트 캡처 바인딩, 설치 실행 시 `prompt()` 호출 및 닫기 클릭 시 7일 쿨다운 저장 연동 구현

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently (Vitest US1 tests pass)

---

## Phase 4: User Story 2 - iOS Safari 전용 홈 화면 추가(A2HS) 수동 안내 툴팁 (Priority: P1)

**Goal**: iOS Safari 환경으로 진입한 미설치 사용자에게 브라우저 하단 공유 메뉴 버튼 위치를 가리키는 뾰족한 데코 꼬리가 있는 말풍선 가이드 툴팁을 3초 지연 노출하고, 닫기 시 7일 차단

**Independent Test**: iOS Safari 유저 에이전트 환경에서 3초 후 하단 중앙에 Safari 안내 툴팁(공유 아이콘 모양 텍스트 포함) 노출 검증. 닫기 클릭 시 7일간 노출 차단 검증.

### Tests for User Story 2 (TDD - Required First) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T010 [P] [US2] `frontend/src/__tests__/PwaInstallBanner.spec.js` 경로에 iOS Safari 기기 감지 시 iOS 수동 안내 툴팁 노출 플래그 활성화를 검증하는 실패하는 단위 테스트 작성
- [ ] T011 [P] [US2] `frontend/src/__tests__/PwaInstallBanner.spec.js` 경로에 툴팁 내 "닫기" 버튼 클릭 시 LocalStorage에 7일 쿨다운 시각이 정상 저장되고 숨김 처리되는지 검증하는 실패하는 단위 테스트 작성

### Implementation for User Story 2

- [ ] T012 [P] [US2] `frontend/src/utils/pwa-helper.js` 경로에 iOS 기기 판별 및 타사 브라우저(Chrome/웹뷰 등)를 배제하고 순정 Safari만 골라내는 유저 에이전트(UA) 판별 헬퍼 함수 구현 (T010 테스트 대상)
- [ ] T013 [US2] `frontend/src/components/PwaInstallBanner.vue` 경로에 iOS Safari 전용 하단 말풍선 가이드 UI(공유 가이드 문구, Apple 표준 공유 아이콘, X 닫기 버튼, 하단 삼각형 꼬리 CSS 데코) 마크업 및 3초 지연 노출 구현
- [ ] T014 [US2] `frontend/src/components/PwaInstallBanner.vue` 경로에 iOS 툴팁의 닫기 핸들러 및 7일 쿨다운 LocalStorage 저장 연동 구현

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently (Vitest US1 & US2 tests pass)

---

## Phase 5: User Story 3 - 이미 설치 완료된 앱 진입 시 배너 및 가이드 제외 (Priority: P2)

**Goal**: 독립 실행 모드(Standalone)로 앱을 사용 중인 사용자에게는 Android 배너와 iOS Safari 툴팁 모두 일절 미노출

**Independent Test**: Standalone 조건(`display-mode: standalone` 매칭 또는 standalone 속성 참)으로 웹 앱 진입 시, 3초 대기 후에도 하단 배너 및 툴팁이 활성화되지 않는지 최종 노출 방어 상태 검증.

### Tests for User Story 3 (TDD - Required First) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T015 [P] [US3] `frontend/src/__tests__/PwaInstallBanner.spec.js` 경로에 브라우저가 Standalone 실행 중일 때 설치 유도 UI 렌더링이 원천 차단(배너/툴팁 노출 생략)되는지 검증하는 실패하는 단위 테스트 작성

### Implementation for User Story 3

- [ ] T016 [P] [US3] `frontend/src/utils/pwa-helper.js` 경로에 `window.navigator.standalone` 속성 및 `window.matchMedia('(display-mode: standalone)')` 미디어를 활용해 독립 모드 여부를 판단하는 헬퍼 함수 구현 (T015 테스트 대상)
- [ ] T017 [US3] `frontend/src/components/PwaInstallBanner.vue` 경로에 컴포넌트 라이프사이클 마운트 진입점 단계에서 standalone 감정 시 3초 타이머 작동 차단 및 UI 은닉 제어 분기 구현

**Checkpoint**: All user stories should now be independently functional (All Vitest unit tests pass)

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Integration into layout, manual E2E validation, and formatting check

- [ ] T018 `frontend/src/App.vue` 경로의 최상위 프론트엔드 엔트리 파일에 `PwaInstallBanner` 컴포넌트를 이식 및 마운트하여 전역 페이지 통합 완료
- [ ] T019 [P] `specs/025-pwa-install-banner/quickstart.md`에 정의된 iOS 디바이스 모의(UserAgent 변경) 및 LocalStorage 쿨다운 시간 변경 디버깅 방식을 적용해 브라우저 E2E 수동 교차 검증 완료
- [ ] T020 [P] `frontend/` 경로에서 `npm run test` 실행으로 Vitest 테스트 스위트 100% 그린 패스 및 pre-commit Ruff/포맷 자동화 린트 최종 검증 완수

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can start immediately
- **Foundational (Phase 2)**: Depends on Setup (Phase 1)
- **User Stories (Phase 3 ~ 5)**: All depend on Foundational (Phase 2) completion
  - 각 스토리는 기본적으로 병렬 구현이 가능하나, TDD 원칙상 단위 테스트(TDD) 작성 ➔ 구현 순서를 엄격히 준수합니다.
- **Polish (Phase 6)**: Depends on all desired user stories being complete

---

## Parallel Example: User Story 1

```bash
# User Story 1의 테스트 작성을 병렬로 먼저 시작 (TDD):
Task: "T005 [P] [US1] frontend/src/__tests__/PwaInstallBanner.spec.js 에 beforeinstallprompt 차단 단위 테스트 구현"
Task: "T006 [P] [US1] frontend/src/__tests__/PwaInstallBanner.spec.js 에 프롬프트 호출 및 쿨다운 저장 단위 테스트 구현"

# User Story 1의 백그라운드 유틸 작성을 병렬로 시작:
Task: "T007 [P] [US1] frontend/src/utils/pwa-helper.js 에 API 및 LocalStorage 쿨다운 판별 헬퍼 구현"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001 ~ T002)
2. Complete Phase 2: Foundational (T003 ~ T004)
3. Complete Phase 3: User Story 1 (T005 ~ T009)
4. **STOP and VALIDATE**: Run `npm run test` and check Android custom banner behavior.
5. Deploy/demo the MVP version.

### Incremental Delivery

1. Setup + Foundational ready.
2. Deliver Android Custom PWA Install Banner (US1) ➔ Deploy MVP.
3. Deliver iOS Safari A2HS Custom Tooltip (US2) ➔ Deploy Incremental Update.
4. Deliver Standalone Exception & Platform Check (US3) ➔ Complete E2E Delivery.
