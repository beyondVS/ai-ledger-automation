# Infrastructure & Network Port Binding Contract

본 문서는 프로덕션 실 서비스 환경에서 가동되는 개별 도커 컨테이너들의 포트 바인딩 규격, 내부 격리 네트워크 소통 구조, 그리고 리소스 제한 임계 스펙을 명문화한 인프라 계약(Contract) 정의서입니다.

---

## 1. 네트워크 및 포트 노출 정책 (Network Ports Mapping)

모든 서비스는 공인 인터넷망(Public IP)으로부터의 위협을 격리하기 위해 Nginx를 제외한 모든 직접 바인딩을 제거하고 컴포즈 격리 네트워크망 내에 숨겨야 합니다.

| 서비스명 (Service Name) | 호스트 외부 포트 (Host Port) | 컨테이너 내부 포트 (Container Port) | 노출 범위 (Scope) | 통신 계약 (Protocol) |
| :--- | :--- | :--- | :--- | :--- |
| **nginx** (Web Gateway) | `80` (HTTP)<br>`443` (HTTPS) | `80`<br>`443` | **공인 (Public)** | 외부 유입 트래픽 수신 및 내부 `api-server` 위임 중계 |
| **api-server** (DRF) | *포트 노출 없음* | `8000` | 사설 (Private Network) | 오직 Nginx 역방향 프록시를 통한 포워딩만 수신 |
| **postgres_db** (PostgreSQL) | *포트 노출 없음* | `5432` | 사설 (Private Network) | 오직 `api-server` 및 `async-worker`의 ORM 연결 수신 |
| **redis_broker** (Redis) | *포트 노출 없음* | `6379` | 사설 (Private Network) | Celery 비동기 브로커 및 캐시 목적으로 내부 컴포넌트만 접속 |
| **async_worker** (Celery) | *포트 노출 없음* | N/A | 사설 (Private Network) | 외부 인바운드 포트가 없으며, Redis 큐로부터 풀링 방식으로 기동 |

---

## 2. 도커 컴포즈 리소스 및 로깅 계약 규격 (Resource & Log Specification)

`docker-compose.prod.yml` 작성 시 개별 서비스 컨테이너는 아래의 하드웨어 리소스 제한 규격과 헬스체크 사양을 준수해야 합니다.

```yaml
# 1. 공통 로깅 규격 계약 (Logging Driver Specification)
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"

# 2. 개별 서비스별 리소스 점유 및 가용성 계약 (Resource Constraints & Healthcheck)
services:
  nginx:
    deploy:
      resources:
        limits:
          cpus: '0.50'
          memory: 256M
        reservations:
          cpus: '0.10'
          memory: 64M
    restart: always

  api-server:
    deploy:
      resources:
        limits:
          cpus: '1.50'
          memory: 1G
        reservations:
          cpus: '0.25'
          memory: 256M
    restart: on-failure:5
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/api/health/ || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 15s

  postgres_db:
    deploy:
      resources:
        limits:
          cpus: '2.00'
          memory: 2G
        reservations:
          cpus: '0.50'
          memory: 512M
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 3

  redis_broker:
    deploy:
      resources:
        limits:
          cpus: '0.50'
          memory: 256M
        reservations:
          cpus: '0.10'
          memory: 64M
    restart: always
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  async_worker:
    deploy:
      resources:
        limits:
          cpus: '1.50'
          memory: 1G
        reservations:
          cpus: '0.25'
          memory: 256M
    restart: on-failure:5
```
