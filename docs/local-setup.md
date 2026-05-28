# 로컬 개발 환경 구축 가이드: Docker Desktop & WSL 2 연동

본 문서는 **1일차 계획 (001-local-env-setup)**에 따른 데이터베이스 인프라 컨테이너 환경을 로컬 PC(Windows)에서 원활하게 구축하고 구동하기 위한 가이드라인입니다.

---

## 1. Docker Desktop & WSL 2 기본 연동

윈도우 환경에서 컨테이너 I/O 성능 극대화 및 파일 권한 충돌 차단을 위해 **WSL 2** 기반의 백엔드 연동을 반드시 설정해야 합니다.

1. **Docker Desktop 기동 및 설정 진입** (톱니바퀴 아이콘 클릭)
2. **General 탭**:
   * `Use the WSL 2 based engine (recommended)` 옵션이 **체크(Enable)** 되어 있는지 확인합니다.
3. **Resources > WSL Integration 탭**:
   * `Enable integration with my default WSL distro` 옵션을 **체크(Enable)** 합니다.
   * 연동해서 사용할 개별 WSL 배포판(예: Ubuntu 등)이 존재할 경우 토글 단추를 활성화합니다.
4. **Apply & Restart** 버튼을 클릭하여 도커 데몬을 다시 시작합니다.

---

## 2. Windows 드라이브 파일 권한 이슈 예방 및Named Volume 사용 권고

* **Windows NTFS와 Linux 간 권한 간극**: 
  * Windows 파일시스템(C드라이브 등)에 위치한 로컬 상대 경로 폴더(예: `./pgdata`)를 PostgreSQL 컨테이너에 직접 마운트하면, PostgreSQL이 부팅되면서 파일 소유권을 슈퍼유저(`postgres`)로 강제 전환(`chown`)하는 과정에서 Windows NTFS가 쓰기 거부/소유권 변경 차단으로 인해 `Permission Denied` 장해를 일으키고 기동이 중단되는 현상이 잦습니다.
* **해결책 (Named Volume)**: 
  * 이를 차단하기 위해 본 프로젝트는 `postgres_data`라는 도커 내장 **네임드 볼륨(Named Volume)**을 사용합니다.
  * 네임드 볼륨은 WSL 2 전용 가상 디스크 영역 내에서 구동되므로, 윈도우 호스트 권한과 물리적으로 완전 격리되어 에러 없이 기동됩니다.

---

## 3. Windows / PowerShell 원클릭 인프라 기동 워크플로우

Windows 환경(PowerShell 5.1+)을 사용하는 개발자는 통합 컨트롤러 스크립트(`scripts/manage-db.ps1`)를 활용하여 인프라를 구동합니다.

1. **환경 변수 파일 준비**:
   * 프로젝트 루트에 있는 `.env.local.example` 파일을 복사하여 `.env.local`을 만듭니다.
   ```powershell
   Copy-Item .env.local.example .env.local
   ```
2. **통합 기동 및 환경 검증**:
   * 단 1개의 통합 컨트롤러 스크립트(`scripts/manage-db.ps1`)를 구동하여 볼륨 확보, 인프라 부팅, 그리고 UTF-8 및 시간대 무결성 정합성 최종 검증까지 한 큐에 E2E 완수합니다.
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/manage-db.ps1
   ```
3. **인프라 자원 안전 회수 및 격리 폐기 (필요 시)**:
   * 로컬 개발을 완전히 중단하고 리소스를 원상 복구하려면 `-Cleanup` 옵션을 추가해 실행합니다.
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/manage-db.ps1 -Cleanup
   ```

---

## 4. macOS / Linux / WSL (Bash 쉘) 원클릭 인프라 기동 워크플로우

UNIX/Linux 계열 개발환경이나 Windows 내의 WSL(Windows Subsystem for Linux) 터미널 환경을 이용하는 경우, Bash 용 관리 스크립트(`scripts/manage-db.sh`)를 사용하여 기동을 완료합니다.

1. **환경 변수 파일 준비**:
   * 프로젝트 루트에 있는 `.env.local.example` 파일을 복사하여 `.env.local`을 만듭니다.
   ```bash
   cp .env.local.example .env.local
   ```
2. **통합 기동 및 환경 검증**:
   * 스크립트에 실행 권한을 부여한 후 구동하여 원클릭 E2E 기동을 완수합니다.
   ```bash
   chmod +x scripts/manage-db.sh
   ./scripts/manage-db.sh
   ```
3. **인프라 자원 안전 회수 및 격리 폐기 (필요 시)**:
   * 로컬 개발을 완전히 중단하고 볼륨까지 깔끔하게 소멸시켜 리소스를 회수하려면 `--cleanup` 옵션을 사용해 실행합니다.
   ```bash
   ./scripts/manage-db.sh --cleanup
   ```
