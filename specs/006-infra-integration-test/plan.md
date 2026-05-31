# Implementation Plan: 1주차 인프라 중간 점검 및 로컬 통합 테스트 수행 (Infra Integration Test)

**Branch**: `006-infra-integration-test` | **Date**: 2026-05-31 | **Spec**: [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/006-infra-integration-test/spec.md)

**Input**: Feature specification from `/specs/006-infra-integration-test/spec.md`

## Summary

본 피처는 1주차 RDBMS 물리 환경(PostgreSQL v18)과 PDF 파서 유틸리티(`PDFTextExtractor`)의 결합 상태를 최종 기계적으로 입증하기 위한 **로컬 동기식 E2E 통합 테스트 파이프라인**을 구축하는 태스크입니다.

[로컬 PDF 로드 -> 텍스트 파싱 -> Django ORM 트랜잭션 원자적 적재 -> 중복 차단 및 FailedTask DLQ 적재]에 이르는 전체 데이터 흐름을 대칭형 크로스 플랫폼 CLI 자동화 스크립트(`scripts/run-pdf-tests`)를 통해 단 15초 이내에 멱등적으로 증명하는 것을 핵심 골자로 합니다.

## Technical Context

**Language/Version**: Python 3.13 (Workspace Venv)

**Primary Dependencies**: `pymupdf (fitz) >= 1.23.0`, `pdfplumber >= 0.10.0`, `django >= 6.0.5`, `djangorestframework >= 3.15.2`

**Storage**: Docker PostgreSQL 18-alpine (격리된 로컬 테스트 전용 데이터베이스 인프라)

**Testing**: `pytest >= 9.0.3` + `pytest-django >= 4.12.0` (Django TestCase 결합)

**Target Platform**: Windows 11 / macOS / Linux Docker 데몬 환경

**Project Type**: `web-service (Django backend integration)`

**Performance Goals**: 테스트 DB 기동부터 마이그레이션, 테스트 코드 가동, 자원 안전 소멸까지의 전 과정 CLI 사이클 타임을 **15초 이내**로 완수하여 고속 로컬 피드백 속도 수호.

**Constraints**: 
- **DB 격리 소멸(Clean Isolation)**: 통합 테스트 완료 시 즉시 테스트 컨테이너와 데이터 볼륨을 자동으로 회수하여 로컬 시스템 자원을 깨끗이 격리함.
- **트랜잭션 ACID 원자성**: 영수증 1장 적재 시 메인 레코드와 상세 품목 배열은 단 하나의 `transaction.atomic()` 내에서 실행 및 실패 시 전액 롤백 보장.
- **하이브리드 테스트 아키텍처**: 헌법 제VIII조에 준하여 DB 결합 테스트는 `django.test.TestCase`를 상속받은 클래스형 스타일로 작성하고, `setUpTestData`를 통해 데이터 셋업 속도 최적화.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 헌법 조항 | 요구 사항 | 준수 여부 및 설계 방안 |
| :--- | :--- | :--- |
| **제I조 (데이터 무결성)** | UNIQUE 중복 적재 차단 및 `transaction.atomic()` 원자성 보장 | **Pass**: 2차 중복 PDF 유입 시 IntegrityError를 성공적으로 유도해 롤백시키고 FailedTask로 안전하게 라우팅하는 E2E 시나리오 수립. |
| **제VI조 (크로스 플랫폼)** | Windows(`*.ps1`)와 macOS/Linux(`*.sh`) 대칭 스크립팅 및 `scripts/` 격리 배치 | **Pass**: `scripts/run-pdf-tests.ps1` 및 `scripts/run-pdf-tests.sh` 대칭 배치를 통해 원클릭 멱등적 통합 테스트 기동/소멸 자동화 설계. |
| **제VIII조 (하이브리드 테스트)** | DB 결합 테스트는 클래스 TestCase 및 setUpTestData 활용 표준화 | **Pass**: `TestPDFIntegrationSuite`를 `django.test.TestCase` 상속 클래스로 설계하여 고속 격리 트랜잭션 롤백 테스트 검증. |

*위반 사항이 전혀 발견되지 않았으므로 품질 게이트를 즉시 통과하며 Phase 0 Research에 정식 진입합니다.*

## Project Structure

### Documentation (this feature)

```text
specs/006-infra-integration-test/
├── spec.md              # 기능 명세서 (Specify 완료)
├── plan.md              # 구현 계획서 (본 파일)
├── research.md          # 기술 연구서 (Phase 0 결과물)
├── data-model.md        # 데이터 모델 명세서 (Phase 1 결과물)
├── quickstart.md        # 퀵스타트 가이드 (Phase 1 결과물)
├── checklists/
│   └── requirements.md  # 명세 품질 체크리스트 (Specify 검증 완료)
└── contracts/
    └── contracts.md     # 데이터/인터페이스 계약 다이어그램 (Phase 1 결과물)
```

### Source Code Layout (repository root)

이 피처는 기존 백엔드 디렉토리 구조와 scripts 폴더 하위에 통합 테스트 자산을 배치합니다.

```text
backend/
├── src/
│   ├── apps/
│   │   ├── ledgers/
│   │   │   ├── services.py      # create_ledger_transactional 구현 완료
│   │   │   └── models.py        # Ledger, LedgerItem 모델 명세
│   │   └── tasks/
│   │       └── models.py        # FailedTask (DLQ) 모델 명세
│   └── utils/
│       └── pdf_extractor.py     # PDFTextExtractor 구현 완료
└── tests/
    ├── resources/
    │   └── receipt_sample.pdf   # 1주차 표준 영수증 PDF 샘플
    └── integration/
        └── test_pdf_integration.py # 신규 통합 테스트 슈트 (Django TestCase 상속)

scripts/
├── run-pdf-tests.ps1            # Windows용 대칭형 원클릭 E2E 기동/Cleanup 스크립트
└── run-pdf-tests.sh             # UNIX/macOS용 대칭형 원클릭 E2E 기동/Cleanup 스크립트
```

**Structure Decision**: 기존 backend의 `tests/integration/` 디렉토리에 통합 테스트를 격리 배치하고, `scripts/` 폴더 하위에 대칭형 CLI 자동화 도구를 생성하여 헌법 제VI조의 격리 배치 원칙을 수호합니다.

## Complexity Tracking

*Violation 및 Justification 대상이 전혀 없습니다. (Clean & Simple Architecture)*
