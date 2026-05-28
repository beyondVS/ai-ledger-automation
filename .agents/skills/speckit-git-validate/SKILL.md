---
name: speckit-git-validate
description: 현재 브랜치가 피처 브랜치 명명 규칙을 준수하는지 검증합니다.
compatibility: Requires spec-kit project structure with .specify/ directory
metadata:
  author: github-spec-kit
  source: git:commands/speckit.git.validate.md
---

# 피처 브랜치 검증 (Validate Feature Branch)

현재 Git 브랜치가 기대하는 피처 브랜치 명명 규칙을 따르는지 검증합니다.

## 사전 요구사항 (Prerequisites)

- `git rev-parse --is-inside-work-tree 2>/dev/null`을 실행하여 Git을 사용할 수 있는지 확인합니다.
- Git을 사용할 수 없는 경우, 경고를 출력하고 검증을 스킵합니다:
  ```
  [specify] Warning: Git repository not detected; skipped branch validation
  ```

## 검증 규칙 (Validation Rules)

현재 브랜치 이름을 확인합니다:

```bash
git rev-parse --abbrev-ref HEAD
```

브랜치 이름은 반드시 다음 패턴 중 하나와 일치해야 합니다:

1. **순차 번호 (Sequential)**: `^[0-9]{3,}-` (예: `001-feature-name`, `042-fix-bug`, `1000-big-feature`)
2. **타임스탬프 (Timestamp)**: `^[0-9]{8}-[0-9]{6}-` (예: `20260319-143022-feature-name`)

## 실행 (Execution)

피처 브랜치에 있는 경우 (두 패턴 중 하나에 일치하는 경우):
- 출력: `✓ On feature branch: <branch-name>`
- `specs/` 디렉토리 하위에 대응하는 스펙 디렉토리가 존재하는지 확인합니다:
  - 순차 번호 브랜치의 경우, 숫자로 이루어진 접두사와 일치하는 `specs/<prefix>-*` 디렉토리를 탐색합니다.
  - 타임스탬프 브랜치의 경우, `YYYYMMDD-HHMMSS` 형식의 접두사와 일치하는 `specs/<prefix>-*` 디렉토리를 탐색합니다.
- 스펙 디렉토리가 존재하는 경우: `✓ Spec directory found: <path>`
- 스펙 디렉토리가 누락된 경우: `⚠ No spec directory found for prefix <prefix>`

피처 브랜치에 있지 않은 경우:
- 출력: `✗ Not on a feature branch. Current branch: <branch-name>`
- 출력: `Feature branches should be named like: 001-feature-name or 20260319-143022-feature-name`

## 점진적 기능 저하 (Graceful Degradation)

Git이 설치되어 있지 않거나 현재 디렉토리가 Git 저장소가 아닌 경우:
- 대체 수단으로 `SPECIFY_FEATURE` 환경 변수를 검사합니다.
- 환경 변수가 설정된 경우, 해당 값을 명명 패턴에 따라 검증합니다.
- 환경 변수가 설정되어 있지 않은 경우, 경고와 함께 검증을 스킵합니다.