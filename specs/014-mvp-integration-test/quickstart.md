# Quickstart Guide: MVP Integration Test

본 문서는 개발자가 MVP Integration Test 기능 개발 환경을 셋업하고, 구현된 API와 프론트엔드 연동을 로컬에서 검증하는 단계별 가이드를 제공합니다.

---

## 1. Local Environment Setup

### 1.1 Local Database Running
PostgreSQL 데이터베이스 컨테이너를 기동합니다.
```powershell
# Windows PowerShell
docker compose -f docker-compose.db.yml up -d
```
```bash
# macOS/Linux
docker compose -f docker-compose.db.yml up -d
```

### 1.2 Python Virtual Environment Sync
`uv`를 통해 백엔드 의존성 및 패키지를 격리된 가상 환경과 동기화합니다.
```bash
# 백엔드 의존성 동기화
uv sync
```

### 1.3 Environment Variables Configuration (`backend/.env`)
백엔드 루트 디렉토리의 `.env` 파일에 Gemini API Key와 PostgreSQL 접속 정보가 유효한지 확인합니다.
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_ledger
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## 2. API Manual Test (cURL)

개발 중인 API 동작을 확인하기 위해 cURL 명령어로 이미지 파일을 전송해 볼 수 있습니다. (가상의 `test_receipt.jpg` 이미지 사용)

```bash
curl -X POST http://localhost:8000/api/v1/ledgers/upload/ \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
  -F "image=@/path/to/test_receipt.jpg"
```

### Expected Response
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
      }
    ]
  }
}
```

---

## 3. Frontend Execution

프론트엔드 개발 서버를 실행하여 영수증 업로드 드롭존 UI와 대시보드 동작을 확인합니다.

```bash
cd frontend
npm install
npm run dev
```

---

## 4. Run Test Suite

개발한 백엔드 코드가 헌법 제VIII조의 테스트 표준을 준수하며 정합성을 입증하는지 `pytest`를 통해 최종 검증합니다.

```bash
# 백엔드 전체 pytest 실행
uv run pytest
```
