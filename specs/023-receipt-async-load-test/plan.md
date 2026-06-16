# Implementation Plan: Receipt Async Load Testing

**Branch**: `023-receipt-async-load-test` | **Date**: 2026-06-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/023-receipt-async-load-test/spec.md`

## Summary

본 피처는 50종의 영수증 이미지가 웹 업로드 API 경로를 통해 일시에 유입되는 물리적 부하 환경에서도 데이터 유실 없이 비동기로 작업을 큐잉 및 처리하고, RDBMS(PostgreSQL)에 가계부 레코드 적재 시 단일 트랜잭션(`transaction.atomic()`) 원자성과 60초 임계 시각 기반 중복 결제 방어 정합성을 보장하도록 비동기 아키텍처를 검증하고 튜닝하는 것을 목표로 합니다. 특히, Supabase Free-tier 및 로컬 DB 환경의 커넥션 풀 고갈을 방지하기 위해 Celery 동시성을 기계적으로 3개 이하로 제한하고, 전체 가용 풀(합산 8개 이하) 한계 조건 내에서 3단계 하이브리드 파싱 파이프라인이 안정적으로 완결되는 부하 테스트 인프라를 구축합니다.

## Technical Context

**Language/Version**: Python 3.13 (django-rest-framework 3.15+, celery 5.4+)

**Primary Dependencies**: Django, Celery, Redis, LiteLLM Router, Pillow, psycopg3

**Storage**: PostgreSQL v18+ (JSONB 및 approval_number 컬럼 탑재), Redis (Celery Broker 및 JWT/세션 캐시)

**Testing**: pytest, django.test.TestCase (하이브리드 테스트 아키텍처)

**Target Platform**: Docker Compose (api-server, async-worker, redis-broker, postgres-db) 로컬 및 프로덕션 환경

**Project Type**: web-service (API Server) & background-worker (Celery Worker)

**Performance Goals**: 50종 벌크 업로드 시 API 응답 속도 5초 이내, 비동기 파싱 완료 시점까지 DB 커넥션 획득 실패(OperationalError) 발생율 0%

**Constraints**: api_server DB 풀 최대 5개, Celery 워커 DB 풀 최대 3개, 전체 합산 8개 이하 하드 제한. Celery worker concurrency 최대 3개 제한.

**Scale/Scope**: 동시 50종 영수증 업로드. DB 적재 트랜잭션 롤백 100% 신뢰성 보장. 중복 생성 방어 100%.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **원칙 I. 데이터 무결성 및 원자성 트랜잭션 최우선**: 통과. 영수증 1장당 `ledgers` 마스터와 `ledger_items` 상세품목 생성을 단일 `transaction.atomic()` 블록으로 묶어 원자성을 수호하며, 60초 임계창 카드 승인 대조 중복 방어 알고리즘 검증을 부하 테스트 환경에 완벽히 구축합니다.
- **원칙 II. 비동기 큐 전환 및 자원 점유 최적화**: 통과. 업로드 API 유입 즉시 202 Accepted 및 Task ID를 반환하고, 실제 무거운 연산(Pillow 전처리, LLM 파싱)은 격리된 Celery 비동기 워커 내부로 이관합니다.
- **원칙 II. DB 커넥션 풀 크기 제한**: 통과. api_server(5), async_worker(3), 합산 8개 제한 조건에 맞춰 동시성을 튜닝하고 부하 테스트 중 커넥션 고갈이 없음을 입증합니다.
- **원칙 III. 3단계 하이브리드 영수증 파싱 전략**: 통과. Ollama -> Gemini Text -> Gemini Vision 3-Tier 연동의 흐름을 보장하며, 로컬 Ollama 호출 시 base64 디코딩 접두사 충돌 방어 로직 정합성을 유지합니다.
- **원칙 VI. 크로스 플랫폼 대칭 툴링 및 스크립트 격리 배치**: 통과. 부하 테스트 자동화 및 인프라 실행 스크립트를 `scripts/` 디렉토리에 Windows/Linux 대칭형으로 작성합니다.
- **원칙 VIII. pytest 및 Django TestCase 하이브리드 테스트 수호**: 통과. DB 연산이 수반되는 부하 및 트랜잭션 정합성 검증은 `django.test.TestCase` 및 `setUpTestData(cls)`를 상속받은 통합 테스트 클래스로 구현합니다.

## Project Structure

### Documentation (this feature)

```text
specs/023-receipt-async-load-test/
├── spec.md              # Feature Specification (작성 완료)
├── plan.md              # This file (작성 완료)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/           # Phase 1 output
    └── upload-api.md    # API 계약 명세
```

### Source Code (repository root)

```text
backend/
├── backend/
│   ├── settings.py      # DB 커넥션 및 Celery 설정
│   └── celery.py        # Celery 초기화
├── ledgers/
│   ├── tasks.py         # 영수증 비동기 파이프라인 Celery 태스크
│   ├── services.py      # 트랜잭션 적재 및 중복 방어 서비스
│   └── views.py         # 다중 업로드 API 뷰
└── tests/
    └── ledgers/
        └── test_load_testing.py  # 50종 부하 테스트 통합 테스트 코드
```

**Structure Decision**: `backend/` 디렉토리 내 장고 프로젝트 소스 및 테스트 구조를 타겟으로 삼으며, `scripts/` 디렉토리 하위에 부하 테스트 가동 크로스 플랫폼 자동화 스크립트를 배치합니다.

## Complexity Tracking

> **Violations**: 없음 (최상위 프로젝트 헌법의 모든 제약 사항과 가이드라인을 100% 충족함)
