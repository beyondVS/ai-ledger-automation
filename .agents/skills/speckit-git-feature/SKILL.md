---
name: speckit-git-feature
description: 순차 번호 또는 타임스탬프가 포함된 피처(feature) 브랜치를 생성합니다.
compatibility: Requires spec-kit project structure with .specify/ directory
metadata:
  author: github-spec-kit
  source: git:commands/speckit.git.feature.md
---

# 피처 브랜치 생성 (Create Feature Branch)

지정된 스펙(specification)에 맞는 새로운 git 피처 브랜치를 생성하고 해당 브랜치로 전환합니다. 이 명령어는 **브랜치 생성만** 처리하며, 스펙 디렉토리와 파일은 코어 `/speckit-specify` 워크플로우에 의해 생성됩니다.

## 사용자 입력 (User Input)

```text
$ARGUMENTS
```

사용자 입력이 비어 있지 않다면 진행하기 전에 **반드시** 이를 고려해야 합니다.

## 환경 변수 오버라이드 (Environment Variable Override)

사용자가 명시적으로 `GIT_BRANCH_NAME`을 제공한 경우(예: 환경 변수, 인자, 또는 요청을 통해), 스크립트를 호출하기 전에 `GIT_BRANCH_NAME` 환경 변수를 설정하여 스크립트로 전달하십시오. `GIT_BRANCH_NAME`이 설정되면:
- 스크립트는 접두사/접미사 생성 단계를 건너뛰고 해당 값을 그대로 브랜치 이름으로 사용합니다.
- `--short-name`, `--number`, `--timestamp` 플래그는 무시됩니다.
- 이름이 숫자 접두사로 시작하는 경우 브랜치 명에서 `FEATURE_NUM`을 추출하며, 그렇지 않으면 전체 브랜치 이름으로 설정됩니다.

## 사전 요구사항 (Prerequisites)

- `git rev-parse --is-inside-work-tree 2>/dev/null`을 실행하여 Git을 사용할 수 있는지 확인합니다.
- Git을 사용할 수 없는 경우, 사용자에게 경고하고 브랜치 생성을 스킵합니다.

## 브랜치 번호 부여 모드 (Branch Numbering Mode)

다음 순서대로 설정을 확인하여 브랜치 번호 부여 전략을 결정합니다:

1. `.specify/extensions/git/git-config.yml` 파일에서 `branch_numbering` 값을 확인합니다.
2. `.specify/init-options.json` 파일에서 `branch_numbering` 값을 확인합니다 (하위 호환성용).
3. 두 설정 모두 존재하지 않는 경우 기본값은 `sequential`입니다.

## 실행 (Execution)

브랜치에 사용할 간결한 단축 이름(2~4 단어)을 생성합니다:
- 피처 설명을 분석하여 가장 의미 있는 키워드를 추출합니다.
- 가능하면 동사-명사 형식을 사용합니다 (예: "add-user-auth", "fix-payment-bug").
- 기술 용어 및 약어(OAuth2, API, JWT 등)는 그대로 보존합니다.

플랫폼에 맞는 적절한 스크립트를 실행합니다:

- **Bash**: `.specify/extensions/git/scripts/bash/create-new-feature.sh --json --short-name "<short-name>" "<feature description>"`
- **Bash (타임스탬프)**: `.specify/extensions/git/scripts/bash/create-new-feature.sh --json --timestamp --short-name "<short-name>" "<feature description>"`
- **PowerShell**: `.specify/extensions/git/scripts/powershell/create-new-feature.ps1 -Json -ShortName "<short-name>" "<feature description>"`
- **PowerShell (타임스탬프)**: `.specify/extensions/git/scripts/powershell/create-new-feature.ps1 -Json -Timestamp -ShortName "<short-name>" "<feature description>"`

**중요**:
- `--number` 플래그는 전달하지 **마십시오**. 스크립트가 자동으로 올바른 다음 번호를 판단합니다.
- 출력 결과를 안정적으로 파싱할 수 있도록 항상 JSON 플래그(Bash는 `--json`, PowerShell은 `-Json`)를 포함하십시오.
- 이 스크립트는 피처당 단 한 번만 실행해야 합니다.
- JSON 출력 결과에는 `BRANCH_NAME`과 `FEATURE_NUM`이 포함됩니다.

## 점진적 기능 저하 (Graceful Degradation)

Git이 설치되어 있지 않거나 현재 디렉토리가 Git 저장소가 아닌 경우:
- 브랜치 생성을 생략하고 경고를 출력합니다: `[specify] Warning: Git repository not detected; skipped branch creation`
- 호출자가 참조할 수 있도록 스크립트는 여전히 `BRANCH_NAME` 및 `FEATURE_NUM`을 출력합니다.

## 출력 (Output)

스크립트는 다음과 같은 JSON을 출력합니다:
- `BRANCH_NAME`: 브랜치 이름 (예: `003-user-auth` 또는 `20260319-143022-user-auth`)
- `FEATURE_NUM`: 사용된 숫자 또는 타임스탬프 접두사