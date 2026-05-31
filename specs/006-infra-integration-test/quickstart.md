# Quickstart Guide: 1주차 인프라 중간 점검 및 로컬 통합 테스트 수행 (Infra Integration Test)

본 문서는 Windows PowerShell 및 UNIX/macOS Bash 양대 환경에서 단 한 줄의 명령어로 로컬 통합 테스트 환경(PostgreSQL 18)을 멱등 기동하고, PDF 무손실 적재 흐름의 정합성을 원터치로 최종 기계 검증하는 방법을 안내합니다.

---

## 1. 사전 요구사항 점검

이 통합 테스트는 실제 도커 컨테이너를 동적으로 가동하고 소멸시키므로 아래 환경이 설치 및 활성화되어 있어야 합니다.

1.  **Docker Desktop** 또는 **Docker Daemon**이 기동되어 있어야 합니다.
2.  **uv** 패키지 관리자가 설치되어 로컬 가상환경(`.venv`)이 동기화되어 있어야 합니다.
    *   *(미동기화 시 `uv sync`를 루트에서 실행하십시오.)*

---

## 2. 원클릭 통합 검증 CLI 가동법

헌법 제VI조(크로스 플랫폼 대칭 툴링)에 의거하여, 개발자는 자신의 로컬 운영체제 대역에 맞춰 아래 명령을 프로젝트 루트 디렉토리에서 즉시 실행합니다.

### 2.1 **Windows 환경 (PowerShell 5.1+)**

파워쉘 터미널을 열고 아래 명령을 실행합니다.

```powershell
# 1. 스크립트 실행 권한 승인 (필요 시)
Set-ExecutionPolicy Bypass -Scope Process -Force

# 2. 통합 검증 원클릭 실행
.\scripts\run-pdf-tests.ps1
```

### 2.2 **macOS / Linux / WSL 환경 (Bash)**

배시 터미널을 열고 아래 명령을 실행합니다.

```bash
# 1. 스크립트 실행 권한 부여
chmod +x ./scripts/run-pdf-tests.sh

# 2. 통합 검증 원클릭 실행
./scripts/run-pdf-tests.sh
```

---

## 3. 원클릭 스크립트 내부 동작 프로세스 요약

스크립트는 수동 개입 없이 다음 과정을 **100% 전자동**으로 제어 및 격리 소멸을 완수합니다.

1.  **DB 인프라 기동**: 격리된 테스트 전용 `ledgerdb-test` 도커 컨테이너를 백그라운드 기동합니다.
2.  **포트 가용 대조**: DB 포트(`54321`)가 완전히 활성화되어 응답할 때까지 안전하게 대기(Health Check)합니다.
3.  **마이그레이션**: Django ORM의 마이그레이션 도구를 자동 연동 기동하여 데이터 스키마 테이블 구조를 멱등 구축합니다.
4.  **테스트 러너 구동**: pytest 실행기를 연동하여 `TestPDFIntegrationSuite` 등 총 14개 단위/통합 테스트를 가동합니다.
5.  **격리 리소스 회수 (Cleanup)**: 테스트 패스/실패 여부와 무관하게, 종료 즉시 테스트 전용 컨테이너와 데이터 볼륨을 완벽하게 삭제(`docker compose down -v`)하여 로컬 시스템 자원을 깨끗이 청소하고 멱등성을 수호합니다.
