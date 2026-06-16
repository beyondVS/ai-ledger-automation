# Quickstart Guide: Asynchronous Load Testing

본 가이드는 3주차 비동기 아키텍처 튜닝 및 50종 영수증 동시 유입 부하 테스트를 로컬 환경에서 실행하고 정합성을 입증하는 신속 가이드입니다.

---

## 1. 테스트 실행 전 환경 점유 제약 설정 (Celery Tuning)

프로젝트 헌법 제II조(자원 점유 최적화)에 따라 Celery 워커의 최대 동시성과 DB 커넥션 제한을 설정해야 합니다.

### 1.1 Docker Compose 환경 (추천)
`docker-compose.yml` 또는 `docker-compose.db.yml` 실행 시 워커의 concurrency를 제어합니다.
* Celery 워커 컨테이너 기동 커맨드 확인:
  `celery -A backend worker --concurrency=3 --loglevel=info`

### 1.2 로컬 가상환경 직접 실행 시
```bash
# 1. uv 가상환경 활성화
uv sync

# 2. Celery 워커 동시성 3제한으로 가동
uv run celery -A backend worker --concurrency=3 --loglevel=info
```

---

## 2. 50종 동시 유입 부하 테스트 통합 실행 (Integration Test)

백엔드 패키지 내 구축된 `test_load_testing.py` 통합 테스트 코드를 실행하여 50종 벌크 인입 시의 비동기 큐 전환 성능 및 트랜잭션 정합성(중복 차단 100%, 오류 시 롤백 100%)을 기계적으로 검증합니다.

```bash
# 1. pytest를 활용한 고속 통합 부하 테스트 가동 (Django DB 연산TestCase 바인딩)
uv run pytest backend/tests/ledgers/test_load_testing.py -v -s
```

* **테스트 수행 시나리오 내역**:
  * 45종의 정상 영수증 이미지 데이터와 5종의 에러 유발용 데이터(손상 포맷, 중복 데이터)를 혼합한 50종의 일괄 업로드 요청 발생.
  * API 서버가 5초 이내에 202 Accepted로 응답하는지 검증 (`SC-001`).
  * 백그라운드 3단계 하이브리드 파싱 수행 중 DB 커넥션 에러 발생 카운트 검증 (`SC-002`).
  * 유효 가계부 45건이 누락 없이 최종 PostgreSQL 적재 완료되는지 확인 (`SC-003`).
  * 에러 영수증 5건에 대해 DB 원자적 롤백이 작동하여 LedgerItem 고아가 발생하지 않는지 검증 (`SC-004`).

---

## 3. 부하 테스트 모니터링 및 결과 분석

부하 테스트 완료 후, 아래 쿼리를 통해 DB 상태를 진단하여 정합성을 최종 판정합니다.

```sql
-- 1. 중복 적재 유무 및 총 적재 수 확인 (정상 45건 기대)
SELECT COUNT(*) FROM ledgers;

-- 2. 고아 상세 품목(Orphan LedgerItems) 유무 진단 (0건 기대)
SELECT COUNT(*) FROM ledger_items WHERE ledger_id IS NULL;

-- 3. 비동기 ReceiptTask 최종 수렴 상태 통계 확인
SELECT status, parser_stage, COUNT(*) 
FROM ledgers_receipttask 
GROUP BY status, parser_stage;
```
