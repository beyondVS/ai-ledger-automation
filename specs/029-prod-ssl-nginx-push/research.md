# Research Report: Production Infrastructure & Unified E2E Notification Release

**Feature**: `029-prod-ssl-nginx-push`

## 1. SSL/HTTPS Certification Management

### Decision
- **결정사항**: Cloudflare 또는 AWS Application Load Balancer (ALB) 등 외부 클라우드 프록시 레이어에서의 **SSL Offloading**을 기용합니다. Nginx 리버스 프록시 컨테이너 자체는 내부 prod-bridge 망 격리 상태에서 HTTP 80 포트로만 가동되며, 외부의 암호화된 HTTPS 요청을 안전하게 전달받아 백엔드 및 프론트엔드로 중계합니다.
- **타당성 (Rationale)**: Let's Encrypt 및 Certbot 컨테이너를 통합 가동할 경우 발생하는 인증서 발급 지연 및 만료 갱신 주기(90일)에 따른 Nginx 일시적 다운타임 리스크를 원천 제거합니다. 클라우드 프록시 및 로드밸런서의 완전 관리형 SSL 서비스를 활용하여 인프라 유지보수 공수를 없애고 가용성을 극대화합니다.
- **고려된 대안 (Alternatives considered)**:
  - **Let's Encrypt + Certbot 컨테이너 탑재**: 로컬 독립형 프로덕션 배포 시 유용하나, 멀티 컨테이너 환경에서 80 포트 소유권 다툼 및 자동 갱신 실패 시 서비스 장해 리스크가 존재하여 기각했습니다.
  - **수동 상용 SSL 인증서 마운트**: 인증서 갱신 시마다 관리자가 컨테이너에 직접 접속하여 파일을 덮어쓰고 Nginx를 리로드해 주어야 하므로 휴먼 에러 가능성이 커 기각했습니다.

## 2. E2E Notification Pipeline Business Trigger Scope

### Decision
- **결정사항**: 이번 정식 릴리즈에서는 (1) 3단계 하이브리드 영수증 파싱 처리 성공/실패 결과 알림과 (2) 사용자 설정 월별 예산 임계치(80%, 100%) 초과 경보 알림을 모두 유기적으로 포함하는 **통합 E2E 알림망**을 구성합니다.
- **타당성 (Rationale)**: 가계부 자동화 서비스의 핵심 가치는 영수증 업로드 후의 비동기 결과 수신과 이를 기반으로 한 실시간 자산 소비 통제(예산 초과 경고)에 있습니다. 두 트리거 모두 백엔드 Celery 비동기 작업에 긴밀히 연계되어 작동하므로, 단일 릴리즈 파이프라인에서 통합 검증하는 것이 E2E 정합성 수호에 가장 적합합니다.
- **고려된 대안 (Alternatives considered)**:
  - **영수증 처리 결과 알림에만 집중**: 예산 경보 알림이 배제되면 사용자는 지출 현황을 파악하기 위해 상시 대시보드에 진입해야 하므로 UX 가치 실현이 부족하여 기각했습니다.
  - **예산 경보 알림에만 집중**: 영수증 업로드 성공 및 AI 파싱 실패에 대한 상태 피드백이 부재하게 되므로 사용자가 시스템 작동 상태를 알 수 없어 기각했습니다.

## 3. Nginx Reverse Proxy Routing Structure

### Decision
- **결정사항**: **단일 도메인 구조 및 서브경로 라우팅** (Vite 프론트엔드 SPA 정적 자산은 루트 경로 `/`로 Nginx가 서빙하고, Django 백엔드 API 서버는 서브경로 `/api/`를 통해 proxy_pass로 역방향 프록시 중계)을 채택합니다.
- **타당성 (Rationale)**: 프론트엔드와 백엔드가 동일한 도메인/포트 아래에서 구동되므로 브라우저 CORS(Cross-Origin Resource Sharing) 설정 복잡도가 사라지고, 단일 SSL 인증서(혹은 와일드카드) 하나만으로 프론트엔드와 API 통신 전체의 보안을 완벽히 수호할 수 있습니다. PWA의 PWA Manifest 및 Service Worker 가동 영역 보안 컨텍스트 확보에도 가장 안정적인 패턴입니다.
- **고려된 대안 (Alternatives considered)**:
  - **서브도메인 분리 구조 (`api.example.com`)**: 프론트엔드와 API 서버의 쿠키 공유 문제 및 XSS 방어를 위한 추가 httpOnly 설정, CORS 처리 등 불필요한 엔지니어링 오버헤드가 발생하여 기각했습니다.
