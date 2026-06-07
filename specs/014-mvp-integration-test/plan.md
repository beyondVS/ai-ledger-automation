# Implementation Plan: MVP Integration Test

**Branch**: `014-mvp-integration-test` | **Date**: 2026-06-07 | **Spec**: [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/014-mvp-integration-test/spec.md)

**Input**: Feature specification from `/specs/014-mvp-integration-test/spec.md`

## Summary

본 피처는 2주차 개발 목표인 "동기식 MVP 완전체 E2E 통합 테스트"를 구현하는 것입니다. Vue 3 기반 프론트엔드 대시보드에서 사용자가 영수증 파일을 올리면 HTML5 Canvas API를 통해 가로 최대 1000px, Quality 0.8 JPEG로 1차 압축하여 서버로 전송합니다. Django 백엔드 서버는 Pillow 모듈을 활용해 이를 WebP 포맷으로 2차 변환하고, Gemini-2.5-Flash API(Structured Outputs 적용)를 호출하여 정형 데이터를 획득합니다. 이후 단일 Django 데이터베이스 트랜잭션(`transaction.atomic()`) 내에서 `ledgers` 및 `ledger_items` 테이블에 데이터를 원자적으로 적재하며, 중복 등록은 복합 고유 제약조건 `UNIQUE (user_id, vendor_registration_number, transaction_date, total_amount)`를 활용해 사전 방지합니다. 프론트엔드와의 하위 호환성을 위해 `status: "COMPLETED"`, `job_id: null` 응답을 10초 이내에 반환하여 동기식 완전한 단일 웹 루프를 실현합니다.

## Technical Context

**Language/Version**: Python 3.11 (backend), Vue.js 3 / JavaScript (frontend)

**Primary Dependencies**: Django, Django REST Framework, Pillow, google-generativeai, uv (backend), Vite, Tailwind CSS (frontend)

**Storage**: PostgreSQL v18+ (JSONB 지원, Native UUIDv7 & AIO), Redis (Broker/Cache)

**Testing**: pytest (pytest-django), Django TestCase (setUpTestData 사용)

**Target Platform**: Docker Compose (Linux Container), Web Browser (PWA)

**Project Type**: Web application (frontend + backend)

**Performance Goals**: 영수증 업로드 후 대시보드 뷰가 완전히 갱신될 때까지 E2E 평균 10초 이내 완료

**Constraints**: 1차 Canvas 압축, 2차 WebP 압축 변환, Gemini Structured Outputs 활용, 단일 트랜잭션 원자적 커밋/롤백, 중복 방지 복합 유니크 제약조건 준수, DB 커넥션 풀 크기 제한(api 5, worker 3, 합산 8개 이하)

**Scale/Scope**: 2주차 동기식 MVP E2E 통합 테스트 범위

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. 데이터 무결성 및 원자성 트랜잭션 최우선**: **PASS**
  - 가계부 적재 시 `ledgers`와 `ledger_items`가 단일 Django 트랜잭션 블록(`transaction.atomic()`)으로 묶여 원자적으로 커밋 및 롤백됨을 보장합니다.
  - 데이터베이스 테이블 레이어에 `UNIQUE (user_id, vendor_registration_number, transaction_date, total_amount)` 복합 고유 제약조건을 정의하여 중복 적재를 원천 방지합니다.
- **II. 비동기 큐 전환 및 자원 점유 최적화**: **PASS**
  - 본 2주차 단계는 동기식 MVP이지만, 3주차 비동기 구조 전환에 대비하여 응답 포맷 규격에 `status: "COMPLETED"`, `job_id: null`을 강제 준수하여 클라이언트의 호환성을 수호합니다.
  - 데이터베이스 커넥션 풀 크기는 최대 8개 한도 내(api_server 5개, 워커 3개)로 관리할 수 있도록 인프라를 설계합니다.
- **III. 하이브리드 비용 최적화 파이프라인**: **PASS**
  - 10자리 가맹점 사업자등록번호를 파싱하여 `merchant_templates` 테이블을 최우선 조회하고, 수동 검증 승인 마크(`is_verified: true`)가 지정된 정적 정규식 규칙이 캐시로 존재할 경우 LLM 호출을 생략하고 로컬 정규식 파서로 우회 파싱합니다.
  - 캐시 정보가 없거나 미검증 상태(`is_verified: false`)인 경우에 한해 LLM API를 폴백 가동하고 규칙 후보군을 자동 제안 적재하도록 설계합니다.
- **IV. SPF/DKIM 기반 엄격한 보안 메일 수집**: **N/A**
  - 본 피처는 웹 UI 영수증 업로드 및 동기식 가계부 생성 범위로 이메일 수집 파이프라인과는 무관합니다.
- **V. Vision-First PWA & HTTPS 보안 환경 강제**: **PASS**
  - 클라이언트 HTML5 Canvas API를 사용하여 업로드 전 이미지를 가로 최대 1000px, Quality 0.8 JPEG로 1차 압축하고, HTTPS 환경 하에서 보안 카메라 연동 규격을 준수합니다.
- **VI. 크로스 플랫폼 대칭 툴링 및 문서 동기화 수호**: **PASS**
  - 본 개발 과정에서 인프라/빌드 관련 스크립트 작성 시 Windows PowerShell(`*.ps1`)과 Bash(`*.sh`) 대칭 배포 및 `scripts/` 격리 배치를 수호합니다.
  - `AGENTS.md` 내의 계획 참조 업데이트와 3대 코어 문서 간의 버전 정합성을 준수합니다.
- **VII. 선언적 의존성 및 uv 패키지 격리 수호**: **PASS**
  - 백엔드 패키지는 `pyproject.toml`과 `uv.lock`에 선언적으로 명세하고, `uv sync`를 통해 격리된 가상 환경을 통제합니다.
- **VIII. pytest 및 Django TestCase 하이브리드 테스트 수호**: **PASS**
  - DB와 결합된 통합 테스트(ORM, DRF View)는 반드시 `django.test.TestCase`를 상속하고 `setUpTestData(cls)`를 통해 초기 DB 오버헤드를 극소화합니다. DB 접근이 없는 로컬 유틸리티 테스트는 `unittest.TestCase`를 상속하고 `pytest` 러너를 활용해 수행합니다.
- **IX. ruff 및 pre-commit 자동화 품질 가드 수호**: **PASS**
  - pre-commit 훅을 적용하여 ruff linter/formatter를 통과함을 보장합니다.

## Project Structure

### Documentation (this feature)

```text
specs/014-mvp-integration-test/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── apps/
│   │   ├── accounts/
│   │   ├── health/
│   │   ├── ledgers/         # 가계부 마스터/상세품목 ORM 모델, API 뷰, 시리얼라이저 등
│   │   │   ├── models.py
│   │   │   ├── views.py
│   │   │   ├── serializers.py
│   │   │   └── urls.py
│   │   └── tasks/
│   ├── config/              # 장고 설정(settings.py, urls.py)
│   └── utils/               # Gemini API 연동, Pillow 이미지 변환 및 정규식 bypass 유틸
└── tests/                   # 백엔드 pytest 테스트 코드 (apps/ledgers/tests/)

frontend/
├── src/
│   ├── components/          # 영수증 드롭존, 대시보드 테이블, 세부품목 아코디언 UI
│   ├── services/            # API 연동 모듈 (axios/fetch 기반)
│   ├── router/              # 라우터
│   └── App.vue
└── tests/                   # 프론트엔드 유닛/인티그레이션 테스트 코드
```

**Structure Decision**: backend/ 및 frontend/로 분리된 웹 애플리케이션 아키텍처를 따르며, 가계부 로직은 `backend/src/apps/ledgers/`에 응집하고 이미지 압축 및 LLM 연산은 `backend/src/utils/` 유틸에 격리하여 구현합니다.

## Complexity Tracking

*(헌법 게이트 위반 사항이 없으므로 비워둠)*
