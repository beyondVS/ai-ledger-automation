# Quickstart Guide: 소비 시각화 차트 및 예산 게이지 (가계부 UI 고도화 1단계)

본 가이드는 가계부 대시보드 시각화 피처를 로컬 환경에서 신속하게 구동하고, 백엔드 API와 프론트엔드 차트 및 예산 게이지 컴포넌트의 동작성을 검증하기 위한 가이드라인을 제공합니다.

## 1. 백엔드 가동 및 API 테스트

### 의존성 확인 및 DB 마이그레이션
백엔드 로컬 가상환경 및 DB 컨테이너가 실행된 상태에서 마이그레이션을 실행합니다.
```bash
# 로컬 DB 컨테이너 실행
docker compose -f docker-compose.db.yml up -d

# 백엔드 의존성 동기화
uv sync

# 신설된 MonthlyBudget 모델 마이그레이션 생성 및 적용
uv run python backend/manage.py makemigrations
uv run python backend/manage.py migrate
```

### 테스트 데이터 생성 및 API 수동 검증
가계부 더미 데이터를 적재한 후, curl을 활용하여 대시보드 통계 API와 예산 편집 API의 동작을 수동 확인합니다.

```bash
# 1. 예산 설정 (Upsert) API 호출 테스트 (amount: 1,500,000원)
curl -X POST http://localhost:8000/api/budgets/ \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <JWT_ACCESS_TOKEN>" \
     -d '{"budget_month": "2026-06", "amount": 1500000}'

# 2. 대시보드 통계 조회 API 호출 테스트 (조회 개월수: 6개월)
curl -X GET "http://localhost:8000/api/ledgers/dashboard/?months=6" \
     -H "Authorization: Bearer <JWT_ACCESS_TOKEN>"
```

---

## 2. 프론트엔드 가동 및 차트 컴포넌트 마운트

### 의존성 설치 및 로컬 서버 실행
프론트엔드 폴더 내에 차트 렌더링 라이브러리(`chart.js`, `vue-chartjs`)를 추가하고 로컬 개발 서버를 기동합니다.
```bash
# 프론트엔드 패키지 추가 (선언적 의존성 및 package.json 일치)
npm install chart.js vue-chartjs

# 프론트엔드 로컬 Vite 개발 서버 기동
npm run dev
```

### UI 가동 검증 체크리스트
1. **대시보드 메인**: `http://localhost:3000/dashboard` 진입 시 원형 차트, 막대 차트, 예산 게이지, TOP 3 가맹점 요약 카드가 2-3열 반응형 그리드 내에서 깨짐 없이 렌더링되는지 확인합니다.
2. **예산 편집**: 예산 편집 아이콘/버튼을 누르고 금액을 입력했을 때, API가 정상 호출되어 DB에 영속화되고 예산 게이지 바의 색상(초록/노랑/빨강)과 남은 금액 정보가 비동기로 갱신되는지 확인합니다.
3. **기간 필터**: 막대 차트 상단에 제공되는 3개월/6개월/12개월 필터를 전환할 때, API 요청이 적절히 발생하여 차트의 데이터가 실시간 교체되는지 확인합니다.

---

## 3. 테스트 코드 실행 (pytest)

헌법 VIII조(하이브리드 테스트)에 따라 DB 결합 API 테스트는 `django.test.TestCase`를 상속받은 파일로 실행합니다.

```bash
# 백엔드 전체 테스트 실행 (100ms 이내 쿼리 성능 확인 포함)
uv run pytest backend/tests/test_dashboard_api.py
```
