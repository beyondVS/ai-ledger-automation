# Implementation Plan: Ledger Detail Edit & Delete Modal (CRUD)

**Branch**: `012-ledger-details-crud` | **Date**: 2026-06-07 | **Spec**: [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/012-ledger-details-crud/spec.md)

**Input**: Feature specification from `/specs/012-ledger-details-crud/spec.md`

## Summary

사용자가 가계부 목록에서 결제 정보 수동 수정 또는 영구 삭제를 요청할 수 있도록 모달(Modal) 기반 다이얼로그 시스템을 구축합니다. `Ledger` 데이터 모델에 지출 카테고리(`category`) 필드를 추가 마이그레이션하고, 본인 소유의 가계부만 수정 및 삭제가 가능하도록 데이터 격리가 수호된 PATCH/DELETE API를 연동합니다. 프론트엔드는 Glassmorphism 효과가 가미된 고급 UI 템플릿(Tailwind CSS)을 적용하여 수정 모달(유효성 검사 필터 탑재)과 삭제 경고 다이얼로그를 신규 추가하고 리스트를 300ms 이내에 즉각 갱신하도록 E2E 통합합니다.

## Technical Context

**Language/Version**: Python 3.11 (Backend Django/DRF) | JavaScript/Node.js (Frontend Vue 3/Vite)

**Primary Dependencies**: Django, djangorestframework, djangorestframework-simplejwt, Vue 3, Vite, Tailwind CSS, Axios, Lucide Icons

**Storage**: PostgreSQL v18+ (ACID 및 카테고리 인덱싱 수호)

**Testing**: pytest & Django TestCase (백엔드) | vitest & @vue/test-utils (프론트엔드)

**Target Platform**: Web Browser / PWA Standalone (Mobile & Desktop)

**Project Type**: web-service & frontend (모노레포 통합 서비스)

**Performance Goals**: 모달 팝업 표시 지연 150ms 이하, 수정/삭제 완료 후 화면 및 누적 누계 갱신 지연 300ms 이하

**Constraints**:
- **인증 연동**: JWT Access Token 기반 로그인 상태 필수 연동 및 헤더(`Authorization: Bearer <token>`) 주입
- **데이터 격리**: `Ledger.objects.filter(user=request.user)` 격리 필터 상시 적용
- **원자성 보장**: 상세 품목 연쇄 삭제 시 단일 트랜잭션(`transaction.atomic()`) 원자성 보장

**Scale/Scope**: 수만 건 이상의 지출 내역 누적 시에도 스크롤 끊김 및 갱신 딜레이 없는 CSS/DOM 처리

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 헌법 조항 | 요구 규칙 | 준수 설계 및 대응 방안 | 통과 여부 |
| :--- | :--- | :--- | :--- |
| **제I조 (데이터 무결성)** | 본인 데이터 격리 수정/삭제 및 atomic 트랜잭션 | `Ledger.objects.filter(user=request.user)` 격리를 통해 데이터 유출을 차단하며, CASCADE 자식 제거를 원자적으로 수행. | **Pass** |
| **제II조 (자원 최적화)** | DB 커넥션 풀 크기 제약 | `api_server` 데이터베이스 설정에 최대 풀 5개 제약 유지 검증. | **Pass** |
| **제V조 (PWA/보안)** | 모바일 터치 및 HTTPS 연동 | 모달 다이얼로그의 모바일 터치 접근성 확보 및 standalone 설치 상태에 어울리는 고급 UI 스키마 제공. | **Pass** |
| **제VI조 (대칭 툴링/문서)** | 3대 코어 문서 및 모노레포 설정 유기적 동기화 | 마일스톤 완료 및 설계 단계에서 `AGENTS.md` 내 계획 링크 연동 및 자동 동기화 완수. | **Pass** |
| **제VIII조 (테스트)** | pytest 러너 & Django TestCase 및 setUpTestData 활용 | DB 조회가 있는 가계부 수정/삭제 뷰 테스트에 `setUpTestData(cls)` 활용 및 `pytest` 기동 검증. | **Pass** |
| **제IX조 (품질 가드)** | ruff 및 pre-commit 자동화 품질 가드 수호 | 코드 수정 완료 후 커밋 전 `pre-commit` 훅을 실행해 린트/포맷 에러 100% 자율 해결. | **Pass** |

## Project Structure

### Documentation (this feature)

```text
specs/012-ledger-details-crud/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── checklists/
    └── requirements.md  # Specification Quality Checklist
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── apps/
│   │   └── ledgers/
│   │       ├── models.py      # category 필드 추가
│   │       ├── views.py       # PATCH, DELETE API (ReceiptDetailView)
│   │       ├── serializers.py # category 직렬화 및 유효성 검사 추가
│   │       └── urls.py        # 엔드포인트 연동
│   └── config/
└── tests/
    └── ledgers/
        └── test_ledger_detail_views.py  # CRUD 뷰 TDD 테스트

frontend/
├── src/
│   ├── components/
│   │   ├── LedgerEditModal.vue   # 수동 정정 모달
│   │   ├── LedgerDeleteModal.vue # 삭제 경고 모달
│   │   ├── LedgerListItem.vue    # 모달 트리거 이벤트 바인딩
│   │   └── DashboardView.vue     # 리스트 동적 갱신 연동
│   └── services/
│       └── ledgerService.js      # PATCH, DELETE fetch API 연동
└── tests/
    └── components/
        ├── LedgerEditModal.spec.js   # 수정 모달 TDD 테스트
        └── LedgerDeleteModal.spec.js # 삭제 모달 TDD 테스트
```

**Structure Decision**: 프론트엔드(Vue 3)와 백엔드(Django REST Framework)가 분리된 모노레포 구조(Option 2)를 채택하며, 백엔드 Django의 `ledgers` 앱과 프론트엔드의 `frontend/src/components` 단위를 타겟으로 편집을 집중시킵니다.

## Complexity Tracking

> *헌법 위반 사항 및 설계적 예외가 없으므로 공란으로 유지합니다.*

