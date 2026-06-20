# Implementation Plan: 비동기 워커 알림 소비 태스크 오프라인 수신 단말 E2E 모바일 푸시 알림 도달 및 디바이스 캐싱 데이터 무결 테스트 완료

**Branch**: `027-e2e-offline-push-caching` | **Date**: 2026-06-21 | **Spec**: [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/027-e2e-offline-push-caching/spec.md)

**Input**: Feature specification from `/specs/027-e2e-offline-push-caching/spec.md`

## Summary

비동기 큐(Celery)에서 소비된 웹 푸시 알림이 오프라인 단말이 온라인으로 복귀했을 때 누락 없이 도달(5초 이내)함을 보장하고, 단말의 IndexedDB 로컬 캐시(최근 30일 이내 최신 100개 제한)에 멱등하게 적재되며, 앱 포그라운드 활성화 시 백엔드 상태와의 동기화를 수행하여 데이터 무결성을 유지하는 E2E 테스트 아키텍처를 구축합니다. 검증을 위해 Playwright 오프라인 에뮬레이션 모드를 결합한 자동화 E2E 테스트를 수립합니다.

## Technical Context

**Language/Version**: Python 3.13 | JavaScript (ES6+) / Vue.js 3

**Primary Dependencies**: Django REST Framework (DRF), Celery, Playwright, Vue 3, Service Worker (sw.js), webpush-api

**Storage**: PostgreSQL v18 (backend log), IndexedDB (device cache)

**Testing**: pytest (backend unit/integration tests), Playwright (E2E push/offline test)

**Target Platform**: Linux server (Docker Compose environment), Modern Web Browsers (Secure Context HTTP/HTTPS)

**Project Type**: Web application (Frontend + Backend)

**Performance Goals**: 오프라인 단말의 온라인 전환 후 지연 푸시 수신 5초 이내, 수동 로컬 캐시 동기화 완료 1.5초 이내

**Constraints**: 로컬 캐시 30일 이내 및 최신 100개 보존(FR-006), 앱 포그라운드 진입 시 1회 API 동기화(FR-007), 1000건 테스트 시 불일치 0%(SC-003)

**Scale/Scope**: 단일 단말 기준 E2E 무결성 검증 (다중 단말 실시간 동기화 제외)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Gate 1 (V. PWA & HTTPS/JWT 보안 환경 강제)**: 서비스 워커(`sw.js`) 구현 시 크롬 확장 프로그램의 비-HTTP 요청으로 인한 `TypeError: Request scheme is unsupported`를 방지하기 위해, fetch 리스너 시작부에 http/https 외의 요청을 사전 차단 및 우회하는 필터링 방어 로직이 정상 작동하고 있는지 확인. (통과 예정)
- **Gate 2 (VIII. pytest 및 Django TestCase 하이브리드 테스트 수호)**: DB 연계 백엔드 테스트는 `django.test.TestCase`를 상속받고 `setUpTestData(cls)`를 사용하여 가동 오버헤드를 극소화하는가? 데이터베이스 조회가 없는 유틸리티는 `unittest.TestCase`를 상속받아 장고 부트스트랩을 우회하는가? 프로덕션 코드에 테스트용 임의 분기가 부재한가? (준수 확인)
- **Gate 3 (VI. 크로스 플랫폼 대칭 툴링 및 문서 동기화 수호)**: 인프라/테스트 관리 도구는 ps1/sh 대칭형 스크립트를 동등 제공하고 `scripts/` 디렉토리에 격리 배치하는가? (준수 확인)
- **Gate 4 (VII. 선언적 의존성 및 uv 패키지 격리 수호)**: 추가 패키지는 `pyproject.toml`에 선언적으로 관리하며 가상환경 Parity를 달성하는가? (준수 확인)

## Project Structure

### Documentation (this feature)

```text
specs/027-e2e-offline-push-caching/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── api.md           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   └── notification.py  # NotificationLog
│   ├── api/
│   │   └── views.py         # Acknowledgment API, Sync API
│   └── services/
└── tests/
    └── integration/
        └── test_notifications.py  # django.test.TestCase 기반 Acknowledgment/Sync 비즈니스 로직 테스트

frontend/
├── src/
│   ├── services/
│   │   └── idb.js           # IndexedDB IndexedDB 캐싱 래퍼 서비스
│   └── pages/
│       └── Dashboard.vue    # 포그라운드 진입 시 동기화 트리거
├── public/
│   └── sw.js                # Push 이벤트 리스너, IndexedDB 적재, 크롬 확장 예외 필터링 포함
└── tests/
    └── e2e/
        └── offline-push.spec.js  # Playwright 기반 오프라인 모드 E2E 테스트
```

**Structure Decision**: 프론트엔드와 백엔드가 결합된 웹 애플리케이션 구조이므로 backend/ src 구조와 frontend/ src 구조를 동시에 선택하여 IndexedDB 캐싱, 서비스 워커, API 뷰, Playwright E2E 테스트를 대칭적으로 배치합니다.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None      | N/A        | N/A                                 |
