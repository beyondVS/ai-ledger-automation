# Research: Receipt Hybrid Parsing Pipeline & Legacy Cleanup

**Feature Branch**: `022-receipt-hybrid-pipeline`

본 문서는 3단계 하이브리드 파이프라인 및 레거시 아키텍처 비활성화/청소를 설계하기 위해 수립된 핵심 기술 결정 및 대안 분석 연구 자료입니다.

---

## 1. 금액 정합성(Checksum) 검증 공식

* **결정 사항 (Decision)**: 
  1단계(Local OCR + Ollama) 및 2단계(Gemini Text-only) 파싱 결과에 대해 상세 품목들의 합산 금액(`sum(item.total_price)`)이 영수증의 총 결제금액(`total_amount`)과 정확히 일치(`차이 = 0`)하는지 검증을 강제 수행합니다.
* **타당성 (Rationale)**: 
  가계부 데이터는 사용자의 자산 정보를 다루므로 강력한 데이터 무결성(Data Integrity)이 필수적입니다. 품목별 단가와 수량의 곱의 총합이 전체 결제액과 다를 경우, 금융 정보 정합성 손실로 간주하여 가장 정밀도가 높은 3단계(Cloud Vision)로 안전하게 에스컬레이션(Escalation)하도록 조치합니다.
* **고려된 대안 (Alternatives considered)**:
  * *대안 B (편차 허용 검증)*: 품목 리스트의 총합 오차가 10% 이내이거나 1,000원 이하인 경우에도 파싱 성공으로 간주.
    * *기각 사유*: 할인이나 세금이 누락된 경우에는 비용을 아낄 수 있으나, 가계부 전체 데이터의 합산 데이터 신뢰도를 영구적으로 해치는 부작용이 크므로 무결성 원칙에 의거해 기각했습니다.
  * *대안 C (품목 존재 여부만 검증)*: 품목 개수만 확인하고 대조 검증을 수행하지 않음.
    * *기각 사유*: LLM이 품목 단가를 완전히 엉뚱하게 추출한 경우(스키마 붕괴에 준하는 상황)를 걸러내지 못하므로 기각했습니다.

---

## 2. 레거시 정규식 캐싱 및 자가치유 인프라 청소 범위

* **결정 사항 (Decision)**: 
  기존 DB 테이블(`merchant_templates`, `template_execution_histories`) 및 장고 모델 스키마는 데이터 유실 방지와 마이그레이션 호환성을 지키기 위해 그대로 보존합니다. 대신, 비즈니스 서비스 레이어 및 Celery 태스크 단에서 관련 호출(`BypassParser.try_bypass_parsing`, `promote_template_if_consistent`, `demote_template`, `trigger_self_healing`)을 완전히 주석 처리하거나 제거하여 무력화합니다.
* **타당성 (Rationale)**: 
  운영 중인 DB 인프라(Supabase Free 등)에서 대량의 이력 데이터가 적재되어 있을 수 있는 테이블을 즉각 Drop할 경우, 마이그레이션 다운타임 및 롤백 리스크가 발생합니다. 코드 레이어에서 호출을 완벽하게 끊는 것만으로도 Celery 큐 적재 0건을 달성할 수 있어 비용/자원 낭비가 완벽하게 차단됩니다.
* **고려된 대안 (Alternatives considered)**:
  * *대안 B (테이블 및 모델 완전 삭제)*: 마이그레이션 파일(`00XX_drop_merchant_templates.py` 등)을 추가하고 모델 정의를 코드베이스에서 완전히 삭제.
    * *기각 사유*: 마이그레이션 수행 시 예기치 못한 데이터 유실 우려가 있고, 롤백이 복잡해질 수 있어 안전성 우선 원칙에 따라 차후 메이저 아키텍처 개편 시점의 백로그로 이관하여 기각했습니다.

---

## 3. 로컬 개발 환경(DEBUG=True)에서의 API 호출 제한 완화

* **결정 사항 (Decision)**: 
  로컬 개발 환경(`DEBUG=True`)이더라도 `.env` 파일에 `GEMINI_API_KEY`와 `GEMINI_ENABLED=True` 설정이 제공된다면, 2단계(Gemini Text-only) 및 3단계(Gemini Vision) 호출 및 E2E 폴백 테스트 동작을 전면 허용합니다. API 키가 제공되지 않는 로컬 환경에서만 1단계(Ollama) 파싱 실패 시 작업을 실패(`FAILED`) 상태로 마무리합니다.
* **타당성 (Rationale)**: 
  개발자 및 통합 테스트(pytest) 실행 시 로컬 환경에서도 3단계 하이브리드 파이프라인의 유기적 흐름(금액 정합성 실패 시 2단계 전환, OCR 실패 시 3단계 전환)을 완벽하게 검증하고 디버깅할 수 있어야 고품질 코드가 보장됩니다.
* **고려된 대안 (Alternatives considered)**:
  * *대안 B (로컬 내 Gemini API 호출 강제 차단)*: `DEBUG=True` 환경에서는 Gemini 관련 모든 아웃바운드 API 호출을 전면 비활성화하고 로컬 Ollama(1단계)만 가동.
    * *기각 사유*: 요금 발생은 확실히 막을 수 있으나, 2, 3단계 폴백 및 E2E 통합 테스트를 로컬에서 사전에 검증할 방법이 원천 차단되어 프로덕션 릴리즈 품질 게이트 통과가 불가능하므로 기각했습니다.
