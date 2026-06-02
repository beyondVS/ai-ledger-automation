# Quickstart: Upload API Integration & Async Schema Design

이 문서는 프론트엔드 업로드 동작부와 동기식 Django API 연동, 클라이언트 가상 폴링 및 Canvas 압축 기능을 빠르게 빌드하고 테스트하기 위한 퀵스타트 가이드입니다.

---

## 1. Frontend Client Integration Example

### HTML5 Canvas 1차 이미지 압축 (가로 1000px)
```javascript
/**
 * HTML5 Canvas를 이용해 이미지를 가로 최대 1000px로 축소하고 JPEG Blob으로 변환합니다.
 * @param {File} file - 업로드할 원본 이미지 파일
 * @returns {Promise<Blob>} - 압축된 이미지 Blob
 */
async function compressImage(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = (event) => {
      const img = new Image();
      img.src = event.target.result;
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');

        const MAX_WIDTH = 1000;
        let width = img.width;
        let height = img.height;

        if (width > MAX_WIDTH) {
          height = Math.round((height * MAX_WIDTH) / width);
          width = MAX_WIDTH;
        }

        canvas.width = width;
        canvas.height = height;
        ctx.drawImage(img, 0, 0, width, height);

        canvas.toBlob(
          (blob) => {
            if (blob) {
              resolve(blob);
            } else {
              reject(new Error("Canvas compression failed"));
            }
          },
          'image/jpeg',
          0.85 // 압축 품질
        );
      };
      img.onerror = (err) => reject(err);
    };
    reader.onerror = (err) => reject(err);
  });
}
```

### 클라이언트 가상 폴링 대기 루프 (Virtual Polling Module)
```javascript
class VirtualPollingManager {
  /**
   * 영수증 작업의 상태를 조회하거나 대기 루프를 구동합니다.
   * @param {string} jobId - 작업 고유 ID
   * @param {string} initialStatus - 초기 반환 상태 ("COMPLETED", "PROCESSING" 등)
   * @param {function} onComplete - 완료 시 콜백
   * @param {function} onError - 에러 시 콜백
   */
  static startPolling(jobId, initialStatus, onComplete, onError) {
    if (initialStatus === 'COMPLETED') {
      // MVP 동기 모드: 지연 없이 즉시 완료 처리
      onComplete();
      return;
    }

    // 3주차 비동기 대비 가상/실제 폴링 루프
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/v1/receipts/status/${jobId}/`);
        const result = await response.json();

        if (result.status === 'COMPLETED') {
          clearInterval(interval);
          onComplete(result.data);
        } else if (result.status === 'FAILED') {
          clearInterval(interval);
          onError(result.error);
        }
      } catch (err) {
        clearInterval(interval);
        onError(err);
      }
    }, 1000); // 1초 간격 상태 확인
  }
}
```

---

## 2. API Server Testing (curl)

### 동기식 영수증 업로드 요청 (Mock Data 생성)
```bash
curl -X POST http://localhost:8000/api/v1/receipts/upload/ \
  -H "Authorization: Bearer <token>" \
  -F "file=@receipt_sample.jpg"
```

### 비동기 작업 상태 조회 요청 (GET)
```bash
curl -X GET http://localhost:8000/api/v1/receipts/status/<job_id>/ \
  -H "Authorization: Bearer <token>"
```

**응답 예시 (PROCESSING/PENDING):**
```json
{
  "job_id": "019e8a8f-202d-7db2-abcf-2c07ff2fb543",
  "status": "PROCESSING",
  "data": null
}
```

**응답 예시 (COMPLETED - 가계부 마스터 및 품목 세부 스키마 완벽 연동):**
```json
{
  "job_id": "019e8a8f-202d-7db2-abcf-2c07ff2fb543",
  "status": "COMPLETED",
  "data": {
    "ledger_id": "019e8a8f-755a-73ab-80a2-276b0cb6b631",
    "merchant_name": "스타벅스",
    "vendor_registration_number": "1208612345",
    "transaction_date": "2026-06-03",
    "total_amount": "15000.00",
    "supply_value": "13636.36",
    "vat_amount": "1363.64",
    "items": [
      {
        "id": "019e8a8f-755c-73ab-80a2-276b0cb6b632",
        "item_name": "아이스 아메리카노",
        "quantity": 2,
        "unit_price": "5000.00",
        "total_price": "10000.00"
      }
    ]
  }
}
```

---

## 3. 백엔드 테스트 실행 방법 (pytest)
헌법 제VIII조에 의거하여 데이터베이스 연합 테스트 및 하이브리드 검증을 pytest를 활용해 실행합니다.
```bash
# Docker Compose 환경 내 백엔드 테스트 스위트 구동
docker compose exec api_server pytest tests/
```
