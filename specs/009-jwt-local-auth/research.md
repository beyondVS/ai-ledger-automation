# Technical Research: Setup Local Authentication with JWT

이 문서는 로컬 회원가입 및 JWT 발급 체계를 구축하는 과정에서 검토된 핵심 기술 의사결정과 타당성, 그리고 대안들을 정리한 연구 문서입니다.

---

## 1. Django Custom User 구현 모델 선정

* **결정사항 (Decision):**
  * `AbstractUser`를 상속받은 Custom User 모델(`accounts.User`)을 최초 셋업하며, `email` 필드를 기본 로그인 식별자(`USERNAME_FIELD`)로 설정합니다.
  
* **타당성 (Rationale):**
  * Django 기본 User 모델은 차후 스키마 확장이 매우 어렵기 때문에 프로젝트 초기 단계에 Custom User 모델을 지정하는 것은 필수적입니다.
  * 가계부 서비스 특성상 사용자 아이디(username)보다 이메일 주소를 사용하는 것이 더 직관적이고 포워딩 수집 기능과의 연동이 매끄럽습니다.
  * `AbstractUser`를 상속하면 Django의 강력한 권한 관리 및 기본 관리자 어드민 필드들을 그대로 재활용할 수 있어 보일러플레이트 코드를 대폭 줄일 수 있습니다.

* **고려된 대안 (Alternatives considered):**
  * **django.contrib.auth.models.User (기본 모델):** 소셜 로그인 확장이나 추가 프로필 정보(영수증 화이트리스트 메일 등) 추가를 위해 DB 마이그레이션을 얹어야 하므로 부작용이 매우 크기 때문에 기각되었습니다.
  * **AbstractBaseUser 직접 구현:** 완전한 자유도가 제공되나 비밀번호 리셋, 어드민 권한, 활성화 플래그 등 기본 인증 보일러플레이트를 직접 모두 작성해야 하므로 개발 생산성 관점에서 기각되었습니다.

---

## 2. JWT 인증 라이브러리 및 블랙리스트 정책

* **결정사항 (Decision):**
  * `djangorestframework-simplejwt` 패키지를 연동하여 JWT 발급 및 보안 검증을 수행하고, 로그아웃 시 토큰을 안전하게 만료시키기 위해 **SimpleJWT Blacklist 앱**을 활성화합니다.
  
* **타당성 (Rationale):**
  * `simplejwt`는 Django REST Framework 진영에서 가장 널리 쓰이고 신뢰성이 검증된 JWT 표준 라이브러리입니다.
  * Access Token(30분) 만료 이후 Refresh Token(14일)을 이용하여 안전하게 무인증 세션을 연장하도록 지원합니다.
  * 로그아웃 요청 시, 유출된 리프레시 토큰의 악용을 원천 차단하기 위해 데이터베이스(또는 고속 Redis) 상에서 해당 리프레시 토큰을 블랙리스트 처리하여 무효화합니다.

* **고려된 대안 (Alternatives considered):**
  * **Django 기본 세션 인증 (Session Authentication):** 모바일 PWA 및 크로스 도메인 API 호출 시 브라우저 쿠키(CSRF 등) 관련 제약이 심하며, 추후 소셜 로그인 및 외부 연동의 확장성이 떨어지므로 기각되었습니다.
  * **DRF 기본 토큰 인증 (TokenAuthentication):** 서버 데이터베이스에 토큰이 영구 저장되어 매 요청마다 DB 조회가 발생하고, 토큰 만료 기능이 내장되어 있지 않아 보안상 적합하지 않으므로 기각되었습니다.

---

## 3. 차후 social-auth-app-django 패키지 연동 대비 스키마 설계

* **결정사항 (Decision):**
  * Custom User 모델에 가입 처(Provider)를 저장하는 필드(`provider`)를 `local` 기본값으로 미리 설계해 둡니다. 나중에 구글/카카오 소셜 로그인이 추가되면 `social-auth-app-django`가 사용하는 `UserSocialAuth` 모델과의 1:N 관계 매핑이 자연스럽게 작동할 수 있도록 준비합니다.

* **타당성 (Rationale):**
  * `social-auth-app-django`는 Django의 내장 User 모델(혹은 Custom User 모델)과 일대일/일대다 관계를 맺는 독자적인 소셜 연동 테이블을 내부적으로 생성하여 구동됩니다.
  * 따라서 당장 소셜 로그인을 완벽히 구현하지 않더라도, Custom User 모델의 유저 고유 키(UUID)와 이메일 유일성(`unique=True`)이 확보되어 있으면 향후 이 패키지를 설치하고 연동하는 단계에서 스키마 부작용이 전혀 발생하지 않습니다.

* **고려된 대안 (Alternatives considered):**
  * **소셜 전용 필드를 User 모델에 직접 추가:** `google_id`, `kakao_id` 등을 User 모델 컬럼에 직접 추가하는 방식은 새로운 소셜 제공처가 늘어날 때마다 테이블 마이그레이션이 발생하므로 다중 소셜 테이블 분리를 기본으로 하는 `social-auth-app-django` 구조와 맞지 않아 배제되었습니다.
