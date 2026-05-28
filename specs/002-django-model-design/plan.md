# Implementation Plan: Django Model Design for AI Ledger

**Branch**: `002-django-model-design` | **Date**: 2026-05-29 | **Spec**: [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/002-django-model-design/spec.md)

**Input**: Feature specification from `/specs/002-django-model-design/spec.md`

## Summary

본 구현 계획은 AI 가계부 자동화 프로젝트의 핵심 데이터 보존 레이어를 수립하기 위한 6대 Django Model(User, Ledger, LedgerItem, MerchantTemplate, FailedTask, UserPushSubscription) 설계를 수립합니다.
강력한 데이터 무결성 보장을 위한 단일 원자적 트랜잭션 적재(`transaction.atomic()`), 동일 영수증의 중복 유입을 예방하는 복합 UNIQUE 제약조건, 가맹점 사업자등록번호 기반 정규식 캐싱 및 우회 바이패스(Bypass) 파서의 오동작 격리 통제, 그리고 PWA 백그라운드 푸시 알림을 위한 VAPID 규격 적재 등의 아키텍처적 요구사항을 설계에 반영합니다.

## Technical Context

**Language/Version**: Python 3.11 (uv 패키지 매니저 기반)

**Primary Dependencies**: Django 5.x, Django REST Framework (DRF), Celery 5.x, Redis (Message Broker & Cache), pytest-django

**Storage**: PostgreSQL v18+ (강력한 ACID 트랜잭션, Native UUIDv7 인덱싱 및 AIO 성능 최적화, 비정형 LLM 파싱 결과 보존을 위한 JSONB 필드 지원)

**Testing**: pytest, pytest-django, django-environ

**Target Platform**: Linux Server / Docker Compose (api_server, postgres_db, redis_broker, async_worker)

**Project Type**: web-service (Django REST Framework API Server & Celery Asynchronous Engine)

**Performance Goals**: 10만 건 이상의 가계부 및 상세 내역 레코드 적재 스트레스 테스트 환경 대응, `EXPLAIN ANALYZE` 쿼리 튜닝을 통해 실시간 지출 대시보드 API 쿼리 응답 시간을 상시 100ms 이내로 방어.

**Constraints**: Supabase Free Plan 등 인프라의 가용한계 극복을 위해, 데이터베이스 최대 커넥션 풀(Connection Pool) 크기를 api_server 최대 5개, Celery async_worker 최대 3개, 전체 합산 8개 이하로 엄격하게 제약 제어.

**Scale/Scope**: 초기 1만 가입자 규모 및 100만 LOC 급 대용량 시계열 트랜잭션 데이터 적재 대응.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

헌법(constitution.md v1.2.0)에 수립된 6대 원칙에 기반하여 설계의 적합성을 평가합니다.

1. **I. 데이터 무결성 및 원자성 트랜잭션 최우선 (Data Integrity & Transaction Atomicity)**
   - **요건**: Ledgers와 LedgerItems의 생성/수정 연산은 단 하나의 `transaction.atomic()` 내에서 실행 및 실패 시 전격 롤백 보장. `UNIQUE (user_id, vendor_registration_number, transaction_date, total_amount)` 복합 UNIQUE 인덱스 적용.
   - **평가**: **[PASS]** Django Model 정의 시 `UniqueConstraint`를 통해 DB 레이어의 복합 유니크 제약을 강제하고, 트랜잭션 처리를 위한 Repository/Service API 설계 계약에 이를 명시하여 정합성을 완벽히 충족함.
2. **II. 비동기 큐 전환 및 자원 점유 최적화 (Asynchronous Processing & Scale Isolation)**
   - **요건**: 무거운 작업 Celery 격리 처리. DB 커넥션 풀 크기 최대 8개 제한 (api_server 5, worker 3).
   - **평가**: **[PASS]** `FailedTask` Dead Letter Queue 모델 도입으로 비동기 예외 격리 적재를 지원하며, Django settings 설정을 통해 커넥션 풀 제약을 완벽히 준수할 수 있는 데이터 모델 메타데이터 스키마를 구성함.
3. **III. 하이브리드 비용 최적화 파이프라인 (Hybrid Bypass for Cost Control)**
   - **요건**: `merchant_templates` 캐시 활용 및 미검증 템플릿(`is_verified: false`) 바이패스 절대 차단.
   - **평가**: **[PASS]** `MerchantTemplate` 모델에 `is_verified` 불리언 플래그를 기본값 `False`로 명확하게 정의하고, 검증 여부에 따른 전용 쿼리 필터 설계를 명시함.
4. **IV. SPF/DKIM 기반 엄격한 보안 메일 수집 (Secure Inbound Email Ingestion)**
   - **요건**: 사용자당 최대 3개의 화이트리스트 메일 발송인 매핑 지원.
   - **평가**: **[PASS]** `User` 모델 내에 최대 3개의 이메일 주소를 화이트리스트 검증 가능하도록 JSONB 형태나 전용 문자열 필드로 관리하는 설계를 수립하여 보안 요건을 완벽히 수용함.
5. **V. Vision-First PWA & HTTPS 보안 환경 강제 (Mobile-first PWA & HTTPS Mandated)**
   - **요건**: VAPID 구독 명세 보존을 위한 구독 정보 스키마 지원.
   - **평가**: **[PASS]** `UserPushSubscription` 스키마 설계를 통해 VAPID v2 스펙을 만족하는 구독 엔드포인트 및 암호화 키 바인딩을 영구 보존할 수 있도록 모델을 설계함.
6. **VI. 크로스 플랫폼 대칭 툴링 및 문서 동기화 수호 (Cross-platform Symmetric Tooling & Autonomous Document Sync)**
   - **요건**: Windows 및 Linux 동등 기동 대칭 툴링 원칙 준수.
   - **평가**: **[PASS]** 향후 마이그레이션 및 DB 초기화 스크립트 작성 시 `manage-db.ps1` 및 `manage-db.sh`를 대칭 구조로 완벽히 제공하도록 명시함.

## Project Structure

### Documentation (this feature)

```text
specs/002-django-model-design/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

이 프로젝트는 Django REST Framework 백엔드와 Vue 3 (PWA) 프론트엔드가 격리 기동되는 하이브리드 아키텍처로 구현되므로 아래의 구조적 레이아웃을 준수합니다.

```text
backend/
├── src/
│   ├── config/              # Django 프로젝트 세팅 및 WSGI/ASGI 설정
│   ├── apps/
│   │   ├── accounts/        # User 및 UserPushSubscription 앱
│   │   │   ├── models.py
│   │   │   └── tests.py
│   │   ├── ledgers/         # Ledger, LedgerItem, MerchantTemplate 앱
│   │   │   ├── models.py
│   │   │   └── tests.py
│   │   └── tasks/           # FailedTask 및 Celery 비동기 작업 관리 앱
│   │       ├── models.py
│   │       └── tests.py
│   └── manage.py
└── tests/
    ├── conftest.py
    └── integration/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/
```

**Structure Decision**: Django REST Framework API 서버와 Vue 3 PWA 프론트엔드 간의 명확한 역할 격리를 위해 **Web application (backend & frontend 분리)** 폴더 구조를 수립하며, 현재의 모델 설계 작업은 주로 `backend/src/apps/` 하위 모듈과 연계됩니다.

## Complexity Tracking

*Gate 검증 결과 헌법적 합의 원칙 및 제약에 대한 정당하지 않은 위반 사항이 전혀 발견되지 않았으므로 해당 내역이 비어 있습니다.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None      | N/A        | N/A                                 |
