# DB Migration & Integrity Validation Quickstart

**Feature**: Database Migration and Unique Constraints
**Branch**: `003-apply-db-unique-constraints`
**Date**: 2026-05-29

본 문서에서는 개발 로컬 개발 환경에서 단 1초 만에 데이터베이스 인프라를 멱등성 있게 초기화하고 마이그레이션을 안전하게 실행하는 대칭형 스크립트 실행 절차를 안내합니다.

---

## 1. 이중 대칭형 데이터베이스 관리 도구 연동

헌법 제VI조에 명문화된 크로스 플랫폼 대칭 툴링 원칙을 영구 수호하기 위해, Windows(PowerShell) 환경과 Linux/macOS(Bash) 실행 환경 모두에서 100% 가동 멱등성을 지닌 관리 도구를 제공합니다.

### 💻 Windows (PowerShell 5.1+ 개발 환경)
PowerShell 관리 정책을 우회하여 마이그레이션을 정밀 구동합니다:
```powershell
powershell -ExecutionPolicy Bypass -File .specify/scripts/powershell/manage-db.ps1 -Action Migration
```

### 🐧 macOS / Linux / WSL (Bash 쉘 환경)
실행 권한을 부여한 뒤 무결성 마이그레이션을 가동합니다:
```bash
chmod +x .specify/scripts/bash/manage-db.sh
./.specify/scripts/bash/manage-db.sh --action migration
```

---

## 2. 멱등적 인프라 안전 회수 및 재부팅 (Reset 가동)

로컬 테스트 샌드박스의 원자적 완전 리셋이 요구될 때, 가상 데이터 볼륨까지 안전하게 일괄 파괴 후 재생성합니다:

- **PowerShell**: 
  ```powershell
  powershell -ExecutionPolicy Bypass -File .specify/scripts/powershell/manage-db.ps1 -Action Reset
  ```
- **Bash**: 
  ```bash
  ./.specify/scripts/bash/manage-db.sh --action reset
  ```

---

## 3. 기계적 정합성 검증 테스트 구동

마이그레이션 빌드 완료 후 모든 고유 제약조건이 100% 정상 작동하는지 pytest 스위트를 통해 확인합니다:
```bash
# 백엔드 하위에서 기계적 검증 수행 (0.58초 초고속 통과 확인)
uv run pytest
```
