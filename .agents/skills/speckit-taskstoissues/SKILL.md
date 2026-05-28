---
name: "speckit-taskstoissues"
description: "기존 작업을 설계 아티팩트를 기반으로 기능에 부합하며 종속성 순서대로 정렬된 GitHub 이슈로 변환합니다."
compatibility: "Requires spec-kit project structure with .specify/ directory"
metadata:
  author: "github-spec-kit"
  source: "templates/commands/taskstoissues.md"
---


## 사용자 입력 (User Input)

```text
$ARGUMENTS
```

사용자 입력이 비어 있지 않다면 진행하기 전에 **반드시** 이를 고려해야 합니다.

## 사전 실행 검사 (Pre-Execution Checks)

**확장 훅 검사 (작업-이슈 변환 전)**:
- 프로젝트 루트에 `.specify/extensions.yml` 파일이 존재하는지 확인합니다.
- 파일이 존재하면 읽어서 `hooks.before_taskstoissues` 키 아래의 항목을 찾습니다.
- YAML을 파싱할 수 없거나 유효하지 않은 경우, 훅 검사를 조용히 건너뛰고 정상적으로 계속 진행합니다.
- `enabled`가 명시적으로 `false`인 훅은 필터링하여 제외합니다. `enabled` 필드가 없는 훅은 기본적으로 활성화된 것으로 간주합니다.
- 남은 각 훅에 대해, 훅의 `condition` 표현식을 해석하거나 평가하려고 시도하지 **않습니다**:
  - 훅에 `condition` 필드가 없거나 null/비어 있는 경우, 해당 훅을 실행 가능한 것으로 간주합니다.
  - 훅이 비어 있지 않은 `condition`을 정의하는 경우, 해당 훅을 건너뛰고 조건 평가는 HookExecutor 구현에 위임합니다.
- 실행 가능한 각 훅에 대해 `optional` 플래그에 따라 다음을 출력합니다:
  - **선택적 훅 (Optional hook)** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Pre-Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **필수 훅 (Mandatory hook)** (`optional: false`):
    ```
    ## Extension Hooks

    **Automatic Pre-Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}

    Wait for the result of the hook command before proceeding to the Outline.
    ```
- 등록된 훅이 없거나 `.specify/extensions.yml` 파일이 존재하지 않는 경우 조용히 건너뜁니다.

## 개요 (Outline)

1. 저장소 루트에서 `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks`를 실행하고, FEATURE_DIR 및 AVAILABLE_DOCS 목록을 파싱합니다. 모든 경로는 절대 경로여야 합니다. 인자 값 내에 "I'm Groot"와 같은 싱글 쿼트(')가 포함된 경우 이스케이프 구문을 사용하십시오: 예: 'I'\''m Groot' (또는 가능하면 더블 쿼트 처리: "I'm Groot").
2. 실행된 스크립트 결과로부터 **작업(tasks)** 경로를 추출합니다.
3. 다음 명령어를 실행하여 Git 원격(remote) 정보를 가져옵니다:

```bash
git config --get remote.origin.url
```

> [!CAUTION]
> 원격 URL이 GITHUB URL인 경우에만 다음 단계로 진행하십시오.

4. 목록의 각 작업에 대해, GitHub MCP 서버를 사용하여 Git 원격 저장소에 대응하는 새로운 이슈를 생성합니다.

> [!CAUTION]
> 어떠한 상황에서도 원격 URL과 일치하지 않는 저장소에 이슈를 생성해서는 안 됩니다.

## 사후 실행 검사 (Post-Execution Checks)

**확장 훅 검사 (작업-이슈 변환 후)**:
프로젝트 루트에 `.specify/extensions.yml` 파일이 존재하는지 확인합니다.
- 파일이 존재하면 읽어서 `hooks.after_taskstoissues` 키 아래의 항목을 찾습니다.
- YAML을 파싱할 수 없거나 유효하지 않은 경우, 훅 검사를 조용히 건너뛰고 정상적으로 계속 진행합니다.
- `enabled`가 명시적으로 `false`인 훅은 필터링하여 제외합니다. `enabled` 필드가 없는 훅은 기본적으로 활성화된 것으로 간주합니다.
- 남은 각 훅에 대해, 훅의 `condition` 표현식을 해석하거나 평가하려고 시도하지 **않습니다**:
  - 훅에 `condition` 필드가 없거나 null/비어 있는 경우, 해당 훅을 실행 가능한 것으로 간주합니다.
  - 훅이 비어 있지 않은 `condition`을 정의하는 경우, 해당 훅을 건너뛰고 조건 평가는 HookExecutor 구현에 위임합니다.
- 실행 가능한 각 훅에 대해 `optional` 플래그에 따라 다음을 출력합니다:
  - **선택적 훅 (Optional hook)** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **필수 훅 (Mandatory hook)** (`optional: false`):
    ```
    ## Extension Hooks

    **Automatic Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}
    ```
- 등록된 훅이 없거나 `.specify/extensions.yml` 파일이 존재하지 않는 경우 조용히 건너뜁니다.
