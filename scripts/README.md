# 📂 AI Ledger Automation Local Scripts Directory

이 디렉토리는 **ai-ledger-automation** 프로젝트의 로컬 개발, 데이터베이스 관리, 비동기 워커 구동, 인프라 보안 상태 점검, 그리고 로드 테스트 등을 자동화하기 위해 구축된 크로스 플랫폼 대칭형 유틸리티 스크립트들이 격리 보존된 공간입니다.

최상위 프로젝트 헌법 제VI조(크로스 플랫폼 대칭 툴링)에 의거하여, 모든 스크립트는 **Windows PowerShell (`.ps1`)**과 **macOS / Linux / WSL Bash (`.sh`)** 환경에서 100% 동일한 동작 멱등성을 보장하도록 이중 대칭형으로 작성되어 있습니다.

---

## 📋 스크립트 명세 및 가이드라인

| 스크립트 그룹 명칭 (PowerShell / Bash) | 핵심 용도 및 역할 | 주요 실행 예제 및 사용법 | 필수 여부 |
| :--- | :--- | :--- | :---: |
| **1. setup_boilerplate**<br>`setup_boilerplate.ps1`<br>`setup_boilerplate.sh` | 로컬 가상환경(`.venv`) 구성, 백엔드 필수 패키지 설치(`uv sync`), `.env` 보일러플레이트 복사 등을 실행해 주는 로컬 개발 환경 초기화 도구입니다. | **PowerShell**:<br>`.\scripts\setup_boilerplate.ps1`<br>**Bash**:<br>`./scripts/setup_boilerplate.sh` | **필수** |
| **2. check_ollama**<br>`check_ollama.ps1`<br>`check_ollama.sh` | 로컬 Ollama 엔진 실행 상태 및 가계부 3단계 하이브리드 파이프라인 1단계 주 모델인 `qwen2.5:14b-instruct-q4_K_M`이 로컬 환경에 다운로드되어 있고 가동 준비가 되었는지 진단합니다. | **PowerShell**:<br>`.\scripts\check_ollama.ps1`<br>**Bash**:<br>`./scripts/check_ollama.sh` | **필수** |
| **3. local-db-controller**<br>`local-db-controller.ps1`<br>`local-db-controller.sh` | `docker-compose.db.yml` 데이터베이스 명세를 래핑하여, 로컬 PostgreSQL 18 RDBMS 컨테이너를 단독 구동(`start`)하거나 중지(`stop`)하는 가벼운 CLI 도구입니다. | **PowerShell**:<br>`.\scripts\local-db-controller.ps1 start`<br>**Bash**:<br>`./scripts/local-db-controller.sh stop` | **필수** |
| **4. manage-db**<br>`manage-db.ps1`<br>`manage-db.sh` | 로컬 데이터베이스의 장고 스키마 마이그레이션(`migrate`), 테이블 초기화(`flush`), 테스트용 목업 데이터 적재(`seed`)를 한 번에 조작하는 데이터 유틸리티입니다. | **PowerShell**:<br>`.\scripts\manage-db.ps1 migrate`<br>**Bash**:<br>`./scripts/manage-db.sh seed` | **필수** |
| **5. start-async-dev**<br>`start-async-dev.ps1`<br>`start-async-dev.sh` | 무거운 도커 전체 서비스를 가동하지 않고, 로컬 파이썬 가상환경 위에서 직접 Redis와 Celery 코어 비동기 워커를 기동하여 핫 리로드(Auto-reload) 통신을 수립합니다. | **PowerShell**:<br>`.\scripts\start-async-dev.ps1`<br>**Bash**:<br>`./scripts/start-async-dev.sh` | **필수** |
| **6. start-notification-worker**<br>`start-notification-worker.ps1`<br>`start-notification-worker.sh` | 백그라운드 Web Push 알림 발송만을 독립적으로 전담하여 소비하는 전용 알림 큐(`notifications`) Celery 워커 기동 도구입니다. | **PowerShell**:<br>`.\scripts\start-notification-worker.ps1`<br>**Bash**:<br>`./scripts/start-notification-worker.sh` | **필수** |
| **7. run-pdf-tests**<br>`run-pdf-tests.ps1`<br>`run-pdf-tests.sh` | 로컬 PDF 파싱 엔진의 정합성과 Gemini 멀티모달 direct 인입 흐름만을 콕 집어 격리 테스트하도록 pytest를 백그라운드 래핑 구동하는 테스트 도구입니다. | **PowerShell**:<br>`.\scripts\run-pdf-tests.ps1`<br>**Bash**:<br>`./scripts/run-pdf-tests.sh` | **필수** |
| **8. run_load_test**<br>`run_load_test.ps1`<br>`run_load_test.sh` | 3주차 아키텍처 튜닝 시 도입된 것으로, 50종 API 동시 다중 유입 상황을 모의하여 트랜잭션 롤백 정합성과 60초 윈도우 결제 중복 방어 알고리즘을 부하 테스트하고 결과를 자동 수집합니다. | **PowerShell**:<br>`.\scripts\run_load_test.ps1`<br>**Bash**:<br>`./scripts/run_load_test.sh` | **필수** |
| **9. run_port_scan**<br>`run_port_scan.ps1`<br>`run_port_scan.sh` | 28일차 인프라 보안 튜닝 후 실제로 데이터베이스, Redis 등의 내부 서비스 포트가 로컬 외부 호스트에 완전히 격리 차단되었으며 Nginx 단일 프록시 인그레스만 뚫려 있는지 자동 보안 진단하는 포트 스캐너입니다. | **PowerShell**:<br>`.\scripts\run_port_scan.ps1`<br>**Bash**:<br>`./scripts/run_port_scan.sh` | **필수** |
| **10. test_hot_reload**<br>`test_hot_reload.ps1`<br>`test_hot_reload.sh` | Docker Compose 볼륨 마운트 개발 환경에서 소스 코드 변경 시 실시간으로 컨테이너 내부 가상환경에 동기화 및 핫 리로딩이 일어나는지 임시 주석을 자동 삽입/회수하며 감시하는 유틸리티입니다. | **PowerShell**:<br>`.\scripts\test_hot_reload.ps1`<br>**Bash**:<br>`./scripts/test_hot_reload.sh` | **필수** |

---

## 🛡️ 개발 지침 및 주의 사항
1. **대칭성 유지**: 이 폴더 내부의 스크립트를 추가하거나 수정할 때는 반드시 Windows용 PowerShell(`.ps1`)과 macOS/Linux용 Bash(`.sh`) 두 버전을 한 쌍으로 동등하게 구현 및 수정해야 합니다.
2. **패스워드 하드코딩 금지**: 스크립트 내부에서 DB나 외부 API 연동이 필요할 시, 절대로 비밀번호나 인증키를 소스 내에 노출하지 않고 `.env` 파일의 쉘 환경 변수 주입 방식으로 작동하도록 구현해야 합니다.
3. **독립 배치 규정**: 로컬 개발 제어, 빌드, RDBMS, 마이그레이션, 테스트 등 프로젝트의 빌드/운영과 관련된 모든 커스텀 자동화 도구 파일들은 이 `scripts/` 폴더 하위에 격리 배치하며, `.specify/` 프레임워크 코어 폴더에 침범하지 않도록 주의하십시오.
