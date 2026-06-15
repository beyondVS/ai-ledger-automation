# Quickstart: Receipt Hybrid Parsing Pipeline & Legacy Cleanup

**Feature Branch**: `022-receipt-hybrid-pipeline`

본 가이드는 개발자와 테스터가 로컬 개발 환경에서 3단계 하이브리드 영수증 파싱 파이프라인의 올바른 작동과 레거시 정규식 캐시 코드의 비활성화를 검증하는 데 도움을 줍니다.

---

## 1. 사전 준비 사항 (Prerequisites)

3단계 하이브리드 파이프라인 중 1단계(로컬) 가동을 위해 로컬 Ollama 모델 실행 상태를 확인해야 합니다.
```bash
# 로컬 Ollama 실행 상태 및 gemma4:e4b 모델 존재 여부 조회
curl http://localhost:11434/api/tags
```

클라우드 폴백(2, 3단계) 동작 테스트를 위해서는 `.env` 환경 변수가 적절히 주입되어야 합니다.
```bash
# backend/.env 설정 (예시)
GEMINI_ENABLED=True
GEMINI_API_KEY=AIzaSyYourRealGeminiKeyHere
OLLAMA_MODEL=gemma4:e4b
OLLAMA_API_BASE=http://localhost:11434
```

---

## 2. 3단계 하이브리드 파이프라인 검증 시나리오

### 시나리오 1: 1단계 로컬 하이브리드 (Ollama) 파싱 완결
* **조건**: Tesseract OCR 문자열이 성공적으로 추출되고, 로컬 Ollama가 정확하게 금액 정합성(`sum(item.total_price) == total_amount`)이 맞는 결과를 반환한 경우.
* **검증 방법**:
  1. 명확한 텍스트가 인쇄된 테스트 영수증 파일을 업로드합니다.
  2. Celery 로그를 조회하여 Gemini API 호출 흔적 없이 로컬 Ollama 파서만 1회 호출되고 최종 저장(Ledger 적재)되었음을 확인합니다.

### 시나리오 2: 2단계 텍스트 폴백 (Gemini Text-only) 기동
* **조건**: 로컬 Ollama API 호출이 실패하거나, 반환된 품목 가격의 합과 총 금액이 불일치하는 경우.
* **검증 방법**:
  1. 테스트 코드에서 로컬 Ollama 응답의 품목 총합을 조작하여 금액 검증 오류를 강제 유발합니다.
  2. 시스템이 2단계 Gemini-2.5-Flash Text-only API(이미지 전송 없음)를 호출해 정밀 파싱을 성공시키고 가계부를 완성하는지 로그를 확인합니다.

### 시나리오 3: 3단계 비전 폴백 (Gemini Vision) 기동
* **조건**: 로컬 OCR 결과에서 의미 있는 문자열이 감지되지 않거나, 2단계 텍스트 전용 구조화가 최종 실패한 경우.
* **검증 방법**:
  1. 텍스트가 존재하지 않거나 극도로 훼손되어 OCR 추출 결과가 0글자인 영수증 파일을 업로드합니다.
  2. 로그 상에서 1, 2단계를 자동으로 우회/생략하고 바로 3단계 Gemini-2.5-Flash Vision API가 구동되어 파싱을 수행하는지 검증합니다.

---

## 3. 레거시 청소 및 비활성화 검증

* **검증 대상**: 기존의 정규식 캐싱 및 자가 치유 관련 Celery 태스크의 비활성화 상태.
* **검증 방법**:
  * 백엔드 테스트 스위트를 구동하여 기존 템플릿 매핑 관련 테스트가 영향 없이 스킵되거나 안전하게 호환 통과하는지 점검합니다.
  ```bash
  # pytest 실행 및 전체 테스트 통과 여부 확인
  uv run pytest
  ```
  * 영수증 업로드 성공 후, 데이터베이스의 `merchant_templates` 테이블에 신규 제안(`propose_new_template`)이 등록되지 않는지 확인하고, Celery 검증 큐(`verify_proposed_regex_task`)가 생성되지 않는 것을 모니터링합니다.
