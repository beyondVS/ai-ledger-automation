# **프로젝트 계획서: AI 기반 세금/영수증 PDF 분석 및 가계부 자동화**

**(AI-Powered Tax/Receipt PDF Analyzer & Automated Ledger with PWA Support)**

## **1\. 프로젝트 컨셉 및 비전 (Project Concept)**

### **1.1. 배경 및 문제 정의**

* **귀찮은 가계부 수동 입력:** 가계부 서비스나 세무 자산 관리 서비스를 이용할 때, 메일로 발송되는 전자 세금계산서나 PDF 영수증을 직접 다운로드하여 금액과 내역을 수동으로 옮겨 적는 과정은 매우 번거롭습니다.  
* **비정형 데이터의 한계:** 이메일 영수증이나 PDF 세금계산서는 발행 기관마다 포맷이 완전히 다릅니다. 고정된 정규식(Regex) 기반의 파싱 엔진은 템플릿이 조금만 바뀌어도 즉시 무력화됩니다.  
* **기존 범용 챗봇의 한계:** ChatGPT 등의 범용 대화형 인터페이스는 단발성 분석은 훌륭히 수행하지만, 지속적인 가계부 누적, 카테고리별 통계 집계, 중복 결제 영수증 차단과 같은 정형적 비즈니스 로직을 수행할 수 없습니다.

### **1.2. 서비스 핵심 가치 (Value Proposition)**

본 프로젝트는 "수집-정제-통계"의 전 과정을 자동화하여 사용자의 개입을 최소화하는 것을 목표로 합니다.

* **제로 터치 수집:** 웹 업로드뿐만 아니라 사용자가 전용 수신 주소로 메일을 포워딩(Forwarding)하는 것만으로 가계부가 즉시 자동 갱신됩니다.  
* **지능형 스키마 변환 및 Vision-First 분석:** 발행처가 어디든 멀티모달(Vision) LLM API가 결제 영수증의 레이아웃 이미지 및 텍스트 데이터를 직접 인지하여 고도로 정제된 일관된 JSON 스키마 구조로 강제 변환합니다.  
* **엔지니어링 중심의 신뢰성 및 보안 확보:** 중복 결제 검증 시스템, 비동기 작업 큐, 이미지 전처리 및 엄격한 메일 발신 도메인 검증 필터와 데이터베이스 트랜잭션 원자성을 도입하여 대량의 메일과 고용량 파일이 동시에 유입되어도 리소스를 보호하고 일관성을 완벽히 유지합니다.  
* **모바일 및 PC 플랫폼 통합 지원 (PWA):** 별도의 앱스토어 등록 심사 과정 없이 iOS와 안드로이드 기기 홈 화면에 즉시 설치(A2HS)하여 앱처럼 실행할 수 있습니다. 네이티브 카메라 연동을 지원하여 영수증 결제 즉시 촬영하여 업로드할 수 있는 모바일 최적화 사용자 경험을 제공합니다.

---

## **2\. 아키텍처 및 데이터 흐름 설계**

### **2.1. 시스템 아키텍처 예상 구조도 (System Architecture Diagram)**

#### **\[방안 A\] 컴포넌트 간 물리적 배치도 (Mermaid)**

```mermaid
flowchart TD  
    %% 클라이언트 영역  
    subgraph Client [PWA Client Side HTML5/Vue]  
        A1[Service Worker Cache]  
        A2[manifest.json Installable]  
        A3[Client-side Image Compress]  
    end

    %% 외부 환경 영역  
    subgraph Ext [External World]  
        B1[Client Web UI]  
        B2[Inbound Email Provider SendGrid/Mailgun Webhook]  
    end

    %% 내부 게이트웨이 및 인입 서버 영역  
    subgraph Ingestion [Internal API Gateway & Ingestion Server]  
        C1[File Upload API - Size Validation]  
        C2[Email Webhook Router - Whitelist Checker]  
    end

    %% 메시지 브로커 영역  
    subgraph Queue [Redis Task Queue - Celery]  
        D1[(Redis Task Queue)]  
    end

    %% 비동기 백그라운드 워커 영역  
    subgraph Worker [Backend Worker Process]  
        E1[Image Preprocessor Pillow Engine]  
        E2[Hybrid Bypass Parser Cost Control Engine]  
        E3[Multimodal LLM Client Structured Outputs]  
        E4[Safe Ledger Loader Rollback on Failure]  
        E5[Push Notification Job Web Push Dispatcher]  
    end

    %% 데이터베이스 영역  
    subgraph DB [Database Layer]  
        F1[(Primary PostgreSQL Database)]  
        F2[(DB Layout Cache)]  
    end

    %% 외부 연동 API 영역  
    subgraph API [External Service APIs]  
        G1[Gemini API]  
        G2[Web Push API]  
    end

    %% 물리적 컴포넌트 간 연결 매핑  
    B1 -->|File Upload / Multipart-form| C1  
    B2 -->|Post Webhook Request| C2  
    C1 -->|Publish Background Task| D1  
    C2 -->|Publish Background Task| D1  
    D1 -->|Subscribe Job / Fetch File Buffer| E1  
    E1 --> E2  
    E2 -->|Check Static Template Bypass| F2  
    E2 -->|LLM Fallback if cache missing| E3  
    E3 <==>|Structured Outputs| G1  
    E3 --> E4  
    E4 -->|Start DB Transaction Block / ACID Write| F1  
    E4 --> E5  
    E5 -->|Emit Job Finished Event| G2  
    F1 -.->|Direct Sync Read / 100ms Target| B1
```

#### **\[방안 B\] 컴포넌트 간 동적 흐름도 (Mermaid)**

```mermaid
graph TD  
    %% 클라이언트 및 외부 유입 영역  
    subgraph External [PWA 하이브리드 클라이언트]  
        UI[PWA Vue App: Manifest/SW 탑재]  
        Camera[Mobile Native Camera: 촬영 가공]  
        Email[이메일 서버 SendGrid/Mailgun]  
    end

    %% API 게이트웨이 및 인입 서버 영역  
    subgraph API_Server [API 인입 서버]  
        UploadRouter[업로드 라우터: 크기 제한]  
        EmailRouter[이메일 웹훅 라우터: SPF/DKIM 및 화이트리스트 필터]  
        AuthRouter[인증 라우터: OAuth 2.0 & JWT 이중 발급 및 검증]  
    end

    %% 메시지 브로커 영역  
    subgraph Message_Broker [이벤트 브로커]
        RedisQueue[(Redis Task Queue: Celery)]
    end

    %% 백그라운드 워커 영역  
    subgraph Worker_System [비동기 워커 시스템]  
        SharpWorker[이미지 전처리 워커: Pillow 최적화]  
        BypassParser[하이브리드 바이패스 파서: 사업자번호 기반 레이아웃 캐시 조회]  
        LLMClient[LLM 연동 모듈: Structured JSON]  
        TxLoader[가계부 적재 모듈: DB 트랜잭션 수호자]  
        NotificationWorker[푸시 알림 워커: VAPID Web Push 발송]  
    end

    %% 데이터 저장소 및 캐시  
    subgraph Storage [데이터 레이어]  
        PostgreSQL[(PostgreSQL DB: 복합 Unique 제약 조건)]  
        RedisCache[(Redis Cache: JWT 세션 및 토큰 블랙리스트)]  
    end

    %% 외부 API 연동  
    Gemini[Gemini-2.5-Flash API]  
    PushServer[OS별 푸시 발송 서버: FCM / APNs]

    %% 데이터 흐름 맵핑  
    UI -->|1. 모바일 기기 카메라 촬영 FE-01| Camera  
    Camera -->|2. 압축 파일 전송| UploadRouter  
    UI -->|1. PC 드래그 앤 드롭 파일 업로드| UploadRouter  
    UI -->|1. 로그인/가입 요청| AuthRouter  
    AuthRouter -->|사용자 세션 검증| RedisCache  
    Email -->|1. 이메일 포워딩 BE-01| EmailRouter  
      
    UploadRouter -->|3. 비동기 작업 발행 BE-02| RedisQueue  
    EmailRouter -->|3. 비동기 작업 발행 BE-02| RedisQueue  
      
    RedisQueue -->|4. 작업 소비 BE-03| SharpWorker  
    SharpWorker -->|5. 최적 이미지 버퍼 인계| BypassParser  
    BypassParser -->|6. 캐시 적중 시 LLM 우회 파싱| TxLoader  
    BypassParser -.->|6. 캐시 미적중 시 신규 호출| LLMClient  
    LLMClient <==>|7. JSON 스키마 강제 BE-04| Gemini  
    LLMClient -->|8. JSON 데이터 인계| TxLoader  
    TxLoader -->|9. 단일 트랜잭션 적재 & 롤백 보장 BE-05| PostgreSQL  
    TxLoader -->|10. 완료 알림 작업 생성| RedisQueue  
    RedisQueue -->|11. 푸시 알림 발송 수행| NotificationWorker  
    NotificationWorker <==>|12. VAPID 인증서 명세 전송| PushServer  
    PushServer -->|13. 단말기 푸시 알림 전달| UI  
      
    UI -.->|14. 대시보드 동기 조회 API BE-07| PostgreSQL
```

### **2.2. 데이터 흐름도 (Data Pipeline Flow)**

\[사용자 행동\] \----------\> (1) PWA 모바일 카메라 영수증 촬영 혹은 PC PDF 업로드  
                                │  
                                ▼  
\[Client Preprocessing\] \-\> (2) 클라이언트 단에서 1차 해상도 다운사이징 및 JPEG 압축 연산 진행  
                                │  
                                ▼  
\[Ingestion Layer\] \----\> (3) API 서버 또는 이메일 웹훅 수신 (SPF/DKIM & 화이트리스트 검증)  
                                │  
                                ▼  
\[Processing Queue\] \---\> (4) Redis / Task Queue 적재 (비동기 처리)  
                                │  
                                ▼  
\[Preprocessing Layer\] \-\> (5) 서버 단 2차 고용량 이미지 리사이징 및 WebP 변환 가공 (Pillow) (단, PDF 파일의 경우 Pillow 이미지 전처리 프로세스를 건너뛰고 원본 PDF Bytes 및 application/pdf MIME 타입을 그대로 후속 엔진에 인계)  
                                │  
                                ▼  
\[Hybrid Bypass Router\] \-\> (6) 사업자번호 패턴 매핑, DB 캐시 레이아웃 적중 시 LLM 우회 처리 (Bypass)  
                                │  
                                ▼ (Bypass Fail 시에만 7단계 진행)  
\[AI Analysis Layer\] \--\> (7) 멀티모달 LLM API 호출 (LiteLLM Router를 통해 로컬 개발 환경(DEBUG=True)에서는 로컬 Ollama gemma4:e4b를 최우선/폴백 가동하여 외부 호출을 전면 차단하고, 프로덕션 환경(DEBUG=False)에서만 외부 Gemini-2.5-Flash를 우선 라우팅하도록 통제)  
                                │  
                                ▼  
\[Storage & Logic\] \----\> (8) 단일 DB 트랜잭션 시작 (Transaction Atomicity 보장)  
                                │  
                                ▼  
                        (9) PostgreSQL DB 가계부/상세품목 일괄 적재 및 자동 매핑 (실패 시 전격 롤백)  
                                │  
                                ▼  
\[Real-time Alert\] \----\> (10) 비동기 워커가 Redis 큐를 거쳐 Web Push API(VAPID) 모바일 푸시 알림 트리거  
                                │  
                                ▼  
\[Presentation\] \-------\> (11) PWA 모바일/PC 대시보드 API 실시간 동기 조회

### **2.3. 데이터베이스 논리적 설계 명세 (Logical Database Schema)**

본 프로젝트는 1주차 3일차에 Django 내장 마이그레이션 도구(Django Migrations)를 도입하여 점진적인 버전 관리 방식으로 데이터베이스 물리 스키마를 동적 생성합니다. 데이터 일관성 유지를 위해 설계 단계의 논리적 스키마 청사진을 아래와 같이 명세합니다.

#### **2.3.1. 엔티티 관계 도식화 (Logical Entity Relations)**

 \[users\] 1 \-------- 0..N \[ledgers\] 1 \-------- 0..N \[ledger\_items\]  
    |                         |  
    |-- 1 \--- 0..N            |-- 1 \--- 0..1 \[merchant\_templates\] (Bypass Cache)  
    |  \[user\_push\_subs\]       |  
    |                         |-- 1 \--- 0..N \[failed\_tasks\] (DLQ Log)

#### **2.3.2. 핵심 테이블 논리 명세**

* **users (사용자 마스터 테이블):**  
  * 역할: 서비스 가입 회원 정보 및 메일 수집 화이트리스트 검증을 위한 메일 매핑 데이터 관리.  
  * 주요 속성: 고유 식별자(ID), 계정 이메일(Email), 패스워드 해시(password\_hash), 가입 연동 제공처(provider - local, google, kakao 등), 포워딩 수신용 서브 메일 주소(registered\_forward\_email), 사용자의 고유 시간대(timezone - VARCHAR, 기본값 'Asia/Seoul'), 생성 및 수정 일시.  
* **ledgers (가계부 마스터 테이블):**  
  * 역할: 개별 영수증 결제 내역의 메타데이터 및 공급가액 등의 집계 수치 저장. 중복 적재 방지를 위한 비즈니스 복합 고유 제약조건 적용.  
  * 주요 속성: 가계부 ID(ID), 사용자 식별 번호(user\_id - users 테이블 참조 FK), 가맹점명(vendor\_name), 사업자등록번호(vendor\_registration\_number), 결제 날짜(transaction\_date), 결제 시간(transaction\_time), 공급가액(subtotal\_amount), 부가세(tax\_amount), 최종 총 결제 금액(total\_amount), 원본 LLM 응답 데이터 백업(raw\_llm\_response - JSONB), 생성 일시.  
  * 주요 제약조건: UNIQUE (user\_id, vendor\_registration\_number, transaction\_date, total\_amount) 복합 유니크 제약 설정으로 동일 결제 영수증 무차별 복사 방지.  
* **ledger\_items (가계부 상세 품목 테이블):**  
  * 역할: 단일 영수증 내의 세부 개별 품목 명세 기록. 부모 행 삭제 시 자식 데이터가 정합성 있게 유실되도록 연쇄 삭제 관계 형성.  
  * 주요 속성: 품목 ID(ID), 가계부 식별 번호(ledger\_id - ledgers 테이블 참조 FK), 품목명(name), 단가(unit\_price), 수량(quantity), 합계 금액(total\_price), 생성 일시.  
  * 주요 제약조건: FOREIGN KEY (ledger\_id) REFERENCES ledgers(id) ON DELETE CASCADE 설정으로 데이터 찌꺼기 방지.  
* **merchant\_templates (가맹점 레이아웃 캐시 테이블):**  
  * 역할: 빈번하게 반복 유입되는 특정 가맹점의 영수증 레이아웃 정규식 규칙을 보존하여 LLM API 호출 우회 수행. 자가 학습 시스템에 의해 자동 제안된 규칙은 격리 검증을 위해 is\_verified 필드로 이중 통제됨.  
  * 주요 속성: 사업자등록번호(registration\_number - PK), 가맹점명(vendor\_name), 정적 정규식 파싱 템플릿 규칙 데이터(parser\_rules - JSONB), **템플릿 자율 검증 통제용 여부(is\_verified - Boolean, 기본값 false)**, 생성 일시.  
* **failed\_tasks (비동기 실패 트래킹 테이블):**  
  * 역할: 비동기 처리 과정 중 LLM 파싱 에러나 예외 발생 시 디버깅을 지원하는 실패 기록 보존소 (Dead Letter Queue 패턴).  
  * 주요 속성: 로그 ID(ID), 사용자 식별 번호(user\_id - users 테이블 참조 FK), 파일명(file\_name), 추출된 무가공 원시 텍스트(raw\_extracted\_text), 오류 내용(error\_message), 콜스택 이력(stack\_trace), 생성 일시.  
* **user\_push\_subscriptions (PWA 푸시 구독 테이블):**  
  * 역할: 백그라운드 워커에 의해 비동기 분석 완료 시점에 단말 푸시 알림(Web Push)을 수신하기 위한 웹 표준 구독 정보 보존.  
  * 주요 속성: 구독 식별 번호(ID), 사용자 식별 번호(user\_id - users 테이블 참조 FK), 브라우저 푸시 엔드포인트 수신 주소(endpoint), p256dh 공개키(p256dh), auth 인증키(auth), 생성 일시.

### **2.4. 핵심 기술 의사결정 (Technical Decision)**

* **핵심근거:**  
  1. 가계부 데이터는 사용자의 자산 정보와 직결되므로 강력한 트랜잭션 ACID 정합성이 보장되어야 합니다.  
  2. 중복 입력을 원천 차단하기 위해 복합 제약 조건(Multi-Column Unique Constraints) 설정이 필수적입니다.  
  3. 월별 소비 분석, 카테고별 지출 통계 등 복잡한 관계형 집계(Aggregation) 쿼리가 지속해서 발생합니다.  
* **추론:** NoSQL 데이터베이스(예: MongoDB)는 유연한 비정형 데이터 적재에는 유리하지만, 동시다발적인 요청에서 분산 트랜잭션 정합성을 완벽히 보장하기 어렵고 대량의 애그리게이션 연산 시 CPU 부하가 높습니다. 반면 관계형 데이터베이스(RDB)는 명확한 스키마 정의를 지원하며, 복합 인덱스를 이용해 중복 입력을 사전에 효율적으로 방지할 수 있고, 다양한 집계 인덱스 최적화 기법을 적용할 수 있습니다.  
* **결론:** PostgreSQL을 메인 데이터베이스로 선정하고, PostgreSQL의 JSONB 타입을 서브로 활용하여 파싱되지 않은 원본 LLM 응답을 백업합니다.

---

## **3\. 기능 요구사항 정의 (Functional Requirements)**

본 프로젝트의 모든 요구사항은 린(Lean) 스타트업 아키텍처 원칙에 따라, 작동 가능한 최소 기능 제품을 조기 가동한 후 점진적으로 기술적 한계를 제거하는 수직적 레이어 흐름에 맞추어 완전하게 구조화되어 설계되었습니다.

### **3.1. Phase 1: 동기식 핵심 MVP 요구사항 (1\~2주차 개발 범위)**

어떠한 분산 비동기 처리 인프라나 대용량 최적화 엔진 없이도, 단일 웹 루프 상에서 \[파일 입력 -\> 이미지 압축 -\> LLM 분석 -\> 가계부 1:N 트랜잭션 적재 -\> 대시보드 실시간 렌더링\]의 코어 사용성이 완결되어 정상 구동되는 것을 보장하는 최소 요구사항 목록입니다.

#### **3.1.1. Ingestion & Core Security (파일 수집 및 인증 MVP)**

* **FE-01-A (기본 파일 업로드):** 데스크톱 PC 브라우저 환경에서 드래그 앤 드롭 또는 파일 탐색기 선택 방식을 사용하여 영수증 이미지(JPEG, PNG) 및 PDF 파일을 서버로 직관적으로 수동 송신할 수 있어야 합니다.  
* **BE-08-A (기본 사용자 생성 및 이메일 매핑):** 사용자가 회원가입을 수행할 수 있는 로컬 계정 데이터베이스를 구축하며, 향후 3주차에 적용할 메일 수집 자동화의 기반이 되는 '영수증 수신용 화이트리스트 포워딩 이메일 정보'를 최초 등록받아 매핑 보존합니다.  
* **BE-08-B (JWT 단일 토큰 세션 인증):** API Gateway 연동 단계의 간소화를 위해, 로컬 회원가입 및 로그인 요청 시 사용자의 기기 정보를 식별하고 사용자 ID가 내포된 JWT 단일 Access Token 기반 보안 세션 검증 미들웨어를 구축합니다.

#### **3.1.2. Preprocessing & Extraction (이미지 전처리 및 파싱 MVP)**

* **FE-04-A (클라이언트 사이드 Canvas 다운사이징):** 네트워크 대역폭 소비량 및 서버 CPU 메모리 고갈 병목을 1차적으로 통제하기 위해, 모바일 화면상에서 업로드 단추를 누르는 즉시 HTML5 Canvas API를 이용하여 이미지를 가로 최대 1000px 수준으로 강제 축소하고 압축 품질 0.8 수준의 JPEG 바이트 버퍼로 인코딩한 뒤 동기 API 요청 바디로 전송합니다.  
* **BE-03-A (서버 사이드 동기적 2차 압축):** 웹 서버에 Multipart-form 형식으로 유입된 이미지 버퍼를 Pillow 네이티브 모듈을 활용하여 무손실에 가까운 WebP 이미지 포맷으로 2차 변환합니다.  
* **BE-04-A (LLM Structured Outputs 연동 및 Polling 준비):** 이미지 버퍼 및 원시 PDF 텍스트를 LLM(Gemini-2.5-Flash 등) API로 동기 송신하고 JSON Schema 제약 규칙을 바인딩해 가맹점명, 사업자등록번호, 결제 날짜, 세부 품목 배열을 포함하는 일관된 정형 데이터로 변환받습니다. 향후 3주차 비동기 구조 전환 시 프론트엔드 통신 호환성이 깨지는 것을 예방하기 위해, 동기 응답 데이터 최상단에 **작업 상태 필드(status: "COMPLETED")** 및 작업 식별자 필드(job\_id: null)를 래핑한 폴링 호환용 JSON 규격을 강제 반환합니다.

#### **3.1.3. Business Logic & Presentation (적재 및 대시보드 시각화 MVP)**

* **BE-05-A (단일 데이터베이스 트랜잭션 수호):** 영수증 1장 파싱 데이터로부터 도출된 메인 가계부 레코드(ledgers)와 가계부 세부 품목 레코드 배열(ledger\_items)의 인서트 연산은 반드시 단 하나의 Django ORM 커넥션 트랜잭션 세션 블록(transaction.atomic()) 내에서 처리되어야 하며, 데이터베이스 연결 끊김을 포함한 일체의 구문 장해 발생 시 전격 전역 롤백(Rollback)되어 데이터 파편화(Dirty State)를 방지해야 합니다.  
* **FE-02-A (소비 지출 대시보드 뷰 및 Polling 선대응):** 월별 총지출 한도 설정, 누적 실 소비 금액, 일자별 소비 흐름(리스트 레이아웃)을 REST API를 거쳐 PostgreSQL에서 쿼리 조회해 온 뒤 화면에 즉각 반응형 그리드로 렌더링해야 합니다. 2주차에 API 연동 시 백엔드의 응답 상태 구조(status 및 job\_id)를 판독하여 임시 폴링 대기 상태 레이아웃(Spinner 또는 Shimmer)을 처리하는 가상 클라이언트 모듈을 선배치합니다.  
* **FE-05-A (가계부 CRUD 및 수동 정정 기능):** AI 분류의 예외 상황에 유저가 능동적으로 대처할 수 있도록, 대시보드 리스트의 특정 셀을 터치하여 가맹점 속성을 즉시 동기식으로 수동 변경/수정하거나 내역을 영구 삭제할 수 있는 관리 모달 인터페이스를 내장합니다.  
* **FE-05-B (가계부 수정 내역 내 카테고리 매핑 보완):** 사용자가 대시보드에서 가계부 내역을 수정하고자 모달을 열었을 때, 기존 적재된 카테고리 정보가 프론트엔드 셀렉트박스의 옵션 리스트와 정확히 대조·바인딩되지 않고 누락되는 현상을 개선합니다. 백엔드의 카테고리 API 명세 스키마와 프론트엔드의 옵션 데이터 구조를 1:1로 매핑하는 변환 필터를 프론트엔드에 추가 적용합니다.

### **3.2. Phase 2: 비동기/보안/성능 고도화 요구사항 (3\~4주차 개발 범위)**

Phase 1에서 완벽하게 구동됨을 E2E 검증한 동기식 MVP 제품 위에, 상용 서비스 수준의 비용 차단 알고리즘, 대용량 분산 메시징 처리, 이메일 파이프라인 연동, 모바일 Native PWA 다운로드 환경 및 실시간 Web Push 알림망을 얹어 백엔드 아키텍처의 완성도를 극대화하는 요구사항 목록입니다.

#### **3.2.1. Scale & Performance (비동기 처리 및 비용 절감 고도화)**

* **BE-02-B (Celery 비동기 큐 전환):** 영수증 업로드 요청 유입 즉시 메인 API 서버에서 전처리 및 무거운 AI 연산을 동기식으로 차례차례 구동하던 기존 파이프라인을 분리합니다. API Gateway는 영수증 파일 버퍼를 받는 즉시 Redis 큐로 인입시킨 후 클라이언트에게 작업 식별자 ID 및 처리 중 상태(Pending, 202)를 즉시 반환하여 응답 지연(Latency) 병목을 완전히 해결합니다.  
* **BE-02-C (독립 격리 워커 프로세스 셋업):** 복잡하고 CPU 점유율이 높은 이미지 변환 연산 및 API 지연 시간이 긴 외부 LLM 통신 프로세스를 메인 API 서버의 이벤트 루프 영역과 완전 격리하여, 독립 실행 환경으로 구동되는 백그라운드 Celery 워커 프로세스 노드 내부에서만 비동기적으로 실행되도록 구성합니다.  
* **BE-09-B (하이브리드 비용 최적화 바이패스 및 템플릿 자율 학습):** 추출된 텍스트 원본 내에서 가맹점의 10자리 사업자등록번호가 판별되면, 데이터베이스의 merchant\_templates 테이블을 즉시 인덱스 조회합니다. 해당 가맹점의 검증 플래그(is\_verified: true)가 지정된 정적 정규식 규칙이 캐시 데이터로 존재할 경우, 유료 LLM API의 호출을 전면 취소하고(Bypass) 로컬 정규식 파서 모듈을 통해 파싱하여 API 연동 비용을 0원에 수렴하도록 완벽히 제어합니다. 만약 캐시 템플릿 정보가 없거나 미검증 상태(is\_verified: false)인 경우 LLM API를 폴백 가동하여 성공 파싱한 결과값을 토대로 정규식 규칙 후보군을 알고리즘 연산해낸 뒤, is\_verified: false 규격으로 캐시 DB에 자율 등록 제안(Auto-Generation)하는 템플릿 자가 학습 파이프라인을 작동시킵니다.

#### **3.2.2. Expansion & Automated Ingestion (이메일 웹훅 및 보안 필터 고도화)**

* **BE-01-B (이메일 인바운드 웹훅 연동):** 사용자가 영수증 파일을 직접 웹 브라우저 화면에 첨부하는 한계를 넘어, 이메일 인바운드 파싱용 수신 메일 웹훅 엔드포인트 라우트를 신설하고 SendGrid/Mailgun 등의 외부 메일 서버로부터 포워딩된 첨부파일을 수신 즉시 Redis Celery 태스크로 포매팅하여 이식합니다.  
* **BE-01-C (SPF/DKIM 및 발신인 이메일 화이트리스트 보안 필터):** 위장 스패머의 대량 메일 투하 공격을 막기 위해 메일 헤더 상에 기록된 SPF 및 DKIM 전자서명 보안 인장을 대조 검증하고, 마스터 DB에 사용자별로 사전에 매핑 등록된 '발신자 화이트리스트 이메일 주소'와 메일 발송 주소가 100% 일치할 경우에만 비동기 큐 인입을 허용하는 이중 전초선 필터링 방어막을 구축합니다.  
* **BE-07-B (EXPLAIN ANALYZE 데이터베이스 쿼리 최적화):** 가계부 통계 집계 데이터가 수십만 건 이상 적재되는 실환경을 모방하여 더미 데이터를 10만 개 이상 적재한 뒤, EXPLAIN ANALYZE 실행 계획 분석기를 통해 풀 테이블 스캔(Full Table Scan)이 발생하는 구간을 조밀하게 탐지하여 transaction\_date 기반 결합 인덱스를 튜닝 및 최적화(100ms 이내 응답 보장)합니다.

#### **3.2.3. PWA & Real-time Web Push (모바일 플랫폼 최적화 고도화)**

* **FE-01-B (PWA 카메라 하드웨어 다이렉트 엑세스):** 모바일 기기로 가입 사용자가 PWA에 접속 시, Native 디바이스 제어 지침인 HTML5 Capture API 및 Accept 속성을 바인딩하여 사진첩에 이미 저장된 자산을 선택할 필요 없이, 스마트폰 네이티브 카메라 셔터를 직접 연동 가동하여 찍는 순간 즉석 업로드가 이루어지도록 제어합니다.  
* **FE-03-B (iOS & Android 기기별 A2HS 설치 가이드):** 안드로이드 기기의 크롬 브라우저가 유도하는 네이티브 바로가기 설치 배너 팝업을 인식 제어하고, 이 기능이 보안 정책상 미지원되는 iOS 사파리 환경 접속 사용자에게는 User-Agent를 지능적으로 식별하여 하단 중앙 '공유하기' 버튼 가이드 툴팁 배너를 띄워 모바일 홈 화면 설치를 친근하게 유도합니다.  
* **BE-10-B (VAPID 사양 Web Push 백그라운드 푸시 시스템):** 비동기 Celery 워커에 의해 영수증 가계부 트랜잭션 적재가 성공 커밋되는 시점에, 데이터베이스 연결(Connection Pool)을 더 이상 점유해 병목을 야기하지 않도록 알림 발송용 큐로 분리 발행한 뒤 VAPID 공개키/개인키 규격을 사용해 사용자가 브라우저나 Standalone PWA 앱을 완전히 닫고 있는 오프라인 상태에서도 기기 상단에 가계부 자동 갱신 알림을 전송합니다.

#### **3.2.4. Account Configuration (계정 환경설정 고도화)**

* **BE-08-C (사용자 타임존 설정 API):** 사용자가 자신의 고유 타임존(예: `Asia/Seoul`, `UTC` 등)을 조회 및 변경할 수 있도록 `PATCH /api/v1/accounts/timezone/` API 엔드포인트를 제공하고 유효성 검증을 거쳐 `User.timezone` 필드에 영속화합니다.
* **FE-08-C (사용자 환경설정 및 타임존 UI):** PWA 프론트엔드 내 환경설정 탭(또는 프로필 페이지)을 구축하고, 지원되는 주요 타임존 목록을 직관적인 드롭다운으로 선택하여 갱신할 수 있는 인터페이스 및 반응형 피드백을 제공합니다.

---

## **4\. 하위 호환성 파괴(Regression) 및 부작용(Side-Effect) 분석**

### **4.1. LLM API 스키마 변경 및 응답 지연 리스크**

* **부작용:** 외부 LLM API 서비스 점검이나 응답 지연(Latency), 혹은 JSON 결과 포맷이 일시적으로 훼손되어 유입될 경우 전체 파이프라인이 멈추거나 DB 스키마 검증 에러가 발생할 수 있습니다.  
* **대책:**  
  1. LLM 호출 단계 전후에 정확한 타임아웃(최대 15초)을 설정합니다.  
  2. 파싱 에러 발생 시 최대 3회 지수 백오프(Exponential Backoff)를 적용하여 재시도하도록 큐 설계를 구성합니다.  
  3. 실패한 요청은 삭제하지 않고 FailedTasks 테이블에 원본 텍스트 파일 및 에러 로그와 함께 격리 수집(Dead Letter Queue 패턴)하여 추후 개발자가 수동 분석할 수 있게 합니다.

### **4.2. 중복 제약 조건 추가로 인한 하위 호환성 및 연속 결제 오판정 리스크**

* **부작용:** 
  1. 기존에 생성된 가계부 데이터 중에 사업자등록번호가 누락되었거나 동일 결제 기록이 우연히 누적된 경우, (vendor\_registration\_number, transaction\_date, total\_amount) 유니크 인덱스를 신규 마이그레이션할 때 DB 마이그레이션 실패(Constraint Violation)가 발생합니다.  
  2. 동일 가맹점, 동일 날짜, 동일 금액의 정상 결제가 연속으로 발생하는 경우 (예: 게임 내 동일 패키지 아이템 여러 번 구매), 기존의 복합 유니크 제약조건에 의해 중복으로 오인되어 데이터가 유실(Silent Drop)됩니다.
* **대책:**  
  1. 새로운 고유 인덱스를 활성화하기 전에 중복된 로우를 선별하여 정제하는 마이그레이션 스크립트를 작성하여 선배포해야 하며, 사업자등록번호가 없는 간이 영수증을 위해 COALESCE(vendor\_registration\_number, '0000000000') 같은 폴백(Fallback) 값을 마이그레이션 스크립트에 포함해야 합니다.
  2. 단순 날짜와 금액 조합의 제약을 넘어 결제 고유 승인 번호 또는 정밀 거래 시간(초 단위 이상)을 복합 유니크 제약조건에 포함하거나, 동일 결제 건에 대한 시간 간격 임계치 알고리즘을 도입하여 연속 결제가 안전하게 구분 적재되도록 고도화합니다.

### **4.3. 이미지 전처리 모듈 도입에 따른 CPU 자원 고갈 리스크**

* **부작용:** Python의 Pillow를 통한 리사이징 연산은 CPU 및 메모리 집약적인 무거운 작업입니다. 고용량 업로드가 몰리면 메인 스레드 대기 시간이 길어지고 API 지연이 발생할 수 있습니다.  
* **대책:** 이미지 변환 및 전처리 비즈니스 로직을 API 응답 경로와 분리하여 백그라운드 비동기 작업 큐의 독립적인 Celery 워커(Worker Process) 내부로 완벽히 격리 실행합니다.

### **4.4. 이메일 화이트리스트 필터링에 따른 데이터 오인 유실(Silent Drop) 리스크**

* **부작용:** 사용자가 본인의 가입 이메일 외에 사내 이메일 등 등록되지 않은 다른 이메일 계정으로 포워딩했을 때, 메일 수신 웹훅이 유효하지 않은 요청으로 취급하여 가계부 누락이 일어나고 유저 경험이 훼손될 수 있습니다.  
* **대책:** 가입 사용자당 가계부에 영수증을 등록할 수 있는 외부 포워딩용 이메일 주소를 최대 3개까지 매핑하여 관리할 수 있도록 마스터 DB 스키마 및 사용자 프로필 관리 화면을 구축하고 보완 정책을 마련합니다.

### **4.5. iOS Safari 만의 제한적 PWA 기능 대응 부작용**

* **부작용:** iOS 기기에서는 사파리 웹 브라우저를 켜고 직접 사용자가 수동으로 홈 화면에 추가를 해야만 푸시 알림 수신 및 전면 전체화면(Standalone) 모드가 정상 작동하며, 안드로이드와 달리 설치 권한 취득을 감지하는 브라우저 API 스펙(beforeinstallprompt)이 전혀 지원되지 않습니다.  
* **대책:** 프론트엔드 단에 사용자 OS 에이전트(User-Agent) 식별 시스템을 탑재하여 iOS 접속 유저에게만 별도로 설계된 '홈 화면 추가 가이드' 모달 배너를 부드럽게 노출하도록 유도합니다.

### **4.6. JWT Refresh Token 도입에 따른 세션 만료 및 DB I/O 부하 리스크**

* **부작용:** 만료된 Access Token을 실시간 갱신해 주기 위해 사용자가 대량의 API 요청을 보낼 때마다 PostgreSQL 마스터 DB에 접근하여 Refresh Token을 상시 조회하고 토큰 블랙리스트를 읽으면 병목이 생깁니다.  
* **대책:** 무상태를 보장하되 토큰의 실시간 파기 및 유효 여부를 극도로 빠르게 처리할 수 있도록, 세션 체크 및 블랙리스트 토큰 저장을 고속 **Redis 메모리 테이블**로 완전 격리하여 데이터베이스 부담을 0으로 억제합니다.

### **4.7. Web Push 발송 지연에 따른 DB 커넥션 병목 리스크**

* **부작용:** 백그라운드 Celery 워커가 DB 적재 쿼리를 연동하는 것과 같은 단일 프로세스 실행 흐름 상에서 외부 브라우저 FCM/APNs 푸시 알림 API까지 순차 동기 호출할 경우, 통신 장해나 외부 지연이 발생했을 때 데이터베이스 트랜잭션 수명을 길게 끌고 가 결국 DB 커넥션 풀이 고갈되는 연쇄 장애를 유발합니다.  
* **대책:** DB 적재 트랜잭션이 성공적으로 커밋 완수된 이후, 독립된 푸시 발송 비동기 이벤트 큐(Notification Queue)를 별도로 발행하도록 구조적으로 전면 분리 설계합니다.

### **4.8. 템플릿 자율 학습 엔진 작동에 따른 DB 캐시 오염 리스크**

* **부작용:** 일시적인 LLM 변환 왜곡에 의해 잘못 도출된 정규식 파싱 규칙이 템플릿 캐시에 자동 등록되어 영구 적재되어 버릴 경우, 해당 가맹점을 이용하는 후속 사용자 전체의 소비 데이터에 영구적인 연쇄 가해(Data Corruption)가 침습하게 됩니다.  
* **대책:** 자가 추출 생성되어 적재되는 모든 정규식 캐시는 테이블 내에 is\_verified 필드값을 무조건 기본 false 상태로 차단하여 실동작 필터에서 격리시킵니다. 오직 관리자 어드민 화면에서 직접 실물 정밀 검증을 거쳐 '수동 승인(Confirm to true)' 처리 완료된 데이터만 Bypass 정적 파싱 루프에 반영되도록 신뢰 한계 경계선(Trust Boundary)을 수립합니다.

### **4.9. 로컬 Docker 통합 환경 운영에 따른 개발 소스 핫 리로딩(Hot-Reloading) 지연 리스크**
* **부작용:** Windows 호스트 환경에서 코드를 수정했으나 Docker 컨테이너 내부로 파일 변경 이벤트가 제대로 전파되지 않아 변경 사항이 실시간 반영되지 않는 문제.
* **대책:**
  1. **백엔드/워커**: 로컬 소스 디렉터리를 볼륨 마운트하고, Django의 `runserver` 핫 리로더를 활용합니다. Celery 워커의 경우 개발 시 변경 사항을 감지하여 자동 재시작하는 watch 유틸리티(예: watchfiles)를 활용합니다.
  2. **프론트엔드**: 로컬 소스 마운트와 함께, `vite.config.js`의 `server.watch` 옵션에 `usePolling: true`를 강제 명시하여 폴링 방식으로 파일 변경을 확실히 감지하게 제어합니다.

---

## **5\. System Architecture Guidelines (보안 및 예외 처리 정책)**

* **비자격 증명화:** AWS S3 Access Key, OpenAI/Gemini API Key, PostgreSQL 패스워드 등 모든 자격 증명은 절대 하드코딩하지 않으며 .env 환경 변수에서 로드합니다.  
* **로깅(Logging) 고도화:** 모든 비동기 작업 및 파싱 실패 시나리오에는 원인 추적이 용이하도록 컨텍스트 정보(사용자 ID, 업로드 파일 파일명, 작업 단계)를 포함한 정형 로그를 winston 또는 Python 내장 logging 시스템 등의 모듈을 통해 파일 및 표준 출력 형태로 기록합니다.  
* **트랜잭션 격리 규칙:** 데이터 적재를 다루는 가계부 비즈니스 레이어에서는 절대로 개별 쿼리 조회를 혼재하지 않으며 반드시 데이터 트랜잭션 블록(transaction.atomic()) 내에 적재 쿼리들을 배치하고 커밋되지 않은 단계에서 에러 포착 시 자동 롤백을 구현합니다.  
* **클라이언트 비노출:** 프론트엔드 환경에서 API Key가 직간접적으로 노출되지 않도록 서버 사이드 프록시(Server-Side Proxy) 구조로 API 호출을 은닉합니다.  
* **PWA 필수 조건 설정 (HTTPS 강제화):** PWA 서비스 워커는 브라우저 보안 규격상 Localhost 환경을 제외하면 무조건 신뢰할 수 있는 보안 도메인(HTTPS) 주소상에서만 구동됩니다. 프로덕션 배포 단계에서 SSL 보안 인증서를 반드시 적용하여 암호화 연동 체제를 완수합니다.

### **5.1. 데이터베이스 커넥션 풀(Connection Pool) 통제 규격**

AWS Free tier, Supabase Free plan 등 제한된 사양의 DBMS 노드를 가동 시 최대 가용 커넥션 수(max\_connections)가 20\~50개 내외로 협소하게 제약됩니다. 멀티 컨테이너 환경에서 커넥션 고갈로 인프라 전체가 붕괴되는 것을 원천 차단하기 위해 커넥션 풀의 최대 허용 크기를 아래와 같이 제약 강제합니다.

* **api\_server 컨테이너:** Django DATABASE 설정 내 CONN\_MAX\_AGE를 적절히 제어하고 데이터베이스 연결 최대 풀 크기(Max Pool Size)를 **5**개로 엄격 제한합니다.  
* **async\_worker 컨테이너:** Celery 백그라운드 워커의 최대 트랜잭션 전용 커넥션 풀 크기를 **3**개로 제한합니다.  
* 전체 컨테이너 세트 가동 시 사용 커넥션의 최대 합산은 **8**개로 유지되어, DBMS 가용 한계 범위 내에서 완벽하게 트랜잭션 정합성을 실현합니다.

### **5.2. 로컬 환경 모바일 PWA HTTPS 터널링 규격**

물리 스마트폰 기기(iOS, Android)를 사용해 로컬 개발용 API 주소에 무선 와이파이(LAN) 대역으로 접속하여 PWA 홈 화면 바로가기 등록 및 Web Push 구독 테스트 진행 시 브라우저 WebKit 보안 규격상 서비스 워커 등록이 전격 거부됩니다. 이 디버깅 한계를 타개하기 위해 다음 가이드를 의무화합니다.

* 로컬 API 포트(예: 8080) 및 Vue 개발 포트를 외부에 임시 SSL 터널 가교로 오픈해 주는 **ngrok / localtunnel**을 디버깅 로컬 개발 터널 도구로 상시 연동합니다.  
* 터널링 도구에 의해 실시간 제공되는 공개 HTTPS 보안 도메인(예: https://abcd-123.ngrok-free.app)을 PWA 기기 수신 테스트용 Base URL로 사용하여 실제 단말 장치 상에서의 모바일 네이티브 연동을 무결하게 디버깅합니다.

### **5.3. Docker Compose 로컬 통합 인프라 명세**

```yaml
version: '3.8'

services:  
  # 1. 관계형 데이터베이스 컨테이너  
  postgres_db:  
    image: postgres:15-alpine  
    container_name: ledger_postgres  
    restart: always  
    environment:  
      POSTGRES_DB: ${DB_NAME:-ledgerdb}  
      POSTGRES_USER: ${DB_USER:-dbuser}  
      POSTGRES_PASSWORD: ${DB_PASSWORD:-dbpassword_secure}  
    ports:  
      - "5432:5432"  
    volumes:  
      - postgres_data:/var/lib/postgresql/data  
    networks:  
      - ledger_network

  # 2. 인메모리 세션 스토어 및 비동기 큐 버퍼 컨테이너  
  redis_broker:  
    image: redis:7-alpine  
    container_name: ledger_redis  
    restart: always  
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD:-redis_password_secure}  
    ports:  
      - "6379:6379"  
    volumes:  
      - redis_data:/data  
    networks:  
      - ledger_network

  # 3. 메인 백엔드 Django API Server  
  api_server:  
    build:  
      context: ./backend  
      dockerfile: Dockerfile  
    container_name: ledger_api  
    restart: always  
    ports:  
      - "8080:8080"  
    command: python manage.py runserver 0.0.0.0:8080  
    volumes:
      - ./backend:/app  # 로컬 소스 핫 리로딩 볼륨 바인드
    environment:  
      - DATABASE_URL=postgres://${DB_USER:-dbuser}:${DB_PASSWORD:-dbpassword_secure}@postgres_db:5432/${DB_NAME:-ledgerdb}  
      - REDIS_URL=redis://:${REDIS_PASSWORD:-redis_password_secure}@redis_broker:6379/0  
      - GEMINI_API_KEY=${GEMINI_API_KEY}  
      - JWT_ACCESS_SECRET=${JWT_ACCESS_SECRET}  
      - JWT_REFRESH_SECRET=${JWT_REFRESH_SECRET}  
      - VAPID_PUBLIC_KEY=${VAPID_PUBLIC_KEY}  
      - VAPID_PRIVATE_KEY=${VAPID_PRIVATE_KEY}  
    depends_on:  
      - postgres_db  
      - redis_broker  
    networks:  
      - ledger_network

  # 4. CPU 집약 연산 및 AI 분석 태스크 담당 Celery 백그라운드 워커 컨테이너  
  async_worker:  
    build:  
      context: ./backend  
      dockerfile: Dockerfile  
    container_name: ledger_worker  
    restart: always  
    # 윈도우 fork 제약이 없으므로 -P 옵션을 사용하지 않고 순정 prefork로 가동
    command: celery -A config worker -l info  
    volumes:
      - ./backend:/app  # 로컬 소스 핫 리로딩 볼륨 바인드
    environment:  
      - DATABASE_URL=postgres://${DB_USER:-dbuser}:${DB_PASSWORD:-dbpassword_secure}@postgres_db:5432/${DB_NAME:-ledgerdb}  
      - REDIS_URL=redis://:${REDIS_PASSWORD:-redis_password_secure}@redis_broker:6379/0  
      - GEMINI_API_KEY=${GEMINI_API_KEY}  
      - VAPID_PUBLIC_KEY=${VAPID_PUBLIC_KEY}  
      - VAPID_PRIVATE_KEY=${VAPID_PRIVATE_KEY}  
    depends_on:  
      - postgres_db  
      - redis_broker  
    networks:  
      - ledger_network

  # 5. 로컬 개발 전용 프론트엔드 컨테이너
  frontend_dev:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: ledger_frontend
    restart: always
    ports:
      - "5173:5173"
    command: npm run dev -- --host 0.0.0.0
    volumes:
      - ./frontend:/app  # 로컬 소스 핫 리로딩 볼륨 바인드
    networks:
      - ledger_network

volumes:  
  postgres_data:  
    driver: local  
  redis_data:  
    driver: local

networks:  
  ledger_network:  
    driver: bridge
```

---

## **6\. 4주 진행 계획 (Detailed Schedule)**

### **6.1. 1주차: 동기식 핵심 MVP 백엔드 구축 (1일차 \~ 7일차)**

* [x] **1일차:** 로컬 통합 개발 환경 셋업. 도커 데스크톱을 설치하고, PostgreSQL 데이터베이스 싱글 가상 인스턴스를 격리된 컨테이너 내부 환경에 독립 빌드.  
* [x] **2일차:** Django Model 클래스 설계 및 수립. 가계부(Ledger), 품목(LedgerItem), 사용자 정보(User), PWA 푸시 구독(UserPushSubscription), 템플릿 캐싱(MerchantTemplate), 실패 로깅용 FailedTask 모델 정의 완료.  
* [x] **3일차:** 데이터베이스 마이그레이션 도구(Django 내장 마이그레이션 시스템) 환경 연동. 2주차에 가동할 중복 적재 유효성 가이드라인 준수를 위해 복합 고유 제약조건 unique\_together 혹은 UniqueConstraint를 각 모델 정의에 적용하고 마이그레이션 파일 작성 및 DB 반영 검증 성공.  
* [x] **4일차:** Python 및 Django 웹 애플리케이션 프레임워크 초기 보일러플레이트 코드 빌드. .env 환경변수 연동 및 데이터베이스 연동용 settings.py 기본 셋업 완수.  
* [x] **5일차:** Docker Compose 명세서 개발 및 테스트. Postgres와 Redis, Django API Server 인프라 노드를 단일 격리된 bridge 가상 네트워크에 바인딩하고 docker-compose up을 통한 원클릭 컨테이너 기동 테스트 마감.  
* [x] **6일차:** PDF 정적 파일 내에 물리적으로 내장된 텍스트 레이어를 무손실 추출하기 위한 Python 내장 기반 PyMuPDF 혹은 pdfplumber 연동 유틸리티 클래스 코드 구현 완료.  
* [x] **7일차:** 1주차 인프라 중간 점검 및 로컬 통합 테스트 수행. 테스트 전용 DB를 가동하여 \[로컬 PDF 파일 업로드 -\> 원시 텍스트 파싱 -\> Django ORM 기반 원시 쿼리 적재\] 흐름의 무결성 검증 및 Git 형상 관리 개시.

### **6.2. 2주차: MVP 프론트엔드 연동 및 동기식 E2E 릴리즈 (8일차 \~ 14일차)**

* [x] **8일차:** 프론트엔드 뷰(Vue 3) 애플리케이션 프로젝트 초기 구축 및 CSS 환경(Tailwind CSS) 세팅. 반응형 구조의 기본 영수증 업로드 드롭존(Dropzone) 레이아웃 퍼블리싱 완료.  
* [x] **9일차:** 프론트엔드 업로드 동작부와 1주차에 구축한 동기식 Django API 서버 연동 진행. 향후 3주차 비동기 전환 시 데이터 하위 호환성을 보장하기 위해, status 및 job\_id 응답 스키마 플레이스홀더(Placeholder) 필드를 미리 설계에 반영하고 폴링(Polling) 대기 상태 가상 모듈을 클라이언트에 선배치.  
* [x] **10일차:** 기본 가입 및 로그인 미들웨어 연동. 프론트엔드 로그인 페이지 퍼블리싱 및 OAuth 2.0 소셜 인입선 확보 전, Django REST Framework 기반 로컬 JWT 발급 체계를 연동하여 유저별 데이터 식별 보안 로직을 탑재하고 실물 JWT 검증 로직으로 완전히 전환.  
* [x] **11일차:** **[추가 계획] 프론트엔드 로그인 상태 체크(인증 토큰 기반 라우터 가드 구현) 및 실제 사용자 로그인/회원가입 UI 화면 개발.** 모바일 사용자 전용 클라이언트 사이드 이미지 리사이징 모듈 내장 (HTML5 Canvas API를 이용하여 업로드 단추를 누르기 직전 1000px 규격 최적화 압축 처리 가동하여 네트워크 트래픽 절감).  
* [x] **12일차:** 대시보드 메인 가계부 리스트 뷰 및 개별 상세 내역 조회 아코디언 컴포넌트 개발. API 서버를 통해 Django ORM에서 누적 적재 데이터를 받아와 화면에 정상 렌더링 확인. (이미 10일차에 구현된 로그인 기능을 바탕으로 실제 인증된 사용자의 가계부 데이터를 호출하여 렌더링)  
* [x] **13일차:** 가계부 상세 레코드 수동 정정(가맹점명 변경, 오분류 카테고리 교정 등) 및 수동 삭제(CRUD) 프론트엔드 모달 다이얼로그 기능 최종 개발 및 연결.  
* [x] **14일차:** 2주차 동기식 MVP 완전체 통합 테스트 및 AI 분석 모듈 현대화. 지원 종료된 `google-generativeai` SDK를 완전히 배제하고, `litellm.Router`를 도입하여 로컬 환경(DEBUG=True)에서는 로컬 Ollama `gemma4:e4b`를 최우선 및 폴백으로 단독 가동하며 프로덕션 환경(DEBUG=False)에서만 외부 Gemini-2.5-Flash를 우선 라우팅하는 다이내믹 라우터(`ReceiptLLMClient`)를 구축 완료. PDF 파일 업로드 시 Pillow 전처리 오류를 예외 분기 처리하여 원본 PDF Bytes 데이터 및 MIME 타입을 API에 직접 전달하는 전처리 고도화 구현. 백엔드 pytest 49개 및 프론트엔드 테스트 38개 전원 그린 패스 완료.

### **6.3. 3주차: 비동기 분산 아키텍처 및 비용/보안 고도화 (15일차 \~ 21일차)**

* [x] **15일차:** 비동기 처리를 위한 Redis 인메모리 스토어 인프라 구축 및 Docker Compose 환경 통합. 2주차까지 설계된 동기식 가동 서버를 Django 메인 서버와 Celery 백그라운드 워커 서버로 역할 분리 설계.  
* [x] **16일차:** Celery를 도입한 비동기 작업 큐 시스템 구축. 인프라 메모리 및 커넥션 부하 방지를 위해, Django settings.py 내 DB 커넥션 풀 크기를 최대 5개, Celery 워커의 풀 크기를 최대 3개로 엄격히 제한하는 풀 통제 알고리즘 구현. 메인 서버는 업로드 접수 즉시 대기(Pending, 202)를 반환하도록 비동기 리팩토링. **[추가 계획] 백엔드, Celery, 프론트엔드를 전체 Dockerizing하고, 로컬 마운트 기반 핫 리로딩 인프라 통합 구축.**  
* [x] **17일차:** 데이터베이스 무결성 보장을 위한 예외 처리 및 롤백 가이드라인 고도화. Django ORM 트랜잭션 블록(transaction.atomic())을 엄밀히 통제하여 마스터 적재 실패 시 품목 리스트까지 롤백하고, 중복 결제 인입 시 무시(Django ORM get_or_create 혹은 bulk_create ignore_conflicts 옵션 활용)하는 안정성 적용. **[추가 계획] 동일 상품 연속 결제 시 오탐지 방지를 위한 중복 체크 알고리즘 고도화 (결제 승인번호/거래 시간 연동 등). 프론트엔드 수정 내역 모달(FE-05-B) 내 카테고리 셀렉트박스 데이터 매핑 누수 버그 해결.**
* [x] **18일차:** 비용 통제 엔진 핵심(뼈대) 구현. `MerchantTemplate` 모델에 검증 여부(`is_verified`) 컬럼 추가 설계. 10자리 사업자등록번호를 추출하여 가맹점을 식별하고, `is_verified: true` 상태인 경우에만 LLM 호출을 우회(Bypass)하여 파싱하며 실패 시 LLM으로 폴백(Fallback)하는 기본 안전장치 구축. 신규 가맹점은 LLM 파싱 성공 후 정규식 규칙을 산출해 `is_verified: false` 상태로 자동 제안(자가 학습)하는 등록 파이프라인 구현.  
* [ ] **19일차:** 자율 템플릿 승인 및 자가 치유(Self-Healing) 알고리즘 고도화. 동일 정규식 규칙이 N회(예: 3회) 이상 일관되게 도출 시 `is_verified: true`로 자동 승인(Auto-Promotion)하는 로직과, 에러 발생 또는 사용자 수동 정정 시 `is_verified: false`로 강등하고 규칙을 자동 갱신(자가 치유)하는 알고리즘을 추가하여 비용 통제 시스템 완결.  
* [ ] **20일차:** 가계부 UI 고도화 1단계 (소비 시각화 차트 및 예산 게이지). 카테고리별 소비 분포 원형 차트 및 월별 지출 흐름 막대 차트 컴포넌트를 구현하고 월 예산 대비 남은 예산 게이지 바, 이번 달 지출 TOP 3 가맹점 요약 카드를 추가하여 직관적인 소비 대시보드 제공.  
* [ ] **21일차:** 가계부 UI 고도화 2단계 (캘린더 뷰 및 다차원 필터링) 및 **사용자 타임존 설정 변경 기능 구현**. 일자별 지출 내역을 달력 화면에서 한눈에 보여주는 캘린더 뷰(Calendar View) 모드를 추가하고 상호명 검색 및 카테고리/기간/금액 대역별 다차원 검색/필터링 패널을 연동하여 검색 편의성 강화. **더불어 사용자의 고유 타임존 설정을 동적으로 갱신할 수 있는 환경설정 API 엔드포인트(PATCH /api/v1/accounts/timezone/) 및 프론트엔드 설정 탭 UI를 구축하여 영수증 결제일 타임존 정합성 파이프라인과 완벽 연동.**  

### **6.4. 4주차: PWA 플랫폼 최적화, Web Push 및 프로덕션 배포 (22일차 \~ 28일차)**

* [ ] **22일차:** 3주차 비동기 아키텍처 튜닝 및 부하 테스트. 웹 업로드 경로로 유입되는 영수증 50종 일시 유입 부하 테스트를 통해 데이터 누락 및 트랜잭션 정합성 검증 완료.  
* [ ] **23일차:** PWA Manifest/Service Worker 캐시 연동 및 HTML5 Capture API 모바일 기기 카메라 연동.  
* [ ] **24일차:** 스마트 단말기(iOS, Android)의 beforeinstallprompt 제어 배너 설계 및 사파리 수동 툴팁 A2HS 레이아웃 가이드 구현.  
* [ ] **25일차:** 백그라운드 VAPID 표준 V2 VAPID 푸시 발송 큐(Notification Queue) 파이프라인 개설 및 FCM/APNs 연동 웹 푸시 비동기 발송 모듈 독립 기동.  
* [ ] **26일차:** 비동기 워커 알림 소비 태스크 오프라인 수신 단말 E2E 모바일 푸시 알림 도달 및 디바이스 캐싱 데이터 무결 테스트 완료.  
* [ ] **27일차:** 대규모 실 인프라용 docker-compose.prod.yml 튜닝 설계 및 호스트 포트 접근 보안 제어.  
* [ ] **28일차:** 서버 실 프로덕션 환경 HTTPS SSL 보안 인증 및 Nginx 리버스 프록시 탑재, 웹 업로드 및 PWA/웹푸시 기반 전 과정 E2E 통합 알림망 정식 릴리즈 완료.

---

## **7. 차후 확장 계획 (Future Scope & Backlog)**

본 4주 개발 로드맵에서는 가계부 UI 고도화 및 사용성 개선에 집중하기 위해 우선순위가 연기된 백로그 항목입니다. 차후 시스템 안정화 완료 후 추가 연동을 위해 설계를 보존합니다.

* **이메일 인바운드 웹훅 연동:** 사용자가 본인의 가입 이메일 주소에서 전용 수신 메일 주소로 포워딩한 메일에서 영수증(PDF/이미지) 첨부파일을 자동으로 추출하여 Celery 비동기 작업 큐로 연동하는 이메일 수신 가교 모듈 개발.
* **SPF/DKIM 및 화이트리스트 보안 필터:** 위장 스팸 공격 방지를 위한 SPF/DKIM 전자서명 검증 유틸리티 및 가입 사용자당 가계부에 메일을 보낼 수 있는 발신용 이메일 화이트리스트(최대 3개 매핑) 테이블 검증 알고리즘 적용.