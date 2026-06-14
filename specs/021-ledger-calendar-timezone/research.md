# Research: 기술 연구 및 아키텍처 의사결정

본 문서는 가계부 UI 고도화 2단계 및 사용자 타임존 설정 변경 기능을 구현하기 위해 수행된 핵심 기술 조사와 최종 아키텍처 결정 사항을 기록합니다.

---

## 1. Django/DRF 기반 사용자별 동적 타임존 적용 및 직렬화 기법

### 조사 배경
시스템은 데이터베이스에 모든 시간(transaction_datetime)을 UTC 기준으로 저장하여 데이터 일관성을 지키고 있습니다. 사용자가 자신의 타임존을 변경했을 때, 서버가 해당 사용자의 타임존 오프셋을 동적으로 읽어 가계부 응답 데이터를 해당 시간대로 자동 변환하여 직렬화(Serialization)해 주는 매커니즘이 필요합니다.

### 아키텍처 의사결정
* **결정사항 (Decision)**:
  * Django의 활성 타임존 미들웨어 패턴을 사용합니다.
  * API 요청 시 인증된 사용자(`request.user`)의 프로필에 기록된 `timezone` 값을 감지하여, Django 스레드 로컬 영역에 `timezone.activate(user_timezone)`를 기동합니다.
* **타당성 (Rationale)**:
  * Django는 `USE_TZ = True` 환경에서 `timezone.activate()`가 호출되면, DRF `DateTimeField`가 데이터를 직렬화할 때 자동으로 활성 시간대로 오프셋을 보정하여 출력(ISO-8601 포맷)합니다.
  * 각 Serializer나 API View에서 직접 날짜 포맷 코드를 작성할 필요가 없어 비즈니스 로직 오염을 원천 방지하며, 장고의 네이티브 시간대 시스템의 강력한 혜택을 온전히 누릴 수 있습니다.
* **고려된 대안 (Alternatives considered)**:
  * Serializer `to_representation()` 메서드를 오버라이드하여 `obj.transaction_datetime.astimezone(pytz.timezone(user_timezone))`을 수동 호출하는 방법.
    * *기각 이유*: 모든 시간 필드마다 개별적으로 수동 제어해야 하므로 중복 코드가 증가하고, 예외 누락(버그) 가능성이 큽니다.

---

## 2. Vue.js 3 Vanilla CSS Grid 기반 월별 캘린더 컴포넌트 구현

### 조사 배경
달력 화면에서 일자별 총 지출액과 건수를 한눈에 확인하고 반응형으로 다차원 필터링에 부합하는 가계부 데이터를 빠르게 로드하는 고성능 캘린더 UI 컴포넌트가 필요합니다. 무거운 외부 캘린더 라이브러리와 Vanilla CSS Grid 커스텀 개발 중 효율성을 비교합니다.

### 아키텍처 의사결정
* **결정사항 (Decision)**:
  * Tailwind CSS의 Grid 기능(`grid-cols-7`)과 Vue 3의 reactive state를 결합하여 자체 Vanilla 캘린더 컴포넌트(`CalendarView.vue`)를 작성합니다.
* **타당성 (Rationale)**:
  * 가계부 달력은 일반 캘린더 일정 관리와 달리, 날짜 칸 안에 지출 요약액과 건수 뱃지를 초록/빨강 계열의 Rich Aesthetics 스타일로 렌더링하고, 특정 조건 필터에 따라 즉시 숫자가 리액티브하게 바뀌어야 합니다.
  * 외부 무거운 라이브러리(예: FullCalendar)는 CSS 커스터마이징이 극도로 까다롭고 의존성 부하가 큽니다. 반면, Vanilla Grid로 일수를 구하는 공식(`new Date(year, month, 1).getDay()`, `new Date(year, month + 1, 0).getDate()`)은 약 30줄의 코드만으로 완벽한 월별 달력 데이터를 동적으로 배열화할 수 있어 압도적으로 가볍고 유연합니다.
* **고려된 대안 (Alternatives considered)**:
  * `v-calendar` 라이브러리 도입.
    * *기각 이유*: PWA 환경에서 초기 번들 크기를 증가시키고 모바일 뷰 적응형 레이아웃 튜닝이 제한되어 기각했습니다.

---

## 3. 다차원 복합 필터링 성능 최적화 및 데이터베이스 인덱싱 설계

### 조사 배경
상호명(텍스트), 카테고리(다중 선택), 기간(시작/종료), 금액(최소/최대) 등 여러 차원의 필터링이 동시에 적용되어 대량의 데이터베이스 쿼리가 발생할 때, 헌법의 SC-003(필터링 렌더링 완료 속도 500ms 이내) 기준을 안정적으로 수호해야 합니다.

### 아키텍처 의사결정
* **결정사항 (Decision)**:
  * 백엔드에서 `django-filter`를 연동하여 복합 쿼리를 안전하고 선언적인 FilterSet으로 정규화합니다.
  * PostgreSQL v18 데이터베이스의 `Ledger` 테이블에 검색 성능 향상을 위한 인덱스를 구축합니다. 
  * 특히 복합 조회 조건이 빈번하게 적용되는 시계열 결제일시(`transaction_datetime`) 컬럼과 사용자 식별자(`user_id`) 컬럼을 결합한 복합 인덱스를 선언하고, 상호명 검색의 성능을 보장하기 위해 `vendor_name`에 대해 부분 문자열 검색 인덱싱을 튜닝합니다.
* **타당성 (Rationale)**:
  * DB 인덱스가 없는 상황에서 10만 건이 넘는 가계부 테이블에 복합 다차원 필터를 걸면 PostgreSQL의 Full Table Scan이 발동되어 응답 성능이 1.5초를 상회하게 됩니다.
  * `(user_id, transaction_datetime DESC)` 복합 인덱스를 걸어주면 사용자별 당월 지출 조회 및 날짜 정렬이 10ms 단위로 해결되며, Django ORM의 `select_related('category')`를 이용해 가맹점/카테고리 조인 횟수를 단 1회 쿼리로 일원화하여 성능 병목을 사전에 파괴할 수 있습니다.
* **고려된 대안 (Alternatives considered)**:
  * 매 필터 조건마다 개별 컬럼에 인덱스를 부여하는 방식.
    * *기각 이유*: PostgreSQL 옵티마이저가 복합 인덱스 하나를 활용하는 것에 비해, 다수의 단일 인덱스는 인덱스 병합(Index Merge) 비용이 추가로 발생하고 쓰기 성능을 저하시키므로 비효율적입니다.
