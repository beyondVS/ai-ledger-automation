# Implementation Plan: Redis In-Memory Store Infrastructure Setup & Celery Worker Role Separation

**Branch**: `015-redis-celery-integration` | **Date**: 2026-06-08 | **Spec**: [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/015-redis-celery-integration/spec.md)

**Input**: Feature specification from `/specs/015-redis-celery-integration/spec.md`

## Summary
시간이 많이 걸리는 영수증 OCR 및 AI 기반 텍스트 분석 작업을 동기 API 흐름에서 분리하여 Celery 백그라운드 워커에서 비동기로 수행하도록 역할을 분리하고, 메시지 브로커로 Redis를 도입하여 다중 컨테이너 Docker Compose 환경으로 통합합니다. 이를 통해 웹 서버 가용성과 UX 즉시 반응성을 극대화합니다.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: Django REST Framework, Celery v5.3+, Redis v7+, litellm.Router, google-genai

**Storage**: PostgreSQL v18+ (가계부 정보 및 작업 내역 보관), Redis v7+ (Celery Broker 및 Result Backend)

**Testing**: pytest (pytest-django), Celery 테스트 전용 워커 환경 가동

**Target Platform**: Linux Server (Docker Compose Multi-container)

**Project Type**: web-service (Django REST Framework Web Server & Celery Background Worker)

**Performance Goals**: 영수증 업로드 요청 Latency 2초 이내 응답 반환, 50건 이상 동시 대량 인입 시 5xx 에러 없이 안정적 처리 보장.

**Constraints**: AWS/Supabase Free tier 환경 고갈을 막기 위한 최대 DB 커넥션 제한 준수 (Gunicorn api_server 5개, Celery async_worker 3개, 총합 8개 이하 통제).

**Scale/Scope**: 로컬 가동을 위한 Docker Compose 다중 컨테이너 통합 (Django, Celery, Redis Broker, Flower Dashboard).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 헌법 조항 | 검증 요건 (Gate Requirements) | 충족 상태 |
| :--- | :--- | :--- |
| **제I조 (원자성 트랜잭션)** | Ledgers 마스터 정보와 LedgerItems 상세 품목 저장은 단일 `transaction.atomic()` 세션 내에서 트랜잭션 무결성을 갖는가 | **PASS** (기존 OCR 분석 처리 롤백 메커니즘을 백그라운드 태스크 내 트랜잭션으로 동일 적용) |
| **제II조 (비동기 및 격리)** | 무거운 연산인 이미지/텍스트 분석을 Celery 비동기 워커로 물리 격리했는가. 총 DB 커넥션 풀 크기가 8개 이하인가 | **PASS** (Gunicorn workers=2, Celery concurrency=2 등으로 제한하여 총 8개 이하 유지 보장) |
| **제VI조 (크로스 플랫폼 대칭)** | 로컬 인프라 구동(Redis, Celery, Flower 기동 포함) 스크립트가 PowerShell(`*.ps1`)과 Bash(`*.sh`) 대칭으로 제공되는가 | **PASS** (scripts/ 디렉토리 하위에 대칭적으로 구현 계획) |
| **제VII조 (선언적 의존성)** | Celery 및 redis 패키지 의존성을 `backend/pyproject.toml`에 선언적으로 추가하고 `uv sync`를 통해 제어하는가 | **PASS** (uv 패키지 관리 표준 엄수) |
| **제VIII조 (하이브리드 테스트)** | DB 접근을 요하는 비동기 태스크 테스트는 `django.test.TestCase`를 상속하여 DB 가속화 혜택을 받는가 | **PASS** (pytest 실행 하위의 Django TestCase 규격 엄수) |

## Project Structure

### Documentation (this feature)

```text
specs/015-redis-celery-integration/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── jobs-api.md      # API endpoint contracts for client polling
│   └── tasks-payload.md # Celery task payload contracts
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml
├── uv.lock
├── src/
│   ├── config/
│   │   ├── celery.py          # Celery 초기화 및 세팅
│   │   ├── settings.py        # Redis/Celery 환경 변수 주입 및 DB 풀 설정
│   │   └── __init__.py        # django 시작 시 celery 앱 로드 설정
│   ├── apps/
│   │   ├── ledgers/
│   │   │   ├── models.py      # LedgerJob 모델 정의
│   │   │   ├── views.py       # 비동기 업로드 접수 및 작업 상태 API 엔드포인트
│   │   │   └── urls.py        # API 라우팅 맵핑
│   │   └── tasks/
│   │       ├── tasks.py       # 비동기 Celery 태스크 (OCR & 텍스트 분석)
│   │       └── client.py      # 향후 SSE/웹소켓 전환을 고려한 알림 발송 추상 클라이언트
│   └── utils/
└── tests/
    └── apps/
        └── ledgers/
            └── test_async_jobs.py # Celery 연동 E2E 통합 테스트

docker-compose.yml             # 다중 컨테이너 통합 환경 (Django, Worker, Redis, Flower)
docker-compose.db.yml          # RDBMS 전용 환경
```

**Structure Decision**: Django 백엔드 내에 Celery 설정(`config/celery.py`)을 추가하고, `ledgers` 앱 하위에 작업 상태 추적 모델 `LedgerJob` 및 폴링용 뷰를 구현합니다. 비동기 작업 자체는 `tasks/tasks.py` 하위의 Celery 태스크가 처리합니다.

## Complexity Tracking

> *Constitution Check 기준 위반 사항이 없으므로 N/A 처리합니다.*
