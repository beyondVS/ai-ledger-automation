# Implementation Plan: django-initial-setup

**Branch**: `004-django-initial-setup` | **Date**: 2026-05-31 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-django-initial-setup/spec.md`

## Summary

`backend/src/config` 하위에 위치한 Django 웹 애플리케이션 프레임워크의 코어 보일러플레이트를 완벽히 작동 가능한 상태로 재정비하고 셋업한다. `.env` 파일을 통한 철저한 환경변수 파싱(`django-environ`)을 구현하여 하드코딩을 배제하며, PostgreSQL v18+ 연동(`psycopg3`) 설정을 완수한다. 또한, 향후 SPA 클라이언트와의 API 통신을 고려해 CORS와 DRF 기본 권한(전역 `IsAuthenticated` 락 적용)을 선행 연동한다.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: Django 4.2 LTS / 5.0+, `django-environ`, `djangorestframework`, `django-cors-headers`, `psycopg[binary]` (psycopg3 C 가속화 드라이버)

**Storage**: PostgreSQL v18+

**Testing**: Django 내장 Test Runner (`backend/src/manage.py test`) 및 `pytest-django`

**Target Platform**: Linux server / Local Docker Compose

**Project Type**: web-service (REST API Backend)

**Performance Goals**: Django 웹 서버 실행 명령 수행 시 3초 이내에 정상 기동 완료

**Constraints**:
- **자격 증명 하드코딩 금지**: settings.py 내부에 데이터베이스 주소, 비밀번호 등 어떠한 자격 증명 관련 폴백 기본값을 하드코딩하는 것도 강력히 방지한다.
- **철저한 환경 검증**: `.env`에 필수 환경 변수(`SECRET_KEY`, `DATABASE_URL`) 누락 시 즉시 `ImproperlyConfigured` 예외를 노출하고 서버 구동을 안전히 중단한다.
- **DB 커넥션 관리**: Supabase Free plan 한계 제약(api_server 최대 5개 커넥션 점유)을 엄수하며, 기본 연결 유지 시간(`CONN_MAX_AGE`)을 60초로 적용하되 `.env`로 동적 오버라이드가 가능하도록 구성한다.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 헌법 조항 | 요구 명세 | 합치성 검증 결과 |
| :--- | :--- | :--- |
| **I. 데이터 정합성 & 트랜잭션** | PostgreSQL v18+ 연동 정합성 확보 및 런타임 커넥션 풀 제어 | **PASS**: `psycopg3` 드라이버를 완벽히 바인딩하고 연결 풀의 안정적 구동 여부 검증 |
| **II. 비동기 큐 & 자원 최적화** | 무료 티어 가용한계(api_server 최대 5개 커넥션 점유) 제약 엄수 | **PASS**: settings.py 내에 `CONN_MAX_AGE: 60` 설정 및 오버라이드 상수를 주입하여 자원 병목 사전 통제 |
| **VI. 크로스 플랫폼 대칭 툴링** | 셋업/기동 커스텀 자동화 스크립트는 `scripts/` 하위에 배치 (Windows `.ps1` 및 macOS/Linux `.sh` 대칭) | **PASS**: 로컬 셋업 자동화 스크립트를 `scripts/` 디렉토리에만 배포하며 양대 OS 호환 대칭 제공. `.specify/` 자산 무혼입 유지 |
| **VII. 선언적 의존성 및 uv 격리** | 패키지 추가 시 반드시 `backend/pyproject.toml`에 기재하고 `uv` 도구를 통한 가상환경 관리 | **PASS**: ad-hoc 설치 배제. `django-environ`, `djangorestframework`, `django-cors-headers`를 `pyproject.toml`에 추가하고 `uv sync`를 통해 락 파일 갱신 |

## Project Structure

### Documentation (this feature)

```text
specs/004-django-initial-setup/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── health_check_contract.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── manage.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py    # 핵심 settings.py 리팩토링 및 셋업 대상
│   │   ├── urls.py        # CORS / Health Check / DRF 진입점 명세
│   │   └── wsgi.py
│   └── apps/              # 어플리케이션 기능 디렉토리
├── pyproject.toml         # backend 의존성 관리
└── uv.lock                # backend 의존성 락 파일

scripts/                   # 프로젝트 관리용 스크립트 (헌법 제VI조)
├── setup_boilerplate.ps1  # Windows용 보일러플레이트 자동화 셋업 도구
└── setup_boilerplate.sh   # macOS/Linux용 보일러플레이트 자동화 셋업 도구
```

**Structure Decision**: 
이미 설계 완료되어 있는 모노레포 구조의 `backend/src/config/` 레이아웃 및 진입점을 전적으로 보존하여 사용합니다. 또한 헌법 제VI조에 따라 빌드 및 의존성 설정을 포함한 커스텀 자동화 스크립트는 프로젝트 루트의 `scripts/` 폴더 하위에만 Windows/macOS 대칭형으로 배포하여 정결성을 완벽하게 수호합니다.

## Complexity Tracking

> **수립된 헌법 규칙에 위배되는 예외 사항 및 복잡성 요소가 없으므로 해당 섹션 비워둠.**
