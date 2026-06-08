# Task Contract: Celery Task Payload & Lifecycle

본 문서에서는 Django 메인 서버가 Celery 메시지 브로커(Redis)로 디스패치하고 백그라운드 워커가 소비하는 비동기 태스크의 서명(Signature) 및 메시지 스키마 계약을 정의합니다.

---

## 1. Celery Task 서명 (Signature)

영수증의 텍스트 추출 및 OCR 분석을 수행하는 비동기 태스크는 다음 규격을 따릅니다.

* **Task Name**: `apps.tasks.tasks.extract_receipt_text_task`
* **Argument Signature**:
  - `job_id`: `str` (UUIDv7 string) - 필수. 작업 상태 조회를 위한 LedgerJob의 PK.
  - `file_path`: `str` (String) - 필수. 웹서버 인입 시 업로드되어 디스크/스토리지에 임시 보관된 영수증 파일의 절대/상대 경로.

---

## 2. 메시지 페이로드 스키마 (Message Payload Schema)

Redis 메시지 브로커를 거쳐 전달되는 JSON 직렬화된 실제 메시지 바디 구조입니다.

```json
{
  "task": "apps.tasks.tasks.extract_receipt_text_task",
  "id": "e30b427b-2329-4d69-b1d8-f80e0717208d",
  "args": [
    "018f3a38-c64a-7182-bcf8-94ef93cf0001",
    "uploads/receipts/20260608_175500_temp.jpg"
  ],
  "kwargs": {},
  "retries": 0,
  "eta": null
}
```

---

## 3. 백그라운드 태스크 처리 흐름 및 재시도 계약 (Retry & Exception Handling Contract)

Celery 백그라운드 워커는 메시지를 수신하면 아래의 단계에 따라 상태 업데이트 및 비즈니스 연산을 수행합니다.

### 3.1 시작 처리
- 태스크 진입 즉시 데이터베이스의 `LedgerJob`을 조회하여 `status`를 `PROCESSING`으로 업데이트하고 저장합니다.

### 3.2 텍스트 추출 및 AI 분석 가동
- `file_path`의 파일을 읽어 이미지 전처리 및 OCR/Gemini API 연산을 구동합니다.

### 3.3 성공 및 트랜잭션 바인딩
- 분석에 성공하면, 생성될 가계부 정보(`Ledger` 및 `LedgerItem`)를 구성합니다.
- **트랜잭션 세션 보장**:
  - Django `transaction.atomic()` 세션 내에서 `Ledger` 마스터와 `LedgerItem` 어레이 레코드를 원자적으로 저장합니다.
  - 저장된 `Ledger` 인스턴스의 ID를 `LedgerJob.ledger_id`에 바인딩하고, `status`를 `SUCCESS`로 마킹하여 데이터베이스에 최종 저장(커밋)합니다.
  - 완료 시, 임시 가동된 `file_path` 경로의 영수증 이미지/PDF 파일은 스토리지 정리기(Garbage Collector)에 의해 안전하게 삭제됩니다.

### 3.4 예외 발생 및 재시도 정책
- 외부 네트워크 타임아웃, OCR API 일시 장해 등 **복구 가능한 임시 장애**가 감지된 경우:
  - Celery의 `self.retry()` 기능을 가동합니다.
  - **재시도 규칙 (FR-005)**:
    - **최대 재시도 횟수**: 3회 (`max_retries=3`)
    - **백오프 간격**: 지수 백오프 적용 (예: 1회차 실패 시 2초 대기, 2회차 4초 대기, 3회차 8초 대기 후 재시도)
- **복구 불가능한 비즈니스 예외** (예: 파일 파손, 잘못된 형식 등) 또는 **최대 재시도 횟수를 초과**한 경우:
  - 트랜잭션을 완전 롤백(Rollback)합니다.
  - `LedgerJob`의 `status`를 `FAILED`로 마킹하고, 예외 스택 및 에러 요약 정보를 `failure_reason`에 채워 데이터베이스에 영속화합니다.
  - 작업 실패 로깅을 발생시킵니다.
