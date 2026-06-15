# Tasks: Receipt Hybrid Parsing Pipeline & Legacy Cleanup

**Input**: Design documents from `/specs/022-receipt-hybrid-pipeline/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/internal-service.md

**Tests**: TDD(테스트 주도 개발) 방식이 요구되었으므로, 각 사용자 스토리별로 구현 태스크에 앞서 테스트 작성 및 실패 확인 태스크가 의무적으로 포함됩니다.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 프로젝트 환경 설정 및 패키지 의존성 최신화

- [ ] T001 `backend/pyproject.toml` 및 `pyproject.toml` 설정 파일에 fitz(PyMuPDF), pytesseract 등 로컬 OCR에 필요한 의존성 유무를 확인하고 락 파일 갱신 및 가상환경 동기화 (`uv sync`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 본격적인 파이프라인 개발 전에 완료되어야 하는 로컬 인프라 환경 검증

- [ ] T002 [P] 로컬 개발 환경에서 Ollama 서비스 실행 상태 및 gemma4:e4b 모델 존재 여부를 사전 확인하기 위한 헬퍼 스크립트 작성 (`scripts/check_ollama.ps1` 및 `scripts/check_ollama.sh`)

---

## Phase 3: User Story 4 - Legacy Caching & Self-Healing Cleanup (Priority: P1) 🎯 MVP

**Goal**: 기존 정적 정규식 기반 캐시 바이패스 파서, 자동 승격, 자가 치유 관련 레거시 로직 비활성화 및 청소

**Independent Test**: 레거시 바이패스 및 승격 테스트 실행 시 무해하게 패스되거나, 더 이상 정적 템플릿 관련 비동기 태스크 및 제안 DB 레코드가 새로 생성되지 않음을 증명

### Tests for User Story 4
> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**
- [ ] T003 [P] [US4] `backend/tests/unit/test_bypass_parser.py` 및 `backend/tests/test_template_promotion.py`, `backend/tests/test_template_self_healing.py` 경로 내의 레거시 바이패스/승격/자가치유 테스트들을 주석 처리하거나 안전하게 우회하도록 테스트 코드 수정

### Implementation for User Story 4
- [ ] T004 [P] [US4] `backend/src/utils/bypass_parser.py` 경로 내의 `BypassParser` 클래스 내 `try_bypass_parsing` 및 `propose_new_template`이 항상 `None`을 반환하도록 로직 비활성화 및 무력화
- [ ] T005 [P] [US4] `backend/src/apps/ledgers/services/promotion.py` 경로의 `promote_template_if_consistent` 및 `demote_template`, `trigger_self_healing` 함수들을 비활성화하고 무력화
- [ ] T006 [US4] `backend/src/apps/tasks/tasks.py` 경로에 정의된 `verify_proposed_regex_task` 및 `self_heal_template_task` Celery 비동기 태스크의 내부 구동 로직 비활성화 및 주석 처리

---

## Phase 4: User Story 1 - Local Hybrid OCR & Ollama Parsing (Priority: P1) 🎯 MVP

**Goal**: 로컬 OCR(PyMuPDF/Tesseract)을 통한 텍스트 획득 및 로컬 Ollama 모델을 활용한 JSON 스키마 구조화와 금액 정합성(오차 0) 검증 성공 시 가계부 원자적 적재

**Independent Test**: 로컬 Ollama 모의 정상 응답 유입 시, 클라우드 API 호출 없이 로컬 단독으로 `Ledger` 및 `LedgerItem` 적재 E2E 동작 성공 확인

### Tests for User Story 1
> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**
- [ ] T007 [P] [US1] Tesseract/PyMuPDF 로컬 OCR 문자 추출 기능에 대한 테스트 코드를 작성하고 pytest로 실패 확인 (`backend/tests/unit/test_local_ocr.py` 생성)
- [ ] T008 [P] [US1] 로컬 Ollama `gemma4:e4b` JSON 스키마 구조화 및 상세 품목 금액 합산 정합성(`sum(item.total_price) == total_amount`) 검증 테스트 코드를 작성하고 pytest로 실패 확인 (`backend/tests/unit/test_ollama_parser.py` 생성)
- [ ] T009 [US1] `ingest_receipt` 메서드의 1단계 로컬 파싱 및 DB 적재 E2E 성공 시나리오에 대한 통합 테스트를 작성하고 pytest로 실패 확인 (`backend/tests/integration/test_receipt_integration.py` 수정)

### Implementation for User Story 1
- [ ] T010 [P] [US1] `backend/src/apps/ledgers/services/__init__.py` 내 fitz(PyMuPDF) 및 Tesseract OCR 호출 부분의 리팩토링 및 예외 복구(0글자 추출) 처리 구현
- [ ] T011 [P] [US1] `backend/src/utils/llm_client.py` 내 로컬 Ollama 텍스트 기반 JSON 구조화 메서드(`parse_receipt_local`) 구현
- [ ] T012 [US1] `backend/src/apps/ledgers/services/__init__.py` 내의 `ingest_receipt`에서 로컬 OCR 문자 추출 후 1단계 로컬 파서(`parse_receipt_local`)를 호출하고 상세 품목 합산 검증(`sum(item.total_price) == total_amount`)을 처리하는 1단계 파이프라인 흐름 및 트랜잭션 적재 구현

---

## Phase 5: User Story 2 - Cloud Text-only Fallback (Priority: P2)

**Goal**: 1단계 금액 정합성 실패 또는 스키마 붕괴 시, 이미 획득한 OCR 문자열만 Gemini-2.5-Flash API로 전송하여 95% 이상 비용을 아끼며 저비용 텍스트 구조화 및 정합성 검증 시도

**Independent Test**: Ollama 파싱 결과의 금액 정합성이 맞지 않는 상황에서 자동으로 2단계 클라우드 텍스트 전용 API로 폴백해 성공 적재되는 E2E 흐름 입증

### Tests for User Story 2
> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**
- [ ] T013 [P] [US2] Gemini-2.5-Flash Text-only API 호출을 통한 텍스트 기반 구조화 기능의 테스트 코드를 작성하고 pytest로 실패 확인 (`backend/tests/unit/test_gemini_text_parser.py` 생성)
- [ ] T014 [US2] 1단계 금액 정합성 실패 시 2단계 Gemini Text-only로 정상 폴백 및 금액 정합성 통과 시 최종 완료되는 흐름의 통합 테스트 코드를 작성하고 pytest로 실패 확인 (`backend/tests/integration/test_receipt_integration.py` 수정)

### Implementation for User Story 2
- [ ] T015 [P] [US2] `backend/src/utils/llm_client.py` 내 Gemini-2.5-Flash Text-only 구조화 호출 메서드 (`parse_receipt_cloud_text`) 구현
- [ ] T016 [US2] `backend/src/apps/ledgers/services/__init__.py` 내의 `ingest_receipt`에서 1단계 로컬 파싱 실패/검증 실패 시, 2단계 클라우드 텍스트 파서(`parse_receipt_cloud_text`)를 가동하고 금액 정합성을 검증하는 2단계 폴백 파이프라인 제어 흐름 구현

---

## Phase 6: User Story 3 - Cloud Vision Fallback (Priority: P3)

**Goal**: 1/2단계 텍스트 기반 분석이 모두 최종 실패했거나 로컬 OCR 텍스트 추출 결과가 비어있을 때, 최후의 보루로서 영수증 원본 이미지(WebP) 또는 PDF 바이너리를 Gemini-2.5-Flash Vision API 멀티모달로 직접 전송해 최종 파싱 달성

**Independent Test**: OCR 문자열이 전혀 추출되지 않는 이미지 유입 시 즉시 3단계 비전 멀티모달 API로 폴백해 E2E 파싱 성공 입증

### Tests for User Story 3
> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**
- [ ] T017 [P] [US3] Gemini-2.5-Flash Vision API 멀티모달(WebP 및 PDF 원본 바이트 전달) 구조화 기능의 테스트 코드를 작성하고 pytest로 실패 확인 (`backend/tests/unit/test_gemini_vision_parser.py` 생성)
- [ ] T018 [US3] 1/2단계 실패 시 최후의 보루로 3단계 Gemini Vision으로 폴백하여 파싱을 성공 완료하는 통합 테스트 코드를 작성하고 pytest로 실패 확인 (`backend/tests/integration/test_receipt_integration.py` 수정)

### Implementation for User Story 3
- [ ] T019 [P] [US3] `backend/src/utils/llm_client.py` 내 Gemini-2.5-Flash Vision 호출 메서드(`parse_receipt_cloud_vision`) 구현 및 PDF 파일 유입 시 이미지 변환을 우회하는 바이패스 분기 구현
- [ ] T020 [US3] `backend/src/apps/ledgers/services/__init__.py` 내의 `ingest_receipt`에서 1, 2단계 최종 실패 혹은 OCR 추출 실패 시, 3단계 비전 폴백 파서(`parse_receipt_cloud_vision`)를 호출해 최종 완결 짓고 실패 시 FAILED 처리하는 3단계 폴백 파이프라인 흐름 완성

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 프로젝트 전체 기능 조율, 린팅, E2E 검증 및 수동 테스트 통과 확인

- [ ] T021 [P] `docs/` 및 `quickstart.md`에 정의된 3가지 수동 검증 시나리오에 따라 로컬 수동 테스트 확인 및 기록
- [ ] T022 [P] Ruff 린터 및 포매터 가드를 통해 전체 파일에 린팅 및 스타일 가이드 정합성 준수 증명 (`uv run ruff check` 및 `uv run ruff format`)
- [ ] T023 전체 pytest 테스트 스위트를 실행하여 작성한 모든 TDD 유닛/통합 테스트 코드(T007, T008, T009, T013, T014, T017, T018)의 100% 통과(Pass) 입증

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 대기 없는 즉시 시작 가능.
- **Foundational (Phase 2)**: Phase 1(의존성 동기화) 완료 후 진행 가능. 모든 사용자 스토리 개발을 블로킹함.
- **User Story 4 (Phase 3)**: 레거시 제거. 3단계 파이프라인 개발 전에 충돌 방지를 위해 최우선 완결되어야 함.
- **User Story 1 (Phase 4)**: 1단계 로컬 파이프라인 구현. 클라우드 폴백의 선행 전제이므로 US2 및 US3보다 선행되어야 함.
- **User Story 2 (Phase 5)**: 2단계 텍스트 폴백 구현. 1단계 로컬 실패 감지 시그널을 수신하므로 US1 구현 완료에 종속됨.
- **User Story 3 (Phase 6)**: 3단계 비전 폴백 구현. 1, 2단계 최종 실패 감지 시그널을 수신하므로 US2 구현 완료에 종속됨.
- **Polish (Phase 7)**: 모든 사용자 스토리가 구현 및 배포된 후에 최종 기동.

### Within Each User Story

1. **테스트 퍼스트 (TDD)**: 각 구현 파일 코딩에 들어가기 전, 테스트 코드를 먼저 작성하고 `pytest`로 실행하여 실패(Red)하는 것을 보증해야 합니다.
2. **비즈니스 인터페이스**: `ReceiptLLMClient` 내 파서 메서드 코딩 후 `ingest_receipt` 내의 제어 흐름을 리팩토링합니다.
3. **E2E 검증**: 각 단계 완료 후 개별 단위/통합 테스트가 통과하는지 순차적으로 검증합니다.

### Parallel Opportunities

- Phase 1, Phase 2의 환경 점유/준비 태스크는 병렬 실행할 수 있습니다.
- US4 내의 `BypassParser` 무력화(T004) 및 `promotion.py` 정리(T005)는 파일이 격리되어 있으므로 병렬 처리가 가능합니다.
- 각 사용자 스토리 페이즈 하위에 마킹된 `[P]` 테스트 태스크와 단위 구현 태스크는 상호 간의 선후 의존성 없이 다른 파일로 분리되어 있으므로 병렬로 작성할 수 있습니다.

---

## Parallel Example: User Story 1

```bash
# User Story 1의 테스트 코드 2종을 병렬로 동시 작성:
Task T007: "Tesseract/PyMuPDF 로컬 OCR 문자 추출 기능 테스트 작성" (tests/unit/test_local_ocr.py)
Task T008: "로컬 Ollama gemma4:e4b JSON 스키마 및 금액 검증 테스트 작성" (tests/unit/test_ollama_parser.py)

# User Story 1의 백엔드 비즈니스 로직과 LLM 파서 클라이언트를 병렬로 동시 구현:
Task T010: "ingest_receipt 내 로컬 OCR 추출 및 예외 복구 구현" (ledgers/services/__init__.py)
Task T011: "ReceiptLLMClient 내 로컬 Ollama 파싱 메서드 구현" (utils/llm_client.py)
```

---

## Implementation Strategy

### MVP First (Phase 3 & Phase 4)

1. Phase 1 Setup 및 Phase 2 Foundational 확인 완료.
2. **Phase 3 (US4) 레거시 정리 완결**: 기존 바이패스 및 캐시, 자가치유 코드/태스크 비활성화 및 청소 완료.
3. **Phase 4 (US1) 로컬 파이프라인 완결**: 로컬 OCR + 로컬 Ollama + 금액 검증 성공 흐름 구현.
4. **STOP and VALIDATE**: 로컬 단독 기동 성공 여부 및 가계부 적재 무결성을 유닛/통합 테스트로 먼저 독자 검증하여 1차 완성품(MVP)을 인도합니다.

### Incremental Delivery (Phase 5 & Phase 6)

1. MVP 인도 완료 후, 2단계 클라우드 텍스트 폴백(Phase 5)을 이식하고 독립 테스트 및 정합성 검증.
2. 이어서 3단계 클라우드 비전 폴백(Phase 6)을 이식하고 독립 테스트 및 정합성 검증.
3. 최종 Polish 단계(Phase 7)로 이행하여 E2E 시나리오 및 스타일 가이드 최종 완성.
