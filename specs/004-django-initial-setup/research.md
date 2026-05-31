# Research Notes: django-initial-setup

본 문서에는 Python 및 Django 초기 보일러플레이트 코드 빌드에 적용할 핵심 기술적 대안들의 타당성과, 명확화 세션(Clarification Session)을 통해 도출된 최종 아키텍처 의사결정 내역을 정리합니다.

---

## 1. 환경 변수 로더 파싱 설계 (Environment Variable Loaders)

### [Decision]
* **결정 사항**: `django-environ` 패키지 도입 및 엄격한 예외 처리 강제
* **타당성**: 
  - Django 개발 환경에 가장 자연스럽고 특화된 로더로, 환경 변수 데이터 타입 캐스팅(Casting)을 내장 지원하여 불필요한 파싱 로직을 줄여줍니다.
  - 특히 `DATABASE_URL` 형식을 단 한 줄의 코드로 PostgreSQL 커넥션 객체 스펙에 매핑(e.g., `db_url()`)할 수 있어 데이터베이스 연결 정합성을 쉽게 달성할 수 있습니다.
  - 절대 보안 및 비하드코딩 원칙에 따라, `SECRET_KEY` 및 `DATABASE_URL`에 대한 하드코딩된 폴백(Fallback) 기본값을 제공하지 않습니다. 이들 변수가 누락될 시 런타임 시작 시점에 `ImproperlyConfigured` 예외를 발생시키고 안전하게 기동을 차단합니다.

### [Alternatives Considered & Rejected]
1. **`python-dotenv` 단독 도입 (Rejected)**:
   - 일반 파이썬 표준 라이브러리로서는 준수하지만, settings.py 내부에서 `os.environ.get()`을 사용하여 모든 환경변수를 직접 캐스팅(e.g., 문자열을 정수형이나 불리언으로 파싱)해야 하므로 부가적인 보일러플레이트 코드가 늘어나며 타입 누출 리스크가 증가하여 기각했습니다.
2. **별도 패키지 없이 내장 `os.environ`만 활용 (Rejected)**:
   - 도커 컨테이너 환경의 환경 변수를 순수하게 이용하는 최적의 방법일 수 있으나, 로컬 가상환경(`.venv`) 단독 구동 시 `.env` 파일의 자동 로드가 지원되지 않아 개발자의 로컬 개발 편의성을 저해하므로 기각했습니다.

---

## 2. API 전역 보안 및 인증 정책 (Global REST API Security Policy)

### [Decision]
* **결정 사항**: 글로벌 접근 차단 및 화이트리스트 기반 선별적 공개
* **타당성**: 
  - settings.py의 `REST_FRAMEWORK` 기본 권한 클래스를 `rest_framework.permissions.IsAuthenticated`로 지정하여 모든 엔드포인트를 기본 폐쇄 상태(Secure by Default)로 셋업합니다.
  - 이는 향후 개발되는 모든 API 뷰가 실수로 비인증 사용자에게 노출되는 것을 컴파일/배포 수준에서 원천 차단하는 강력한 보안 통제력을 제공합니다.
  - 로컬 서버 헬스 체크(Health Check)와 같이 외부에 공개되어야 하는 특정 엔드포인트만 선별적으로 뷰 클래스 내부에서 `permission_classes = [AllowAny]`를 명시하여 예외 허용합니다.

### [Alternatives Considered & Rejected]
1. **글로벌 개방 정책 `AllowAny` 기본값 지정 (Rejected)**:
   - 개발 및 로컬 테스트의 유연성은 매우 높으나, 향후 개발자가 보안 권한 클래스를 깜빡 잊고 명시하지 않은 API가 프로덕션에 그대로 배포되어 개인 금융 정보(Ledger)가 그대로 외부에 유출되는 치명적인 보안 사고 가능성을 제공하므로 엄격히 기각했습니다.

---

## 3. 데이터베이스 연결 재사용 및 스로틀링 (Database Connection Pooling)

### [Decision]
* **결정 사항**: 동적 자원 재사용 (`CONN_MAX_AGE: 60` 기본값 적용 및 `.env` 제어)
* **타당성**: 
  - Django의 기본 데이터베이스 연결 동작(매 요청마다 생성 및 폐기)은 다량의 단기 쿼리 발생 시 커넥션 수립을 위한 TCP 핸드셰이크 부하를 지속 유발하여 응답 시간을 저하시킵니다.
  - `CONN_MAX_AGE`를 60초로 셋업하여 1분 동안 활성 커넥션을 재사용하도록 보증해 응답성을 보장합니다.
  - 또한 전체 자원 점유 최적화 규칙에 의거하여, 무료 데이터베이스 티어(Supabase 등)의 최대 가용 커넥션 풀(api_server 기준 최대 5개) 초과 붕괴를 예방하기 위해, 해당 연결 나이(Age) 및 크기를 `.env` 파일의 `DATABASE_CONN_MAX_AGE` 환경변수로 동적 스로틀링 조정 가능하도록 다이렉트 노출 바인딩합니다.

### [Alternatives Considered & Rejected]
1. **커넥션 즉각 폐기 `CONN_MAX_AGE: 0` (Rejected)**:
   - DB 서버의 커넥션 점유 리스크는 제로로 수렴하여 고갈을 완벽히 방어하지만, 가계부 데이터 적재 및 조회 시 매 HTTP 요청마다 10~20ms의 DB 핸드셰이크 접속 지연이 강제 축적되므로 기각했습니다.
2. **영구 유지 `CONN_MAX_AGE: None` (Rejected)**:
   - 핸드셰이크 부하를 제로로 만들지만 다수의 웹 애플리케이션 파드가 수평 확장(Horizontal Scaling)되어 기동할 시 순식간에 Supabase 무료 티어 DB의 가용한계(최대 10~20개 커넥션)를 초과하여 DB 붕괴를 초래하므로 기각했습니다.
3. **SQLite3 로컬 포백 제공 (Rejected)**:
   - PostgreSQL 인프라가 미기동된 상태에서도 테스트 가능하도록 하는 방법이나, 이 경우 native UUIDv7 인덱스 튜닝 및 `psycopg3`만의 고급 풀 성능 혜택을 개발 단계에서 기계적으로 완벽히 테스트 검증할 수 없어 아키텍처 무결성 보장을 위해 기각했습니다.
