---
name: "speckit-implement"
description: "tasks.md에 정의된 모든 태스크를 처리 및 실행하여 구현 계획을 실제로 실행합니다."
compatibility: "프로젝트 루트에 .specify/ 디렉토리가 있는 spec-kit 프로젝트 구조가 필요합니다."
metadata:
  author: "github-spec-kit"
  source: "templates/commands/implement.md"
---


## 사용자 입력

```text
$ARGUMENTS
```

진행하기 전에 사용자 입력이 비어있지 않다면 **반드시** 고려해야 합니다.

## 실행 전 확인 사항

**확장 기능 훅 확인 (구현 작업 시작 전)**:
- 프로젝트 루트에 `.specify/extensions.yml`이 존재하는지 확인합니다.
- 존재할 경우, 파일을 읽고 `hooks.before_implement` 키 아래의 항목들을 찾습니다.
- YAML 파싱이 불가능하거나 유효하지 않은 경우, 훅 확인을 자동으로 건너뛰고 정상적으로 진행합니다.
- `enabled`가 명시적으로 `false`인 훅은 제외합니다. `enabled` 필드가 없는 훅은 기본적으로 활성화된 것으로 간주합니다.
- 남은 훅들에 대해, 훅의 `condition` 표현식을 해석하거나 평가하려고 시도하지 **마십시오**:
  - 훅에 `condition` 필드가 없거나 비어있는(null/empty) 경우, 실행 가능한 훅으로 처리합니다.
  - 훅에 비어있지 않은 `condition`이 정의되어 있다면, 훅 실행을 건너뛰고 조건 평가를 HookExecutor 구현체에 위임합니다.
- 실행 가능한 각 훅에 대해 `optional` 플래그를 기준으로 아래 내용을 출력합니다:
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
- 등록된 훅이 없거나 `.specify/extensions.yml`이 존재하지 않는 경우 자동으로 건너뜁니다.

## 개요

1. 저장소 루트에서 `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks`를 실행하여 FEATURE_DIR과 AVAILABLE_DOCS 목록을 파싱합니다. 모든 경로는 절대 경로여야 합니다. "I'm Groot"와 같이 인자 값에 단일 인용부호가 들어가는 경우 이스케이프 구문을 사용합니다: 예: 'I'\''m Groot' (또는 가급적 큰따옴표 사용: "I'm Groot").

2. **품질 체크리스트 완료 상태 확인** (FEATURE_DIR/checklists/ 폴더가 존재하는 경우):
   - checklists/ 디렉토리 내의 모든 체크리스트 파일들을 스캔합니다.
   - 각 체크리스트 문서에 대해 다음 항목들을 집계합니다:
     - 총 항목수: `- [ ]` 또는 `- [X]` 또는 `- [x]` 마크가 포함된 모든 라인 수
     - 완료 항목수: `- [X]` 또는 `- [x]` 마크가 포함된 라인 수
     - 미완료 항목수: `- [ ]` 마크가 포함된 라인 수
   - 다음과 같이 상태 테이블을 생성합니다:

     ```text
     | 체크리스트 파일 | 총 항목수 | 완료 | 미완료 | 상태 |
     |-----------------|----------|------|--------|------|
     | ux.md           | 12       | 12   | 0      | ✓ PASS |
     | test.md         | 8        | 5    | 3      | ✗ FAIL |
     | security.md     | 6        | 6    | 0      | ✓ PASS |
     ```

   - 전체 종합 상태를 평가합니다:
     - **PASS**: 모든 체크리스트 문서에 미완료(`- [ ]`) 항목이 0개인 경우
     - **FAIL**: 하나 이상의 체크리스트 문서에 미완료 항목이 남아있는 경우

   - **하나라도 미완료된 체크리스트가 있는 경우**:
     - 미완료 항목 개수가 표시된 상기 테이블을 출력합니다.
     - **중단** 후 사용자에게 질문을 던집니다: "일부 체크리스트가 미완료 상태입니다. 그럼에도 구현을 계속 진행하시겠습니까? (yes/no)"
     - 사용자의 피드백 수신 시까지 대기합니다.
     - 사용자가 "no" 또는 "wait" 또는 "stop"이라고 답변하면 실행을 보류 및 중단합니다.
     - 사용자가 "yes" 또는 "proceed" 또는 "continue"라고 답변하면 3단계로 이동하여 진행합니다.

   - **모든 체크리스트가 완료 상태인 경우**:
     - 모든 체크리스트 통과 테이블을 출력합니다.
     - 자동으로 3단계로 이동하여 진행합니다.

3. 구현에 필요한 컨텍스트를 로드하고 분석합니다:
   - **필수**: tasks.md를 읽어 전체 태스크 목록 및 실행 계획 파악
   - **필수**: plan.md를 읽어 기술 스택, 아키텍처 및 폴더 디렉토리 구조 파악
   - **존재하는 경우**: data-model.md를 읽어 데이터 엔티티와 관계 파악
   - **존재하는 경우**: contracts/를 읽어 API 명세 및 테스트 검증 요건 파악
   - **존재하는 경우**: research.md를 읽어 결정된 기술 사양 및 제약 사항 파악
   - **존재하는 경우**: .specify/memory/constitution.md를 읽어 프로젝트 핵심 원칙 및 제약 파악
   - **존재하는 경우**: quickstart.md를 읽어 통합 시나리오 파악

4. **프로젝트 환경 설정 검증**:
   - **필수**: 실제 프로젝트 셋업에 맞춰 제외 파일들(ignore files)을 생성 또는 검증합니다:

    **감지 및 생성 로직**:
    - 저장소가 실제 git 저장소인지 감지하기 위해 아래의 명령이 정상적으로 작동하는지 확인합니다 (성공 시 .gitignore 파일 생성 및 검증):

      ```sh
      git rev-parse --git-dir 2>/dev/null
      ```

    - Dockerfile*이 존재하거나 plan.md에 Docker 관련 요건이 있는 경우 → .dockerignore 생성/검증
    - .eslintrc*가 존재하는 경우 → .eslintignore 생성/검증
    - eslint.config.*가 존재하는 경우 → 해당 설정의 `ignores` 항목에 필요한 제외 패턴이 누락 없이 설정되어 있는지 검증
    - .prettierrc*가 존재하는 경우 → .prettierignore 생성/검증
    - .npmrc 또는 package.json이 존재하는 경우 → .npmignore 생성/검증 (배포용 빌드일 때)
    - 테라폼 파일(*.tf)이 존재하는 경우 → .terraformignore 생성/검증
    - Helm 차트 파일들이 존재해 .helmignore가 필요한 경우 → .helmignore 생성/검증

    **제외 파일이 이미 존재하는 경우**: 필수 제외 패턴이 정상적으로 들어있는지 검증하고, 누락된 핵심 패턴만 뒤에 덧붙여서 보완합니다.
    **제외 파일이 없는 경우**: 감지된 해당 기술 환경에 대한 완벽한 제외 패턴 모음을 포함해 새로 파일을 생성합니다.

    **기술 스택별 일반 제외 패턴** (plan.md의 기술 스택 기준):
    - **Node.js/JavaScript/TypeScript**: `node_modules/`, `dist/`, `build/`, `*.log`, `.env*`
    - **Python**: `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `dist/`, `*.egg-info/`
    - **Java**: `target/`, `*.class`, `*.jar`, `.gradle/`, `build/`
    - **C#/.NET**: `bin/`, `obj/`, `*.user`, `*.suo`, `packages/`
    - **Go**: `*.exe`, `*.test`, `vendor/`, `*.out`
    - **Ruby**: `.bundle/`, `log/`, `tmp/`, `*.gem`, `vendor/bundle/`
    - **PHP**: `vendor/`, `*.log`, `*.cache`, `*.env`
    - **Rust**: `target/`, `debug/`, `release/`, `*.rs.bk`, `*.rlib`, `*.prof*`, `.idea/`, `*.log`, `.env*`
    - **Kotlin**: `build/`, `out/`, `.gradle/`, `.idea/`, `*.class`, `*.jar`, `*.iml`, `*.log`, `.env*`
    - **C++**: `build/`, `bin/`, `obj/`, `out/`, `*.o`, `*.so`, `*.a`, `*.exe`, `*.dll`, `.idea/`, `*.log`, `.env*`
    - **C**: `build/`, `bin/`, `obj/`, `out/`, `*.o`, `*.a`, `*.so`, `*.exe`, `*.dll`, `autom4te.cache/`, `config.status`, `config.log`, `.idea/`, `*.log`, `.env*`
    - **Swift**: `.build/`, `DerivedData/`, `*.swiftpm/`, `Packages/`
    - **R**: `.Rproj.user/`, `.Rhistory`, `.RData`, `.Ruserdata`, `*.Rproj`, `packrat/`, `renv/`
    - **범용 공통**: `.DS_Store`, `Thumbs.db`, `*.tmp`, `*.swp`, `.vscode/`, `.idea/`

    **도구별 제외 패턴**:
    - **Docker**: `node_modules/`, `.git/`, `Dockerfile*`, `.dockerignore`, `*.log*`, `.env*`, `coverage/`
    - **ESLint**: `node_modules/`, `dist/`, `build/`, `coverage/`, `*.min.js`
    - **Prettier**: `node_modules/`, `dist/`, `build/`, `coverage/`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`
    - **Terraform**: `.terraform/`, `*.tfstate*`, `*.tfvars`, `.terraform.lock.hcl`
    - **Kubernetes/k8s**: `*.secret.yaml`, `secrets/`, `.kube/`, `kubeconfig*`, `*.key`, `*.crt`

5. tasks.md 구조를 파싱하여 다음 요소를 식별 및 추출합니다:
   - **태스크 페이즈**: Setup, Tests, Core, Integration, Polish
   - **태스크 의존 관계**: 순차 실행 구간과 병렬[P] 실행 규칙 구분
   - **상세 태스크**: ID, 설명, 목적지 소스 파일 경로, 병렬 처리 마커 [P]
   - **실행 논리적 흐름**: 작업 실행 순서 및 선행조건 의존성 조건 확인

6. 설계된 태스크 계획에 맞춰 점진적으로 구현을 수행합니다:
   - **페이즈별 실행**: 이전 페이즈가 완전히 성공 및 완료되어야 다음 페이즈로 이동할 수 있습니다.
   - **의존성 준수**: 순차 태스크는 명시된 순서대로 하나씩 구현하고, 병렬 태스크[P]는 동시에 함께 병렬 개발을 수행할 수 있습니다.
   - **TDD 사양 준수**: TDD가 활성화되어 있는 경우, 반드시 기능 구현 소스 수정 작업 전에 매핑되는 테스트 코드 구현 태스크를 먼저 수행 완료해야 합니다.
   - **동일 파일 충돌 회피**: 동일한 파일을 수정하는 복수의 태스크들은 무조건 순차적으로 하나씩 수행해야 합니다.
   - **검증 체크포인트**: 각 페이즈가 완료될 때마다 명시된 테스트나 빌드를 실행하여 정상 완료를 검증하고 넘어갑니다.

7. 구현 작업 실행 원칙:
   - **Setup 우선**: 프로젝트 폴더 구조, 필요한 패키지 종속성, 기본 설정을 가장 먼저 끝마칩니다.
   - **테스트 선작성**: API 계약, 엔티티 검증 및 데이터 통합 시나리오에 필요한 테스트 케이스들을 먼저 코딩합니다 (요청 시).
   - **핵심 개발**: 데이터 모델, 핵심 비즈니스 로직 서비스, CLI 명령 핸들러, 라우터 엔드포인트 등을 확실하게 구현합니다.
   - **통합 설계**: 데이터베이스 연결 연동, 관련 미들웨어 장착, 시스템 로깅 구성, 외부 서비스 통신 로직 등을 붙입니다.
   - **마무리 조율**: 단위 테스트 최종 통과 검증, 성능 튜닝, 필수 사용자 안내 문서 보완 등을 마칩니다.

8. 진행 상태 추적 및 오류 해결:
   - 각 단일 태스크 완료 시마다 진행 경과를 명확히 사용자에게 보고합니다.
   - 순차 태스크가 하나라도 실패하는 경우, 전체 워크플로우를 중단합니다.
   - 병렬 태스크[P] 실행 중 일부 실패 발생 시, 성공한 태스크들은 계속 유지하되 실패한 태스크들의 내역과 실패 원인 로그를 명시해 보고합니다.
   - 디버깅을 돕기 위해 오류 컨텍스트가 포함된 직관적인 에러 피드백을 제시합니다.
   - 정상 진행이 어려운 장벽을 만났을 경우, 사용자가 취할 수 있는 현실적인 우회/보완 단계를 제안합니다.
   - **[매우 중요]** 완료한 태스크들에 대해서는 반드시 태스크 파일(`tasks.md`) 내의 마크를 `- [ ]`에서 `- [X]`로 안전하게 교체하여 완료 상태를 갱신해 두어야 합니다.

9. 완결성 검증:
   - Verify all required tasks are completed
   - Check that implemented features match the original specification
   - Validate that tests pass and coverage meets requirements
   - Confirm the implementation follows the technical plan
   - Report final status with summary of completed work

Note: This command assumes a complete task breakdown exists in tasks.md. If tasks are incomplete or missing, suggest running `/speckit-tasks` first to regenerate the task list.

10. **Check for extension hooks**: After completion validation, check if `.specify/extensions.yml` exists in the project root.
    - If it exists, read it and look for entries under the `hooks.after_implement` key
    - If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally
    - Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
    - For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
      - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
      - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation
    - For each executable hook, output the following based on its `optional` flag:
      - **Optional hook** (`optional: true`):
        ```
        ## Extension Hooks

        **Optional Hook**: {extension}
        Command: `/{command}`
        Description: {description}

        Prompt: {prompt}
        To execute: `/{command}`
        ```
      - **Mandatory hook** (`optional: false`):
        ```
        ## Extension Hooks

        **Automatic Hook**: {extension}
        Executing: `/{command}`
        EXECUTE_COMMAND: {command}
        ```
    - If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently
