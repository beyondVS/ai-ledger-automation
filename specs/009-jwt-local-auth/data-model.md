# Data Model Specification: Setup Local Authentication with JWT

본 피처에서 구현될 데이터 모델의 상세 명세와 제약 조건, 유효성 검사 규칙을 정의합니다.

---

## 1. User (사용자 모델)

Django의 기본 인증 체계와 완벽히 호환되도록 `AbstractUser`를 상속받아 구현되며, 이메일을 식별값으로 취급하는 Custom User 모델입니다.

### 1.1. 필드 상세 명세

| 필드명 | 데이터 타입 | 제약 조건 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| **id** | UUID (UUIDv7) | Primary Key, 고유성 | (자동생성) | 사용자의 고유 내부 식별자 |
| **email** | VARCHAR(255) | Unique, Not Null, Email형식 | - | 로그인 및 알림 수신에 사용되는 고유 이메일 주소 |
| **password** | VARCHAR(128) | Not Null (PBKDF2 암호화 해시) | - | 암호화 저장되는 비밀번호 |
| **provider** | VARCHAR(20) | Choices: `['local', 'google', 'kakao']` | `'local'` | 가입 수단 제공처 (향후 소셜 로그인 대응용) |
| **is_active** | BOOLEAN | Not Null | `True` | 계정 활성화 상태 유무 |
| **is_staff** | BOOLEAN | Not Null | `False` | 관리자 페이지 접근 권한 유무 |
| **date_joined** | DATETIME | Not Null | (현재시간) | 가입 일시 |

### 1.2. 유효성 검사 및 정합성 규칙
* **이메일 중복 방지:** 데이터베이스 레이어에서 `unique=True` 인덱스를 강제하여 동일 이메일로의 중복 회원가입을 100% 차단합니다.
* **이메일 형식 검증:** Django 내장 `EmailValidator`를 통해 올바른 이메일 포맷(`username@domain.com`)만 가입할 수 있도록 API 직렬화기(Serializer) 단계에서 검증합니다.
* **비밀번호 안전성:** 비밀번호는 평문으로 저장되지 않으며, Django 기본 비밀번호 해시 업그레이드 규칙에 따라 안전하게 암호화되어 데이터베이스에 적재됩니다.

---

## 2. JWT Blacklist Model (SimpleJWT Outstanding / Blacklisted Token)

`djangorestframework-simplejwt` 라이브러리가 로그아웃 토큰 파기 및 세션 무효화 관리를 위해 내부적으로 관리하는 테이블 구조입니다.

### 2.1. OutstandingToken (발행된 모든 리프레시 토큰 관리)
* **user_id:** 해당 토큰을 발급받은 User FK
* **jti:** JWT 고유 ID 식별자 (UUID)
* **token:** 리프레시 토큰 원본 텍스트
* **created_at / expires_at:** 발급일 및 만료일

### 2.2. BlacklistedToken (폐기된 리프레시 토큰 블랙리스트)
* **token_id:** OutstandingToken 테이블을 참조하는 FK
* **blacklisted_at:** 해당 토큰이 만료/로그아웃되어 블랙리스트에 등재된 일시
