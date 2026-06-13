# Quickstart: Template Promotion & Self-Healing

본 가이드는 개발자와 테스터가 로컬 환경에서 가맹점 템플릿의 자동 승인(Auto-Promotion) 및 자가 치유(Self-Healing) 파이프라인 기능을 빠르게 테스트하고 유효성을 검증할 수 있도록 돕습니다.

## 1. 사전 준비 (Setup Environment)

Docker Compose RDBMS가 구동 중이고 최신 마이그레이션이 반영되어 있어야 합니다.

1. **로컬 DB 기동:**
   ```bash
   # Windows (PowerShell)
   powershell -ExecutionPolicy Bypass -File scripts/local-db-controller.ps1 -Action Migration
   
   # Linux/macOS
   ./scripts/local-db-controller.sh --action migration
   ```
2. **Celery Worker 및 Redis 가동 확인:**
   테스트를 위해서는 비동기 Celery 워커 프로세스가 활성화되어 있어야 합니다. (로컬 디버깅 시 `OLLAMA_ENABLED=True` 설정 시 Ollama 모델이 동작하고 있어야 폴백이 정상 처리됩니다.)

---

## 2. 시나리오 1: 템플릿 자동 승인(Auto-Promotion) 검증

동일 가맹점 영수증을 3회 유입시켰을 때, `is_verified` 플래그가 자동으로 `true`가 되는지 테스트합니다.

1. **테스트 스크립트 실행 (혹은 단위 테스트 실행):**
   `pytest`를 활용해 자동 승격 관련 단위 테스트를 수행합니다.
   ```bash
   uv run pytest backend/tests/test_template_promotion.py
   ```
2. **수동 E2E 테스트 검증 단계:**
   * **1차 영수증 업로드:** 신규 가맹점 영수증 업로드 -> 템플릿 생성 (`is_verified: false`, `consistency_count: 1`)
   * **2차 영수증 업로드:** 동일 가맹점 영수증 업로드 -> 정규식 일치 감지 (`consistency_count: 2`)
   * **3차 영수증 업로드:** 동일 가맹점 영수증 업로드 -> 정규식 일치 및 자동 승격 (`is_verified: true`, `consistency_count: 0`)
   * **4차 영수증 업로드:** 동일 가맹점 업로드 -> LLM을 건너뛰고 바이패스 캐시 파서가 초고속 파싱하는 것을 로그에서 확인.

---

## 3. 시나리오 2: 템플릿 강등 및 자가 치유(Self-Healing) 검증

승격된 템플릿 상태에서 수동 데이터 정정을 유발하여 템플릿이 강등되고 규칙이 재생성되는지 확인합니다.

1. **단위 테스트 실행:**
   ```bash
   uv run pytest backend/tests/test_template_self_healing.py
   ```
2. **수동 E2E 테스트 검증 단계:**
   * **Given:** 템플릿의 `is_verified`가 `True`인 상태
   * **When:** 사용자가 대시보드에서 파싱된 최종 가계부 항목을 수정(정정 API 호출)
   * **Then:** 
     * 해당 `MerchantTemplate`의 `is_verified`가 `False`로 즉시 강등됨을 데이터베이스에서 조회 확인.
     * 백그라운드 Celery 비동기 태스크로 자가 치유 정규식 도출 연산이 트리거됨.
     * 새로운 정규식이 검증을 통과하여 `MerchantTemplate.regex_pattern`에 갱신 적재되고 `last_healing_at` 시각이 기록됨을 확인.
