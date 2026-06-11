<!--
[Sync Impact Report]
- Version Change: v1.12.0 -> v1.13.0
- Ratified: 2026-05-29 | Last Amended: 2026-06-11
- Key Principles Defined:
  1. I. 데이터 무결성 및 원자성 트랜잭션 최우선 (Data Integrity & Transaction Atomicity)
  2. II. 비동기 큐 전환 및 자원 점유 최적화 (Asynchronous Processing & Scale Isolation)
  3. III. 하이브리드 비용 최적화 파이프라인 (Hybrid Bypass for Cost Control)
  4. IV. SPF/DKIM 기반 엄격한 보안 메일 수집 (Secure Inbound Email Ingestion)
  5. V. Vision-First PWA & HTTPS 보안 환경 강제 (Mobile-first PWA & HTTPS Mandated)
  6. VI. 크로스 플랫폼 대칭 툴링 및 문서 동기화 수호 (Cross-platform Symmetric Tooling & Autonomous Document Sync)
  7. VII. 선언적 의존성 및 uv 패키지 격리 수호 (Declarative Dependencies & Package Isolation)
  8. VIII. pytest 및 Django TestCase 하이브리드 테스트 수호 (Hybrid Test Architecture & Domain Parity)
  9. IX. ruff 및 pre-commit 자동화 품질 가드 수호 (Ruff Linter & pre-commit Quality Guard)
- Added/Modified: (1) google-generativeai 라이브러리를 제거하고 google-genai 최신 공식 SDK 및 litellm 패키지를 도입하여 로컬 Ollama(gemma4:e4b) 연동 및 다이내믹 라우팅 분기 체계를 구축. (2) PDF 파싱 시 기계적 텍스트 파싱을 배제하고, PDF 원본 바이트를 Gemini 멀티모달 API에 application/pdf 파트를 통해 네이티브하게 멀티모달 분석을 태움(v1.7.0). (3) LiteLLM Router(litellm.Router)를 도입하여 로컬 환경에서는 Ollama gemma4:e4b를 최우선 주 모델 및 폴백 모델로 가동하고, 프로덕션(DEBUG=False) 환경에서만 Gemini-2.5-Flash를 우선적으로 라우팅하는 다이내믹 라우터(ReceiptLLMClient) 체계로 전격 통합(v1.8.0). (4) 백엔드, Celery, 프론트엔드 전체 Dockerizing 완료 및 핫 리로딩 인프라 통합 구축(v1.9.0). (5) 동일 상품 연속 결제 오탐지 방지를 위해 approval_number 필드를 신설하고, 승인번호 고유성 대조 및 1분(60초) 임계 시각 대조 하이브리드 중복 방어 알고리즘을 도입. 프론트엔드 수정 내역 모달(FE-05-B) 내 유실되거나 유효하지 않은 카테고리 데이터 바인딩 유입 시 '미분류'로 자동 폴백하는 안전 바인딩 정책을 적용하여 누수를 제거함(v1.10.0). (6) 이메일 포워딩 수집 및 SPF/DKIM 보안 필터링의 구현 일정을 4주 개발 로드맵에서 제외하고 차후 확장 계획 백로그로 안전하게 이관 보존함(v1.10.1). (7) 동기식 레거시 파서(CostControlParser) 및 관련 태스크(process_llm_fallback_task)를 영구 제거하고 Celery 기반 비동기 파이프라인으로 일원화. 중복 결제 발생 시 재전파(re-raise) 처리 대신 안전한 FAILED 실패 상태 반환 구조로 전환(v1.11.0). (8) 백엔드 컨테이너의 파이썬 실행 환경을 3.13-slim으로 업그레이드하고, pyproject.toml 설정 파일을 프로젝트 루트에 단일화(Single Source of Truth)하여 Ruff 린트/포맷 룰을 워크스페이스 전역으로 일치시킴(v1.11.0). (9) Gemini API 호출 장애 시 로컬 Ollama 폴백 가동 대역에서 base64 데이터 디코딩 규격 충돌(prefix 유무) 문제를 방지하기 위해, parse_receipt 메서드 단에서 try-except 블록으로 에러를 캐치하고 Ollama에 맞는 무접두사 base64 스트링으로 페이로드를 동적 가공 재인서트하는 방어벽을 구축함(v1.11.0). (10) 이메일 상세 결제 시각(오전/오후 시:분) 결합 파싱 정규화 구현 및 LLM 제안 정규식을 원시 텍스트와 대조 검증하는 Celery 비동기 검증 태스크(verify_proposed_regex_task)를 추가하고, 검증 성공 시 템플릿의 자동 검증 플래그(is_auto_verified)를 True로 마킹하도록 전용 파이프라인 고도화(v1.12.0). (11) 사용자의 고유 타임존 설정을 보존하기 위해 User 모델에 timezone 필드를 추가하고, 영수증 결제일시 파싱 시 외부 의존성(dateparser) 추가 없이 파이썬 내장 표준 라이브러리(datetime, zoneinfo) 및 User.timezone을 기반으로 로컬 시간대를 UTC 기준 Timezone-aware 시간대로 정밀 정규화하는 파이프라인 및 중복 검증 태스크를 구축함. LLM API 스키마/프롬프트를 개정하여 Naive 일시만 추출하도록 통제함(v1.13.0).
- Added Sections: 없음
- Deleted Sections: 없음
- Synchronized Templates:
  - plan-template.md: ✅ 동기화 완료 (D:\Projects\Private\ai-ledger-automation\.specify\templates\plan-template.md)
  - spec-template.md: ✅ 동기화 완료 (D:\Projects\Private\ai-ledger-automation\.specify\templates\spec-template.md)
  - tasks-template.md: ✅ 동기화 완료 (D:\Projects\Private\ai-ledger-automation\.specify\templates\tasks-template.md)
- Pending / Deferred Items: 이메일 포워딩 기반 가계부 자동 수집 파이프라인 (SendGrid 웹훅 & SPF/DKIM 보안 필터)
-->

# AI 기반 세금/영수증 PDF 분석 및 가계부 자동화 프로젝트 헌법

## Core Principles

### I. 데이터 무결성 및 원자성 트랜잭션 최우선 (Data Integrity & Transaction Atomicity)

가계부 데이터는 사용자의 금융 자산 정보와 직접적으로 연계되므로 강력한 트랜잭션 ACID 정합성이 완벽히 보장되어야 합니다. 영수증 1장의 분석 데이터로부터 도출된 메인 가계부 레코드(ledgers)와 상세 품목 레코드 배열(ledger_items)의 생성 및 수정 연산은 반드시 단 하나의 Django ORM 트랜잭션 세션 블록(`transaction.atomic()`) 내에서 원자적으로 처리되어야 합니다. 네트워크 단절이나 데이터베이스 장해 등 일체의 예외 발생 시에는 전격 전역 롤백(Rollback)하여 데이터 파편화(Dirty State)를 방지해야 합니다. 또한, 중복 결제 영수증의 무차별적인 복사 적재를 방지하기 위해 `UNIQUE (user_id, vendor_registration_number, transaction_date, total_amount)` 복합 고유 제약조건을 데이터베이스 테이블 레이어에 강력히 적용하여 동일 순간의 중복 입력을 차단하고, 동일 상품 연속 결제 시의 오탐지를 완벽히 배제하기 위해 카드 승인번호 유효성 대조 및 60초(1분) 임계 시간 차이를 대조 판별하는 지능형 시간 윈도우 중복 방어 알고리즘을 애플리케이션 레이어에 탑재하는 것을 핵심 원칙으로 선언합니다.

### II. 비동기 큐 전환 및 자원 점유 최적화 (Asynchronous Processing & Scale Isolation)

대용량 유입 및 고연산 부하 속에서 전체 서비스의 마비 및 인프라 붕괴를 원천 방지하기 위해 API 요청 응답 흐름과 무거운 백그라운드 처리 과정을 엄격하게 물리적으로 격리합니다. 이미지 리사이징(Pillow) 및 외부 멀티모달 LLM API 호출과 같이 CPU 점유율이 높고 대기 시간이 긴 오프라인 연산은 Celery 비동기 독립 워커 프로세스 내부에서만 실행되어야 하며, API 게이트웨이 서버는 유입 즉시 Redis Broker를 거쳐 임시 대기 상태(Pending, 202) 및 작업 식별자 ID를 즉시 반환하여 프론트엔드의 응답 지연(Latency) 병목을 예방합니다. 또한, supabase 등의 무료 등급 DB 인프라 가용 한계를 고려하여 최대 허용 데이터베이스 커넥션 풀(Connection Pool) 크기를 api_server 컨테이너 5개, Celery async_worker 3개, 전체 합산 8개 이하로 엄격하게 제약하여 리소스 고갈 붕괴를 사전에 제어합니다.

### III. 하이브리드 비용 최적화 파이프라인 (Hybrid Bypass for Cost Control)

유료 멀티모달 LLM API 연동에 수반되는 예산 소비를 차단하고 운영 효율을 극대화하기 위해 지능형 레이아웃 캐싱 및 바이패스(Bypass) 파이프라인을 작동합니다. 분석 대상 텍스트에서 가맹점의 10자리 사업자등록번호가 식별되면 가맹점 레이아웃 캐시 테이블(`merchant_templates`)을 최우선 인덱스 조회합니다. 해당 가맹점의 수동 검증 승인 마크(`is_verified: true`)가 지정된 정적 정규식 규칙이 캐시 데이터로 존재할 경우, 유료 LLM API의 호출을 전면 취소하고 로컬 정규식 파서 모듈을 통해 즉각 파싱을 마쳐 호출 비용을 0원에 수렴하도록 완벽히 통제합니다. 캐시 정보가 없거나 미검증 상태(`is_verified: false`)인 경우에 한해 LLM API를 폴백(Fallback) 가동하고, 성공 파싱 데이터 기반의 정규식 규칙 후보군을 자율 학습 알고리즘으로 자동 제안하여 캐시 DB에 격리 적재하는 자율 진화 파이프라인을 의무화합니다.

### IV. SPF/DKIM 기반 엄격한 보안 메일 수집 (Secure Inbound Email Ingestion) (※ 차후 백로그 이관)

사용자 가계부에 이메일 포워딩을 통한 영수증 무단 누적 수집 시도를 완벽히 방어하기 위해 이중 전초선 필터링 방어막을 엄격하게 구축합니다. (※ 본 조항의 구체적인 구현 요건은 4주 개발 로드맵에서 보류되어 차후 확장 계획 백로그로 이관되었습니다.) SendGrid/Mailgun 등의 인바운드 메일 웹훅 유입 시, 메일 헤더 상에 기록된 SPF 및 DKIM 전자서명 보안 인장을 대조 검증하여 위변조 메일을 1차단합니다. 또한 마스터 DB에 사용자별로 사전에 매핑되어 등록된 화이트리스트 이메일 주소(사용자당 최대 3개)와 발송인 주소가 100% 일치할 경우에만 비동기 Celery 태스크 적재를 허용하여, 외부 악성 메일 폭탄 스팸 공격과 비동기 메시징 큐의 리소스 고갈 위협을 완벽히 격리 통제합니다.

### V. Vision-First PWA & HTTPS 보안 환경 강제 (Mobile-first PWA & HTTPS Mandated)

모바일 플랫폼에서의 즉각적이고 안정적인 바로가기 설치(A2HS) 및 네이티브 카메라 연동 최적화 사용자 경험을 웹 표준 사양 위에서 견고하게 실현합니다. 모바일 PWA 접속 시 HTML5 Capture API와 Accept 속성을 바인딩하여 사진첩 리소스를 거칠 필요 없이 스마트폰 네이티브 카메라 셔터를 직접 연동 촬영하도록 제어합니다. 또한 네트워크 전송 대역폭 절감 및 서버의 고용량 이미지 압축 연산 경감을 위해, 업로드 직전 클라이언트 단 HTML5 Canvas API를 가동하여 이미지를 가로 최대 1000px 수준으로 1차 압축 처리하여 전송합니다. 마지막으로, 서비스 워커의 정상적 등록 및 VAPID 명세의 백그라운드 Web Push 알림 수신을 위한 브라우저 보안 규격을 달성하기 위해, 로컬 호스트 디버깅 대역을 제외한 모든 실서버 환경에서 HTTPS SSL 보안 도메인 적용을 강제합니다.

### VI. 크로스 플랫폼 대칭 툴링 및 문서 동기화 수호 (Cross-platform Symmetric Tooling & Autonomous Document Sync)

개발자의 로컬 환경 셋업과 데이터베이스 관리 등 개발 편의성을 좌우하는 인프라 툴링은 특정 운영체제에 종속되지 않는 크로스 플랫폼 사용성이 완벽히 보장되어야 합니다. 인프라 관리 도구를 설계할 시에는 Windows(PowerShell, `*.ps1`)와 macOS/Linux/WSL(Bash, `*.sh`) 양대 실행 대역 모두에서 동일한 가동 멱등성과 기계적 환경 검증 혜택을 받도록 대칭적인 이중 스크립트 배포 원칙을 강력하게 준수해야 합니다. 더불어, 프로젝트의 로컬 제어, 빌드, RDBMS 환경 기동, 마이그레이션, 테스트 등 프로젝트 개발 관리에 요구되는 모든 커스텀 자동화 스크립트/도구 파일들은 반드시 프로젝트 루트의 `scripts/` 디렉토리 하위에 직접 생성 및 배치해야 합니다. `.specify/` 디렉토리는 오직 Spec-Kit 프레임워크 고유 자산 및 빌트인 템플릿으로만 정결하게 유지되어야 하며, 임의의 커스텀 관리 도구가 혼입되는 것을 엄격히 금지합니다. 끝으로, 시스템 환경 및 툴 사양이 수정되거나 프로젝트 버전이 업그레이드되는 경우 개발자는 지시를 받기 전에 선제적이고 유기적으로 3대 코어 문서(`README.md`, `AGENTS.md`, `.specify/memory/constitution.md`)와 모노레포 설정 파일(`pyproject.toml`, `backend/pyproject.toml`) 간의 교차 동기화 정합성을 분석하고 자동으로 버전을 정합 동기화하여 프로젝트 버전의 완전한 일치 상태를 수호하도록 규정합니다.

### VII. 선언적 의존성 및 uv 패키지 격리 수호 (Declarative Dependencies & Package Isolation)

모든 애플리케이션의 패키지 의존성은 ad-hoc 방식의 임의 `pip install` 또는 시스템 전역 패키지 오염을 원천 차단하기 위해, 반드시 `pyproject.toml`과 `uv.lock`을 통한 선언적 명세 하에 엄격하게 통제되어야 합니다. 로컬 개발, 테스트 실행, 가상 환경 구축 시에는 오직 `uv` 도구를 사용하여 프로젝트 수준의 격리된 가상 환경(`.venv`) 내에서 의존성 동기화(`uv sync`) 및 잠금(`uv lock`) 처리를 완료해야 합니다. 도커(Docker) 가동 시에는 호스트 디렉터리 볼륨 마운트와의 충돌로 컨테이너 내부의 패키지가 덮어씌워지는 부작용을 원천 예방하기 위해, 컨테이너 내부 가상환경을 `/venv` 절대 경로로 격리 생성하여 소스 코드 핫 리로드를 보장해야 합니다. 임의의 패키지 무단 설치를 금지하며, 이를 위반하여 선언적 락 파일의 무결성을 깨뜨리는 행위는 헌법에 위배되는 중대 과실로 간주합니다.

### VIII. pytest 및 Django TestCase 하이브리드 테스트 수호 (Hybrid Test Architecture & Domain Parity)

백엔드 테스트 인프라는 고속 테스트 실행 및 CLI 생산성을 좌우하는 **pytest 실행기(Runner)**와 데이터베이스 트랜잭션 원자성을 수호하는 **Django TestCase**의 가치를 유기적으로 융합한 하이브리드 구조를 확고하게 수호합니다.

데이터베이스 연산이 수반되거나 Django 핵심 컨텍스트(ORM, 모델 고유 키 제약, DRF View 및 Serializer)를 교차 검증해야 하는 모든 비즈니스 로직 테스트는 반드시 `django.test.TestCase` 클래스를 상속받는 명시적 클래스 스타일로 작성해야 합니다. 또한 공통 테스트 데이터를 구성할 때는 매 테스트 메서드마다 DB 인서트가 반복되는 것을 방지하기 위해 반드시 `setUpTestData(cls)` 클래스 메서드를 활용하여 데이터베이스 가동 오버헤드를 극소화하여야 합니다. 반면, 데이터베이스 접근이 완전히 부재하고 순수한 파일 I/O, 메모리 연산 및 데이터 파싱만을 검증하는 독립 유틸리티성 테스트는 표준 라이브러리의 `unittest.TestCase`를 상속받도록 격리 설계함으로써 불필요한 가상 DB 기동 및 장고 설정 오버헤드를 원천적으로 회피하여 초고속 개발자 피드백 루프를 수호하도록 규정합니다.

### IX. ruff 및 pre-commit 자동화 품질 가드 수호 (Ruff Linter & pre-commit Quality Guard)

코드 스타일의 일관성 및 사전 결함 예방을 위해 Rust 기반의 초고속 린터/포매터인 `ruff`와 `pre-commit` 훅 자동화 가드를 수호합니다. 모든 파이썬 소스 코드는 로컬 커밋 전에 반드시 pre-commit 훅을 통과하여 린팅 및 포매팅 정합성이 기계적으로 검증되어야 합니다. 임의로 이 검사를 우회하거나 무효화하여 커밋하는 행위를 금지하며, 개발 환경 변경 시 `pre-commit` 도구의 선언적 버전 관리를 준수하여 코드 무결성을 유지해야 합니다.

## 기술 스택 및 아키텍처 제약 조건 (Tech Stack & Architectural Constraints)

본 프로젝트의 모든 시스템 아키텍처 및 세부 컴포넌트는 다음의 정의된 엄격한 기술 프레임워크 한계선 내에서 설계 및 개발되어야 합니다.

* **백엔드 코어 (Backend Core)**: Python 3.13 + Django Web Framework & Django REST Framework (DRF) (패키지 관리: **uv**)
* **비동기 처리 엔진 (Task Queue)**: Celery Worker + Redis Broker (JWT 세션 블랙리스트 및 캐시 통합 병용)
* **데이터 보존 레이어 (Storage Layer)**: PostgreSQL v18+ (주요 ACID 데이터, Native UUIDv7 & AIO) + JSONB 지원 (비정형 원시 LLM 백업용) + approval_number (결제 승인번호 백업 보존)
* **인공지능 연동 모듈 (AI Core)**: LiteLLM Router 기반 다이내믹 라우터 (로컬 환경: Ollama gemma4:e4b 우선 및 동일 모델 폴백 / 프로덕션 환경: Gemini-2.5-Flash 우선 및 Ollama 폴백. ReceiptLLMClient를 통한 단일 base64 image_url 통합 및 Pydantic Structured Outputs 규격 강제 바인딩)
* **수집 파이프라인 (Email Ingestion)**: SendGrid / Mailgun Inbound Parser Webhook + SPF/DKIM 및 사용자 이메일 화이트리스트 이중 매핑 필터
* **프론트엔드 플랫폼 (PWA Client)**: Vue.js 3 (Vite + Vue 3) + PWA Manifest & Service Worker Cache (iOS Safari용 A2HS 수동 유도 툴팁 포함) + Tailwind CSS
* **푸시 허브 (Notification)**: VAPID v2 표준 규격 Web Push API (백그라운드 디스패치를 위한 Celery 전용 Notification Queue 분리 운영)
* **가상 인프라 배포 (Deployment)**: Docker Compose 통합 관리 (api_server, postgres_db, redis_broker, async_worker)

## 개발 및 릴리즈 체크 품질 게이트 (Development Workflow & Quality Gates)

기획 명세서(`spec.md`) 작성 단계부터 최종 프로덕션 빌드 배포 단계까지, 모든 개발 산출물은 아래의 품질 게이트 기준을 만족하여 입증된 경우에만 릴리즈될 수 있습니다.

* **Phase 1 (동기식 MVP) 품질 게이트**:
  - 드래그앤드롭 및 원시 PDF/이미지 단일 웹 루프 동기식 업로드 E2E 동작 무결성 달성.
  - PDF 파일 유입 시 Pillow 전처리를 우회하여 PDF 원본 바이너리 그대로를 LLM API에 application/pdf 파트로 직접 전달하는 다이렉트 멀티모달 파이프라인 무결성 입증.
  - 메인 가계부 레코드(ledgers)와 품목 배열(ledger_items)이 Django ORM 단일 트랜잭션 세션 블록(`transaction.atomic()`) 내에서 성공 커밋되고, 실패 시 롤백됨을 증명.
  - Canvas 다운사이징 1차 리사이징 이미지 바이트 버퍼 유입 성공 검증.
  - 3주차 비동기 구조 전환에 프론트엔드가 하위 호환성을 유지할 수 있도록 `status: "COMPLETED"` 및 `job_id: null` 형태의 MVP 폴링 호환용 JSONB 규격 강제 준수.
* **Phase 2 (비동기 및 고도화) 품질 게이트**:
  - 웹 업로드 및 메일 웹훅 유입 시 즉시 202 Accepted 및 작업 식별자 ID를 반환하며, 실제 무거운 이미지 전처리(Pillow WebP 변환) 및 AI 연산은 격리 실행되는 백그라운드 Celery Worker 내부에서만 실행됨을 E2E 검증.
  - SPF/DKIM 정합성 검증 필터 및 발신인 이메일 화이트리스트 매핑 방어막의 스팸/공격 차단율 100% 증명.
  - 10만 건 이상의 더미 데이터를 적재한 스트레스 테스트 환경에서 `EXPLAIN ANALYZE` 쿼리 분석기를 통한 인덱싱 튜닝 및 최적화를 달성하여, 실시간 지출 대시보드 API 쿼리 응답 시간을 상시 **100ms 이내**로 방어.
  - PWA standalone 설치 유도 및 VAPID 암호화 키 바인딩을 적용하여 앱을 닫고 있는 오프라인 기기 상단에 Web Push 알림이 정상 도달함을 증명.
  - 자가 제안(Auto-Generation)되는 사업자번호 기반 정규식 템플릿은 무조건 `is_verified: false`로 신규 적재되어 실제 bypass 파서에 유입되지 못하게 격리 차단하고, 오직 어드민 수동 검토 완료 후 `is_verified: true` 승인 시에만 LLM 호출 우회 바이패스에 반영되도록 신뢰 한계선 준수.
  - 승인번호가 다른 연속 결제를 허용하고, 승인번호가 동일하거나 없을 경우 60초(1분) 이내의 인입 건에 대해서만 중복으로 간주하고 초과 건은 정상 적재 처리하는 60초 임계창 시간-윈도우 중복 방어 알고리즘 E2E 정합성 검증.
  - 프론트엔드 가계부 내역 수정 모달 상에서 기존 지정 카테고리가 누락되거나 유효하지 않을 때 UI 상에서 '미분류'로 자동 대치 바인딩 및 전송 정합성 검증.

## Governance

본 프로젝트의 거버넌스는 수립된 헌법을 최상위 의사결정의 척도로 삼으며, 헌법의 개정 및 이력 관리는 다음의 규정에 의거하여 통제됩니다.

* **헌법 개정 절차**: 프로젝트의 중대한 설계 스택 변경, 비즈니스 영속성 위배 가능성, 혹은 핵심 개발 원칙의 추가/수정은 본 문서의 수정 및 수동 정밀 영향 분석을 동반하며, 승인 즉시 시맨틱 버저닝(Semantic Versioning)에 의거해 버전을 갱신하여 문서 최하단에 기록합니다.
* **버전 관리 규정 (Versioning Policy)**:
  - **MAJOR (A.x.x)**: 트랜잭션 격리 규칙 변경, 주 데이터베이스 변경, 혹은 기존 하위 호환성을 완전히 붕괴시키는 데이터 정합성 파괴 원칙 변경 시 개정.
  - **MINOR (x.B.x)**: 비용 절감용 바이패스 엔진 추가, PWA 카메라 연동이나 이메일 웹훅 필터 고도화 등 신규 안전성 파이프라인이나 아키텍처 규칙이 추가/확장될 시 개정.
  - **PATCH (x.x.C)**: 세부 문맥 자구 정제, 오타 수정, 비실질적 포맷팅 최적화 시 개정.

**Version**: v1.13.0 | **Ratified**: 2026-05-29 | **Last Amended**: 2026-06-11
