# Tasks: Server Production SSL & E2E Push Release

**Input**: Design documents from `specs/029-prod-ssl-nginx-push/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: TDD (Test-Driven Development) is requested. Test writing tasks MUST precede implementation tasks in each user story phase, and developers must ensure tests fail before implementing source code.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `-[ ] [ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Configure basic env for production deployment in `.env.example` and `backend/src/config/`
- [x] T002 Sync Python environment dependencies in `backend/pyproject.toml` and verify `pywebpush` package is specified

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 [P] Implement basic Nginx proxy config shell and draft `nginx.conf`
- [x] T004 [P] Configure production `docker-compose.prod.yml` template structure

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Production HTTPS & Security Proxy (Priority: P1) 🎯 MVP

**Goal**: 외부 로드밸런서(Cloudflare/ALB) 포트 80/443만 Nginx 인그레스로 허용하며, 컨테이너 리소스 고정 및 PostgreSQL/Redis 외부 포트 완전 차단하고, HTTP 접속을 HTTPS로 301 리다이렉트하는 프로덕션 인프라 구축.

**Independent Test**: Nginx 리다이렉트 규칙 테스트를 pytest로 기동하여 50ms 이내 301 응답 여부와 보안 포트 검증 통과를 입증함.

### Tests for User Story 1 (TDD) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T005 [P] [US1] Write pytest infrastructure check tests to verify PostgreSQL/Redis host port block and Nginx redirect rules in `backend/tests/test_nginx_infrastructure.py`

### Implementation for User Story 1

- [x] T006 [US1] Finalize `nginx.conf` with HTTPS redirection and subpath API proxy routing logic
- [x] T007 [US1] Complete `docker-compose.prod.yml` with container CPU/memory limit controls and postgres/redis port block configurations under `prod-bridge` network isolation

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Receipt Upload to Web Push E2E Journey (Priority: P1)

**Goal**: 영수증 업로드 처리 결과(성공/실패) 및 예산 한도(80%, 100%) 초과 트리거 시 VAPID 웹푸시 발송을 구현하고, 오프라인 IndexedDB 로컬 멱등 캐싱 및 서비스워커의 수신 확인(ACK)/오프라인 델타 동기화(Sync) 연동 구현.

**Independent Test**: 오프라인 상태 PWA를 가동하고 Celery 비동기 푸시 태스크를 발송한 뒤, 온라인 복귀 시 IndexedDB 적재(중복 차단) 및 백엔드로 ACK가 전달되는 Playwright E2E 테스트 통과.

### Tests for User Story 2 (TDD) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T008 [P] [US2] Write backend DRF tests for PushSubscription CRUD, ACK post, and Sync API endpoints in `backend/tests/test_notifications_api.py`
- [x] T009 [P] [US2] Write unit tests for Celery push dispatch task, retry backoff mechanism, and 404/410 Gone deactivation logic in `backend/tests/test_notifications_tasks.py`
- [x] T010 [P] [US2] Write frontend unit tests to verify IndexedDB schema upsert and garbage collection (with transaction isolation) in `frontend/tests/unit/notifications.spec.js`
- [x] T011 [P] [US2] Write Playwright E2E test verifying offline notification queueing, network reconnection caching, and ACK dispatching in `frontend/tests/e2e/offline-push.spec.js`

### Implementation for User Story 2

- [x] T012 [P] [US2] Create database models for `PushSubscription` and `NotificationLog` (with composite unique key and UUIDv7) in `backend/src/models/push_subscription.py` and `backend/src/models/notification_log.py`
- [x] T013 [US2] Create Celery task logic for VAPID push broadcasting, 3-times exponential backoff retry, and inactive state update for invalid endpoints in `backend/src/tasks/notification_tasks.py`
- [x] T014 [US2] Implement API views for sub/unsub registration, ACK reception, and offline delta sync in `backend/src/views/notifications.py`
- [x] T015 [P] [US2] Implement IndexedDB notification cache store with multi-transaction GC (30-day and 100-limit) in `frontend/src/services/notificationCache.js`
- [x] T016 [US2] Implement PWA Service Worker logic supporting non-HTTP schema bypass filters and background push ACKs in `frontend/src/sw.js`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Production Configuration Testing & Diagnostics (Priority: P2)

**Goal**: 배포 상태의 정상 여부를 확인하기 위해 강제로 테스트 푸시를 트리거하는 CLI 커맨드 및 정식 검증을 가동하는 쉘 스크립트 도구 제공.

**Independent Test**: `./scripts/run_e2e_push_test.ps1`을 가동하여 100% 정상 수신 검증 결과를 확인.

### Tests for User Story 3 (TDD) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T017 [P] [US3] Write test for administrative custom Django command triggering test push in `backend/tests/test_diagnostics_commands.py`

### Implementation for User Story 3

- [x] T018 [US3] Implement custom django-admin cli command triggering VAPID test push in `backend/src/apps/notifications/management/commands/trigger_test_push.py`
- [x] T019 [US3] Write cross-platform CLI verification shell script triggering push tests in `scripts/run_e2e_push_test.ps1` and `scripts/run_e2e_push_test.sh`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T020 [P] Execute `uv run pre-commit run --all-files` and verify `ruff check` passes
- [x] T021 Update `README.md` and check project core documentation sync
- [x] T022 Validate complete deployment test scenario using `quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 2

```bash
# Launch all backend and frontend unit/integration tests for User Story 2:
Task: "Write backend DRF tests for PushSubscription CRUD, ACK post, and Sync API endpoints in backend/tests/test_notifications_api.py"
Task: "Write unit tests for Celery push dispatch task, retry backoff mechanism, and 404/410 Gone deactivation logic in backend/tests/test_notifications_tasks.py"
Task: "Write frontend unit tests to verify IndexedDB schema upsert and garbage collection (with transaction isolation) in frontend/tests/unit/notifications.spec.js"

# Launch all models and independent frontend store implementation for User Story 2:
Task: "Create database models for PushSubscription and NotificationLog (with composite unique key and UUIDv7) in backend/src/models/push_subscription.py and backend/src/models/notification_log.py"
Task: "Implement IndexedDB notification cache store with multi-transaction GC (30-day and 100-limit) in frontend/src/services/notificationCache.js"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
