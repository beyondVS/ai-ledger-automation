# Implementation Plan: Database Integrity & Payment Duplicate Prevention & Category UI Fix

**Branch**: `017-db-integrity-payment-fix` | **Date**: 2026-06-11 | **Spec**: [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/017-db-integrity-payment-fix/spec.md)

**Input**: Feature specification from `/specs/017-db-integrity-payment-fix/spec.md`

## Summary

본 피처는 가계부 결제 데이터 적재의 신뢰성을 극대화하기 위해 백엔드 Django 트랜잭션 원자성을 보장하고, 승인번호 및 1분(60초) 임계값 기반의 결제 중복 판단 알고리즘을 도입합니다. 또한 프론트엔드의 수정 모달(FE-05-B)에서 나타나는 카테고리 데이터 매핑 유실 버그를 완전히 해결하여 데이터 정합성과 사용자 경험을 개선합니다.

## Technical Context

**Language/Version**: Python 3.11 (Backend), JavaScript / ES6+ & Vue.js 3 (Frontend)

**Primary Dependencies**: Django 4.2+, Django REST Framework (DRF), Celery 5.3+, Redis (Broker), Vite, Tailwind CSS (declarative package management with `uv`)

**Storage**: PostgreSQL v18+ (ACID Data, Native UUIDv7 & AIO), JSONB field support

**Testing**: pytest (Runner), Django `django.test.TestCase` (for Database transaction & ORM testing), Python `unittest.TestCase` (for pure logic unit testing)

**Target Platform**: Docker Compose Environment (api-server, postgres-db, redis-broker, async-worker) / Modern Web Browsers (Mobile-first PWA)

**Project Type**: Web application (Backend & Frontend Monorepo)

**Performance Goals**: 지출 대시보드 및 결제 적재 API의 데이터베이스 트랜잭션 롤백 및 중복 우회 연산을 100ms 이내에 완료

**Constraints**: 최대 RDBMS 커넥션 풀 크기 제약 (api-server 컨테이너 5개, Celery worker 3개, 전체 합산 8개 이하 유지)

**Scale/Scope**: 10만 건 이상의 더미 데이터 적재 환경에서 고성능 인덱싱 정합성 유지, 중복 결제 오탐률 0% 달성

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **원자성 보장 (헌법 제I조)**: 마스터(Ledger)와 하위 품목 배열(LedgerItem)의 생성/수정 연산은 단일 `transaction.atomic()` 블록 내에서 처리되는가? → **PASS (예외 발생 시 전격 롤백 설계)**
- **중복 입력 차단 (헌법 제I조)**: DB 테이블 레이어의 복합 고유 제약조건과 연계하여 중복 결제 인입 시 무시(기존 데이터 보존 및 성공 응답 반환) 처리를 구현하는가? → **PASS (get_or_create 및 ignore_conflicts 옵션 활용)**
- **크로스 플랫폼 및 스크립트 배치 (헌법 제VI조)**: 추가되는 스크립트나 도구가 프로젝트 루트의 `scripts/` 디렉토리에 위치하는가? → **PASS (해당 없음, 신규 관리용 외부 스크립트 없음)**
- **하이브리드 테스트 아키텍처 (헌법 제VIII조)**: DB 정합성 검증 테스트는 `django.test.TestCase`를 상속받고 `setUpTestData(cls)`를 사용하는가? 단순 로직 검증은 `unittest.TestCase`를 활용하는가? → **PASS (하이브리드 테스트 원칙 엄수)**

## Project Structure

### Documentation (this feature)

```text
specs/017-db-integrity-payment-fix/
├── plan.md              # This file
├── research.md          # Phase 0 output (Decisions & Rationale)
├── data-model.md        # Phase 1 output (Entities & Rules)
├── quickstart.md        # Phase 1 output (How to test & run)
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── contracts/           # Phase 1 output (API/UI Contracts)
    └── api-contract.md  # API & Component Interface contract
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── ledgers/
│   │   ├── models.py      # Ledger, LedgerItem, Category 모델 정의 및 Constraints
│   │   ├── services.py    # transaction.atomic() 트랜잭션 제어 및 중복 체크 알고리즘
│   │   └── views.py       # DRF API View (중복 시 바이패스 및 200/201 성공 응답 제어)
└── tests/
    ├── integration/
    │   └── test_ledger_transaction.py # transaction.atomic 롤백 및 중복 바이패스 통합 테스트
    └── unit/
        └── test_duplicate_check.py     # 1분 임계값 기반 중복 체크 알고리즘 독립 단위 테스트

frontend/
├── src/
│   ├── components/
│   │   └── LedgerEditModal.vue       # FE-05-B 수정 내역 모달 및 카테고리 셀렉트박스 데이터 바인딩
│   └── services/
│       └── categoryApi.js            # 카테고리 데이터 조회 및 매핑 서비스
```

**Structure Decision**: Monorepo 기반의 Web application (backend/ 및 frontend/ 분리형) 구조를 선택하여, Django 백엔드 내 DB 트랜잭션 고도화와 Vue 3 수정 모달 UI 버그 픽스를 독립적으로 병행 구현합니다.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*(헌법 위반 사항이 없으므로 비워둠)*
