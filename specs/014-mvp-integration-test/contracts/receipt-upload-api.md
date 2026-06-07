# API Contract: Receipt Upload API (Synchronous MVP)

본 문서는 Vue 3 프론트엔드와 Django 백엔드 간의 영수증 이미지 업로드 및 동기식 가계부 생성 API 스키마를 정의합니다.

## Endpoint Overview

* **Path**: `/api/v1/ledgers/upload/`
* **Method**: `POST`
* **Content-Type**: `multipart/form-data`
* **Authentication**: JWT Bearer Token (`Authorization: Bearer <JWT_TOKEN>`)

---

## Request Specification

### Request Body (Multipart-form)

| Field Name | Type | Required | Description |
|------------|------|----------|-------------|
| `image`    | File (Binary) | Yes | Canvas API를 통해 가로 폭 최대 1000px, Quality 0.8 JPEG로 1차 압축 인코딩된 영수증 이미지 파일 |

---

## Response Specification

### 1. HTTP 200 OK (성공 및 가계부 적재 완료)
3주차 비동기 구조 전환에 대비하여 프론트엔드가 호환성을 유지할 수 있도록 `status: "COMPLETED"`, `job_id: null` 스키마 구조를 필수로 포함합니다.

```json
{
  "status": "COMPLETED",
  "job_id": null,
  "ledger": {
    "id": "018ff39d-2b4a-7bc9-8e43-a60d00000001",
    "vendor_name": "스타벅스 역삼대로점",
    "vendor_registration_number": "1208612345",
    "transaction_date": "2026-06-07T12:34:56Z",
    "total_amount": 15000.00,
    "items": [
      {
        "id": "018ff39d-2b4a-7bc9-8e43-a60d00000002",
        "item_name": "카페아메리카노 Tall",
        "unit_price": 4500.00,
        "quantity": 2,
        "amount": 9000.00
      },
      {
        "id": "018ff39d-2b4a-7bc9-8e43-a60d00000003",
        "item_name": "부드러운 생크림 카스텔라",
        "unit_price": 6000.00,
        "quantity": 1,
        "amount": 6000.00
      }
    ]
  }
}
```

### 2. HTTP 409 Conflict (중복 업로드 차단)
`UNIQUE (user_id, vendor_registration_number, transaction_date, total_amount)` 제약조건에 의해 동일 영수증에 대한 중복 업로드가 탐지되어 차단되었을 때의 응답입니다.

```json
{
  "error_code": "DUPLICATE_RECEIPT",
  "message": "이미 등록된 결제 내역의 영수증입니다."
}
```

### 3. HTTP 422 Unprocessable Entity (파싱 실패 또는 데이터 유효성 검사 실패)
Gemini API OCR 분석 결과 필수 필드(가맹점명, 결제금액 등) 획득 실패 혹은 기타 비즈니스 검증 실패 시의 응답입니다. 트랜잭션은 롤백 처리된 상태입니다.

```json
{
  "error_code": "PARSING_FAILED",
  "message": "영수증 이미지 분석 또는 데이터 파싱에 실패했습니다."
}
```

### 4. HTTP 500 Internal Server Error (Gemini API 장애 혹은 기타 백엔드 치명적 에러)
외부 API 통신 장애 혹은 인프라 시스템 오류로 정상 처리가 불가능한 상태입니다.

```json
{
  "error_code": "SERVER_ERROR",
  "message": "서버 내부 처리 중 장해가 발생했습니다."
}
```
