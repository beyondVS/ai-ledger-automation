# Implementation Plan: Docker Compose Prod Tuning & Port Security

**Branch**: `028-docker-compose-prod-tuning` | **Date**: 2026-06-23 | **Spec**: [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/028-docker-compose-prod-tuning/spec.md)

**Input**: Feature specification from `/specs/028-docker-compose-prod-tuning/spec.md`

**Note**: This plan defines the infrastructure configuration, resources allocation limits, logs rotation management, and ports security mapping protocols for the production release of the application.

## Summary

본 구현 계획은 대규모 실 운영 환경에 대응하기 위해 프로덕션 도커 컴포즈 환경(`docker-compose.prod.yml`)을 최적화 튜닝하고, 외부 포트 노출 차단 등의 보안 제어 및 로그 무한 누적 방지 방어벽을 설계하는 작업입니다. 사용자의 의사결정(Q1: A, Q2: A, Q3: A)에 의거하여 포트 접근을 차단하고, 도커 Named Volume을 적용하며, 절대 리소스 한계를 YAML 상에 고정 선언하는 방향으로 구체적인 실행 계획을 정의합니다.

## Technical Context

**Language/Version**: Python 3.13 (Backend API & Celery) / Docker Compose Specification v2.x+ / Nginx v1.25+

**Primary Dependencies**: Docker Engine v27+, Nginx, docker-compose-plugin

**Storage**: PostgreSQL v18+ (Named Volume 적용), Redis v7+ (Internal bridge network only)

**Testing**: pytest (헬스체크 오작동 감지 시나리오 및 복구 시간 측정 검증용), nmap/nc (외부 IP 포트 격리 검증용)

**Target Platform**: Linux Server (Ubuntu 22.04 LTS 이상 환경 권장)

**Project Type**: Infrastructure deployment & Port-level security control

**Performance Goals**: 
- 외부 공인망 대상 포트 스캔 시 웹 포트(80/443) 이외의 전용 포트 접근 100% 차단 (Connection Refused/Filtered).
- 헬스체크 비정상 판정 시 60초 이내에 자동 OOTB 감지 및 재시작 완료.
- 무제한 로그 누적으로 인한 디스크 고갈 예방 (단일 컨테이너당 누적 로그 총합 30MB 상한 강제).

**Constraints**:
- docker-compose.prod.yml 파일 내에 CPU 점유 비율 및 메모리 물리 한도(limits) 고정 작성.
- PostgreSQL 데이터 볼륨 마운트는 Named Volume(`postgres_data`)을 적용하여 호스트와의 권한 격리 및 이식성 수호.

**Scale/Scope**: 전체 프로덕션 도커 서비스 (Nginx 역방향 프록시, DRF api-server, Celery async-worker, PostgreSQL 데이터베이스, Redis 캐시/브로커)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **헌법 제II조 (자원 점유 최적화 및 커넥션 풀 격리)**:
  - 컴포즈 설정 상에서 PostgreSQL 커넥션 설정과 개별 컨테이너 자원 한도(limits)를 절대 용량으로 분할 제한하여, 특정 프로세스의 폭주가 인프라 붕괴로 번지는 것을 물리 격리합니다. (부합 완료)
- **헌법 제V조 (HTTPS/JWT 보안 강제 및 서비스 워커 규격 수호)**:
  - 프로덕션 릴리즈 환경을 위해 외부 유입 포트를 Nginx 80/443 포트로 일원화하고 프록시 포워딩을 수행하여, 실서버에서의 SSL 적용 및 보안 통신 환경 구축을 인프라 레벨에서 강제할 수 있도록 지원합니다. (부합 완료)
- **헌법 제VI조 (크로스 플랫폼 대칭 툴링 및 scripts/ 격리 수호)**:
  - 본 설계에 따라 배포 인프라를 가동하거나 외부 포트 접근 격리 상태를 모니터링 검증하는 커스텀 자동화 툴 스크립트는 프로젝트 루트의 `scripts/` 폴더 하위에 Bash(`*.sh`) 및 PowerShell(`*.ps1`) 대칭형 파일로 구축할 계획입니다. (부합 완료)

## Project Structure

### Documentation (this feature)

```text
specs/028-docker-compose-prod-tuning/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── ports-contract.md
└── tasks.md             # Phase 2 output (created by /speckit-tasks command)
```

### Source Code (repository root)

```text
.
├── docker-compose.yml             # 로컬 개발 및 E2E 테스트 통합 제어용 컴포즈
├── docker-compose.prod.yml        # 프로덕션 최적화 튜닝 및 포트 격리용 컴포즈
├── backend/                       # DRF api-server 및 Celery 비동기 워커 소스
├── frontend/                      # Vue.js 3 PWA 모바일 클라이언트 소스
├── scripts/                       # 크로스 플랫폼 대칭형 검증 도구 배치
│   ├── run_port_scan.ps1          # 포트 차단 검증 스크립트 (Windows)
│   └── run_port_scan.sh           # 포트 차단 검증 스크립트 (Bash)
└── specs/                         # 기획 명세 및 구현 계획 디렉토리
```

**Structure Decision**: 상위 프로젝트 루트 레벨에 기존 `docker-compose.yml`과 대칭되는 `docker-compose.prod.yml` 파일을 작성 배치하여 모노레포 관리 통합성을 높이고, 검증에 필요한 도구는 헌법 제VI조에 의거하여 `scripts/` 폴더 내에 배치합니다.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*(해당 사항 없음. 헌법 상의 자원 최적화, 보안 환경, 크로스 플랫폼 대칭 툴링 규칙을 100% 충족함)*
