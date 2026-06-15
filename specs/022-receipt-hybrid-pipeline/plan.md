# Implementation Plan: Receipt Hybrid Parsing Pipeline & Legacy Cleanup

**Branch**: `022-receipt-hybrid-pipeline` | **Date**: 2026-06-16 | **Spec**: [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/022-receipt-hybrid-pipeline/spec.md)

**Input**: Feature specification from `/specs/022-receipt-hybrid-pipeline/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

---

## Summary

로컬의 경제성과 클라우드의 정밀성을 유기적으로 조율하는 **3단계 하이브리드 파이프라인(Local OCR + Ollama ➔ Gemini Text-only ➔ Gemini Vision)**을 구축하여 영수증 파싱 비용을 95% 이상 절감하면서 99%의 파싱 성공률을 확보합니다.
더불어, 시스템의 오작동 및 Celery 자원 낭비를 차단하기 위해 유지보수가 불가능했던 기존의 정적 정규식 기반 캐시 바이패스 및 자가 치유(`BypassParser`, `MerchantTemplate` 캐싱, `promotion.py` 승격/강등, 자가 치유 Celery 태스크) 아키텍처를 완벽하게 비활성화 및 청소합니다.

---

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: Django Web Framework, Celery, Redis Broker, litellm (with LiteLLM Router), PyMuPDF (fitz), pytesseract

**Storage**: PostgreSQL (v18+) (기존 `merchant_templates`, `template_execution_histories` 스키마 유지하되 비활성화)

**Testing**: pytest 및 Django TestCase (하이브리드 테스트 아키텍처)

**Target Platform**: Linux Server (Docker 환경)

**Project Type**: web-service

**Performance Goals**: 백엔드 대시보드 API 쿼리 응답 시간 100ms 이내 방어

**Constraints**: 무료 등급 DB 인프라 가용한계로 인한 데이터베이스 커넥션 풀 크기 제약 (api_server 최대 5개, Celery async_worker 최대 3개, 전체 합계 8개 이하 통제)

**Scale/Scope**: 1일 수천 건의 영수증 처리 대역폭 내에서 이미지 토큰 비용을 95% 이상 절감하는 비용 통제 아키텍처 적용

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

* **I. 데이터 무결성 및 원자성 트랜잭션 최우선**:
  * *준수 방식*: `create_ledger_transactional`을 활용한 Ledgers/LedgerItems의 `transaction.atomic()` 하 원자적 적재 보장. 동일 상품 연속 결제 오탐 방어 알고리즘(60초 임계 시각 대조 및 승인번호 대조) 유지. (검증 결과: **PASS**)
* **II. 비동기 큐 전환 및 자원 점유 최적화**:
  * *준수 방식*: API는 수집 즉시 202 및 Job ID를 반환하며, 이미지 변환 및 AI 연산은 Celery 비동기 독립 워커 내에서만 격리 구동. DB 커넥션 풀을 8개 이하로 유지. (검증 결과: **PASS**)
* **III. 3단계 하이브리드 영수증 파싱 전략 및 비용 최적화**:
  * *준수 방식*: 본 피처의 핵심 목적이므로 3단계 하이브리드 기동 순서와 레거시 캐시 파이프라인 비활성화 요건을 충족. (검증 결과: **PASS**)
* **VII. 선언적 의존성 및 uv 패키지 격리 수호**:
  * *준수 방식*: 모든 패키지 의존성은 `pyproject.toml` 및 `uv.lock` 선언적 락 파일을 기반으로 uv sync를 통해 통제. (검증 결과: **PASS**)
* **VIII. pytest 및 Django TestCase 하이브리드 테스트 수호**:
  * *준수 방식*: DB 결합 비즈니스 로직 테스트는 `django.test.TestCase` 상속 및 `setUpTestData(cls)` 활용, 데이터베이스 미사용 유틸리티 테스트는 `unittest.TestCase` 상속. (검증 결과: **PASS**)

---

## Project Structure

### Documentation (this feature)

```text
specs/022-receipt-hybrid-pipeline/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── internal-service.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── apps/
│   │   ├── ledgers/
│   │   │   ├── services/
│   │   │   │   ├── __init__.py  # ingest_receipt 내 3단계 파이프라인 구현 및 레거시(Bypass) 호출 제거
│   │   │   │   └── promotion.py # promotion/demote 비활성화 및 청소
│   │   │   └── models.py        # MerchantTemplate, TemplateExecutionHistory 모델 사용 중단(Deprecated 마킹)
│   │   └── tasks/
│   │       └── tasks.py         # verify_proposed_regex_task, self_heal_template_task 비활성화/제거
│   └── utils/
│       ├── llm_client.py        # ReceiptLLMClient 내 1/2/3단계 개별 메서드 구현 및 다이내믹 라우팅
│       └── bypass_parser.py     # try_bypass_parsing 무력화 (항상 None 반환 또는 로직 청소)
└── tests/
    ├── unit/
    │   └── test_bypass_parser.py # 레거시 테스트 청소
    ├── test_template_promotion.py # 레거시 테스트 청소
    └── test_template_self_healing.py # 레거시 테스트 청소
```

**Structure Decision**:
기존 장고 백엔드 서비스 구조(`backend/src/apps/` 및 `backend/src/utils/`)의 기존 배치를 그대로 유지하며, 내부 서비스 연동 및 클라이언트의 다이내믹 라우팅 모듈 위주로 Surgical Update를 수행하여 결합도를 최소화합니다.

---

## Complexity Tracking

> **Complexity Gate**: 헌법 위반 사항 및 정당화 내역이 없으므로 비어 있음.
