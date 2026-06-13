# Implementation Plan: Cost Control Engine Core Implementation

**Branch**: `018-cost-control-engine` | **Date**: 2026-06-11 | **Spec**: [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/018-cost-control-engine/spec.md)

**Input**: Feature specification from `/specs/018-cost-control-engine/spec.md`

## Summary

본 피처는 유료 멀티모달 LLM API의 불필요한 호출을 원천 차단하여 예산 비용을 획기적으로 통제(0원 수렴)하기 위한 비용 통제 엔진 핵심(뼈대)을 구현합니다. 결제 데이터 텍스트에서 10자리 사업자등록번호(BRN)를 감지하여 가맹점을 식별하고, `is_verified: true` 상태인 검증 완료 템플릿의 정규식 규칙으로 즉각 정적 파싱하여 LLM 호출을 우회(Bypass)합니다. 번호 감지 실패 시 LLM으로 즉각 폴백(Fallback)하되, 사용자 대기 지연을 방어하고자 Celery 백그라운드 비동기 큐로 안전하게 격리 처리합니다. 또한, 최초 분석이 성공한 신규 가맹점에 대해서는 정규식 타당성 임시 자가 테스트 통과 시 `is_verified: false` 임시 상태의 템플릿을 자동으로 제안하는 자율 진화 등록 파이프라인을 구축합니다.

## Technical Context

**Language/Version**: Python 3.11 (Backend)

**Primary Dependencies**: Django 4.2+, Django REST Framework (DRF), Celery 5.3+, Redis (Broker), LiteLLM (Router), google-genai SDK

**Storage**: PostgreSQL v18+ (ACID Data, Native UUIDv7 & AIO), JSONB field support

**Testing**: pytest (Runner), Django `django.test.TestCase` (DB 통합 및 API 뷰 테스트용), Python `unittest.TestCase` (정적 정규식 파서 로직 유닛 테스트용)

**Target Platform**: Docker Compose Environment (api-server, postgres-db, redis-broker, async-worker)

**Project Type**: Web application (Backend & Frontend Monorepo)

**Performance Goals**: 정적 우회 파서 가동 시 50ms 이내에 데이터 추출 및 적재를 완료하여 즉시 동기 응답(201) 처리

**Constraints**: 최대 RDBMS 커넥션 풀 크기 제약 (api-server 컨테이너 5개, Celery worker 3개, 전체 합산 8개 이하 유지)

**Scale/Scope**: 10만 건 이상의 더미 데이터 적재 환경에서 고성능 인덱싱 정합성 유지

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **원자성 보장 (헌법 제I조)**: 마스터 가계부 레코드(`Ledger`)와 하위 품목 레코드 배열(`LedgerItem`)의 생성/수정 연산은 단일 `transaction.atomic()` 블록 내에서 처리되는가? → **PASS (예외 발생 시 전격 롤백 설계)**
- **비동기 큐 전환 및 자원 점유 최적화 (헌법 제II조)**: LLM 폴백 등 무겁고 지연이 발생하는 연산은 Celery 비동기 독립 워커로 격리 실행되는가? → **PASS (Celery 백그라운드 태스크 설계)**
- **하이브리드 비용 최적화 파이프라인 (헌법 제III조)**: 10자리 사업자등록번호 기반 `merchant_templates` 테이블 우선 조회, `is_verified: true`인 정규식 규칙으로 LLM 우회, 실패 시 LLM 폴백 및 `is_verified: false` 자가 학습 파이프라인이 구현되는가? → **PASS (하이브리드 비용 통제 파이프라인 설계 완비)**
- **크로스 플랫폼 대칭 툴링 및 문서 동기화 수호 (헌법 제VI조)**: 추가되는 자동화 스크립트나 도구가 프로젝트 루트의 `scripts/` 디렉토리에 위치하는가? → **PASS (해당 없음, 신규 관리용 외부 스크립트 없음)**
- **선언적 의존성 및 uv 패키지 격리 수호 (헌법 제VII조)**: 추가 패키지는 pyproject.toml 및 uv.lock을 활용하는가? → **PASS**
- **pytest 및 Django TestCase 하이브리드 테스트 수호 (헌법 제VIII조)**: DB 결합 테스트는 `django.test.TestCase`와 `setUpTestData(cls)`를 사용하고, 순수 유틸리티 테스트는 `unittest.TestCase`를 사용하는가? → **PASS (하이브리드 테스트 규칙 엄수)**

## Project Structure

### Documentation (this feature)

```text
specs/018-cost-control-engine/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── contracts/
    └── api-contract.md  # API Contract specification
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── ledgers/
│   │   ├── models.py      # MerchantTemplate 모델 정의 및 Constraints
│   │   ├── services.py    # CostControlParser(우회/폴백) 및 RegexGenerator(자가학습) 로직
│   │   ├── tasks.py       # Celery 비동기 LLM 폴백/자가학습 태스크
│   │   └── views.py       # DRF API View (업로드 시 우회 여부에 따른 PENDING/COMPLETED 제어)
│   └── admin/
│       └── views.py       # 어드민 가맹점 템플릿 수동 승인 API
└── tests/
    ├── integration/
    │   └── test_cost_control_parser.py # django.test.TestCase 기반 우회/폴백 통합 테스트
    └── unit/
        └── test_regex_parser.py        # unittest.TestCase 기반 순수 정규식 매칭 유닛 테스트
```

**Structure Decision**: Backend Django REST Framework 모노레포 구조 하에서 `ledgers` 앱 내에 비용 통제 파서와 자가 학습 엔진 서비스를 모듈화하여 배치하며, 통합 테스트와 단위 테스트는 하이브리드 테스트 작성 규약에 부합하게 독립 경로로 격리합니다.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*(헌법 위반 사항이 없으므로 비워둠)*
