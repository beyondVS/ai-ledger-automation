# Implementation Plan: Frontend Authentication and Client-side Image Resizing

**Branch**: `010-auth-ui-image-resize` | **Date**: 2026-06-05 | **Spec**: [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/010-auth-ui-image-resize/spec.md)

**Input**: Feature specification from [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/010-auth-ui-image-resize/spec.md)

---

## Summary

본 피처는 프론트엔드 로그인 상태 체크(인증 토큰 기반 라우터 가드 구현) 및 실제 사용자 로그인/회원가입 UI 화면 개발과 모바일 사용자 전용 클라이언트 사이드 이미지 리사이징 모듈(HTML5 Canvas API 1000px JPEG 80% 압축)의 내장 구현을 목표로 합니다. 백엔드의 SimpleJWT API와 정교하게 연동하여 보안 접근 통제를 수행하고, 업로드 직전 클라이언트 압축을 거쳐 트래픽을 최소화합니다.

## Technical Context

**Language/Version**: Python 3.11 (백엔드) & JavaScript/TypeScript (Vue.js 3 / Vite) (프론트엔드)

**Primary Dependencies**: Django, Django REST Framework, djangorestframework-simplejwt (백엔드) & Vue.js 3, vue-router@4, tailwindcss (프론트엔드)

**Storage**: PostgreSQL v18+ (주요 ACID 데이터) & LocalStorage (프론트엔드 JWT 토큰 보관소)

**Testing**: pytest / django.test.TestCase (백엔드) & Vitest / @vue/test-utils (프론트엔드)

**Target Platform**: Docker Compose 가상 인프라 배포 환경, Modern Mobile & Desktop Web Browsers (Safari, Chrome 등)

**Project Type**: Web application (frontend + backend 모노레포 구조)

**Performance Goals**: 
- 모바일 고용량 영수증 이미지 업로드 시 전송 크기 90% 이상 절감 (5MB -> 500KB 이하)
- 비로그인 사용자의 무단 보안 구역 진입 차단 0.5초 이내 완료 (Vue Router Navigation Guard)
- 로그인/회원가입 폼 제출 후 첫 페이지 렌더링 2초 이내 완료

**Constraints**:
- Supabase 무료 DB 커넥션 풀 크기 제약 (api 5개, celery 3개, 합산 8개 이하 유지)
- 실서버 HTTPS SSL 보안 도메인 적용 강제 (서비스 워커 등록 규격 충족)
- Canvas API 드로잉 버퍼 제한에 의한 모바일 단말 메모리 세이프 가드 작동

**Scale/Scope**: 가계부 업로드 및 관리를 보호하는 인증 게이트웨이 화면 및 이미지 전처리 파이프라인

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **헌법 제V조 (Mobile-first PWA & HTTPS Mandated) 준수 여부**: `Pass`. 업로드 전 클라이언트 단 HTML5 Canvas API를 가동하여 이미지를 가로 최대 1000px 및 JPEG 80% 압축 처리하여 전송하는 것을 아키텍처 및 유틸리티 설계의 필수 규칙으로 수용함.
- **헌법 제VI조 (Cross-platform Symmetric Tooling & Autonomous Document Sync) 준수 여부**: `Pass`. `AGENTS.md`의 계획 참조 마커를 이번 10번째 계획인 [plan.md](file:///D:/Projects/Private/ai-ledger-automation/specs/010-auth-ui-image-resize/plan.md) 경로로 동기화하여 유지함.
- **헌법 제VIII조 (pytest 및 Django TestCase 하이브리드 테스트 수호) 준수 여부**: `Pass`. 로그인/회원가입 API 백엔드 기능 연동 및 인증 테스트 작성 시 `django.test.TestCase` 클래스를 상속받고 `setUpTestData(cls)`를 활용하도록 설계 단계에서 엄격히 제한함.

## Project Structure

### Documentation (this feature)

```text
specs/010-auth-ui-image-resize/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── checklists/
│   └── requirements.md  # Specification Quality Checklist (Pass)
└── contracts/
    └── auth-api.md      # API schema contract between FE and BE
```

### Source Code (repository root)

```text
backend/
├── src/
│   └── apps/
│       └── accounts/        # User, UserRegisterSerializer, Login/Logout Views
└── tests/
    └── apps/
        └── accounts/        # JWT Authentication E2E tests using django.test.TestCase

frontend/
├── src/
│   ├── components/
│   │   └── auth/            # LoginView.vue, RegisterView.vue UI views
│   ├── router/
│   │   └── index.js         # Vue Router configuration & beforeEach guard
│   ├── utils/
│   │   └── imageResizer.js  # Canvas API Image resizing utility
│   └── services/
│       └── authService.js   # JWT authentication client & LocalStorage store binding
└── tests/
    └── components/          # Vitest UI Component tests
```

**Structure Decision**: 프론트엔드와 백엔드가 분리된 웹 애플리케이션 모노레포 구조(Option 2)를 채택하고, 기존 백엔드 `accounts` 앱 모듈과 신규 프론트엔드 `router`, `auth` 컴포넌트, `imageResizer` 유틸리티를 결합하여 설계합니다.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

헌법 위반 사항이 전혀 없으므로 해당 없음 (`N/A`).
