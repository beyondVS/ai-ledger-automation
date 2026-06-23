# Feature Specification: Server Production SSL & E2E Push Release

**Feature Branch**: `029-prod-ssl-nginx-push`

**Created**: 2026-06-23

**Status**: Approved

**Input**: User description: "서버 실 프로덕션 환경 HTTPS SSL 보안 인증 및 Nginx 리버스 프록시 탑재, 웹 업로드 및 PWA/웹푸시 기반 전 과정 E2E 통합 알림망 정식 릴리즈 완료."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Production HTTPS & Security Proxy (Priority: P1)

사용자는 HTTPS 보안 프로토콜을 통해서만 서비스에 접속할 수 있어야 하며, HTTP 접속 시 HTTPS로 강제 리다이렉트되어야 합니다. 모든 정적 자산과 API 호출은 SSL 보안 연결하에 작동해야 합니다.

**Why this priority**: 보안 및 PWA 설치/웹 푸시 규격을 충족하기 위한 필수 기반 인프라입니다.

**Independent Test**: 브라우저에서 http://로 접속 시 https://로 정상 리다이렉트되는지 확인하고, 유효한 SSL 인증서가 브라우저에 적용되었는지 검증합니다.

**Acceptance Scenarios**:

1. **Given** HTTP connection is initiated, **When** Nginx receives the request, **Then** it redirects to HTTPS with 301.
2. **Given** HTTPS connection is established, **When** client requests API or static assets, **Then** Nginx routes to correct containers securely.

---

### User Story 2 - Receipt Upload to Web Push E2E Journey (Priority: P1)

사용자가 PWA 앱에서 카메라로 영수증을 캡처하거나 파일을 업로드하면, 백엔드 Celery 태스크에서 비동기로 분석을 처리하고, 처리가 완료되는 즉시 브라우저로 웹푸시 알림을 발송하여 수신합니다. 단말이 오프라인 상태일 때는 수신 대기하고 온라인 복귀 시 캐시된 알림이 IndexedDB에 안전하게 적재되고 백엔드로 ACK가 전달됩니다.

**Why this priority**: 오프라인 캐싱 및 웹 푸시가 결합된 가계부 자동화의 핵심 사용자 여정(E2E)입니다.

**Independent Test**: 백엔드 mock DB를 시딩하고 E2E 오프라인 푸시 테스트 쉘 스크립트를 기동하여 알림 발송 및 단말 도달, IndexedDB 멱등적 적재 여부를 검증합니다.

**Acceptance Scenarios**:

1. **Given** active user subscription is registered, **When** receipt processing finishes, **Then** backend triggers Web Push notification.
2. **Given** user terminal is offline, **When** notification is sent, **Then** it is cached in IndexedDB upon reconnection and acknowledged back to API.

---

### User Story 3 - Production Configuration Testing & Diagnostics (Priority: P2)

시스템 관리자는 배포된 실 서버 프로덕션 환경의 정상 동작 여부(Nginx, Django API, Celery, Redis, PostgreSQL)를 확인하기 위해, 강제로 테스트 알림을 발생시키고 전체 파이프라인의 응답 지연을 측정할 수 있는 진단 도구 혹은 테스트 커맨드를 사용할 수 있어야 합니다.

**Why this priority**: 프로덕션 배포 후 시스템 가용성과 알림망의 E2E 건전성을 정기적 또는 배포 직후에 모니터링하기 위함입니다.

**Independent Test**: 관리자 API 혹은 백엔드 CLI 커맨드를 통해 mock 사용자에게 테스트 웹푸시를 발송하고 수신 성공 여부를 파악합니다.

**Acceptance Scenarios**:

1. **Given** admin permissions, **When** trigger test command is executed, **Then** it bypasses regular queues and sends immediate web push.

---

### Edge Cases

- Let's Encrypt 인증서 갱신 시 일시적인 Nginx 서비스 다운타임 방지
- 웹 푸시 수신 시 브라우저 알림 권한이 거부되었을 때의 사용자 경험 처리 및 예외 처리
- IndexedDB 저장 용량 초과 또는 트랜잭션 타임아웃 발생 시 오프라인 알림 유실 방지
- 네트워크 끊김 및 플래핑 상태에서 수신 확인(Acknowledgment) API 호출 실패 시 재시도 로직

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Nginx MUST enforce HTTPS by redirecting all HTTP traffic to HTTPS.
- **FR-002**: System MUST support SSL Offloading via external cloud proxies (e.g. AWS ALB, Cloudflare), where Nginx operates on HTTP port 80 and receives forwarded HTTPS traffic securely.
- **FR-003**: E2E notification pipeline MUST support 3-tier receipt processing results (Success/Failure) and monthly budget threshold breach (80% and 100%) as core business events to alert users dynamically.
- **FR-004**: Nginx MUST be configured with a single domain routing structure utilizing subpath routing, serving frontend SPA assets at the root path (/) and reverse proxying backend API requests under the (/api/) subpath without CORS conflicts.
- **FR-005**: Offline push caching system MUST persist notifications to IndexedDB with UUIDv7 as key to ensure idempotency.
- **FR-006**: Web push subscriptions MUST deactivate immediately upon receiving 404 or 410 Gone responses from push services.

### Key Entities

- **PushSubscription**: 사용자 브라우저의 웹푸시 구독 엔티티. 브라우저 엔드포인트 정보, P256DH 키, Auth 인증 토큰 등을 관리합니다.
- **NotificationLog**: 전송된 알림 내역의 로그 엔티티. UUIDv7 식별자, 수신자 정보, 전송 일시, 전송 유형, 성공 여부 등을 기록합니다.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of HTTP incoming requests are redirected to HTTPS within 50ms.
- **SC-002**: Web Push notifications triggered by backend tasks are delivered to browser client within 5 seconds under stable network.
- **SC-003**: No duplicate notification records are inserted into IndexedDB even under extreme network flapping (100% idempotency).
- **SC-004**: All expired notification logs (older than 30 days) are successfully purged without service disruption.

## Assumptions

- Let's Encrypt 또는 외부 CA를 통해 신뢰할 수 있는 SSL 인증서가 확보되어야 프로덕션 가동이 가능합니다.
- 프론트엔드는 빌드 후 Nginx가 직접 정적 파일로 서빙하거나 Vite 프로덕션 프리뷰를 Nginx가 중계합니다.
- 사용자는 알림 수신을 위한 브라우저 권한을 승인한 상태여야 웹 푸시가 유효하게 전송됩니다.
- 모바일 환경에서의 PWA 기능 제공을 위해 HTTPS 연결이 필수적입니다.
