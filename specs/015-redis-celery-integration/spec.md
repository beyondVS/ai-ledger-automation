# Feature Specification: Redis In-Memory Store Infrastructure Setup & Celery Worker Role Separation

**Feature Branch**: `015-redis-celery-integration`

**Created**: 2026-06-08

**Status**: Draft

**Input**: User description: "비동기 처리를 위한 Redis 인메모리 스토어 인프라 구축 및 Docker Compose 환경 통합. 2주차까지 설계된 동기식 가동 서버를 Django 메인 서버와 Celery 백그라운드 워커 서버로 역할 분리 설계."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Receipt Upload with Asynchronous Extraction and Instant Response (Priority: P1)

영수증을 업로드하면 시간이 오래 걸리는 텍스트 추출 및 OCR 분석 작업이 백그라운드에서 비동기로 처리되고, 사용자는 페이지가 고정되는 현상 없이 즉시 업로드 성공 및 접수 결과를 확인하고 대시보드로 이동할 수 있습니다.

**Why this priority**: 메인 사용자 경험(UX)의 핵심 부분이며, 파일 업로드 시 발생하는 긴 서버 타임아웃 문제를 해결하여 서비스의 전체적인 체감 성능을 향상시키는 핵심 기능입니다.

**Independent Test**: 영수증 업로드 API 호출 시 동기식 OCR 처리를 거치지 않고, 2초 이내에 접수 상태(예: 작업 ID 및 상태 'Pending')를 응답하는지 검증합니다.

**Acceptance Scenarios**:

1. **Given** 사용자가 대시보드에서 영수증을 업로드하고, **When** 업로드 요청을 전송하면, **Then** 시스템은 대기 상태의 작업 ID를 반환하며 사용자 화면은 지연 없이 즉시 대시보드로 새로고침된다.
2. **Given** 백그라운드 워커에서 텍스트 추출이 완료되면, **When** 사용자가 대시보드 목록을 새로고침하여 영수증 내역을 조회할 때, **Then** 해당 영수증의 데이터 필드에 추출된 최종 텍스트 정보가 올바르게 업데이트되어 출력된다.

---

### User Story 2 - System Stability under Batch Upload (Priority: P2)

여러 장의 영수증을 동시에 일괄 업로드(Batch Upload)하더라도 웹 애플리케이션 서버가 응답 불능 상태나 게이트웨이 타임아웃에 빠지지 않고, 유입되는 영수증 분석 요청들이 대기열(Queue)에 안전하게 누적되어 워커에 의해 순차적으로 정상 처리됩니다.

**Why this priority**: 대량의 데이터 처리 시 발생할 수 있는 시스템 부하를 격리하고, 웹 서버의 가용성을 보호하여 가계부 서비스의 신뢰성을 유지하기 위함입니다.

**Independent Test**: 10개 이상의 영수증을 동시에 업로드 요청하여, 웹 응답이 504 Timeout 없이 모두 성공적으로 큐에 적재되고 백그라운드에서 누락 없이 차례로 완수되는지 확인합니다.

**Acceptance Scenarios**:

1. **Given** 한 번에 15개의 영수증이 동시에 업로드될 때, **When** 웹 서버가 이를 수신하면, **Then** 웹 서버는 서비스 지연 없이 모든 요청을 메시지 대기열에 분할 적재하고 즉시 접수 처리 응답을 보낸다.

---

### Edge Cases

- **What happens when** 백그라운드에서 OCR 분석을 진행하는 동안 외부 API나 라이브러리 예외로 인해 텍스트 추출이 실패하는 경우 어떻게 처리되는가?
- **How does system handle** 백그라운드 워커 서버가 시스템 부하로 다운되었다가 재시작되었을 때, 메시지 브로커에 누적되어 있던 대기 중인 작업들의 메시지 영속성 및 유실 여부는 어떻게 처리되는가?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 시스템은 기존의 동기식 영수증 분석 로직을 분리하여 웹 응답 이후 백그라운드 프로세스에서 동작하는 비동기 태스크로 전환해야 한다.
- **FR-002**: 시스템은 웹 서버와 백그라운드 분석 작업을 처리하는 워커 서버를 상호 분리된 독립 컨테이너/프로세스로 구동하여 단일 프로세스 장애가 타 영역으로 전파되는 것을 격리해야 한다.
- **FR-003**: 사용자는 작업 ID를 활용하여 본인의 영수증 분석 태스크의 실시간 처리 상태(Pending, Processing, Success, Failed)를 조회할 수 있는 기능적 엔드포인트를 가져야 한다.
- **FR-004**: 백그라운드 분석 도중 예외가 발생할 경우, 해당 태스크는 안전하게 실패 상태로 마킹되고 시스템 전체(웹 서버 및 타 태스크)는 지속 가동되어야 한다.
- **FR-005**: 시스템은 비동기 작업 실패 시 재시도(Retry) 규칙을 가져야 하며, 최대 3회의 재시도 및 지수 백오프(Exponential Backoff) 정책을 적용해야 한다.
- **FR-006**: 백그라운드에서 처리 중인 영수증 분석 결과를 최종 사용자에게 전달하기 위해 클라이언트 주기적 폴링(Polling) 방식을 적용하며, 차후 SSE(Server-Sent Events)나 푸시 알림으로 유연하게 변경할 수 있는 추상화된 구조 설계를 보장해야 한다.
- **FR-007**: 비동기 작업을 스케줄링하고 큐의 상태를 모니터링하기 위해 실시간 대시보드(예: Flower)를 구축하고 로컬 개발/운영 환경에 통합해야 한다.

### Key Entities *(include if feature involves data)*

- **LedgerJob**: 비동기로 처리되는 개별 영수증 분석 태스크를 식별하고 상태를 추적하기 위한 데이터 엔티티입니다.
  - *작업 ID (Job UUID)*: 태스크 식별용 고유 식별자.
  - *대상 Ledger ID (Ledger Reference)*: 분석 결과를 반영할 대상 가계부 내역과의 연계 레퍼런스.
  - *진행 상태 (Job Status)*: Pending, Processing, Success, Failed.
  - *실패 사유 (Failure Reason)*: 오류 발생 시 디버깅을 위한 에러 로그 요약 정보.
  - *타임스탬프 (Timestamps)*: 생성 일시, 갱신 일시.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 단일 영수증 업로드 시 사용자가 업로드 완료 및 접수 응답을 받기까지 소요되는 응답 시간(Latency)은 2초 이내여야 합니다.
- **SC-002**: 동시 영수증 업로드 요청이 50건 이상 일시 유입되더라도 웹 서버의 CPU/메모리 병목이나 5xx 계열 서버 에러가 발생하지 않고 100% 정상 수신되어야 합니다.
- **SC-003**: 백그라운드 워커 프로세스가 갑작스럽게 정지되었다가 재가동되는 최악의 상황에서도, 브로커 인프라 내에 대기 중이던 처리 대기 태스크들의 유실률은 0%여야 합니다.

## Assumptions

- 메시지 브로커(Redis) 및 백그라운드 워커는 동일한 로컬 가상 네트워크망(Docker Compose) 내에서 안전한 접근 제어를 통해 통신한다고 가정합니다.
- 영수증 OCR 텍스트 분석 모듈은 백그라운드 워커 내부에서 안전하게 로딩 및 임포트될 수 있는 구조로 이미 구현되어 있다고 가정합니다.
- 데이터베이스(PostgreSQL)는 다중 컨테이너 접속(웹 서버 및 백그라운드 워커 서버)을 허용하도록 적절한 커넥션 풀 크기 제한 정책을 공유한다고 가정합니다.
