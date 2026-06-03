# Implementation Plan: Setup Local Authentication with JWT

**Branch**: `009-jwt-local-auth` | **Date**: 2026-06-03 | **Spec**: [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/009-jwt-local-auth/spec.md)

**Input**: Feature specification from `specs/009-jwt-local-auth/spec.md`

## Summary

로컬 환경에서의 원활한 가계부 기능 테스트 및 보안 세션 통제를 위해 Django 기본 User 모델을 상속받은 Custom User 모델을 구현하고, `djangorestframework-simplejwt` 라이브러리를 활용해 로컬 회원 가입 및 JWT 발급/검증 체계를 구축합니다. 향후 `social-auth-app-django` 패키지를 이용한 소셜 로그인 확장이 용이하도록 가입 제공처(Provider) 등의 데이터 모델 사전 설계를 포함합니다.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: Django 4.2+, Django REST Framework (DRF), djangorestframework-simplejwt, social-auth-app-django (차후 도입 예정)

**Storage**: PostgreSQL v18+

**Testing**: pytest (테스트 러너), Django TestCase (`django.test.TestCase` + `setUpTestData` - DB 연합), unittest TestCase (`unittest.TestCase` - 순수 로직)

**Target Platform**: Docker Compose 로컬 인프라 (Linux 컨테이너 환경)

**Project Type**: web-service

**Performance Goals**: 회원가입 및 로그인 API 응답 속도 100ms 이내 방어 (DB 인덱스 최적화 및 JWT 무상태 검증 활용)

**Constraints**: 이메일 주소 고유성(`unique=True`), 비밀번호 안전 해싱(Django 기본 PBKDF2), Access Token 30분 만료, Refresh Token 14일 만료

**Scale/Scope**: 로컬 가입 및 JWT 기반 E2E 인증 MVP (소셜 로그인은 1단계 제외 및 연동 대비 스키마 설계에만 국한)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **제I조 데이터 무결성 및 원자성 게이트:** 이메일의 유니크 제약 조건을 데이터베이스 스키마 단에서 강제하여 중복 가입을 원천 차단하고 가입 트랜잭션의 원자성을 보장하는가? (통과 - Custom User 모델의 `email` 필드에 `unique=True` 설정 및 가입 뷰에 트랜잭션 적용)
- [x] **제VI조 크로스 플랫폼 대칭 및 문서 동기화 게이트:** 로컬 기동 및 관리 스크립트 작성 시 Windows(PowerShell)와 Bash 스크립트를 대칭적으로 구성하며, `AGENTS.md` 등의 코어 문서가 정상적으로 동기화되는가? (통과 - scripts 디렉토리 하위에 대칭형 도구 준수 및 이 변경 사항에 맞춰 AGENTS.md 계획 링크 업데이트)
- [x] **제VII조 선언적 의존성 게이트:** 새로 도입되는 `djangorestframework-simplejwt` 등의 의존성이 `pyproject.toml` 및 `uv.lock`에 선언적으로 관리되며 ad-hoc pip 설치를 배제하는가? (통과 - uv 패키지 통제 사용)
- [x] **제VIII조 하이브리드 테스트 게이트:** DB 접근이 수반되는 인증/인가 API 및 모델 테스트는 `django.test.TestCase`와 `setUpTestData`를 상속 및 적용하고, 토큰 서명 파싱 등 순수 유틸 테스트는 `unittest.TestCase`로 분리 설계하는가? (통과 - 하이브리드 테스트 전략 설계에 수록)

## Project Structure

이 피처는 백엔드(Django API Server) 내부에 장고 앱 형태로 구현됩니다.

### Documentation (this feature)

```text
specs/009-jwt-local-auth/
├── plan.md              # 이 문서 (구현 계획서)
├── research.md          # Phase 0 결과물 (인증 기술 리서치)
├── data-model.md        # Phase 1 결과물 (Custom User DB 모델 명세)
├── quickstart.md        # Phase 1 결과물 (로컬 API 가동 및 테스트 퀵스타트)
└── contracts/           # Phase 1 결과물 (가입/로그인 HTTP API 규격)
    ├── register.json    # 회원 가입 API 스키마
    └── login.json       # 로그인/JWT 발급 API 스키마
```

### Source Code (repository root)

이 기능은 백엔드 프로젝트 내부에 구현됩니다.

```text
backend/
├── apps/
│   └── accounts/        # 사용자 인증 담당 App
│       ├── models.py    # Custom User 모델 정의
│       ├── views.py     # 가입 및 로그인 API 뷰
│       ├── serializers.py # 데이터 검증 및 토큰 발급 직렬화기
│       └── urls.py      # 인증 엔드포인트 라우팅
├── config/
│   ├── settings.py      # DRF 및 SimpleJWT 설정 반영
│   └── urls.py          # accounts urls 마스터 라우팅 연동
└── tests/
    └── accounts/
        ├── test_models.py  # User 모델 테스트 (Django TestCase)
        ├── test_views.py   # JWT 가입/로그인 API 테스트 (Django TestCase)
        └── test_tokens.py  # 토큰 서명/검증 자체 유틸 테스트 (unittest TestCase)
```

**Structure Decision**: Django 앱 기반 단일 프로젝트 구조로 `backend/apps/accounts/` 아래에 핵심 인증 소스코드를 배치하고, `backend/tests/accounts/` 아래에 하이브리드 테스트 코드를 격리하여 관리합니다.

## Complexity Tracking

*추가적인 복잡성 증가나 헌법 위반 정당화 필요 사항 없음.*
