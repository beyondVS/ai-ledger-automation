# Internal Service Interface Contract: Receipt Ingestion Pipeline

**Feature Branch**: `022-receipt-hybrid-pipeline`

본 문서는 영수증 파일 업로드 비동기 핸들러와 3단계 하이브리드 파이프라인 파서 간의 서비스 레이어 인터페이스 계약을 정의합니다.

---

## 1. 영수증 수집 서비스 인터페이스 (Ingestion Service)

### 1.1 `ingest_receipt` 메서드
* **호출 주체**: Celery 비동기 태스크 (`process_receipt_job_task`)
* **메서드 서명**:
  ```python
  def ingest_receipt(self, user: User, image_file: File, existing_job: ReceiptUploadJob = None) -> Ledger
  ```
* **동작 흐름**:
  1. `ReceiptUploadJob`을 조회하거나 생성합니다 (작업 상태는 `PROCESSING`으로 전이).
  2. 업로드된 영수증 파일(이미지 또는 PDF)에 대해 로컬 OCR(PyMuPDF/Tesseract)을 순차 구동해 1차 원시 텍스트를 추출합니다.
  3. 3단계 하이브리드 파이프라인의 분기를 가동하여 최종 `ReceiptSchema` DTO 데이터를 반환받습니다.
  4. 단일 DB 트랜잭션(`transaction.atomic()`) 내에서 `create_ledger_transactional` 서비스를 실행하여 가계부 마스터 및 세부 품목 테이블에 원자적으로 적재합니다.
  5. `ReceiptUploadJob`의 상태를 `COMPLETED`로 변경하고, 생성된 `Ledger` 인스턴스를 반환합니다.
  6. 예외 발생 시, `ReceiptUploadJob` 상태를 `FAILED`로 변경하고 실패 사유(`failure_reason`)를 기입한 뒤 예외를 안전하게 마무리합니다.

---

## 2. 하이브리드 파서 인터페이스 (Hybrid Parser)

### 2.1 `ReceiptLLMClient`
3단계 하이브리드 파싱을 관장하는 핵심 클라이언트 모듈입니다.
* **메서드 서명 (1단계: Local Ollama)**:
  ```python
  def parse_receipt_local(self, raw_ocr_text: str) -> ReceiptSchema | None
  ```
  * 입력받은 OCR 원시 텍스트만을 로컬 Ollama `gemma4:e4b` 모델로 구조화합니다.
* **메서드 서명 (2단계: Cloud Text-only)**:
  ```python
  def parse_receipt_cloud_text(self, raw_ocr_text: str) -> ReceiptSchema | None
  ```
  * 입력받은 OCR 원시 텍스트만을 Gemini-2.5-Flash API로 송신하여 구조화합니다.
* **메서드 서명 (3단계: Cloud Vision)**:
  ```python
  def parse_receipt_cloud_vision(self, file_buffer: io.BytesIO, mime_type: str) -> ReceiptSchema | None
  ```
  * 영수증 파일의 원본(WebP 압축 버퍼 또는 PDF 바이트)과 프롬프트를 Gemini-2.5-Flash 멀티모달 API로 송신하여 구조화합니다.

### 2.2 파싱 결과 및 예외 핸들링 계약
* 1단계 또는 2단계의 파싱 결과가 성공한 경우, 반드시 상세 품목 합산 정합성 검사(`sum(item.total_price) == total_amount`)를 충족해야 최종 성공으로 처리되어 DB 적재에 진입합니다.
* 금액 검증 실패 또는 스키마 붕괴 예외 감지 시, 에러를 반환하여 즉각 다음 단계 폴백으로 제어권을 이식해야 합니다.
