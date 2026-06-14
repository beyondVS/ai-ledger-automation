# API Contract: 가계부 다차원 필터링 및 캘린더 요약 API

본 문서는 상호명, 카테고리, 기간, 금액 복합 필터를 적용하여 가계부 거래 목록 및 월별 캘린더 지출 요약을 획득하기 위한 API 계약 사양을 정의합니다.

---

## 1. 다차원 필터링 거래 목록 조회 API

* **HTTP Method**: `GET`
* **URL**: `/api/v1/ledgers/`
* **Authentication**: `Bearer JWT Token`
* **Content-Type**: `application/json`

### Query Parameters

| 파라미터명 | 데이터 타입 | 필수 여부 | 설명 |
| :--- | :--- | :--- | :--- |
| `q` | `String` | 선택 | 상호명 텍스트 검색어 (부분 일치) |
| `categories` | `String` | 선택 | 복수 카테고리 UUID 리스트 (쉼표로 구분, 예: `uuid1,uuid2`) |
| `start_date` | `String (YYYY-MM-DD)` | 선택 | 조회 기간 시작일 |
| `end_date` | `String (YYYY-MM-DD)` | 선택 | 조회 기간 종료일 |
| `min_amount` | `Decimal` | 선택 | 최소 결제 금액 범위 |
| `max_amount` | `Decimal` | 선택 | 최대 결제 금액 범위 |

### 성공 응답 (HTTP 200 OK)

사용자 고유 타임존 오프셋 기준으로 변환 완료된 거래일시 및 DTO 리스트가 반환됩니다.

```json
{
  "status": "success",
  "data": {
    "results": [
      {
        "id": "e830c25a-4e8c-7ad8-8001-cf5e197d197a",
        "transaction_datetime": "2026-06-14T15:30:00+09:00",
        "vendor_name": "스타벅스 강남점",
        "category": {
          "id": "c12a7bd8-5e8c-8bd9-9002-df6e297d297b",
          "name": "식비"
        },
        "total_amount": 12500.00,
        "currency": "KRW",
        "approval_number": "12345678"
      }
    ],
    "count": 1
  }
}
```

---

## 2. 월별 캘린더 요약 조회 API

달력 그리드(Grid)에 일자별 총액과 지출 건수를 고속 렌더링하기 위한 집계 전용 API입니다.

* **HTTP Method**: `GET`
* **URL**: `/api/v1/ledgers/calendar/`
* **Authentication**: `Bearer JWT Token`

### Query Parameters

| 파라미터명 | 데이터 타입 | 필수 여부 | 설명 |
| :--- | :--- | :--- | :--- |
| `year` | `Integer` | 필수 | 조회 대상 연도 (예: `2026`) |
| `month` | `Integer` | 필수 | 조회 대상 월 (예: `6`, 1~12) |
| `q` | `String` | 선택 | (목록 연동용) 상호명 검색어 |
| `categories` | `String` | 선택 | (목록 연동용) 복수 카테고리 UUID 리스트 |
| `min_amount` | `Decimal` | 선택 | (목록 연동용) 최소 결제 금액 범위 |
| `max_amount` | `Decimal` | 선택 | (목록 연동용) 최대 결제 금액 범위 |

* **시간대 기준**: 날짜 분할 기준은 전적으로 사용자의 활성 타임존 로컬 일자를 기준으로 집계되어야 합니다.

### 성공 응답 (HTTP 200 OK)

사용자 설정 타임존 오프셋 기준으로 각 로컬 일자(Date)별 총 지출액 합계와 건수를 맵 형태로 반환합니다. 외화 결제 내역(USD 등)이 존재할 경우 기본 통화(KRW)로 자동 환산하여 합산 표시됩니다.

```json
{
  "status": "success",
  "data": {
    "year": 2026,
    "month": 6,
    "daily_summaries": {
      "2026-06-01": {
        "total_amount": 54000.00,
        "count": 2
      },
      "2026-06-14": {
        "total_amount": 12500.00,
        "count": 1
      }
    },
    "monthly_total": 66500.00
  }
}
```
