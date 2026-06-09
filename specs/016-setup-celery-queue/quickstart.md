# Quickstart: 로컬 Docker 개발 환경 실행 및 검증 가이드

본 가이드는 전체 서비스 스택(Postgres, Redis, Django API, Celery 워커, Vue 프론트엔드)을 Docker Compose로 일괄 기동하고 핫 리로딩이 완벽히 작동하는 개발 인프라를 사용하는 절차를 규정합니다.

## 1. 개발 스택 기동 방법

저장소 루트 디렉터리에서 아래 명령을 사용하여 모든 격리 컨테이너를 기동합니다.

```bash
# 1. 환경 변수 파일 복사 (필요 시)
cp .env.example .env

# 2. Docker Compose 빌드 및 백그라운드 기동
docker compose up --build -d

# 3. 로그 실시간 모니터링 (선택 사항)
docker compose logs -f
```

기동 완료 시 접근 주소:
* **프론트엔드 웹앱**: `http://localhost:5173`
* **백엔드 API 서버**: `http://localhost:8080`

---

## 2. 핫 리로딩 (Hot-Reloading) 검증 절차

코드 수정 사항이 빌드 재실행 없이 실시간으로 컨테이너 내부에 투영되는지 검증하는 순서입니다.

### 백엔드 (Django runserver) 검증
1. 로컬의 `backend/config/settings.py` 또는 views.py 파일을 열어 주석을 달거나 텍스트를 수정합니다.
2. `docker compose logs api_server`를 확인하여 runserver 프로세스가 자동으로 소스 변경을 감지하고 `Watching for file changes with StatReloader`를 통해 리스타트되는지 검사합니다.

### 프론트엔드 (Vue3 / Vite) 검증
1. 로컬의 `frontend/src/views/` 하위 Vue 컴포넌트 내부 텍스트를 일부 변경합니다.
2. 브라우저(`http://localhost:5173`)에서 페이지를 수동 새로고침할 필요 없이 변경 사항이 HMR(Hot Module Replacement)을 통해 실시간으로 1.5초 이내에 자동 반영되는지 확인합니다.
3. *Vite 감지 오류 방어 설정*: `frontend/vite.config.js` 파일 내에 아래 설정이 바인딩되어 있는지 상시 체크하십시오.
   ```javascript
   server: {
     watch: {
       usePolling: true, // Windows-Docker 볼륨 마운트 시 필수
       interval: 100
     }
   }
   ```
