# API Interface Contract

**Feature**: Dashboard Ledger List and Detail Accordion Component

본 계약서는 프론트엔드 대시보드와 백엔드 API 간의 데이터 연동 규격을 문서화합니다. 가계부 리스트 조회 및 비동기 업로드 진행 상황 조회를 위한 REST API 스키마를 정의합니다.

## 1. Authentication
모든 API 요청은 10일차에 연동 완료된 JWT 인증 체계를 탑재해야 합니다.
* **HTTP Header 필수 항목**:
  ```http
  Authorization: Bearer <JWT_ACCESS_TOKEN>
  ```
* **인증 실패 처리 (401 Unauthorized)**:
  유효하지 않거나 만료된 토큰인 경우 백엔드는 `401` 코드를 반환하며, 프론트엔드는 세션을 정리하고 로그인 화면으로 리디렉션 처리해야 합니다.

---

## 2. API Endpoints

### 2.1. 가계부 리스트 조회 (Get Ledger List)
로그인한 사용자 본인의 당월(현재 월) 기준 가계부 목록을 최신 결제일순으로 일괄 조회합니다. 아코디언 컴포넌트 즉시 렌더링을 위해 각 가계부 항목 하위에 상세 품목(`items` 배열)을 동봉합니다.

* **URL**: `/api/v1/receipts/`
* **Method**: `GET`
* **Query Parameters**: 없음 (백엔드 내부적으로 현재 날짜 기준의 당월 범위 자동 필터)
* **Response (200 OK)**:
  ```json
  [
    {
      "id": "01944e8d-88f5-7c1c-9226-eb52c6f1a8e1",
      "vendor_name": "스타벅스 역삼역점",
      "vendor_registration_number": "1208112345",
      "transaction_date": "2026-06-07",
      "total_amount": "13500.00",
      "supply_value": "12272.73",
      "vat_amount": "1227.27",
      "created_at": "2026-06-07T16:30:00Z",
      "updated_at": "2026-06-07T16:30:00Z",
      "items": [
        {
          "name": "아이스 아메리카노",
          "quantity": 2,
          "price": "4500.00"
        },
        {
          "name": "클래식 스콘",
          "quantity": 1,
          "price": "4500.00"
        }
      ]
    }
  ]
  ```

---

### 2.2. 영수증 업로드 상태 조회 (Get Receipt Job Status)
비동기적으로 진행 중인 영수증 파싱 분석 작업의 실시간 상태를 폴링하기 위한 엔드포인트입니다.

* **URL**: `/api/v1/receipts/status/<uuid:job_id>/`
* **Method**: `GET`
* **Response (200 OK - PENDING / PROCESSING 상태)**:
  ```json
  {
    "job_id": "01944e8d-99f5-7c1c-9226-eb52c6f1a8e2",
    "status": "PENDING",
    "data": null
  }
  ```
* **Response (200 OK - COMPLETED 상태)**:
  ```json
  {
    "job_id": "01944e8d-99f5-7c1c-9226-eb52c6f1a8e2",
    "status": "COMPLETED",
    "data": {
      "ledger_id": "01944e8d-88f5-7c1c-9226-eb52c6f1a8e1",
      "merchant_name": "스타벅스 역삼역점",
      "vendor_registration_number": "1208112345",
      "transaction_date": "2026-06-07",
      "total_amount": "13500.00",
      "items": [
        {
          "name": "아이스 아메리카노",
          "quantity": 2,
          "price": "4500.00"
        },
        {
          "name": "클래식 스콘",
          "quantity": 1,
          "price": "4500.00"
        }
      ]
    }
  }
  ```
