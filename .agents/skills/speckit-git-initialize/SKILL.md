---
name: speckit-git-initialize
description: 첫 번째 커밋과 함께 Git 저장소를 초기화합니다.
compatibility: Requires spec-kit project structure with .specify/ directory
metadata:
  author: github-spec-kit
  source: git:commands/speckit.git.initialize.md
---

# Git 저장소 초기화 (Initialize Git Repository)

현재 프로젝트 디렉토리에 Git 저장소가 아직 없는 경우 초기화합니다.

## 실행 (Execution)

프로젝트 루트에서 해당 플랫폼에 맞는 스크립트를 실행합니다:

- **Bash**: `.specify/extensions/git/scripts/bash/initialize-repo.sh`
- **PowerShell**: `.specify/extensions/git/scripts/powershell/initialize-repo.ps1`

확장 스크립트 파일들을 찾을 수 없는 경우, 다음 기본 명령으로 대체하여 실행하십시오:
- **Bash**: `git init && git add . && git commit -m "Initial commit from Specify template"`
- **PowerShell**: `git init; git add .; git commit -m "Initial commit from Specify template"`

스크립트는 모든 검사 과정을 내부적으로 처리합니다:
- Git을 사용할 수 없는 경우 스킵
- 이미 Git 저장소 내부인 경우 스킵
- `git init`, `git add .`, `git commit`을 실행하고 초기 커밋 메시지를 작성합니다.

## 사용자 정의 (Customization)

프로젝트에 특화된 Git 초기화 단계를 추가하려면 스크립트를 다음과 같이 커스텀화하십시오:
- 커스텀 `.gitignore` 템플릿 추가
- 기본 브랜치 이름 설정 (`git config init.defaultBranch`)
- Git LFS 설정
- Git 훅(hooks) 설치
- 커밋 서명(signing) 설정
- Git Flow 초기화

## 출력 (Output)

성공 시:
- `✓ Git repository initialized`

## 점진적 기능 저하 (Graceful Degradation)

Git이 설치되어 있지 않은 경우:
- 사용자에게 경고를 보냅니다.
- 저장소 초기화를 건너뜁니다.
- 프로젝트는 Git 없이도 계속 정상 작동합니다 (스펙은 여전히 `specs/` 하위에 생성될 수 있습니다).

Git이 설치되어 있지만 `git init`, `git add .` 또는 `git commit`이 실패한 경우:
- 사용자에게 에러를 표시합니다.
- 부분적으로 초기화된 불안정한 저장소로 계속 진행하는 대신 이 명령을 중단합니다.