# Implementation Plan: Upload API Integration & Async Schema Design

**Branch**: `008-upload-api-integration` | **Date**: 2026-06-03 | **Spec**: [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/008-upload-api-integration/spec.md)

**Input**: Feature specification from `/specs/008-upload-api-integration/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary
프론트엔드 드래그앤드롭 업로드 컴포넌트와 1주차에 구축한 동기식 Django API 서버를 연동하여 E2E 업로드 흐름을 실현합니다. 향후 3주차 비동기(Celery) 전환 시 프론트엔드와 백엔드의 하위 호환성을 보장하기 위해 `status` 및 `job_id` 응답 스키마 플레이스홀더를 도입하고, 프론트엔드에 1차 Canvas 이미지 압축(최대 1000px) 및 추상화된 가상 폴링 대기 루프(`VirtualPollingManager`)를 구현하여 선배치합니다.

## Technical Context

**Language/Version**: Python 3.11, JavaScript ES6+ (Vue 3)

**Primary Dependencies**: Django, Django REST Framework (DRF), Vue 3, Vite, Tailwind CSS

**Storage**: PostgreSQL v18+ (ACID ledgers/ledger_items 트랜잭션, Native UUIDv7), Redis (가상 캐시/향후 브로커)

**Testing**: pytest (테스트 러너), Django TestCase (DB/View 검증), unittest.TestCase (순수 유틸 검증)

**Target Platform**: Docker Compose 통합 가상 환경 (api_server, postgres_db)

**Project Type**: Web Application (Frontend Vue.js 3 + Backend Django DRF)

**Performance Goals**: 동기 처리 완료 3초 이내, 가상 폴링 결과 UI 바인딩 0.1초 이내

**Constraints**: 
- 3주차 비동기 전환 시 데이터/API 하위 호환성 유지 (`status` 및 `job_id` 스키마 준수)
- 데이터베이스 최대 허용 커넥션 풀 api_server 5개 이하로 제약

**Scale/Scope**: 단일 영수증 업로드 E2E 루프, 가상 폴링, 1차 압축 리사이징

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **제I조 (데이터 무결성 & 원자성)**: ledgers와 ledger_items의 레코드 생성/수정 연산은 Django ORM의 단일 트랜잭션 블록(`transaction.atomic()`)으로 감싸 원자성을 보장하며, DB 테이블 레이어에 `UNIQUE (user_id, vendor_registration_number, transaction_date, total_amount)` 복합 고유 제약을 설정하여 중복 적재를 차단합니다. (통과: Pass)
- **제II조 (비동기 격리 & 커넥션 풀)**: supabase DB 커넥션 한계를 고려해 api_server 커넥션 풀을 5개 이하로 제약합니다. Celery 비동기 연동을 감안한 status 및 job_id 구조를 API 스키마에 선반영합니다. (통과: Pass)
- **제III조 (비용 최적화 파이프라인)**: 파서 연동 시 사업자번호 10자리 기반 `merchant_templates` 조회 우회 및 `is_verified` 필터 통제 정책을 데이터 레이어 및 파싱 비즈니스 로직에 반영합니다. (통과: Pass)
- **제V조 (Canvas 압축 & PWA 카메라)**: 프론트엔드에서 HTML5 Capture API 및 Canvas API를 탑재하여 업로드 직전 가로 최대 1000px 수준으로 1차 압축 처리를 진행합니다. (통과: Pass)
- **제VI조 (크로스 플랫폼 대칭 툴링)**: 추가되는 프로젝트 관리 스크립트가 있을 경우 Windows/Linux 대칭적으로 작성하여 `scripts/`에만 배치합니다. (통과: Pass)
- **제VII조 (선언적 의존성)**: 패키지 추가 시 `pyproject.toml`에 명시하고 `uv lock` / `uv sync`를 실행합니다. (통과: Pass)
- **제VIII조 (pytest & Django TestCase 하이브리드)**: DB 결합 테스트는 `django.test.TestCase` 및 `setUpTestData(cls)`를 사용하고, 순수 유틸 테스트는 `unittest.TestCase`를 활용해 격리하고 `pytest`를 기반으로 초고속 실행합니다. (통과: Pass)

## Project Structure

### Documentation (this feature)

```text
specs/008-upload-api-integration/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           
│   └── upload-api.md    # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── backend/
│   ├── settings.py
│   └── urls.py
├── receipts/
│   ├── models.py         # Ledger, LedgerItem, ReceiptUploadJob 모델
│   ├── serializers.py    # API 입출력 직렬화 스키마
│   ├── views.py          # upload 및 status/ API 뷰
│   └── services/
│       └── parser.py     # OCR 파서 및 템플릿 바이패스 서비스
└── tests/
    ├── test_views.py     # Django TestCase 기반 API 뷰 통합 테스트
    └── test_parser.py    # unittest.TestCase 기반 순수 파서 테스트

frontend/
├── src/
│   ├── components/
│   │   └── ReceiptDropzone.vue # HTML5 Canvas 1차 압축 탑재 업로드 컴포넌트
│   ├── services/
│   │   ├── uploadService.js    # Canvas 압축 및 axios API 통신
│   │   └── pollingService.js   # 가상 폴링 대기 루프 모듈
│   └── pages/
│       └── Dashboard.vue
└── tests/
```

**Structure Decision**: Frontend + Backend 가 구분된 모노레포 구조(Option 2)를 따르며, 백엔드는 장고의 `receipts/` 앱 내부 및 통합 `tests/`에서 동작을 제어하고, 프론트엔드는 `frontend/src/` 아래의 관련 컴포넌트 및 서비스에 연동 코드를 반영합니다.

## Complexity Tracking

*Gate 통과 시 어떠한 헌법 위배 사유도 존재하지 않으므로 본 섹션은 비워둡니다.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None      | N/A        | N/A                                 |
