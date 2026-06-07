# Feature Specification: MVP Integration Test

**Feature Branch**: `014-mvp-integration-test`

**Created**: 2026-06-07

**Status**: Draft

**Input**: User description: "2주차 동기식 MVP 완전체 통합 테스트. 웹 브라우저에서 영수증 사진을 찍어 전송하면 약 10초 이내에 화면이 동기적으로 갱신되며 가계부 테이블에 아이템이 적재되는 완전한 단일 웹 루프 완성."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - E2E Receipt Upload & Synchronous Ingestion (Priority: P1) 🎯 MVP

사용자는 웹 브라우저(Vue 3) 대시보드 화면에서 영수증 사진을 업로드한다. 클라이언트는 이미지를 1차 Canvas 압축한 후 API 서버로 송신하며, 서버(Django)는 Pillow 2차 WebP 압축, Gemini API 호출을 통한 AI 분석, 단일 트랜잭션 DB 적재를 동기식으로 일괄 처리한다. 처리가 완료되면 화면은 10초 이내에 동기적으로 갱신되어 새로 추가된 가계부 내역과 상세 품목을 출력한다.

**Why this priority**: 2주차 개발 목표인 "동기식 MVP 완전체"를 달성하고 사용자에게 핵심 제로-터치 가치를 E2E로 증명하기 위한 최우선 MVP 시나리오입니다.

**Independent Test**: 웹 UI 상에서 테스트용 영수증 이미지(JPEG)를 드롭존에 업로드한 후, 10초 이내에 업로드 성공 알림과 함께 대시보드 테이블에 가맹점명 및 결제 내역, 그리고 세부 품목 아코디언 메뉴가 정확하게 렌더링되는지 확인합니다.

**Acceptance Scenarios**:

1. **Given** 로그인된 사용자가 대시보드 페이지에 머물러 있는 상태에서, **When** 드롭존에 영수증 이미지 파일을 업로드하면, **Then** 10초 이내에 화면 스피너가 사라지며 `ledgers` 및 `ledger_items`가 가계부 내역에 실시간으로 적재 및 노출된다.
2. **Given** 이미지 분석 중 LLM 파싱 장해나 API 타임아웃이 발생한 상황에서, **When** 동기식 가계부 생성이 실패하면, **Then** 데이터베이스 트랜잭션은 전격 롤백(Rollback)되어 데이터 오염이 발생하지 않는다.
3. **Given** 이미 적재 완료된 동일한 결제 영수증에 대해, **When** 사용자가 중복 업로드를 시도하면, **Then** DB의 복합 유니크 제약조건에 의해 차단되며 중복 아이템이 적재되지 않는다.

### Edge Cases

- **초고용량 이미지 업로드**: 클라이언트 Canvas API가 가로 최대 1000px로 1차 축소하여 전송하므로 서버 메모리 폭주를 예방한다.
- **LLM API 일시적 오류**: Gemini API 호출 실패 시 데이터베이스 트랜잭션이 ACID하게 롤백을 수행하여 더티 데이터를 남기지 않는다.
- **연속 동일 결제**: 중복 결제로 감지되어 차단되어야 하는 복합 고유 제약 조건 필터를 안전하게 검증한다.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 클라이언트(Vue 3)는 영수증 파일 감지 즉시 HTML5 Canvas를 활용하여 가로 최대 1000px, Quality 0.8 수준의 JPEG 이미지 바이트 버퍼로 1차 압축 인코딩을 수행해 서버로 전송해야 합니다.
- **FR-002**: 서버(Django)는 Multipart-form으로 수신된 이미지 버퍼를 Pillow 모듈을 활용하여 WebP 포맷으로 2차 변환해야 합니다.
- **FR-003**: 서버는 변환된 이미지 버퍼를 Gemini-2.5-Flash API로 송신하고, JSON Schema 규격이 명시적으로 강제된 정형 가계부 데이터(가맹점명, 사업자번호, 결제일시, 세부품목 배열)를 수신해야 합니다.
- **FR-004**: 서버는 Gemini API 수신 데이터를 바탕으로 `ledgers` 및 `ledger_items` 테이블의 삽입 연산을 단일 Django 트랜잭션 블록(`transaction.atomic()`) 내에서 원자적으로 수행해야 하며, 예외 발생 시 전역 롤백을 이행해야 합니다.
- **FR-005**: 3주차 비동기 구조 전환에 대비하여 서버는 동기 응답 반환 시 `status: "COMPLETED"` 및 `job_id: null` 형식의 JSON 포맷 규격을 강제 반환해야 합니다.
- **FR-006**: 데이터베이스 테이블 설계 시 `UNIQUE (user_id, vendor_registration_number, transaction_date, total_amount)` 복합 고유 제약조건을 강력히 준수하고 중복 적재를 사전에 방지해야 합니다.
- **FR-007**: 10자리 사업자등록번호 파싱 시 `merchant_templates` 캐시 테이블을 최우선 조회하여 수동 검증 승인(`is_verified: true`)된 정적 정규식 규칙이 존재하면 유료 LLM 호출을 우회(Bypass)하여 즉시 로컬 파싱하고, 미등록 시에만 LLM API를 폴백 가동하며 미검증 후보 규칙을 자동 제안 등록해야 합니다.

### Key Entities

- **users (사용자)**: 회원 식별자, 가계부 소유주 정보
- **ledgers (가계부 마스터)**: 가맹점명, 사업자등록번호, 결제 날짜, 총액, raw_llm_response(JSONB)
- **ledger_items (가계부 상세품목)**: ledger_id(FK - Cascade), 품목명, 단가, 수량, 합계금액
- **failed_tasks (실패 로깅)**: 파싱 실패 시 원본 정보 및 오류 내용 수집

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 사용자가 웹 화면에서 영수증을 업로드하고 대시보드 뷰가 갱신되는 전 과정(E2E)이 평균 **10초 이내**로 완료되어야 합니다.
- **SC-002**: 데이터 적재 처리 중 장해가 발생했을 때 단 하나의 더티 데이터도 발생하지 않고 100% 롤백되어야 합니다. (Dirty State 0%)
- **SC-003**: 중복된 영수증 유입 시 데이터베이스 복합 제약조건에 의해 중복 적재 시도가 100% 탐지되어 차단되어야 합니다.

## Assumptions

- 사용자는 최신 규격을 지원하고 네트워크 연결이 안정적인 모바일/PC 브라우저 환경에서 PWA에 접근합니다.
- Gemini API의 응답 속도는 10초 이내 E2E 목표를 충족할 수 있을 정도로 정상 가동 상태입니다.
- 이 단계는 3주차 비동기(Celery/Redis) 파이프라인 도입 전, E2E 연동의 정상 가동을 확인하기 위한 최종 동기식 E2E MVP 테스트 단계입니다.
