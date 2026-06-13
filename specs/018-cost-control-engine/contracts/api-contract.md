# API Contract: Cost Control Engine Core Implementation

## API Specifications

### 1. 영수증 업로드 & 분석 접수 API
사용자가 영수증 파일(이미지 또는 PDF)을 업로드하여 가계부 분석을 요청하는 엔드포인트입니다. 정적 우회 파서 매칭 성공 시 즉각 동기 처리(201)되며, 미매칭 또는 우회 실패 시 비동기 Celery 태스크로 전환(202)됩니다.

* **Endpoint**: `POST /api/ledgers/upload/`
* **Content-Type**: `multipart/form-data`
* **Request Body**:
  * `file`: Binary (영수증 PDF 또는 이미지 파일)

* **Response (201 Created - 우회 Bypass 즉시 파싱 성공 시)**:
  ```json
  {
    "status": "COMPLETED",
    "job_id": null,
    "ledger": {
      "id": "78b7b25e-e47d-419b-a3d5-e23fa2031c2e",
      "merchant_name": "스타벅스 역삼점",
      "business_number": "1208612345",
      "total_amount": 13800.0,
      "transaction_date": "2026-06-11T14:30:00+09:00",
      "approval_number": "30012948"
    },
    "message": "검증 완료된 가맹점 템플릿(Bypass)을 사용하여 동기식 파싱 및 가계부 적재가 즉각 완료되었습니다."
  }
  ```

* **Response (202 Accepted - LLM 폴백 또는 최초 분석 비동기 전환 시)**:
  ```json
  {
    "status": "PENDING",
    "job_id": "41680d0d-b152-47ef-b4b7-d1cb7f6bc90e",
    "message": "영수증 백그라운드 분석 및 LLM 폴백 파이프라인이 정상 접수되었습니다. 제공된 job_id로 상태를 폴링하십시오."
  }
  ```

---

### 2. 비동기 분석 작업 상태 폴링 API
비동기로 전환된 Celery 영수증 분석 작업의 현재 진행 상태를 조회합니다.

* **Endpoint**: `GET /api/ledgers/jobs/<uuid:job_id>/`
* **Response (200 OK - 처리 대기 또는 분석 진행 중)**:
  ```json
  {
    "status": "PENDING",
    "job_id": "41680d0d-b152-47ef-b4b7-d1cb7f6bc90e",
    "result": null
  }
  ```

* **Response (200 OK - 백그라운드 분석 및 가계부 적재 완료)**:
  ```json
  {
    "status": "COMPLETED",
    "job_id": "41680d0d-b152-47ef-b4b7-d1cb7f6bc90e",
    "result": {
      "ledger_id": "78b7b25e-e47d-419b-a3d5-e23fa2031c2e",
      "merchant_name": "이마트 역삼점",
      "business_number": "2208112345",
      "total_amount": 45800.0,
      "transaction_date": "2026-06-11T12:00:00+09:00"
    }
  }
  ```

* **Response (200 OK - 작업 실패 및 예외 로그)**:
  ```json
  {
    "status": "FAILED",
    "job_id": "41680d0d-b152-47ef-b4b7-d1cb7f6bc90e",
    "error": "LLM 폴백 분석 엔진 가동 중 API 한도 초과 오류가 발생하였습니다. 데이터베이스 트랜잭션이 안전하게 롤백되었습니다."
  }
  ```

---

### 3. 어드민 가맹점 템플릿 규칙 수동 승인 API
자가 학습 파이프라인을 거쳐 자동으로 제안된 미검증 템플릿(`is_verified: false`)의 정규식 매칭 정합성을 확인한 후 최종 승인합니다.

* **Endpoint**: `POST /api/admin/merchant-templates/<uuid:template_id>/verify/`
* **Content-Type**: `application/json`
* **Request Body**:
  ```json
  {
    "is_verified": true,
    "rules": {
      "total_amount_regex": "합계\\s*([0-9,]+)",
      "transaction_date_regex": "일자\\s*([0-9\\.\\-]+)",
      "items_regex": "품명\\s*(.+?)\\s*단가"
    }
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "template_id": "e2f12345-bcde-4f01-8b90-123456789abc",
    "is_verified": true,
    "message": "가맹점 템플릿이 성공적으로 승인되었으며, 차기 동일 가맹점의 영수증 파싱 요청부터 LLM 호출 우회(Bypass) 처리가 실행됩니다."
  }
  ```
