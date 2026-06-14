# API Contract: 월별 예산 관리 API (`/api/budgets/`)

본 API는 사용자가 대시보드 또는 설정 화면에서 월별 지출 예산 금액을 설정, 수정, 조회하기 위한 계약 명세입니다.

## 1. 개요
* **경로(Path)**: `/api/budgets/`
* **인증(Authentication)**: 필요 (세션 또는 JWT Bearer 토큰)

---

## 2. 예산 설정/수정 (`POST`)

특정 월의 예산을 새로 생성하거나 이미 존재하는 경우 수정(Upsert)을 동시 처리합니다. (또는 RESTful하게 `POST`로 신규 생성, `PATCH`로 부분 수정을 지원할 수 있으나, 편의 및 중복 방지를 위해 서버가 Upsert 로직을 내장하는 것을 권장합니다.)

### 요청 바디 (Request Body - JSON)

```json
{
  "budget_month": "2026-06",
  "amount": 1200000
}
```

* `budget_month`: 예산을 설정하고자 하는 연월 (`YYYY-MM` 규격)
* `amount`: 설정할 예산 총액 (Decimal, 0 이상의 양수)

### 응답 페이로드 (Response Payload - `200 OK` 또는 `201 Created`)

```json
{
  "id": "018fcc18-2e40-7ab3-8e4d-52825d19c3b1",
  "budget_month": "2026-06-01",
  "amount": 1200000,
  "created_at": "2026-06-14T03:32:00Z",
  "updated_at": "2026-06-14T03:32:00Z"
}
```

---

## 3. 예산 조회 (`GET`)

특정 월의 예산 설정을 단건 조회합니다.

### 요청 파라미터 (Query Parameters)

| 파라미터명 | 타입 | 필수 여부 | 기본값 | 설명 |
|:---|:---:|:---:|:---:|:---|
| **`month`** | String | 필수 | - | 조회하고자 하는 연월 (`YYYY-MM` 규격) |

### 응답 페이로드 (Response Payload - `200 OK`)

```json
{
  "id": "018fcc18-2e40-7ab3-8e4d-52825d19c3b1",
  "budget_month": "2026-06-01",
  "amount": 1200000,
  "created_at": "2026-06-14T03:32:00Z",
  "updated_at": "2026-06-14T03:32:00Z"
}
```

* 해당 월의 예산 데이터가 데이터베이스에 존재하지 않는 경우, 서버는 기본 예산(예: `1,000,000`원) 또는 `404 Not Found`가 아닌 기본값 응답 구조(또는 Default Budget DTO)를 반환하거나 HTTP `200 OK`에 `amount: 1000000` 기본값을 담아 내려보내 프론트의 폴백 처리를 돕습니다.

---

## 4. 예외 및 에러 처리

### `400 Bad Request`
* **요청 예산이 음수인 경우 (`amount < 0`)**
  ```json
  {
    "amount": ["예산 금액은 0원 이상이어야 합니다."]
  }
  ```
* **연월 포맷 형식이 유효하지 않은 경우**
  ```json
  {
    "budget_month": ["올바른 연월 형식(YYYY-MM)이 아닙니다."]
  }
  ```
