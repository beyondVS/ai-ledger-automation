# Quickstart: Database Integrity & Payment Duplicate Prevention & Category UI Fix

## 1. 개발 및 테스트 환경 준비 (Development Environment)

본 피처를 로컬에서 테스트하고 검증하기 위한 환경 셋업입니다.

### 1.1 로컬 데이터베이스 기동
PostgreSQL v18+ RDBMS를 독단적으로 실행합니다:
```bash
docker compose -f docker-compose.db.yml up -d
```

### 1.2 백엔드 파이썬 패키지 의존성 동기화
`uv` 패키지 관리자를 사용하여 격리된 가상 환경의 종속성을 정렬합니다:
```bash
uv sync
```

---

## 2. 테스트 가동 및 정합성 검증 (Running Tests)

헌법 제VIII조(pytest 및 Django TestCase 하이브리드 테스트 수호)에 따라 구성된 통합 및 단위 테스트 모음을 실행하여 기능을 기계적으로 입증합니다.

### 2.1 전체 백엔드 테스트 실행
```bash
uv run pytest
```

### 2.2 트랜잭션 롤백 및 중복 바이패스 통합 테스트 단독 실행
```bash
uv run pytest backend/tests/integration/test_ledger_transaction.py
```

### 2.3 1분 임계값 기반 중복 체크 알고리즘 단위 테스트 단독 실행
```bash
uv run pytest backend/tests/unit/test_duplicate_check.py
```

### 2.4 파이썬 코드 스타일 및 린트 검증 (Ruff)
커밋을 수행하기 전 린트 및 포맷 정합성을 확인합니다:
```bash
uv run ruff check
uv run ruff format
```

---

## 3. 프론트엔드 카테고리 셀렉트박스 로컬 가동 (Frontend Local Run)

수정 모달 UI 컴포넌트(`LedgerEditModal.vue`)의 버그가 올바르게 수정되었는지 확인하기 위한 방법입니다.

### 3.1 프론트엔드 로컬 서버 기동
```bash
cd frontend
npm install
npm run dev
```

### 3.2 UI 검증 확인 절차
1. 로컬 브라우저로 프론트엔드 개발 환경에 접속합니다.
2. 가계부 내역 목록에서 임의의 거래 항목을 클릭하여 수정 내역 모달(`FE-05-B`)을 활성화합니다.
3. **매핑 검증**: 기존에 지정되어 있던 카테고리가 드롭다운에 정상 매핑되어 노출되는지 확인합니다.
4. **유실 예외 검증**: 백엔드에서 카테고리 정보가 유실(Null)된 거래 건의 경우, 셀렉트박스에 기본값으로 **'미분류'**가 정상 렌더링되는지 확인합니다.
5. **저장/수정**: 카테고리를 변경하고 저장 버튼을 누른 후, 목록 화면에 실시간으로 데이터 바인딩이 갱신되어 반영되는지 체크합니다.
