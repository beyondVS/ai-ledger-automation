# Implementation Plan: Template Promotion & Self-Healing

**Branch**: `019-auto-promote-template` | **Date**: 2026-06-13 | **Spec**: [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/019-auto-promote-template/spec.md)

**Input**: Feature specification from `/specs/019-auto-promote-template/spec.md`

## Summary

가맹점 영수증 레이아웃 템플릿의 자동 승인(Auto-Promotion), 강등(Demotion), 그리고 자가 치유(Self-Healing) 파이프라인을 구축하여 완전히 자동화된 비용 통제 엔진을 실현합니다. 동일한 파싱 규칙이 3회 연속 일관되게 도출될 경우 템플릿을 자동으로 승인하여 LLM API 비용을 회피하고, 에러나 사용자 데이터 수동 정정 발생 시 즉각 강등 조치 후 정정 데이터를 기준으로 템플릿을 자율 갱신(자가 치유)합니다.

## Technical Context

**Language/Version**: Python 3.13 (백엔드) / Vue 3 + Tailwind CSS (어드민 프론트엔드)

**Primary Dependencies**: Django 6.0+, djangorestframework, Celery 5.3+, redis, google-genai, litellm

**Storage**: PostgreSQL v18+ (ACID Transaction, JSONB, native UUIDv7)

**Testing**: pytest (비동기 및 단위 테스트) + Django TestCase (DB atomic 원자성 검증)

**Target Platform**: Linux Server (Docker Compose 로컬/프로덕션 인프라)

**Project Type**: web-service & async-worker (Django API Server + Celery Background Worker)

**Performance Goals**:
* 템플릿 강등 및 우회 차단 처리 시 5초 이내에 실시간 완료.
* 대시보드 어드민 API 쿼리 응답 시간 100ms 이내 방어.

**Constraints**:
* 연속 자가 치유 시도 3회 실패 시 자가 치유 프로세스 차단 및 관리자 수동 승격 보류 큐로 강제 이송.
* DB 커넥션 풀 크기 api_server 5개, async_worker 3개로 제약 수호.

**Scale/Scope**:
* 가맹점별 10자리 사업자등록번호 기반 템플릿 데이터 관리.
* 자가 치유 갱신 후 파싱 정확도 95% 이상 목표 유지.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **I. 데이터 무결성 및 원자성 트랜잭션 최우선**:
   * `MerchantTemplate` 및 `TemplateExecutionHistory` 업데이트 및 적재 연산은 Django ORM의 `transaction.atomic()` 하에서 하나의 트랜잭션으로 원자 처리되어야 함. (Pass)
2. **II. 비동기 큐 전환 및 자원 점유 최적화**:
   * 자가 치유 정규식 도출(LLM 호출) 및 사전 검증은 Celery 비동기 독립 워커(`verify_proposed_regex_task` 등의 확장 비동기 태스크) 내부에서 비동기로 실행되어야 함. (Pass)
3. **III. 하이브리드 비용 최적화 파이프라인**:
   * **[조정 필요]** 기존 헌법에는 "오직 어드민 수동 검토 완료 후에만 `is_verified: true` 승인"을 제약했으나, 가맹점 규모 확장에 대응하기 위해 "동일 정규식 3회 일치 시 자동 승인" 및 "에러/사용자 정정 시 자동 강등 및 자가치유"라는 자율 템플릿 승격 엔진을 신설함. 이는 비용 우회 절감율을 높이기 위해 타당하므로 허용함 (Complexity Tracking에 정당화 기재). (Pass - Justified)
4. **VI. 크로스 플랫폼 대칭 툴링 및 문서 동기화 수호**:
   * 로컬 빌드 및 데이터 마이그레이션 도구는 `scripts/local-db-controller.ps1`/`sh` 이중 대칭형 스크립트로 동작함을 유지함. (Pass)
5. **VIII. pytest 및 Django TestCase 하이브리드 테스트 수호**:
   * 템플릿 승인 및 강등/자가치유 라이프사이클의 DB 트랜잭션 수호 테스트는 `django.test.TestCase`를 상속하고 `setUpTestData(cls)`를 구현하여 작성하며, 순수 정규식 유틸리티 테스트는 `unittest.TestCase`로 작성함. (Pass)

## Project Structure

### Documentation (this feature)

```text
specs/019-auto-promote-template/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── admin_api.md     # Phase 1 output (Admin API schemas)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   └── template.py       # MerchantTemplate 확장 및 TemplateExecutionHistory 정의
│   ├── services/
│   │   ├── parser.py         # BypassParser 캐싱 및 ReceiptLLMClient 폴백 통합
│   │   └── promotion.py      # Template Promotion & Self-Healing 비즈니스 로직 서비스
│   ├── tasks/
│   │   └── template_tasks.py # 자가 치유 비동기 Celery 태스크
│   └── api/
│       └── admin_views.py    # 어드민 템플릿 조회 및 수동 조정 API 엔드포인트
└── tests/
    └── test_templates.py     # 템플릿 승인 및 자가 치유 단위/통합 테스트 코드

frontend/
├── src/
│   ├── components/
│   │   └── admin/            # 어드민 전용 공통 컴포넌트
│   └── pages/
│       └── admin/
│           ├── TemplateList.vue    # 가맹점 템플릿 목록 및 상태 뷰어 페이지
│           └── TemplateDetail.vue  # 템플릿 실행 이력 및 자가치유 로그 조회 페이지
```

**Structure Decision**: 백엔드 API 및 Celery 비동기 아키텍처에 핵심 로직을 분산 배치하고, 프론트엔드의 `pages/admin/`에 관리자용 모니터링/수동 개입 뷰를 신설하여 UI 상의 계약을 충족합니다.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 헌법 제III조 "수동 승인만 허용" 위배 | 가맹점 규모 확장에 대응하기 위해 사람이 직접 승인 버튼을 누르지 않아도 동일 패턴 3회 반복 검증 시 자동 승격(Promotion)하여 비용 우회 도입 효율을 극대화하기 위함. | 100% 수동 검토만 유지할 경우, 관리자의 검토 지연으로 인해 유료 LLM 비용이 지속 누수되고 바이패스 활성화율이 현격히 떨어짐. |
