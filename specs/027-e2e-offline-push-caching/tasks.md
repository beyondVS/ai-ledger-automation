# Tasks: 비동기 워커 알림 소비 태스크 오프라인 수신 단말 E2E 모바일 푸시 알림 도달 및 디바이스 캐싱 데이터 무결 테스트 완료

**Input**: Design documents from `/specs/027-e2e-offline-push-caching/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/api.md

**Tests**: TDD(테스트 주도 개발) 요구에 따라, 각 구현 단계에 앞서 테스트 코드를 먼저 작성하여 실패를 확인한 후 실제 기능을 구현하는 태스크 흐름을 엄격하게 반영하였습니다.

**Organization**: 각 작업은 사용자 스토리별로 그룹화되어 독립적인 개발 및 테스트, MVP 증분 배포가 가능하도록 조직화되었습니다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 처리 가능 (대상 파일이 서로 다르고 다른 작업에 블로킹되지 않음)
- **[Story]**: 매핑되는 사용자 스토리 식별자 (예: [US1], [US2], [US3])
- 파일 설명 및 코드 구현 시 정확한 경로를 반드시 포함합니다.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 프로젝트 기초 뼈대 구조 및 테스트 검증용 Playwright 환경 확인

- [ ] T001 `specs/027-e2e-offline-push-caching/` 디렉토리에 필요한 테스트 사양 구조 및 퀵스타트 명세 확인
- [ ] T002 `frontend/package.json`에 Playwright 및 모바일 오프라인 에뮬레이션 테스트를 위한 의존성 모듈 설치 및 셋업 확인
- [ ] T003 [P] 백엔드 및 프론트엔드 로컬 린터(Ruff, ESLint) 및 git pre-commit 자동화 품질 가드 동작 여부 사전 확인

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 사용자 스토리의 기반이 되는 DB 컬럼 상태, 서비스 워커 기본 틀 및 IndexedDB 기초 셋업

**⚠️ CRITICAL**: 이 페이즈의 모든 핵심 인프라 구현이 완료되기 전까지는 개별 사용자 스토리 구현을 진행할 수 없습니다.

- [ ] T004 백엔드 Django `backend/src/models/notification.py` 경로에서 알림의 수신 상태 관리를 위해 `NotificationLog` 모델에 `DELIVERED` 상태를 지원하도록 보완하고 마이그레이션 코드 생성 및 반영
- [ ] T005 [P] 프론트엔드 `frontend/src/services/idb.js` 경로에 IndexedDB 데이터베이스(`ai-ledger-notifications`) 및 수신 알림 테이블(`notifications`) 초기 셋업용 영속 적재 래퍼 인터페이스 코딩
- [ ] T006 [P] 프론트엔드 서비스 워커 `frontend/public/sw.js` 경로의 fetch 이벤트 처리기 내에 크롬 확장 프로그램이 유발하는 `chrome-extension://` 등 비-HTTP 요청의 간섭을 차단하고 바이패스하는 린팅 예외 방어 로직 추가
- [ ] T007 프론트엔드 `frontend/playwright.config.js` 경로에 모바일 오프라인 모드 E2E 테스트 기동을 위한 Playwright 브라우저 및 네트워크 모킹 글로벌 설정 구성

**Checkpoint**: Foundation ready - 이제 사용자 스토리 단위로 병렬/순차 테스트 작성 및 구현에 진입할 수 있습니다.

---

## Phase 3: User Story 1 - 오프라인 단말의 웹 푸시 알림 지연 도달 검증 (Priority: P1) 🎯 MVP

**Goal**: 오프라인 상태 단말이 온라인 복귀 시, FCM/APNs 대기 큐에 적재되어 있던 푸시 알림이 유실 없이 5초 이내에 도달 및 노출되는지 검증

**Independent Test**: 단말 네트워크를 오프라인으로 끈 후 백엔드에서 푸시 발송 ➔ 온라인 복구 ➔ 서비스 워커가 5초 이내에 푸시를 도달 수신하여 화면에 알림이 표시됨을 확인

### Tests for User Story 1 (TDD 우선) ⚠️

- [ ] T008 [P] [US1] `frontend/tests/e2e/offline-push.spec.js` 경로에 오프라인 단말의 온라인 복귀 후 지연 푸시 도달을 검증하는 Playwright E2E 테스트 코드 작성 (구현 전 실행하여 테스트 실패 확인)
- [ ] T009 [P] [US1] `backend/tests/integration/test_notifications.py` 경로에 Celery 비동기 알림 소비 워커의 외부 푸시 연동 상태를 확인하는 통합 테스트 코드 작성 (구현 전 실행하여 테스트 실패 확인)

### Implementation for User Story 1

- [ ] T010 [US1] 백엔드 `backend/src/tasks/notification_tasks.py` 경로에 Celery 비동기 워커가 외부 푸시 서비스로 메시지를 안전하게 디스패치하는 백그라운드 소비 태스크 구현 및 예외 로직 적용
- [ ] T011 [US1] 프론트엔드 서비스 워커 `frontend/public/sw.js` 경로에 `push` 이벤트 수신 리스너를 구현하여 백그라운드에서 지연 도달한 알림을 감지하고 Notification API를 통해 최종 사용자 화면에 노출하는 핸들러 코딩
- [ ] T012 [US1] T008 및 T009에서 작성한 테스트 코드를 재구동하여 백엔드 발송과 프론트엔드 오프라인 복귀 도달 E2E 정합성 테스트가 100% 성공 완료됨을 증명

**Checkpoint**: 이 시점에서 오프라인 단말 복귀 시의 지연 알림 도달 MVP 기능이 완벽하게 동작하며 독립적으로 테스트 완료됩니다.

---

## Phase 4: User Story 2 - 수신 알림의 디바이스 로컬 캐싱 및 백엔드 로그 무결성 대조 검증 (Priority: P2)

**Goal**: 단말에 도달한 알림이 IndexedDB 로컬 캐시에 즉시 저장되고, 백엔드 Acknowledgment 및 Sync API를 거치며 데이터 필드가 100% 일치하도록 보장

**Independent Test**: 알림 수신 즉시 개발자 도구 IndexedDB 저장소 레코드(UUIDv7, title, body, status, timestamp) 대조 ➔ 백엔드 API 응답 결과와 1대1 필드 일치 확인

### Tests for User Story 2 (TDD 우선) ⚠️

- [ ] T013 [P] [US2] `frontend/tests/e2e/offline-push.spec.js` 경로에 도달한 푸시 알림의 로컬 스토리지 필드 무결성과 백엔드 수신 확인 상태를 동시 대조하는 Playwright E2E 검증 테스트 코드 작성 (구현 전 실패 확인)
- [ ] T014 [P] [US2] `backend/tests/integration/test_notifications.py` 경로에 Acknowledgment API(수신확인) 및 Sync API(델타동기화)의 요청/응답 페이로드 규격을 검증하는 Django API 테스트 코드 작성 (구현 전 실패 확인)

### Implementation for User Story 2

- [ ] T015 [P] [US2] 프론트엔드 서비스 워커 `frontend/public/sw.js` 경로 내 푸시 핸들러 하위에 수신된 알림 객체를 `frontend/src/services/idb.js` 인터페이스를 호출해 IndexedDB에 즉시 `CachedNotification` 레코드로 자동 영속 캐싱하는 로직 구현
- [ ] T016 [US2] 백엔드 `backend/src/api/views.py` 경로에 단말 수신 확인을 접수하여 `NotificationLog` 상태를 `DELIVERED`로 변경하는 Acknowledgment POST API 뷰 구현
- [ ] T017 [US2] 백엔드 `backend/src/api/views.py` 경로에 사용자의 최종 동기화 시각 이후의 델타 알림 목록을 반환하는 Sync GET API 뷰 구현
- [ ] T018 [US2] 프론트엔드 대시보드 진입 뷰 `frontend/src/pages/Dashboard.vue` 경로에 사용자의 Document Focus(포그라운드 진입) 이벤트를 바인딩하여 백엔드 Sync API를 호출하고 로컬 캐시를 갱신 및 상태 보정하는 트리거 코딩
- [ ] T019 [US2] T013 및 T014에서 구축한 E2E 및 API 테스트를 구동하여 로컬 IndexedDB 캐시 스키마와 백엔드 API 간의 100% 필드 일치 및 데이터 무결성 검증 통과를 완수

**Checkpoint**: 이 시점에서 수신된 알림의 로컬 영속 캐싱 및 포그라운드 진입 시의 자동 동기화 기능이 완료되어 정합성 무결성이 독립적으로 증명됩니다.

---

## Phase 5: User Story 3 - 네트워크 플래핑 시의 중복 캐싱 방지 및 자동 재동기화 검증 (Priority: P3)

**Goal**: 네트워크 연결 단절 및 재연결이 다중 반복(플래핑)되는 극한 상황에서도 로컬 캐시에 중복 레코드가 쌓이지 않고 멱등성을 보장

**Independent Test**: 동일 알림 ID 전송 중 단말 네트워크 단절/연결을 3회 이상 강제 반복 ➔ IndexedDB 내 동일 ID 레코드가 1개만 유니크하게 존재하는지 확인

### Tests for User Story 3 (TDD 우선) ⚠️

- [ ] T020 [P] [US3] `frontend/tests/e2e/offline-push.spec.js` 경로에 단시간 내 네트워크 플래핑 상황을 에뮬레이션하여 동일 푸시 메시지 수신 시 로컬 캐시의 중복 적재 유무를 확인하는 Playwright 스트레스 테스트 코드 작성 (구현 전 실패 확인)

### Implementation for User Story 3

- [ ] T021 [US3] 프론트엔드 서비스 워커 `frontend/public/sw.js` 경로 내 로컬 캐시 쓰기 루틴에 알림 고유 UUIDv7 키 기준 중복 여부를 먼저 체크하는 멱등성 검사(Upsert 분기) 로직 구현
- [ ] T022 [US3] T020의 플래핑 E2E 테스트를 구동하여 불안정한 네트워크 전환 도중에도 로컬 캐시 오염 및 알림 팝업 중복 노출이 완벽히 방어됨을 확인하고 성공 통과 보장

**Checkpoint**: 이 단계가 완료되면 불안정한 대역폭 환경 하에서의 멱등성 및 중복 방어 무결성 검증이 최종 완료됩니다.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 오래된 알림의 로컬 퍼지 처리, 기계적 린팅 품질 가드 수호 및 문서 실효성 검증

- [ ] T023 [P] 프론트엔드 `frontend/src/services/idb.js` 경로의 IndexedDB 유틸리티 하위에 최근 30일 초과 혹은 누적 100개 한도를 벗어나는 오래된 캐시 데이터를 로컬 저장소에서 자동으로 제거(Purge)하는 가비지 컬렉션 함수 구현
- [ ] T024 [P] 기기 오프라인 기획 문서인 `quickstart.md`에 기재된 모든 로컬 컴포즈 실행 흐름을 최종 재시뮬레이션하여 문서 가독성 및 정확성 수호
- [ ] T025 `uv run ruff check` 및 `npm run lint` 포맷팅 점검 툴을 실행하여 전체 코드 수정본에 대해 헌법 규격의 기계적 린트 통과 보장

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 대기 없이 즉시 시작할 수 있습니다.
- **Foundational (Phase 2)**: Setup 완료 후 실행되며, **모든 사용자 스토리(US1, US2, US3) 구현을 차단**합니다.
- **User Stories (Phase 3 ~ 5)**: Foundational 페이즈가 100% 완료된 시점부터 진행됩니다. 
  - 각 스토리는 우선순위 순서(P1 ➔ P2 ➔ P3)에 맞게 순차적으로 개발하거나, 리소스가 나뉠 경우 상호 파일 간섭 없이 독립적으로 병렬 개발을 병행할 수 있습니다.
- **Polish (Phase 6)**: 모든 사용자 스토리가 완결되고 통합 검증이 끝난 후 조율 단계로 수행됩니다.

### Within Each User Story
1. TDD 원칙에 따라 **테스트 코드를 먼저 작성**하고 테스트가 정상적으로 실패함을 확인합니다.
2. 이후 모델(Database/IndexedDB) ➔ 비즈니스 서비스 ➔ API 뷰 ➔ UI 통합 순으로 점진 코딩합니다.
3. 해당 사용자 스토리의 모든 태스크가 끝나고 독립 검증 테스트를 정상 통과한 후 다음 순위 스토리로 전이합니다.

### Parallel Opportunities
- **T005** (IndexedDB 인터페이스 코딩)와 **T006** (서비스 워커 확장 예외 필터링)은 대상 파일이 격리되어 있어 Phase 2 내에서 동시에 병렬 처리가 가능합니다.
- 각 사용자 스토리 페이즈 내의 TDD용 백엔드 테스트 및 프론트엔드 E2E 테스트 뼈대 작성 작업(`[P]` 마커 포함) 역시 초기 설계 단계에서 동시에 병렬 구축이 가능합니다.

---

## Parallel Example: User Story 2

```bash
# User Story 2 TDD 테스트 코드를 병렬로 먼저 작성:
Task A: "Playwright E2E 필드 무결성 검증 테스트 작성 in frontend/tests/e2e/offline-push.spec.js"
Task B: "Sync/Acknowledgment API 페이로드 검증 테스트 작성 in backend/tests/integration/test_notifications.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. **Phase 1 (Setup)** 및 **Phase 2 (Foundational)** 완수.
2. **Phase 3 (User Story 1)**의 테스트 및 구현을 완료하여 오프라인 복귀 즉시 지연 푸시가 수신(5초 이내)되는 MVP 단계 실현.
3. **중단 및 확인**: Playwright E2E 테스트로 MVP가 완벽히 독립 구동되는지 검증한 후 다음 릴리즈(US2)로 증분 확장.

### Incremental Delivery
- **증분 1 (MVP)**: 오프라인 지연 도달 및 서비스 워커 가로채기 통과.
- **증분 2 (무결 캐싱)**: 수신 데이터의 IndexedDB 적재, Acknowledgment 확인 상태 변경, 앱 실행 시 자동 델타 동기화 완료.
- **증분 3 (멱등 플래핑 방어)**: 네트워크 플래핑 시 멱등키 기반 캐시 오염 100% 방지.
- **증분 4 (최적화)**: 로컬 캐시 30일/100개 자동 퍼지 가비지 컬렉터 가동.
