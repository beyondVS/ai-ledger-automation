# Implementation Plan: Database Migration and Unique Constraints

**Branch**: `003-apply-db-unique-constraints` | **Date**: 2026-05-29 | **Spec**: [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/003-apply-db-unique-constraints/spec.md)

**Input**: Feature specification from `/specs/003-apply-db-unique-constraints/spec.md`

## Summary

본 계획은 데이터베이스 마이그레이션 도구(Django Migrations) 환경을 로컬 인프라와 원자적으로 연동하고, 2주차 중복 적재 유효성 가이드라인을 완수하기 위해 각 모델(`Ledger`, `UserPushSubscription` 등) 정의 단에 최신 권장 규격인 `models.UniqueConstraint`를 통한 복합 고유 제약조건을 장착하는 설계를 다룹니다. 또한, 사업자등록번호 결락(null) 시 고유성 충돌 방어 우회가 발생하는 현상을 물리 차단하기 위해 기본 폴백 값 정책(`'0000000000'`)을 유기적으로 결합합니다.

## Technical Context

**Language/Version**: Python >=3.12 (프로젝트 표준 준수)

**Primary Dependencies**: django>=6.0.5, django-environ>=0.13.0, psycopg[binary]>=3.3.4 (C-가속 psycopg3 드라이버 연동)

**Storage**: PostgreSQL 18-alpine

**Testing**: pytest>=9.0.3, pytest-django>=4.12.0

**Target Platform**: Docker Compose / Linux server / Windows Local Development

**Project Type**: web-service (Django REST Framework 백엔드)

**Performance Goals**: SC-003: 로컬 DB 재생성 및 마이그레이션 일제 기동 처리 시간 2초 이내.

**Constraints**: Supabase DB Connection Pool 최대 8개 한계(api: 5, worker: 3) 수호. 중복 유효성 차단 및 FailedTask DLQ 격리 로깅.

**Scale/Scope**: 3개 신규 앱(`accounts`, `ledgers`, `tasks`) 내 복합 고유 제약조건 장착 및 마이그레이션 멱등성 보장.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **원칙 I. 데이터 무결성 및 원자성 트랜잭션 최우선**: `UNIQUE (user_id, vendor_registration_number, transaction_date, total_amount)` 복합 고유 제약조건을 데이터베이스 테이블 레이어에 `UniqueConstraint`를 활용해 강력하게 인덱스 강제 적용.
- **원칙 VI. 크로스 플랫폼 대칭 툴링 및 문서 동기화**: Windows(PowerShell, `.ps1`) 및 macOS/Linux(Bash, `.sh`) 양대 실행 대역 모두에서 동일한 가동 멱등성을 지닌 이중 스크립트 배포 원칙 고수.
- **원칙 VII. 선언적 의존성 및 uv 패키지 격리 수호**: `pyproject.toml` 및 `uv.lock`을 통해 백엔드의 파이썬 의존성을 프로젝트 수준으로 격리하고 선언적으로 제어.

*판정: 모든 헌법 조항을 100% 무결하게 준수함 (Pass).*

## Project Structure

### Documentation (this feature)

```text
specs/003-apply-db-unique-constraints/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── checklists/          # Phase 0 spec validation quality checklist
│   └── requirements.md
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── model_contracts.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── apps/
│   │   ├── accounts/
│   │   │   ├── migrations/
│   │   │   │   └── 0001_initial.py
│   │   │   └── models.py
│   │   ├── ledgers/
│   │   │   ├── migrations/
│   │   │   │   └── 0001_initial.py
│   │   │   ├── models.py
│   │   │   └── services.py
│   │   └── tasks/
│   │       ├── migrations/
│   │       │   └── 0001_initial.py
│   │       └── models.py
│   ├── config/
│   │   ├── settings.py
│   │   └── asgi.py
│   └── manage.py
└── tests/
    └── unit/
        └── models/
            ├── test_ledger_atomic.py
            ├── test_ledger_duplicate.py
            ├── test_merchant_template.py
            └── test_user.py
```

**Structure Decision**: Web application backend (Option 2) 구조를 채택하며, 백엔드 코어 디렉토리 레이아웃(`backend/src/apps/`)과 테스트 스위트 구조를 완벽하게 유지합니다.

## Complexity Tracking

*GATE: No violations identified.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| N/A | N/A | N/A |
