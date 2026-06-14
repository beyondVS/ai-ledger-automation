# API Contract: 대시보드 통계 통합 API (`/api/ledgers/dashboard/`)

본 API는 대시보드 화면에 진입하거나 조회 기간을 동적으로 필터링할 때 필요한 모든 시각화 데이터를 단일 DTO로 압축하여 초고속 반환(목표 응답 100ms 이내)하기 위한 엔드포인트 계약입니다.

## 1. 개요
* **경로(Path)**: `/api/ledgers/dashboard/`
* **메서드(Method)**: `GET`
* **인증(Authentication)**: 필요 (세션 또는 JWT Bearer 토큰)

## 2. 요청 파라미터 (Query Parameters)

| 파라미터명 | 타입 | 필수 여부 | 기본값 | 설명 |
|:---|:---:|:---:|:---:|:---|
| **`months`** | Integer | 선택 | `3` | 월별 지출 흐름 막대 차트에서 시각화할 최근 개월 수 (허용값: `3`, `6`, `12` 등) |

---

## 3. 응답 페이로드 (Response Payload - `200 OK`)

```json
{
  "budget": {
    "amount": 1000000,
    "spent_amount": 300000,
    "remaining_amount": 700000,
    "spent_ratio": 30.0,
    "status": "safe"
  },
  "category_spending": [
    {
      "category_name": "식비",
      "amount": 200000,
      "ratio": 66.7
    },
    {
      "category_name": "교통비",
      "amount": 50000,
      "ratio": 16.7
    },
    {
      "category_name": "미분류",
      "amount": 50000,
      "ratio": 16.7
    }
  ],
  "monthly_trends": [
    {
      "month": "2026-04",
      "amount": 850000
    },
    {
      "month": "2026-05",
      "amount": 920000
    },
    {
      "month": "2026-06",
      "amount": 300000
    }
  ],
  "top_merchants": [
    {
      "merchant_name": "스타벅스 강남점",
      "amount": 150000,
      "rank": 1
    },
    {
      "merchant_name": "쿠팡",
      "amount": 100000,
      "rank": 2
    },
    {
      "merchant_name": "카카오택시",
      "amount": 50000,
      "rank": 3
    }
  ]
}
```

### 필드 상세 설명

#### `budget` (예산 게이지용 정보)
* `amount`: 당월 설정된 총 예산 금액
* `spent_amount`: 당월 누적 총지출액
* `remaining_amount`: 남은 예산액 (`amount - spent_amount`). 예산 초과 시 음수 반환 가능
* `spent_ratio`: 소진율 (`spent_amount / amount * 100`)
* `status`: 게이지의 시각 상태 정보. `safe` (소진율 50% 미만), `warning` (50%~80%), `danger` (80% 초과)

#### `category_spending` (카테고리별 원형 차트용 정보)
* `category_name`: 카테고리 명칭 (비어있는 경우 '미분류'로 매핑)
* `amount`: 해당 카테고리의 당월 지출 합계
* `ratio`: 당월 총지출 대비 비율 (%)

#### `monthly_trends` (월별 지출 흐름 막대 차트용 정보)
* `month`: 연월 정보 (`YYYY-MM`)
* `amount`: 해당 월의 총 지출 합산액

#### `top_merchants` (TOP 3 가맹점 요약 정보)
* `merchant_name`: 가맹점명
* `amount`: 해당 가맹점의 당월 총 지출액
* `rank`: 순위 (1~3)
