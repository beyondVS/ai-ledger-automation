# Feature Specification: Setup Local Authentication with JWT

**Feature Branch**: `009-jwt-local-auth`

**Created**: 2026-06-03

**Status**: Draft

**Input**: User description: "기본 가입 및 로그인 미들웨어 연동. 프론트엔드 로그인 페이지 퍼블리싱 및 OAuth 2.0 소셜 인입선 확보 전, Django REST Framework 기반 로컬 JWT 발급 체계를 연동하여 유저별 데이터 식별 보안 로직을 탑재하고 실물 JWT 검증 로직으로 완전히 전환."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Local Account Registration (Priority: P1)

사용자는 이메일 주소와 안전한 비밀번호를 사용하여 로컬 서비스 계정을 생성할 수 있습니다.

**Why this priority**: 가계부 데이터를 소유하고 관리할 주체(사용자)를 식별하기 위한 첫 번째 필수 단계입니다.

**Independent Test**: 회원가입 폼을 통해 이메일과 비밀번호를 입력하고 가입을 요청했을 때, 정상적으로 계정이 생성되고 즉시 로그인할 수 있는 상태가 되는지 검증합니다.

**Acceptance Scenarios**:

1. **Given** 등록되지 않은 고유 이메일과 유효한 비밀번호를 입력하고, **When** 가입을 제출하면, **Then** 계정이 생성되고 가입 성공 상태를 반환한다.
2. **Given** 이미 등록된 이메일 주소를 입력하고, **When** 가입을 제출하면, **Then** 중복 가입 오류 메시지를 표시하고 계정 생성을 차단한다.

---

### User Story 2 - User Login & Token Acquisition (Priority: P1)

사용자는 가입한 이메일과 비밀번호를 입력하여 시스템에 로그인하고, API 접근을 위한 보안 인증 토큰을 발급받습니다.

**Why this priority**: 로그인에 성공해야만 대시보드 조회나 영수증 업로드 등의 후속적인 개인화 기능을 사용할 수 있습니다.

**Independent Test**: 로그인 화면에서 올바른 자격 증명을 입력했을 때, API 서버로부터 보안 토큰을 정상 수신하여 로컬 브라우저 세션에 저장하는지 확인합니다.

**Acceptance Scenarios**:

1. **Given** 등록된 올바른 이메일과 비밀번호를 입력하고, **When** 로그인을 요청하면, **Then** 인증 토큰(Access Token 및 Refresh Token)을 정상 발급받고 대시보드로 이동한다.
2. **Given** 잘못된 비밀번호 또는 가입되지 않은 이메일을 입력하고, **When** 로그인을 요청하면, **Then** 로그인 실패 안내를 표시하고 페이지 진입을 차단한다.

---

### User Story 3 - Authenticated Data Identification (Priority: P1)

로그인된 사용자는 본인의 데이터만을 조회하고 관리할 수 있도록 모든 API 요청 시 토큰 기반의 사용자 식별이 이루어집니다.

**Why this priority**: 타인의 금융 데이터 노출을 원천적으로 막고, 로그인 상태에서 가계부 적재 및 대시보드 동기 조회가 가능하게 하는 핵심 보안 메커니즘입니다.

**Independent Test**: 인증 토큰을 동반하여 가계부 리스트 API를 요청했을 때 해당 토큰에 맵핑된 사용자의 데이터만 반환되며, 토큰이 없거나 잘못된 토큰일 경우 거부되는지 테스트합니다.

**Acceptance Scenarios**:

1. **Given** 로그인 성공 후 획득한 유효한 인증 토큰을 요청 헤더에 포함하고, **When** 가계부 리스트 조회를 요청하면, **Then** 본인의 가계부 데이터 목록이 정상 조회된다.
2. **Given** 인증 토큰 없이 혹은 위조된 토큰으로, **When** 가계부 데이터 조회를 시도하면, **Then** 접근 권한 없음(401 Unauthorized) 오류와 함께 조회가 거부된다.

---

### Edge Cases

- **Access Token 만료**: 사용자가 활성화된 상태에서 Access Token이 만료되면, Refresh Token을 사용하여 사용자 개입(재로그인) 없이 백그라운드에서 자동으로 Access Token을 갱신할 수 있어야 합니다.
- **두 토큰 모두 만료**: Access Token과 Refresh Token이 모두 만료되거나 무효화된 상태에서 API를 호출할 경우, 자동으로 안전하게 세션을 만료하고 로그인 페이지로 리다이렉트 처리되어야 합니다.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 시스템은 사용자가 이메일과 비밀번호를 입력하여 로컬 계정을 가입할 수 있게 해야 합니다.
- **FR-002**: 가입 시 입력된 패스워드는 데이터베이스 저장 전에 일방향 해시 함수로 안전하게 암호화되어 관리되어야 합니다.
- **FR-003**: 시스템은 사용자가 로그인 성공 시 짧은 수명의 Access Token과 긴 수명의 Refresh Token을 함께 발급해야 합니다.
- **FR-004**: 모든 가계부 데이터 등록/수정/조회 API는 반드시 요청 헤더의 Access Token을 검증하여 사용자를 식별해야 합니다.
- **FR-005**: 가입 시 수집할 필수 정보는 이메일 주소와 패스워드로 최소화하며, 추가적인 사용자 이름이나 옵션 정보는 가입 후 설정화면에서 수정하도록 처리해야 합니다.
- **FR-006**: Django Custom User 모델을 상속 구현하여 이메일의 유니크 제약 조건을 보장하며, 향후 `social-auth-app-django` 패키지를 이용한 소셜 로그인 추가 도입이 원활하도록 제공처(Provider) 필드 구조를 사전에 갖추어야 합니다.
- **FR-007**: 보안 및 편의성 균형을 고려하여, 발급되는 Access Token의 만료 시간은 30분, Refresh Token의 만료 시간은 14일로 설정합니다.

### Key Entities

- **User (사용자)**: 시스템에 가입한 개별 주체. 고유 식별자(UUIDv7), 이메일 주소, 암호화된 비밀번호 해시, 생성일시 정보를 보유합니다.
- **UserSession (사용자 세션)**: 사용자의 로그인 시점에 생성되는 인증 정보. 발급된 인증 토큰 정보와 만료 기한을 포함하며, 리프레시 토큰 무효화 처리를 추적할 수 있습니다.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 사용자는 회원가입을 시작한 시점부터 완료할 때까지 평균 1분 이내에 마칠 수 있어야 합니다.
- **SC-002**: 올바른 자격 증명으로 로그인 버튼을 누른 후, 2초 이내에 토큰 획득 및 대시보드 데이터 렌더링이 시작되어야 합니다.
- **SC-003**: 유효하지 않은 토큰(위조, 만료 등)을 포함한 불법적인 가계부 API 접근은 100% 탐지되어 안전하게 차단되어야 합니다.

## Assumptions

- 사용자는 모바일 또는 PC 브라우저 환경에서 표준 입력 폼을 통해 가입 및 로그인을 수행합니다.
- 향후 추가될 외부 소셜 로그인(OAuth 2.0)과의 기술적 구조 일치를 위해 세션 인증 대신 JWT 토큰 전달 규격을 표준으로 채택합니다.
- 토큰 전송 간 정보 유출을 차단하기 위해 실물 API 게이트웨이 및 서버는 HTTPS 보안 환경 위에서 작동합니다.
