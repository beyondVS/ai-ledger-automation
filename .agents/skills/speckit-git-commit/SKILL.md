---
name: speckit-git-commit
description: Spec Kit 명령 완료 후 변경 사항을 자동으로 커밋합니다.
compatibility: Requires spec-kit project structure with .specify/ directory
metadata:
  author: github-spec-kit
  source: git:commands/speckit.git.commit.md
---

# 변경 사항 자동 커밋 (Auto-Commit Changes)

Spec Kit 명령어가 완료된 후 모든 변경 사항을 자동으로 스테이징하고 커밋합니다.

## 동작 방식 (Behavior)

이 명령은 핵심 명령어 실행 전후에 훅(hook)으로 호출됩니다:

1. 훅 컨텍스트로부터 이벤트 이름을 확인합니다 (예: `after_specify` 훅으로 호출된 경우 이벤트명은 `after_specify`이고, `before_plan` 훅으로 호출된 경우 이벤트명은 `before_plan`이 됩니다).
2. `.specify/extensions/git/git-config.yml` 파일에서 `auto_commit` 섹션을 확인합니다.
3. 특정 이벤트 키를 찾아 자동 커밋이 활성화(enabled)되어 있는지 확인합니다.
4. 이벤트별 전용 키가 없는 경우 `auto_commit.default` 설정으로 대체합니다.
5. 설정에 명시된 명령어별 `message`가 있으면 사용하고, 그렇지 않으면 기본 메시지를 사용합니다.
6. 활성화되어 있고 커밋되지 않은 변경 사항이 있는 경우 `git add .` 및 `git commit`을 실행합니다.

## 실행 (Execution)

이 명령을 트리거한 훅으로부터 이벤트 이름을 확인한 다음 스크립트를 실행합니다:

- **Bash**: `.specify/extensions/git/scripts/bash/auto-commit.sh <event_name>`
- **PowerShell**: `.specify/extensions/git/scripts/powershell/auto-commit.ps1 <event_name>`

`<event_name>`을 실제 훅 이벤트명(예: `after_specify`, `before_plan`, `after_implement` 등)으로 대체하십시오.

## 설정 (Configuration)

`.specify/extensions/git/git-config.yml` 파일에서 설정 가능합니다:

```yaml
auto_commit:
  default: false          # 글로벌 설정 — 모든 명령에 대해 자동 커밋을 켜려면 true로 설정하십시오.
  after_specify:
    enabled: true          # 명령어별 개별 오버라이드
    message: "[Spec Kit] Add specification"
  after_plan:
    enabled: false
    message: "[Spec Kit] Add implementation plan"
```

## 점진적 기능 저하 (Graceful Degradation)

- Git을 사용할 수 없거나 현재 디렉토리가 저장소가 아닌 경우: 경고와 함께 스킵합니다.
- 설정 파일이 존재하지 않는 경우: 스킵합니다 (기본적으로 비활성화됨).
- 커밋할 변경 사항이 없는 경우: 메시지와 함께 스킵합니다.