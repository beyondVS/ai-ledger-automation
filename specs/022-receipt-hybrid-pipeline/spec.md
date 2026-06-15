# Feature Specification: Receipt Hybrid Parsing Pipeline & Legacy Cleanup

**Feature Branch**: `022-receipt-hybrid-pipeline`

**Created**: 2026-06-16

**Status**: Draft

**Input**: User description: "3단계 하이브리드 영수증 파싱 전략(3-Tier Hybrid Pipeline) 구축 및 기존 정규식 바이패스(Bypass) 템플릿 아키텍처 제거/정리.
  * **1단계 (Local Hybrid)**: PDF(PyMuPDF) 또는 이미지(Tesseract)를 사용한 1차 로컬 OCR 문자열 획득 후, 로컬 Ollama `gemma4:e4b` 텍스트 모델을 통한 JSON 스키마 구조화 시도 (비용 0원 달성).
  * **2단계 (Cloud Text-only Fallback)**: 로컬 모델의 스키마 붕괴 또는 금액 정합성(Checksum) 검증 실패 시, 이미 확보된 로컬 OCR 문자열만 Gemini-2.5-Flash API로 전송하여 입력 이미지 토큰 비용을 95% 이상 절감하는 초저비용 구조화 시도.
  * **3단계 (Cloud Vision Fallback)**: 로컬 OCR 문자 추출 실패 또는 앞선 텍스트 파싱 오류 발생 시 최후의 보루로 영수증 원본 이미지(WebP 변환 데이터) 혹은 PDF를 Gemini-2.5-Flash 멀티모달로 송신하여 99% 파싱 무결성 수호.
  * **레거시 정리**: 기존 `BypassParser` 매칭, `promotion.py` 일관성/승격 및 `self_healing` 자가치유 Celery 태스크 등 정적 정규식 기반 캐시 파이프라인의 안전 비활성화 및 청소."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Local Hybrid OCR & Ollama Parsing (Priority: P1)

**Description**:
사용자가 영수증 파일(이미지 또는 PDF)을 업로드하면, 시스템은 백그라운드 Celery 태스크에서 로컬 라이브러리(PDF의 경우 PyMuPDF, 이미지의 경우 Tesseract)를 사용해 OCR 문자열을 추출합니다. 추출 성공 시 추가적인 유료 LLM 호출 없이 비용 0원을 달성하기 위해, 로컬 Ollama `gemma4:e4b` 모델에 해당 텍스트를 전달하여 JSON 스키마 구조화를 수행하고 가계부 데이터를 생성합니다.

**Why this priority**:
유료 API 호출 비용을 완전히 회피하여 비용 0원의 로컬 지향 데이터 수집을 가능하게 하는 가장 기초적이고 파급력이 큰 MVP 시나리오입니다.

**Independent Test**:
클라우드 API(Gemini)에 대한 연동 없이 로컬 Tesseract 및 Ollama 만이 구동되는 환경에서 영수증을 업로드하고, 데이터가 `ReceiptSchema` 규격의 DTO로 정확히 파싱되어 DB에 적재되는지 E2E로 검증합니다.

**Acceptance Scenarios**:

1. **Given** 사용자가 한글 및 영문 텍스트가 선명히 인쇄된 카드 영수증 이미지를 업로드했을 때,
   **When** 로컬 Tesseract OCR이 정상적으로 텍스트를 감지하고,
   **Then** 로컬 Ollama `gemma4:e4b` 모델이 텍스트로부터 가맹점명, 사업자번호, 결제시각, 금액, 세부 품목 리스트를 정확히 추출하여 `ReceiptSchema`로 구조화합니다.
2. **Given** Ollama 파싱 결과가 반환되었을 때,
   **When** 파싱된 세부 품목들의 합산 금액과 영수증의 총 결제금액이 정합성 검증 규칙을 완벽히 충족한다면,
   **Then** 2단계 및 3단계 클라우드 호출을 완전히 우회하고 즉시 가계부 데이터베이스 적재(create_ledger_transactional)를 완료하고 작업을 완료 상태(COMPLETED)로 마킹합니다.

---

### User Story 2 - Cloud Text-only Fallback for Broken Schemas (Priority: P2)

**Description**:
1단계 로컬 Ollama 모델의 결과가 깨진 JSON 형식이거나, 데이터 검증 단계에서 금액 정합성(Checksum) 검증에 실패한 경우, 이미 로컬 OCR 단계에서 획득해 둔 텍스트 본문만을 Gemini-2.5-Flash API로 전송하여 저비용 텍스트 분석 및 스키마 구조화를 시도합니다.

**Why this priority**:
텍스트 기반의 Gemini API 호출은 이미지 기반의 멀티모달 호출에 비해 토큰 사용량이 극히 적어 입력 토큰 비용을 95% 이상 절감하면서도, 상용 클라우드 LLM의 뛰어난 구조화 정밀도를 안정적으로 빌려 쓸 수 있는 비용 통제의 교량 역할을 합니다.

**Independent Test**:
로컬 Ollama 연동을 가짜 응답(JSON 붕괴 또는 금액 정합성 불일치)으로 모킹 처리한 상태에서 영수증 텍스트가 Gemini-2.5-Flash API 텍스트 전송 파이프라인을 정상 작동시키고 최종 구조화 데이터를 생성하는지 검증합니다.

**Acceptance Scenarios**:

1. **Given** 1단계 Ollama가 금액 정합성 검증에 실패한 결과를 반환하였을 때,
   **When** 시스템이 2단계 클라우드 텍스트 전용 폴백 파이프라인으로 전환되고,
   **Then** 이미 획득한 로컬 OCR 텍스트만을 Gemini-2.5-Flash API로 전송하여 다시 스키마 구조화를 완료하고 데이터베이스에 최종 저장합니다.

---

### User Story 3 - Cloud Vision Fallback for Failed OCR (Priority: P3)

**Description**:
영수증 원본의 해상도 저하, 기울어짐, 노이즈 등으로 인해 로컬 OCR(PyMuPDF/Tesseract) 단계에서 텍스트가 전혀 추출되지 않거나(0글자), 앞선 1단계 및 2단계 텍스트 기반 파싱이 모두 정합성 검증에 실패한 경우, 최후의 보루로서 영수증 원본 이미지(WebP 압축 버퍼) 또는 PDF 바이트 스트림을 Gemini-2.5-Flash 멀티모달(Vision) API로 직접 송신하여 높은 파싱 무결성을 확보합니다.

**Why this priority**:
비용 최적화도 중요하지만, 사용자 경험의 연속성을 저해하는 분석 실패(FAILED) 확률을 극소화하기 위한 최종적인 파싱 안전장치입니다.

**Independent Test**:
로컬 OCR이 한 글자도 추출하지 못하는 빈 이미지나 악성 PDF를 업로드했을 때, 시스템이 1, 2단계를 자동으로 우회/폴백하고 3단계 멀티모달 API를 직접 실행해 영수증을 안정적으로 파싱하는지 확인합니다.

**Acceptance Scenarios**:

1. **Given** 사용자가 흐릿하거나 텍스트 감지가 불가능한 영수증 이미지를 업로드하여 로컬 OCR의 반환값이 비어있을 때,
   **When** 시스템이 즉시 3단계 클라우드 비전 폴백을 수행하여 WebP 압축 이미지를 Gemini-2.5-Flash 멀티모달 API로 송신하고,
   **Then** 이미지 비주얼 정보를 바탕으로 정확한 가계부 `ReceiptSchema` 데이터를 반환받아 무결하게 적재합니다.

---

### User Story 4 - Legacy Regex Caching & Self-Healing Pipeline Cleanup (Priority: P1)

**Description**:
시스템의 오작동을 예방하고 아키텍처를 고도로 단순화하기 위해, 기존의 정적 정규식 기반 캐시 파이프라인(`BypassParser`, `MerchantTemplate` 캐싱, `promotion.py` 자동 승격, 자가 치유)과 관련된 코드 및 Celery 비동기 태스크들을 안전하게 비활성화하고 청소합니다.

**Why this priority**:
새로운 3단계 하이브리드 파이프라인과의 로직 충돌 및 불필요한 Celery 리소스 점유를 원천적으로 방지하고, 유지보수가 불가능한 동적 정규식 학습 엔진의 복잡성을 완전히 걷어내기 위함입니다.

**Independent Test**:
영수증 파싱 및 가계부 적재 E2E 테스트 실행 시, 기존의 정규식 제안/승격/자가치유 관련 로직 및 Celery 태스크가 더 이상 호출되지 않으며, 모든 테스트가 통과되는 것을 검증합니다.

**Acceptance Scenarios**:

1. **Given** 3단계 하이브리드 파이프라인을 거쳐 영수증 파싱이 완료되었을 때,
   **When** 데이터베이스 적재가 성공하더라도,
   **Then** `BypassParser` 캐시 매핑을 실행하지 않고, 신규 템플릿 후보군 생성(`propose_new_template`) 및 정규식 자동 검증 태스크(`verify_proposed_regex_task.delay`)를 트리거하지 않습니다.

---

### Edge Cases

- **Tesseract 및 PyMuPDF 미설치 또는 I/O 오류 발생**: 로컬 텍스트 추출이 불가능할 경우 예외를 삼키지 않고, `text_ocr_failed` 상태를 반환하여 1, 2단계를 안전하게 건너뛰고 3단계 Cloud Vision Fallback으로 신속히 이동합니다.
- **클라우드 API 키 미설정 또는 네트워크 단절**: Gemini API 호출 실패 시 작업이 먹통이 되지 않고 `failure_reason`에 구체적인 장애 정보를 기록한 후 `status = "FAILED"` 상태로 최종 종료됩니다.
- **이미지 리사이징Canvas/Pillow 도중 크기 손실**: 비전 폴백을 수행할 때 Pillow의 WebP 리사이징이 정상 작동하여 허용 데이터 크기(최대 1000px 등) 내로 원본 비주얼이 안전하게 래핑 및 전달되어야 합니다.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 시스템은 영수증 파일이 입력되었을 때 Local OCR -> Cloud Text-only -> Cloud Vision의 3단계 하이브리드 파싱 파이프라인을 순차적으로 수행해야 합니다.
- **FR-002**: 로컬 OCR 텍스트가 정상적으로 확보된 경우, 로컬 Ollama 모델(`gemma4:e4b`)의 비동기 호출을 통해 1차 파싱을 수행하여 유료 API 비용을 우회해야 합니다.
- **FR-003**: 시스템은 1단계 또는 2단계 파싱 결과에 대해 **금액 정합성(Checksum) 검증**을 강제 수행해야 합니다. 금액 정합성 검증은 상세 품목들의 합산 금액(`sum(item.total_price)`)이 영수증의 총 결제금액(`total_amount`)과 정확히 일치(차이 = 0)하는지 확인해야 합니다. 일치하지 않는 경우 검증 실패로 판단하여 다음 단계로 폴백합니다.
- **FR-004**: 1단계 로컬 파싱이 실패(스키마 붕괴, API 에러)하거나 금액 정합성 검증을 통과하지 못한 경우, 이미 확보된 텍스트만을 사용하여 Gemini-2.5-Flash API로 2단계 Text-only 파싱을 요청해야 합니다.
- **FR-005**: 로컬 OCR 결과가 비어있거나, 2단계 텍스트 전용 파싱마저 최종 실패한 경우 최후의 폴백으로 WebP 변환 이미지 또는 PDF 원본 바이너리를 사용하여 Gemini-2.5-Flash 멀티모달(Vision) API로 3단계 파싱을 태워야 합니다.
- **FR-006**: PDF 파일의 경우 3단계 진입 시 이미지 전처리(Pillow 변환)를 생략하고 PDF 바이너리 데이터를 직접 Gemini API의 `application/pdf` 파트를 통해 전달해야 합니다.
- **FR-007**: 기존 정적 정규식 기반 캐시 파이프라인(`BypassParser`, `MerchantTemplate` 캐싱, `promotion.py` 자동 승격, 자가 치유)과 관련된 호출 및 로직을 비활성화하고 청소합니다. 이때 기존 DB 테이블(`merchant_templates`, `template_execution_histories`) 및 장고 모델 스키마는 데이터 보존 및 마이그레이션 호환성을 위해 삭제하지 않고 유지하되, 관련 비즈니스 로직(BypassParser 매칭, promotion, self_healing) 코드 호출만 완전히 제거하고 무력화합니다.
- **FR-008**: 로컬 개발(`DEBUG=True`) 환경과 프로덕션(`DEBUG=False`) 환경에서의 API 키 유무에 따른 파이프라인 실행 제한 조건을 설계해야 합니다. 로컬 개발 환경(`DEBUG=True`)이더라도 `GEMINI_API_KEY` 환경변수가 정상적으로 제공되는 경우 2단계(클라우드 텍스트 폴백) 및 3단계(클라우드 비전 폴백) 동작과 테스트를 전면 허용합니다. 만약 API 키가 부재하는 경우에만 1단계(Ollama)만 기동하며, 실패 시 다음 단계로 넘어가지 않고 작업을 실패(`FAILED`) 처리합니다.
- **FR-009**: 가맹점 카테고리가 누락되거나 유효하지 않은 카테고리가 입력되는 경우 기본값을 '기타' 또는 '미분류'로 자동 강제 매핑 및 영속화하는 폴백 정책을 적용해야 합니다.

### Key Entities

- **ReceiptUploadJob**: 영수증 파싱 비동기 작업 정보를 추적 및 영속화합니다. (status: PENDING, PROCESSING, COMPLETED, FAILED)
- **Ledger & LedgerItem**: 단일 트랜잭션(`transaction.atomic()`) 내에서 원자적으로 생성되는 최종 가계부 내역 정보입니다.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 3단계 하이브리드 파이프라인 구축 후, 정상적인 텍스트 추출이 가능한 영수증에 대해 입력 이미지 토큰 전송 대비 Gemini API 비용을 **95% 이상 절감**해야 합니다.
- **SC-002**: 흐릿한 영수증을 포함한 전체 테스트 대상 영수증 파일에 대한 파싱 최종 성공률(1, 2, 3단계 합산)을 **99% 이상**으로 방어해야 합니다.
- **SC-003**: 템플릿 매핑, 승격 및 자가 치유 관련 Celery 비동기 태스크들의 신규 큐 적재 횟수를 **0건**으로 하향 조정하여 Celery 서버의 불필요한 리소스 오버헤드를 완전히 걷어내야 합니다.

## Assumptions

- **Ollama 실행 보장**: 로컬 개발 환경 혹은 개발/도커 환경에서는 Ollama 서비스(포트 11434)가 기동 중이고 `gemma4:e4b` 모델이 사전 다운로드되어 준비된 상태를 가정합니다.
- **API 자격 증명 관리**: 2, 3단계 클라우드 폴백 기동에 필요한 `GEMINI_API_KEY`는 코드에 노출하지 않고 `.env` 환경 변수 주입 방식으로 안전하게 조율합니다.
- **카테고리 폴백 매핑**: Pydantic DTO 스키마 제약에 따라 카테고리는 헌법에 지정된 한국 가계부 대분류(식비, 생활용품, 쇼핑 등)에 맞추어 강제 변환하며, 매핑이 불가능하거나 누락된 비정상 카테고리는 '기타'로 싱크하여 데이터베이스 제약을 충족시킵니다.
