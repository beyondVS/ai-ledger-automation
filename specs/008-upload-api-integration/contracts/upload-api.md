# API Contract: Receipt Upload and Status Polling

## 1. Receipt Upload Endpoint

### Endpoint Details
- **Method**: `POST`
- **Path**: `/api/v1/receipts/upload/`
- **Content-Type**: `multipart/form-data`

### Request Parameters
- **Headers**:
  - `Authorization`: `Bearer <token>` (필요 시 세션 및 JWT 토큰 인증 검증)
- **Body**:
  - `file` (Binary File, Required): 사용자가 1차 압축(HTML5 Canvas, 가로 최대 1000px)하여 전송한 영수증 이미지 파일 (PNG, JPEG 등)

### Response 1: 200 OK (동기식 즉시 완료 - v1 MVP 단계)
- **Content-Type**: `application/json`
- **Body Schema**:
  ```json
  {
    "job_id": "018f3d6c-6a9b-7c1d-8f2e-3c4d5e6f7a8b",
    "status": "COMPLETED",
    "data": {
      "ledger_id": "97e6a71e-0cf2-4aeb-8321-9e797ba9cde2",
      "merchant_name": "스타벅스 역삼역점",
      "vendor_registration_number": "1208612345",
      "transaction_date": "2026-06-03",
      "total_amount": 15000.00,
      "items": [
        {
          "name": "아이스 아메리카노",
          "quantity": 2,
          "price": 5000.00
        },
        {
          "name": "초콜릿 칩 스콘",
          "quantity": 1,
          "price": 5000.00
        }
      ]
    }
  }
  ```

### Response 2: 202 Accepted (비동기 처리 수락 - v2 백그라운드 Celery 연동 단계용)
- **Content-Type**: `application/json`
- **Body Schema**:
  ```json
  {
    "job_id": "018f3d6c-6a9b-7c1d-8f2e-3c4d5e6f7a8b",
    "status": "PROCESSING",
    "data": null
  }
  ```

---

## 2. Receipt Status Polling Endpoint (3주차 대응 가상 인터페이스)

프론트엔드 가상 폴링 모듈이 상태 조회를 진행할 수 있도록 미리 명세를 규정합니다.

### Endpoint Details
- **Method**: `GET`
- **Path**: `/api/v1/receipts/status/<job_id>/`
- **Path Parameters**:
  - `job_id` (UUID, Required): 상태를 조회할 작업 고유 식별자

### Response 1: 200 OK (처리 진행 중)
- **Body Schema**:
  ```json
  {
    "job_id": "018f3d6c-6a9b-7c1d-8f2e-3c4d5e6f7a8b",
    "status": "PROCESSING",
    "data": null
  }
  ```

### Response 2: 200 OK (처리 완료)
- **Body Schema**:
  ```json
  {
    "job_id": "018f3d6c-6a9b-7c1d-8f2e-3c4d5e6f7a8b",
    "status": "COMPLETED",
    "data": {
      "ledger_id": "97e6a71e-0cf2-4aeb-8321-9e797ba9cde2",
      "merchant_name": "스타벅스 역삼역점",
      "vendor_registration_number": "1208612345",
      "transaction_date": "2026-06-03",
      "total_amount": 15000.00,
      "items": [
        {
          "name": "아이스 아메리카노",
          "quantity": 2,
          "price": 5000.00
        }
      ]
    }
  }
  ```

### Response 3: 200 OK (처리 실패)
- **Body Schema**:
  ```json
  {
    "job_id": "018f3d6c-6a9b-7c1d-8f2e-3c4d5e6f7a8b",
    "status": "FAILED",
    "data": null,
    "error": {
      "code": "OCR_PARSING_ERROR",
      "message": "영수증 이미지에서 텍스트를 추출하는 데 실패했습니다."
    }
  }
  ```
