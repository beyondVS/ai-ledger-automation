# Implementation Plan: Celery 비동기 작업 큐 및 Docker 통합 개발 환경 구축

**Branch**: `016-setup-celery-queue` | **Date**: 2026-06-09 | **Spec**: [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/016-setup-celery-queue/spec.md)

**Input**: Feature specification from `/specs/016-setup-celery-queue/spec.md`

## Summary
메인 API 서버에 집중되던 동기식 파일 수집 및 AI 분석 파이프라인을 Celery 비동기 작업 큐와 Redis 메시지 브로커 기반의 아키텍처로 전격 전환합니다. Supabase 인프라를 고려하여 최대 DB 커넥션 풀을 api_server 5개, async_worker 3개로 엄격히 규제하며, 백엔드(Django), Celery, 프론트엔드(Vue3/Vite) 전체 개발 환경을 Dockerizing하고 로컬 바인드 마운트를 설정하여 소스 수정 시 실시간 핫 리로딩되는 통합 개발 환경을 구축합니다.

## Technical Context

**Language/Version**: Python 3.11, JavaScript (ES6+), HTML5

**Primary Dependencies**: Django (4.2+), djangorestframework, Celery (5.3+), redis (4.6+), Vue (3.x), Vite (4.x+), watchfiles

**Storage**: PostgreSQL (v18+), Redis (v7-alpine)

**Testing**: pytest (pytest-django), Django TestCase (hybrid test strategy)

**Target Platform**: Linux server (inside Docker), Web browser (PWA)

**Project Type**: web-service (frontend + backend detected)

**Performance Goals**: 95% of upload requests responded with HTTP 202 under 500ms

**Constraints**: Database connection pool limit: api_server <= 5, async_worker <= 3, total <= 8

**Scale/Scope**: 50 concurrent invoice uploads queued and processed without database connection timeout or failure

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Gate 1: 데이터 무결성 및 원자성 트랜잭션 최우선**
  - 가계부 적재 연산은 단일 `transaction.atomic()` 세션 내에서 처리하며 예외 시 롤백됨을 보장합니다.
  - 중복 입력 방지를 위한 `UNIQUE (user_id, vendor_registration_number, transaction_date, total_amount)` 제약조건을 DB 스키마에 엄격히 명시합니다. (준수 상태: Pass)
- **Gate 2: 비동기 큐 전환 및 자원 점유 최적화**
  - 파일 리사이징(Pillow) 및 외부 LLM API 호출과 같이 연산이 무겁고 Latency가 긴 작업을 Celery 비동기 독립 워커 프로세스로 격리 가동합니다.
  - API 서버는 즉시 HTTP 202 Accepted 및 job_id를 응답하여 블로킹 병목을 방지합니다.
  - DB 커넥션 풀을 api_server 5개, async_worker 3개, 합산 8개 이하로 강제 튜닝합니다. (준수 상태: Pass)
- **Gate 3: 크로스 플랫폼 대칭 툴링 및 문서 동기화 수호**
  - 개발망 기동 및 DB 관리를 위한 관리 도구 스크립트는 `scripts/`에 배치하고 PowerShell(`.ps1`) 및 Bash(`.sh`) 양대 포맷을 대칭형으로 지원합니다.
  - `.specify/` 내부에는 임의의 커스텀 관리 도구가 혼입되지 않도록 정결성을 유지합니다. (준수 상태: Pass)
- **Gate 4: 선언적 의존성 및 uv 패키지 격리 수호**
  - 백엔드 파이썬 패키지는 `pyproject.toml` 및 `uv.lock`에 선언적으로 완전 명세 관리하며 가상 가동 환경(`.venv`)을 동기화합니다. (준수 상태: Pass)
- **Gate 5: pytest 및 Django TestCase 하이브리드 테스트 수호**
  - DB 및 ORM 조회가 필요한 테스트는 `django.test.TestCase` + `setUpTestData`를 사용하여 속도를 향상시킵니다.
  - DB 조회가 필요 없는 유틸리티는 `unittest.TestCase`를 활용해 기동 오버헤드를 배제합니다. (준수 상태: Pass)

**Gate Evaluation**: Pass (위반 항목 없음, 헌법의 모든 설계 제약을 만족함)

## Project Structure

### Documentation (this feature)

```text
specs/016-setup-celery-queue/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/
    └── task-api.md      # Phase 1 output
```

### Source Code (repository root)

```text
backend/
├── config/              # Django settings.py (DB 풀 제한 등)
├── api/                 # Django API Server & Views
├── tasks/               # Celery Tasks (Pillow, LLM, DB Write)
└── tests/               # pytest & Django TestCase

frontend/
├── src/
│   ├── components/      # Vue Components (Upload modal)
│   ├── views/           # Dashboard Polling
│   └── vite.config.js   # usePolling watch 설정
└── tests/
```

**Structure Decision**: Option 2: Web application 구조를 채택하여 백엔드(Django/Celery) 및 프론트엔드(Vue3/Vite) 모노레포 아키텍처로 가져가며, 각각 로컬 볼륨 마운트 연동에 따라 핫 리로딩하도록 독립 실행합니다.
