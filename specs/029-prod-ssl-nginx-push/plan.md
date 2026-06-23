# Implementation Plan: Server Production SSL & E2E Push Release

**Branch**: `029-prod-ssl-nginx-push` | **Date**: 2026-06-23 | **Spec**: [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/029-prod-ssl-nginx-push/spec.md)

**Input**: Feature specification from `specs/029-prod-ssl-nginx-push/spec.md`

## Summary
실서버 프로덕션 환경의 고가용성 격리 배포(prod-bridge 내부 격리망 및 외부 포트 노출 차단) 및 SSL Offloading 기반의 HTTPS 역방향 프록시 인프라를 Nginx 게이트웨이를 통해 정식 탑재합니다. 아울러 3단계 하이브리드 영수증 비동기 파싱 태스크의 성공/실패 결과 및 월별 예산 한도(80%, 100%) 초과 경보 이벤트를 트리거로 작동하는 E2E 웹푸시 알림 채널(VAPID)을 구축하고, 네트워크 플래핑 시 오프라인 알림 IndexedDB 멱등적 로컬 캐싱 및 수신 확인(Acknowledgment ACK) 통신 체계를 프로덕션 규격에 맞춰 정식 릴리즈 및 E2E 검증합니다.

## Technical Context

**Language/Version**: Python 3.13, JavaScript (ES6+, Vue 3)

**Primary Dependencies**: `django-rest-framework`, `pywebpush`, `celery`, `redis`, `nginx`

**Storage**: PostgreSQL 18+ (JSONB 및 Native UUIDv7 탑재), IndexedDB (브라우저 로컬 알림 스토리지)

**Testing**: `pytest` (백엔드 단위/통합 테스트), `Playwright` (E2E 오프라인 웹푸시 검증 테스트)

**Target Platform**: Linux Server (Docker Compose v2 기반 멀티 컨테이너 환경)

**Project Type**: web-service

**Performance Goals**: Nginx HTTP -> HTTPS 301 리다이렉트 지연 50ms 이하, 백엔드 트리거 후 브라우저 알림 수신 완료 5초 이하 (안정적인 네트워크 환경 기준)

**Constraints**: Cloudflare/ALB를 통한 SSL Offloading 수용 (Nginx는 HTTP 80 포트로 동작), 단일 도메인 기반의 API(/api/) 및 프론트엔드 정적 파일 proxy_pass 중계 (CORS-free), PostgreSQL/Redis 컨테이너 외부 호스트 포트 바인딩 완전 차단, IndexedDB GC 처리 시 독립 readwrite 트랜잭션 격리 수립

**Scale/Scope**: Nginx 설정 고도화, `docker-compose.prod.yml` 성능/보안 튜닝, E2E 푸시 알림망 테스트 자동화 스크립트 구축

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Gate 1**: `docker-compose.prod.yml` 및 `docker-compose.yml` 상에 PostgreSQL(5432)과 Redis(6379)의 `ports` 바인딩이 외부로 노출되어 있지 않은가?
  - *Status*: **Pass** (호스트 포트 노출을 배제하고 오직 `prod-bridge` 내부 네트워크 대역에서만 상호 연결되도록 제약함 - 제X조 준수)
- **Gate 2**: Nginx의 리버스 프록시 설정이 CORS 설정 오버헤드 방지를 위해 단일 도메인 구조로 되어 있는가?
  - *Status*: **Pass** (Vite 정적 리소스 `/` 서빙 및 Django API `/api/` 리버스 프록시 중계 계약 성립 - 제V조 및 제X조 준수)
- **Gate 3**: Service Worker 및 IndexedDB 내의 가비지 컬렉션(GC) 로직 수행 시 브라우저 트랜잭션 타임아웃 예방을 위해 독립 트랜잭션이 격리 수립되었는가?
  - *Status*: **Pass** (30일 초과 삭제와 100개 초과 퍼지 작업에 대해 개별 write 트랜잭션을 실행하도록 프론트엔드 서비스 캐시 모듈에 명시 - 제V조 준수)
- **Gate 4**: E2E 오프라인 푸시 테스트 코드 내에 백엔드 API 단의 E2E 강제 테스트용 임시 분기가 심어져 있지 않은가?
  - *Status*: **Pass** (E2E 스위트 `offline-push.spec.js` 내에서 `child_process.execSync`로 백엔드 CLI 시더 스크립트를 직접 쉘 기동하여 테스트 격리를 수호하도록 보장함 - 제VIII조 준수)

## Project Structure

### Documentation (this feature)

```text
specs/029-prod-ssl-nginx-push/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── api.md           # REST API 및 인프라 프록시 계약 명세
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

이 피처는 Vue.js 프론트엔드와 Django 백엔드가 결합된 복합 모노레포 구조로 가동됩니다.

```text
backend/
├── src/
│   ├── models/          # PushSubscription, NotificationLog 모델
│   ├── views/           # 알림 등록, 해제, ACK, Sync API 뷰
│   └── tasks/           # Celery 웹푸시 발송 백그라운드 태스크
└── tests/               # pytest 기반 알림 API 유닛/통합 테스트

frontend/
├── src/
│   ├── components/      # 알림 상태 렌더링 컴포넌트
│   ├── services/        # IndexedDB 캐시 서비스, Web Push 구독 연동
│   └── sw.js            # 서비스 워커 (비-HTTP 스키마 예외 필터링 포함)
└── tests/               # Playwright 기반 E2E 오프라인 알림 테스트

docker-compose.prod.yml   # 프로덕션 전용 컨테이너 리소스 고정 및 네트워크 격리 정의
nginx.conf                # Nginx 인그레스 및 역방향 프록시 라우팅 정의
scripts/
└── run_e2e_push_test.ps1/sh # E2E 통합 테스트 쉘 기동 스크립트 (크로스 플랫폼 대칭)
```

**Structure Decision**: 프론트엔드 SPA 정적 자산과 백엔드 Django REST API가 `docker-compose.prod.yml`을 통해 통합 핫 릴리즈될 수 있도록, 위 2열(Option 2: Web application) 모노레포 레이아웃 구조를 영구 수호하고 결정합니다.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*(프로젝트 헌법상의 모든 게이트를 통과하였으며, 정당화가 필요한 헌법 위반 사항이 부재하므로 작성하지 않습니다)*
