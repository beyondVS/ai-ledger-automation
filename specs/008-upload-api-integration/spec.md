# Feature Specification: Upload API Integration & Async Schema Design

**Feature Branch**: `008-upload-api-integration`

**Created**: 2026-06-03

**Status**: Draft

**Input**: User description: "프론트엔드 업로드 동작부와 1주차에 구축한 동기식 Django API 서버 연동 진행. 향후 3주차 비동기 전환 시 데이터 하위 호환성을 보장하기 위해, status 및 job_id 응답 스키마 플레이스홀더(Placeholder) 필드를 미리 설계에 반영하고 폴링(Polling) 대기 상태 가상 모듈을 클라이언트에 선배치."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Receipt Upload and Immediate Reflection (Priority: P1)

사용자가 가계부 영수증 이미지를 프론트엔드 업로드 UI에 드롭하면, 시스템은 동기식 API를 통해 영수증을 즉시 분석하고 결과를 화면에 반영한다.

**Why this priority**: 영수증 업로드 및 파싱 결과를 확인하는 것은 이 서비스의 가장 핵심 가치이며, 동기식 연동이 완료되어야 기본적인 사용자 흐름이 성립한다.

**Independent Test**: 사용자가 영수증 이미지를 업로드하고, API 서버가 성공적으로 파싱한 결과 데이터가 화면의 가계부 항목으로 즉시 갱신되는지 확인한다.

**Acceptance Scenarios**:

1. **Given** 가계부 입력 화면에 진입한 상태에서,
   **When** 영수증 드롭존에 유효한 이미지(PNG, JPG 등)를 드롭하여 업로드를 실행하면,
   **Then** 업로드 중인 인디케이터가 표시되고, API 처리가 완료되면 파싱된 상세 내역이 화면에 채워진다.

2. **Given** 네트워크 상태가 불안정하거나 서버 오류가 발생한 상태에서,
   **When** 영수증을 업로드하면,
   **Then** 업로드 실패 메시지가 사용자에게 직관적으로 표시되고 재시도할 수 campaigners.

---

### User Story 2 - Pre-installation of Client-side Polling Virtual Module (Priority: P2)

향후 비동기 처리(3주차)로 전환될 때를 대비하여, 클라이언트에는 서버의 상태를 주기적으로 확인하는 폴링(Polling) 가상 대기 모듈이 선배치되어 동작한다. 현재는 동기식이므로 첫 응답에 즉시 완료 상태가 반환되지만, 가상 모듈을 통해 비동기 상태 흐름에 대응할 준비가 되어 있음을 검증한다.

**Why this priority**: 3주차에 백엔드를 Celery 비동기 작업으로 전환할 때 클라이언트 코드의 대대적인 수정 없이 데이터 하위 호환성을 유지하고, 매끄러운 UX 전환을 보장하기 위함이다.

**Independent Test**: 가상 비동기 상태(예: API가 임의로 `PROCESSING` 또는 `PENDING` 상태를 반환하도록 Mocking함)를 주입했을 때, 클라이언트의 가상 폴링 모듈이 작동하여 대기 UI를 유지하다가 완료 처리되는지 시뮬레이션 테스트를 수행한다.

**Acceptance Scenarios**:

1. **Given** 서버가 동기식 응답으로 처리 상태를 `"COMPLETED"`로 즉시 반환하면,
   **When** 클라이언트 가상 폴링 모듈이 이 상태를 읽었을 때,
   **Then** 추가 폴링 요청을 보내지 않고 즉시 결과를 화면에 렌더링하고 완료한다.

2. **Given** 서버가 비동기 호환을 위한 플레이스홀더 상태(예: `"PENDING"` 또는 `"PROCESSING"`)와 작업 식별자(`job_id`)를 반환하면,
   **When** 클라이언트 가상 폴링 모듈이 작동을 개시하여,
   **Then** 정해진 주기마다 상태 조회 요청을 시뮬레이션하거나 대기 상태를 유지하다가, 최종 완료 상태가 되었을 때 화면을 갱신한다.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 시스템은 사용자가 업로드한 영수증 이미지 데이터를 수집하여 Django API 서버의 동기식 업로드 엔드포인트로 전송해야 한다.
- **FR-002**: Django API 서버는 영수증 처리 응답 시, 향후 비동기 처리에 대응하기 위해 작업 고유 식별자(`job_id`, UUIDv7 규격의 플레이스홀더)와 현재 처리 상태(`status`) 필드를 포함하여 반환해야 한다.
- **FR-003**: API 서버는 현재 동기식으로 동작하므로, 성공 시 응답 스키마의 `status` 값을 항상 `"COMPLETED"`로 지정하여 반환해야 한다.
- **FR-004**: 프론트엔드 클라이언트는 업로드 API 응답을 수신하면 `status` 필드를 기반으로 흐름을 분기하는 "가상 폴링 모듈"을 탑재해야 한다.
- **FR-005**: 클라이언트 가상 폴링 모듈은 `status`가 `"COMPLETED"`인 경우 즉시 동기 완료로 처리하고 데이터를 화면에 표시하며, 그 외의 미완료 상태(`"PENDING"`, `"PROCESSING"`)인 경우 상태 확인 주기(예: 1초)를 가지는 가상 대기 루프를 구동해야 한다.

### Key Entities

- **Receipt Upload Job (영수증 업로드 작업)**: 영수증 분석 요청을 추적하기 위한 가상의 비동기 태스크 정보.
  - `job_id`: 작업 고유 식별자 (3주차 비동기 도입 시 Celery Task ID와 매핑될 UUIDv7 형식 플레이스홀더)
  - `status`: 현재 처리 진행 상태 (허용 값: `"PENDING"`, `"PROCESSING"`, `"COMPLETED"`, `"FAILED"`)
  - `created_at`: 작업 생성 일시
- **Receipt Details (영수증 분석 결과)**: 처리 완료 시 반환되는 가계부 원본 정보 및 파싱 내역 데이터.
  - `merchant_name`: 가맹점명
  - `transaction_date`: 거래 일자
  - `amount`: 총 금액
  - `items`: 상세 품목 목록

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 사용자가 드롭존에 영수증을 업로드하고 화면에 분석 결과가 표시되기까지 전체 프로세스가 동기식 환경에서 3초 이내에 완료되어야 한다.
- **SC-002**: 클라이언트 가상 폴링 모듈은 `"COMPLETED"` 상태의 API 응답을 받았을 때 추가적인 네트워크 지연이나 중복 요청 없이 0.1초 이내에 결과를 화면에 렌더링해야 한다.
- **SC-003**: API 스키마 변경 시(즉, 3주차 Celery 비동기 작업 도입으로 인해 중간에 `"PENDING"` 상태가 반환되더라도), 클라이언트는 에러를 일으키지 않고 가상 폴링 모듈을 통해 상태 대기 화면을 자연스럽게 유지해야 한다.

## Assumptions

- **ASM-001**: 1주차에 구축된 동기식 Django API 서버는 현재 단일 요청 흐름 내에서 OCR 및 데이터 적재를 완료하고 결과를 즉시 리턴할 수 있다.
- **ASM-002**: `job_id`는 현재 동기식 처리에서도 임의의 유효한 UUID를 생성하여 반환함으로써, 클라이언트가 데이터 타입 검증을 올바르게 통과하도록 보장한다.
- **ASM-003**: 가상 폴링 모듈은 향후 실제 비동기 상태 엔드포인트(예: `/api/v1/receipts/status/<job_id>/`)로 손쉽게 전환할 수 있도록 추상화된 메서드 형태로 설계된다.
