# Quickstart: Align Branch and Spec Numbering

본 피처는 실제 구동할 애플리케이션 코드가 존재하지 않으므로, 아래 형상 및 문서 구조 확인으로 퀵스타트를 갈음합니다.

## 확인 방법

1. 현재 Git 브랜치 확인:
   ```bash
   git branch
   ```
   출력 결과에 `013-align-branch-number` 브랜치가 선택되어 있는지 확인합니다.

2. 스펙 폴더 및 설정 확인:
   - `specs/013-align-branch-number/` 하위에 `spec.md` 및 `plan.md`가 존재하는지 확인합니다.
   - `.specify/feature.json`의 `feature_directory`가 `specs/013-align-branch-number`로 올바르게 갱신되어 있는지 확인합니다.
