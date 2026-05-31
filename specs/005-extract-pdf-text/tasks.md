# Tasks: PDF Text Lossless Extraction Utility

**Input**: Design documents from `/specs/005-extract-pdf-text/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/contracts.md

**Tests**: 단위 테스트를 통한 엄격한 기계적 하네스 검증을 위해 단위 테스트 태스크들이 필수(T007, T010, T013 등)로 포함되어 있으며, 실제 구현 코딩 전 테스트 코드를 선제적으로 작성하여 무결성을 증명합니다.

**Organization**: 각 태스크는 사용자가 합의한 3가지 핵심 유저 스토리(NFC 무손실, 하이브리드 Fallback, DTO 에러 포장)를 독립적이고 원자적으로 분할 구현 및 테스트할 수 있도록 사용자 스토리 단위로 정교하게 조직화되어 있습니다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 다른 파일에 독립적으로 병렬 기동 가능한 태스크 (상호 의존이 배제되어 병렬 처리 가능)
- **[Story]**: 매핑되는 사용자 스토리 번호 (예: US1, US2, US3)
- 소스 코드 및 검증 스크립트의 정확하고 리터럴한 실제 물리 경로 명시

## Path Conventions

- 백엔드 모노레포 구조에 의거하여 아래 경로 규격을 엄격하게 준수합니다.
  - **백엔드 소스 루트**: `backend/src/`
  - **백엔드 유틸리티 코드**: `backend/src/utils/pdf_extractor.py` (클래스 및 DTO 구현)
  - **백엔드 단위 테스트**: `backend/tests/unit/test_pdf_extractor.py`
  - **크로스 플랫폼 도구**: `scripts/run-pdf-tests.ps1` 및 `scripts/run-pdf-tests.sh` (scripts/ 폴더 하위 이중화 대칭 배포)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 프로젝트 패키지 락킹 및 초기 디렉토리/의존성 환경 구축

- [X] T001 `backend/pyproject.toml` 파일에 `pymupdf` 및 `pdfplumber` 라이브러리 의존성 선언 추가
- [X] T002 `D:\Projects\Private\ai-ledger-automation` 루트에서 `uv lock` 및 `uv sync`를 실행하여 가상환경 `.venv` 내에 패키지 격리 및 패키지 락 정합성 일치화 수행
- [X] T003 `backend/src/utils/pdf_extractor.py` 및 `backend/tests/unit/test_pdf_extractor.py` 작성을 위한 기본 모듈 패키징 초기 셋업

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 사용자 스토리의 근간이 되는 DTO 구조 및 유니코드 정규화 뼈대 마련

**⚠️ CRITICAL**: 이 페이즈의 뼈대 구조가 완벽하게 다듬어지기 전까지는 개별 유저 스토리 구현에 착수할 수 없습니다.

- [X] T004 `backend/src/utils/pdf_extractor.py` 파일 내부에 `ExtractionResult` DTO 클래스 데이터 규격 속성 및 타입 설계 및 구현
- [X] T005 `backend/src/utils/pdf_extractor.py` 파일 내부에 `PDFTextExtractor` 메인 클래스 뼈대 선언 및 한글 NFC 정규화 유틸리티 함수 구현
- [X] T006 `scripts/run-pdf-tests.ps1` 및 `scripts/run-pdf-tests.sh` 경로에 백엔드 PDF 파싱 유틸리티 단위 테스트를 기계적으로 실행 및 자동화할 수 있는 양대 크로스 플랫폼 대칭형 검증 스크립트 작성 (헌법 제VI조 대칭 스크립트 격리 원칙 수호)

**Checkpoint**: 기반 인프라 기동 준비 완료 - 유저 스토리 병렬 구현 및 TDD 테스트 검증 개시 가능

---

## Phase 3: User Story 1 - 영수증 PDF 내장 텍스트 무손실 추출 (Priority: P1) 🎯 MVP

**Goal**: PyMuPDF 엔진을 최우선 구동하여 PDF 내장 텍스트 레이어를 깨짐 없이 100% 무손실 완성형 한글로 파싱

**Independent Test**: `backend/tests/unit/test_pdf_extractor.py` 단독 기동을 통해 한글 자모 깨짐 복원 무결성 증명

### Tests for User Story 1 (TDD)
- [X] T007 [P] [US1] `backend/tests/unit/test_pdf_extractor.py` 경로에 PyMuPDF 단독 정상 추출 성공 및 한글 NFC 유니코드 조합 정합성 검증을 수행하는 단위 테스트 케이스 우선 작성 (TDD 지향)

### Implementation for User Story 1
- [X] T008 [US1] `backend/src/utils/pdf_extractor.py` 파일에 PyMuPDF를 이용한 텍스트 추출(`layout: bool` 매개변수 연동 및 `layout=True` 시 `blocks` 탭/공백 정렬 보존 기능) 구현
- [X] T009 [US1] `backend/src/utils/pdf_extractor.py` 파일에 텍스트 추출 직후 완성형 한글 NFC 표준 정규화 필터 적용 구현

**Checkpoint**: PyMuPDF 기반의 완성형 한글 텍스트 무손실 추출 기능 완전 작동 및 독립 검증 통과

---

## Phase 4: User Story 2 - 엔진 선택 및 자동 Fallback 처리 (Priority: P2)

**Goal**: PyMuPDF 구동 실패 또는 인코딩 결함 감지 시, pdfplumber 엔진으로 실시간 자동 Fallback 복구 수행

**Independent Test**: `backend/tests/unit/test_pdf_extractor.py`에 PyMuPDF 실패 상황을 모킹하여 pdfplumber 자동 복구 검증

### Tests for User Story 2
- [X] T010 [P] [US2] `backend/tests/unit/test_pdf_extractor.py` 경로에 PyMuPDF 파싱 오류(C-Level/인코딩 깨짐) 발생 시 pdfplumber 엔진으로 Fallback하여 복구 성공하는지 검증하는 단위 테스트 케이스 우선 작성

### Implementation for User Story 2
- [X] T011 [US2] `backend/src/utils/pdf_extractor.py` 파일에 pdfplumber 추출 엔진 (`layout: bool` 매개변수 연동 및 `layout=True` 시 `extract_text(layout=True)` 공백 보존 기능) 연동 구현
- [X] T012 [US2] `backend/src/utils/pdf_extractor.py` 파일에 PyMuPDF 작동 중 예외 발생 시 `pdfplumber`로 투명하게 전환하는 **자동 Fallback 메커니즘**의 예외 포착 로직 구현

**Checkpoint**: 하이브리드 상호 보완 자동 Fallback 프로토콜 E2E 성공 및 독립 단위 검증 통과

---

## Phase 5: User Story 3 - 에러 핸들링 및 유효성 검증 (Priority: P3)

**Goal**: 보안 암호화 PDF 및 물리적 텍스트 레이어가 전무한 스캔 이미지 PDF에 대한 안전한 DTO 에러 포장 반환

**Independent Test**: 비정상 PDF 파일을 로드했을 때 크래시 없이 `success=False` DTO 및 안전한 에러 메시지가 획득됨을 테스트로 증명

### Tests for User Story 3
- [X] T013 [P] [US3] `backend/tests/unit/test_pdf_extractor.py` 경로에 암호화 PDF(Password Incorrect) 및 텍스트 레이어가 전무한 스캔 PDF 유입 시 `success: False` DTO 반환을 검증하는 예외 처리 단위 테스트 케이스 우선 작성

### Implementation for User Story 3
- [X] T014 [US3] `backend/src/utils/pdf_extractor.py` 파일에 PDF 로딩 시 `doc.is_encrypted` 속성을 감지하여 `is_encrypted: True`로 래핑 반환하는 검증 필터 구현
- [X] T015 [US3] `backend/src/utils/pdf_extractor.py` 파일에 추출된 전체 문자가 0개인 경우 `has_text_layer: False` 및 OCR 파이프라인 우회 사유 에러 메시지(`No physical text layer detected`)를 포장해 반환하는 텍스트 레이어 검증 필터 구현

**Checkpoint**: 모든 비정상 악성 PDF 유입에 대해 프로세스 중단 없는 견고한 철벽 에러 복원력 확보 완료

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 초대형 문서 성능 최적화, 3대 코어 문서 버전 교차 동기화 및 린터 검증 기계적 완료

- [X] T016 `backend/src/utils/pdf_extractor.py` 파일에 50페이지 이상 초대형 PDF 로드 시 메모리 보호를 위한 페이지 단위 부분 추출(`start_page`, `end_page`) 및 제네레이터(Generator) 스트리밍 최적화 로직 구현
- [X] T017 `D:\Projects\Private\ai-ledger-automation`에서 헌법 제VI조(자율 교차 동기화)에 준해 3대 코어 문서(`README.md`, `AGENTS.md`, `.specify/memory/constitution.md`)와 모노레포 설정 파일의 정합성 유기적 교차 동기화 자율 점검 실행
- [X] T018 `scripts/run-pdf-tests.ps1` 및 `scripts/run-pdf-tests.sh` 양대 스크립트를 실제 로컬에서 실행하여 단위 테스트 커버리지 100% 만족 여부 및 linter(black/ruff 등) 포맷 무결성 기계적 검증 수행

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 선행 의존성 없이 즉각 시작 가능.
- **Foundational (Phase 2)**: Setup(Phase 1) 완료에 엄격히 종속되며, 개별 사용자 스토리를 강력하게 블로킹(BLOCK)함.
- **User Stories (Phase 3 ~ 5)**: Foundational(Phase 2) 기둥 설계가 마감되는 즉시 기동 가능.
  - 팀 리소스 가용 시 병렬 개발 가능 (각 파일 및 클래스가 완벽히 격리 설계되었기 때문).
  - 1인 개발 시 비즈니스 우선순위 순서대로 점진적 기동 가능 (US1 MVP → US2 Fallback → US3 Error handling).
- **Polish (Phase 6)**: 모든 핵심 사용자 스토리(US1 ~ US3)가 성공 완료된 이후 최종 튜닝 진입.

### User Story Dependencies

- **User Story 1 (P1)**: Foundational 완성 후 무조건 즉각 시작 가능 (독립성 보장).
- **User Story 2 (P2)**: PyMuPDF 기본 뼈대(US1)를 활용하므로, US1의 파싱 텍스트 유니코드 NFC 정규화 로직 위에 상호 작용하여 유연하게 기동.
- **User Story 3 (P3)**: 예외 처리 래핑이므로, US1 및 US2 엔진 인스턴스 예외를 캐치하여 데이터 가교 역할을 수행하므로 마지막에 배치.

### Parallel Opportunities

- **Setup (Phase 1)** 및 **Foundational (Phase 2)**의 각 `[P]` 태스크들은 파일이 완전히 다르므로 동시 병렬 작업 가능.
- **User Story 1 ~ 3**의 테스트 코딩 `[P]` 태스크들은 `backend/tests/unit/test_pdf_extractor.py` 내부의 독립된 테스트 함수들로 정의되므로, 개발자가 여럿인 경우 테스트 함수 구조를 먼저 분할 정의하여 병렬 코딩 가능.

---

## Parallel Example: User Story 1 (TDD)

```bash
# TDD에 의거하여 US1의 텍스트 파싱 테스트와 NFC 유니코드 정규화 테스트 케이스 선제 기동:
Task: "T007 [P] [US1] backend/tests/unit/test_pdf_extractor.py 경로에 PyMuPDF 단독 정상 추출 성공 및 한글 NFC 유니코드 조합 정합성 검증을 수행하는 단위 테스트 케이스 우선 작성 (TDD 지향)"

# 이후 실제 비즈니스 유틸리티 추출기 및 한글 정규화 구현:
Task: "T008 [US1] backend/src/utils/pdf_extractor.py 파일에 PyMuPDF를 이용한 텍스트 추출 구현"
Task: "T009 [US1] backend/src/utils/pdf_extractor.py 파일에 텍스트 추출 직후 완성형 한글 NFC 표준 정규화 필터 적용 구현"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. **Setup & Foundational 마감**: Phase 1 & Phase 2 완수하여 `fitz` 패키지 락킹 및 `PDFTextExtractor` 뼈대 구조 빌드.
2. **US1 집중 코딩**: PyMuPDF 기반 무손실 텍스트 파싱 구현 마감.
3. **독립 검증 벤치마크**: `scripts/run-pdf-tests.ps1`을 가동하여 **T007**과 **T008/T009**가 100% 녹색불로 검증 완료되는지 MVP 상태 전격 증명 후 전개.

### Incremental Delivery

- **Step 1**: Setup + Foundational 완수 -> 프로젝트 뼈대 가동 가능.
- **Step 2**: US1 (MVP) 추가 및 단위 검증 마감 -> 실제 내장 텍스트 PDF 무손실 추출 서비스 가동.
- **Step 3**: US2 Fallback 추가 및 단위 검증 마감 -> 예외 PDF 한글 자모 깨짐 시의 하이브리드 고신뢰 복원 지원.
- **Step 4**: US3 Error handling 추가 및 단위 검증 마감 -> 암호화 PDF 및 스캔 이미지 유입 시 비동기 큐 마비 없는 크래시-프리 복원력 달성.
- **Step 5**: Polish 완수 -> 대용량 부분 추출 generator 및 버전 교차 동기화 완결.

---

## Notes

- 모든 태스크는 체크박스 `- [X]`로 정교하게 완료 표시되어 있습니다.
- 각 ID는 `T001`부터 `T018`까지 고유하고 엄격하게 순차 정렬되어 있습니다.
- 모든 태스크 설명에 작업 대상 소스 파일 및 검증 도구의 **명확한 리터럴 물리 경로**를 누락 없이 100% 명시했습니다.
- 테스트 코딩은 필수이며, 각 스토리 페이즈 최상단에 배치하여 TDD 흐름을 유도했습니다.
- 태스크 간 충돌이나 애매모호한 형용사구 표현을 배제하여 코딩 에이전트가 완벽하게 즉시 실행 가능하도록 정제했습니다.
