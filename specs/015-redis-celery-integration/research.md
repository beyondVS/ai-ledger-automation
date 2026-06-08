# Research and Decisions: Redis/Celery Infrastructure Integration

본 문서에서는 동기식 MVP 서버를 Django 메인 API 서버와 Celery 백그라운드 워커 서버로 분리 설계하고, 메시지 브로커로 Redis를 도입하기 위한 기술적 연구 결과를 기술합니다.

## 1. 결정사항 (Technical Decisions)

### [Decision 001] Celery 비동기 큐 도입 및 Redis 메시지 브로커 통합
* **내용**: 2주차까지 설계된 동기식 영수증 분석 모듈을 Celery 태스크로 전환하고, 이를 관리할 메시지 브로커로 Redis를 독립 컨테이너로 통합합니다.
* **상세 구성**:
  - Redis 공식 Alpine 이미지 기반 컨테이너 구동.
  - Redis의 영속성(AOF 또는 RDB)을 활성화하여 워커의 비정상 종료 시에도 메시지 큐 대기 건이 100% 보존되도록 구성.
  - Celery 결과 저장소(Result Backend)로도 Redis를 병용하되, 최종 분석 결과 데이터는 PostgreSQL RDBMS에 즉시 영속화하여 중복을 최소화합니다.

### [Decision 002] 큐 모니터링을 위한 Flower 대시보드 로컬/운영 환경 통합
* **내용**: Celery의 모니터링 표준 도구인 Flower 컨테이너를 Docker Compose에 추가하여 웹 기반 대시보드(기본 포트 5555)로 실시간 작업 적체 상태, 성공률, 실패 원인을 가시화합니다.
* **상세 구성**:
  - 로컬 개발 환경(Docker Compose)에서 포트 5555로 포워딩하여 관리자 편의 제공.

### [Decision 003] 클라이언트 폴링 방식의 비동기 상태 추적 및 알림 추상화
* **내용**: 단기적으로 프론트엔드가 3~5초 간격으로 작업 ID(`job_id`)를 활용해 작업 상태를 주기적으로 확인하는 API 폴링 방식을 채택합니다.
* **상세 구성**:
  - 향후 WebSocket이나 Server-Sent Events(SSE)로의 원활한 전환을 보장할 수 있도록, 백엔드 내부의 알림 처리 클래스(`NotificationClient`)를 인터페이스로 추상화하여, 상태 변경 시 발송 로직의 커플링을 제거합니다.

### [Decision 004] 데이터베이스 커넥션 풀 크기 제약 준수 (헌법 제II조 수호)
* **내용**: Supabase Free Plan 등 인프라의 DB 최대 허용 커넥션 수(기본 10~20개 내외) 고갈을 방지하기 위해 전체 컨테이너의 합산 커넥션 개수를 8개 이하로 강제 설정합니다.
* **상세 구성**:
  - **Django API Container**: Gunicorn worker 2개 가동 (각 worker당 DB connection max 2개 지정, 총 4개 대역 확보)
  - **Celery Worker Container**: Celery Concurrency=2 설정 (DB connection max 2개 지정, 총 2개 대역 확보)
  - **예비 대역**: 2개 대역을 수동 쿼리 및 로컬 쉘 디버깅 용도로 보존.

---

## 2. 타당성 (Rationale)

* **체감 사용자 경험 극대화**: OCR 분석 및 LLM 호출 연산은 파일 크기와 외부 API 환경에 따라 최하 5초에서 최대 30초 이상 소요될 수 있습니다. 이를 동기식으로 대기하게 하면 브라우저 504 Timeout이 발생하기 쉽습니다. 비동기 큐 전환으로 API 응답 속도를 **2초 이내**로 대폭 단축할 수 있습니다.
* **서버 자원 보호 (격리)**: API 서버와 워커 서버를 컨테이너 단위로 분리함으로써, OCR 이미지 연산이나 다량의 LLM 호출로 인해 워커의 CPU/메모리가 100% 점유되더라도, 사용자가 사용하는 API 메인 서버의 응답 가용성에는 전혀 타격을 주지 않는 장애 격리(Fault Isolation)가 가능합니다.
* **RDBMS 부하 보호**: Celery 워커의 동시 태스크 처리량(Concurrency)을 2개로 물리적 제한하여, 백그라운드 큐에 수만 건의 작업이 일시에 밀려들더라도 RDBMS(PostgreSQL)에 가해지는 쓰기 트래픽의 병목 현상을 방어할 수 있습니다.

---

## 3. 고려된 대안 (Alternatives Considered)

### 대안 1: Redis 대신 RabbitMQ를 메시지 브로커로 도입
* **평가**: RabbitMQ는 AMQP 표준을 완벽 지원하며 신뢰성이 높으나, 프로젝트 규모 대비 컨테이너 리소스 점유율이 높고 로컬 설정 및 디버깅 오버헤드가 큽니다.
* **기각 사유**: Redis는 캐시 저장소 및 향후 JWT 세션 블랙리스트 등 타 기능과의 통합 병용이 가능하므로 경량화 및 리소스 극대화를 위해 Redis를 브로커로 최종 낙점하였습니다.

### 대안 2: 첫 구현부터 SSE(Server-Sent Events) 푸시 알림 전면 도입
* **평가**: 작업 완료 직후 실시간 푸시를 주어 화면을 갱신하므로 최상의 UX를 선사합니다.
* **기각 사유**: ASGI 가동(Daphne/Uvicorn), Redis PubSub 통합 및 클라이언트 리커넥션 대응 등으로 인한 초기 설계 오버헤드가 큽니다. 따라서 단기 MVP 동작을 달성하기 위해 간단하고 검증된 폴링 방식을 채택하되, 차후 전환이 용이하도록 코드를 인터페이스 추상화 처리하는 차선책을 채택하였습니다.
