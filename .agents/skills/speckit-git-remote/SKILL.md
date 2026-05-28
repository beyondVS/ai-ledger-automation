---
name: speckit-git-remote
description: GitHub 연동을 위해 Git 원격(remote) URL을 감지합니다.
compatibility: Requires spec-kit project structure with .specify/ directory
metadata:
  author: github-spec-kit
  source: git:commands/speckit.git.remote.md
---

# Git 원격 URL 감지 (Detect Git Remote URL)

GitHub 서비스 연동(예: 이슈 생성 등)을 위해 Git 원격 저장소 URL을 감지합니다.

## 사전 요구사항 (Prerequisites)

- `git rev-parse --is-inside-work-tree 2>/dev/null`을 실행하여 Git을 사용할 수 있는지 확인합니다.
- Git을 사용할 수 없는 경우, 경고를 출력하고 빈 값을 반환합니다:
  ```
  [specify] Warning: Git repository not detected; cannot determine remote URL
  ```

## 실행 (Execution)

다음 명령어를 실행하여 원격 URL을 가져옵니다:

```bash
git config --get remote.origin.url
```

## 출력 (Output)

원격 URL을 파싱하여 다음 항목을 결정합니다:

1. **저장소 소유자 (Repository owner)**: URL에서 추출합니다 (예: `https://github.com/github/spec-kit.git`에서 `github` 추출)
2. **저장소 이름 (Repository name)**: URL에서 추출합니다 (예: `https://github.com/github/spec-kit.git`에서 `spec-kit` 추출)
3. **GitHub 여부 (Is GitHub)**: 원격지가 GitHub 저장소를 가리키는지 여부

지원되는 URL 형식:
- HTTPS: `https://github.com/<owner>/<repo>.git`
- SSH: `git@github.com:<owner>/<repo>.git`

> [!CAUTION]
> 원격 URL이 실제로 github.com을 가리키는 경우에만 GitHub 저장소로 보고하십시오.
> URL 형식이 일치하지 않는 경우 원격지가 GitHub라고 임의로 가정하지 마십시오.

## 점진적 기능 저하 (Graceful Degradation)

Git이 설치되어 있지 않거나, 현재 디렉토리가 Git 저장소가 아니거나, 원격지가 설정되지 않은 경우:
- 빈 결과를 반환합니다.
- 에러를 발생시키지 마십시오 — Git 원격 정보가 없어도 다른 워크플로우는 정상적으로 계속 진행되어야 합니다.