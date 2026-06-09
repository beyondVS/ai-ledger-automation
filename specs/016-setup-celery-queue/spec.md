# Feature Specification: Celery 비동기 작업 큐 및 Docker 통합 개발 환경 구축

**Feature Branch**: `016-setup-celery-queue`

**Created**: 2026-06-09

**Status**: Draft

**Input**: User description: "Celery를 도입한 비동기 작업 큐 시스템 구축. 인프라 메모리 및 커넥션 부하 방지를 위해, Django settings.py 내 DB 커넥션 풀 크기를 최대 5개, Celery 워커의 풀 크기를 최대 3개로 엄격히 제한하는 풀 통제 알고리즘 구현. 메인 서버는 업로드 접수 즉시 대기(Pending, 202)를 반환하도록 비동기 리팩토링. [추가 계획] 백엔드, Celery, 프론트엔드를 전체 Dockerizing하고, 로컬 마운트 기반 핫 리로딩 인프라 통합 구축."

## Clarifications

### Session 2026-06-09

- Q: 비동기 작업 상태 조회(Polling) 주기 및 타임아웃 임계치 정책 → A: 2초 간격 폴링 수행, 최대 30초 대기 후 완료되지 않을 시 타임아웃(실패) 처리 (옵션 A)
- Q: Celery 비동기 작업 실패 시 자동 재시도(Retry) 정책 → A: 최대 3회 자동 재시도 수행 (지수 백오프(Exponential Backoff) 대기 적용) (옵션 B)
- Q: 이번 016 피처의 구현 범위 경계선 (Out-of-Scope) 지정 정책 → A: 웹 업로드 비동기화 및 Docker Compose 인프라 구축에 집중하고, 이메일 웹훅 및 푸시 알림은 이번 016 피처의 Out-of-Scope로 배제하여 후속 피처로 연기 (옵션 A)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 비동기 영수증 업로드 및 상태 조회 (Priority: P1)

사용자가 PWA 대시보드 또는 이메일 포워딩을 통해 영수증을 업로드하면, 긴 대기 시간 없이 즉시 접수 상태가 대시보드에 노출되고, 백그라운드 분석이 완료되면 결과가 대시보드에 자동으로 업데이트되어 최신 내역을 조회할 수 있다.

**Why this priority**: 메인 API 서버의 Latency 병목을 해결하고 사용자에게 빠른 업로드 접수 피드백을 제공하여 쾌적한 UX를 확보하는 데 핵심이 되는 P1 MVP 시나리오입니다.

**Independent Test**: 메인 API 서버에 파일 업로드 API 요청을 전송하여 즉시 HTTP 202 응답과 작업 ID를 반환받는지 확인하고, 이후 작업 상태 확인(Polling) API를 통해 상태가 Completed로 전환되고 데이터베이스에 최종 적재되는지 E2E로 테스트할 수 있습니다.

**Acceptance Scenarios**:

1. **Given** 사용자가 대시보드에서 영수증 이미지 파일을 업로드할 때, **When** 업로드 요청을 전송하면, **Then** 서버는 즉시 HTTP 202 Pending 응답과 작업 ID(job_id)를 반환하고 화면에 처리 대기 뷰를 노출한다.
2. **Given** 백그라운드 Celery 워커가 영수증 분석 작업을 수신했을 때, **When** 이미지 전처리 및 LLM 연동 후 성공적으로 완료하여 DB 적재를 마치면, **Then** Polling을 수행하는 클라이언트는 작업 완료 상태를 감지하여 대시보드에 가계부 상세 내역을 갱신 렌더링한다.

---

### User Story 2 - 전체 개발 스택 Dockerize 및 원클릭 기동 (Priority: P2)

개발자가 로컬 머신에서 Docker Compose 명령어로 DB, Redis, 백엔드(Django), 워커(Celery), 프론트엔드(Vue3)를 모두 기동할 수 있으며, 로컬에서 편집기로 소스 코드를 수정하면 별도의 재빌드나 컨테이너 재시작 없이 즉시 소스가 핫 리로딩되어 실시간 반영된다.

**Why this priority**: 로컬 호스트 PC의 환경 불일치를 차단하고 Celery 비동기 아키텍처에 필요한 복잡한 프로세스 기동 절차를 자동화하여 개발 생산성을 개선하기 위한 P2 핵심 사양입니다.

**Independent Test**: docker-compose up을 기동한 후 로컬 환경의 백엔드 파이썬 소스 및 프론트엔드 Vue 컴포넌트를 수정하고, 컨테이너 재빌드 없이 소스 변경이 즉시 핫 리로딩을 통해 서비스에 실시간 적용되는지 관찰하여 검증할 수 있습니다.

**Acceptance Scenarios**:

1. **Given** 로컬 개발자가 터미널에서 Docker Compose 기동 명령을 수행하면, **When** 모든 서비스(Postgres, Redis, API, Worker, Frontend)가 정상 시작되면, **Then** 단일 로컬 포트로 프론트엔드 웹앱과 백엔드 API에 정상 접근 가능하다.
2. **Given** 도커 컨테이너 세트가 실행 중인 상태에서, **When** 로컬 편집기에서 코드를 수정하고 저장하면, **Then** 백엔드는 runserver 자동 리로딩이, 프론트엔드는 Vite HMR을 통해 변경 내용이 1.5초 이내에 브라우저에 자동 반영된다.

---

### Edge Cases

- **DB 커넥션 한도 초과 시**: 50개 이상의 업로드 작업이 일시에 몰려 DB 최대 커넥션 풀 한도(백엔드 5개, 워커 3개)에 도달하는 극한 상황에서, DB 커넥션 유실 에러를 뿜지 않고 큐에 적재된 Celery 태스크들이 커넥션을 획득할 때까지 원활히 대기한 뒤 순차적으로 무결하게 최종 적재를 완료하는가?
- **비동기 작업 도중 예외/실패**: 백그라운드 Celery 워커에서 Pillow 이미지 리사이징 도중 에러가 나거나 LLM API 호출에 실패했을 때, 작업 상태가 Failed로 안전하게 저장되고 사용자의 대시보드에 에러 상태 및 실패 사유가 적절히 시각화되어 노출되는가?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: API 서버는 파일 업로드 API 인입 시, 무거운 이미지 처리 및 AI 분석을 비동기로 미루고 작업 식별자(job_id)가 포함된 HTTP 202 Accepted 응답을 즉시 반환해야 한다. 프론트엔드는 2초 간격으로 작업 상태를 폴링(Polling)하며, 최대 30초 이내에 완료되지 않는 경우 타임아웃(실패)으로 처리해야 한다.
- **FR-002**: Redis를 메시지 브로커로 사용하여 Celery 워커 환경을 가동하고, 영수증 이미지 전처리(Pillow), 정규식 바이패스, LLM Structured Outputs 연동, 가계부 1:N 트랜잭션 적재 처리를 비동기 작업(Task)으로 수행해야 한다. 일시적인 외부 API 연동 실패 등 예외 발생 시 최대 3회 자동 재시도(지수 백오프 적용)를 실행해야 한다.
- **FR-003**: 한정된 DB 연결 자원 보호를 위해 백엔드 Django 설정에서 DB 커넥션 풀을 최대 5개 이하로 제약하고, Celery 비동기 워커 측의 최대 DB 커넥션 풀 크기를 최대 3개 이하로 엄격하게 통제해야 한다.
- **FR-004**: 백엔드, Celery, 프론트엔드를 전체 Dockerizing하고, 로컬 디렉터리와 컨테이너 내부를 바인드 마운트하여 컨테이너 재빌드 없이 소스 핫 리로딩(Hot-Reloading)이 양방향으로 즉시 수행되는 Docker Compose 개발 인프라를 통합 구축해야 한다.
- **FR-005**: 윈도우 OS의 파일 변경 이벤트가 도커 컨테이너 내부로 유실되는 것을 방지하기 위해 프론트엔드 Vite 환경 설정 파일에 폴링 감지 옵션(`usePolling: true`)을 빌트인 탑재해야 한다.

### Key Entities

- **AsyncTask (비동기 작업)**:
  - `job_id`: 고유 작업 식별자 (UUIDv7)
  - `status`: 작업 상태 (Pending, Processing, Completed, Failed)
  - `error_message`: 작업 실패 시 기록되는 예외 내용
  - `created_at` / `updated_at`: 작업 생성 및 최종 갱신 일시
  - `user_id`: 작업을 요청한 사용자 마스터의 외래키

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 파일 업로드 API 요청의 메인 서버 응답 지연 시간(Latency)이 기존 동기식 평균 5초 이상에서 비동기 Pending 즉시 응답 구조를 통해 95% 이상의 요청에 대해 500ms 이내로 단축되어야 한다.
- **SC-002**: 로컬 개발 머신에서 단 한 번의 Docker Compose 실행 명령을 통해 전체 인프라(DB, Cache, 백엔드 API, Celery 워커, Vue 프론트엔드)가 오류 없이 즉시 기동되어야 한다.
- **SC-003**: 50개의 가상 영수증이 API 업로드와 메일 웹훅을 통해 일시에 동시에 인입되어도 DB 커넥션 유실 에러(OperationalError)가 단 한 건도 발생하지 않고 100% 정상 대기 및 비동기 순차 처리되어야 한다.
- **SC-004**: 소스 코드 수정 후 컨테이너 재빌드 및 재부팅 단계 없이 프론트엔드 브라우저 화면 및 백엔드 런타임에 소스 수정 사항이 1.5초 이내에 실시간 반영(핫 리로딩)되어야 한다.

## Assumptions

- 개발자의 로컬 환경에는 Docker Desktop 및 Docker Compose V2가 설치되어 작동하고 있다고 가정합니다.
- Windows 호스트 환경에서의 마운트 디렉터리 파일 변경 감지 지연 문제를 회피하기 위해 Vite 개발 서버 감지에 폴링을 도입한다고 가정합니다.
- 비동기 작업 브로커 및 캐시 스토어로 Docker 기반의 Redis 이미지를 동일 가상 네트워크 내에 격리 가동한다고 가정합니다.
- 이메일 인바운드 수신 웹훅 및 VAPID 표준 푸시 알림 전송 시스템 구현은 이번 016 피처의 Out-of-Scope로 정의하며, 후속 피처에서 개별 처리한다고 가정합니다.
