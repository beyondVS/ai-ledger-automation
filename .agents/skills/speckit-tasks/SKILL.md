---
name: "speckit-tasks"
description: "사용 가능한 설계 결과물들을 바탕으로 기능 구현에 대한 독립적 실행 및 의존성 정렬이 포함된 태스크 목록(tasks.md)을 생성합니다."
compatibility: "프로젝트 루트에 .specify/ 디렉토리가 있는 spec-kit 프로젝트 구조가 필요합니다."
metadata:
  author: "github-spec-kit"
  source: "templates/commands/tasks.md"
---


## 사용자 입력

```text
$ARGUMENTS
```

진행하기 전에 사용자 입력이 비어있지 않다면 **반드시** 고려해야 합니다.

## 실행 전 확인 사항

**확장 기능 훅 확인 (태스크 생성 전)**:
- 프로젝트 루트에 `.specify/extensions.yml`이 존재하는지 확인합니다.
- 존재할 경우, 파일을 읽고 `hooks.before_tasks` 키 아래의 항목들을 찾습니다.
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

1. **설정(Setup)**: 저장소 루트에서 `.specify/scripts/powershell/setup-tasks.ps1 -Json`을 실행하고 JSON 결과에서 FEATURE_DIR, TASKS_TEMPLATE, 그리고 AVAILABLE_DOCS 목록을 파싱합니다. `FEATURE_DIR`과 `TASKS_TEMPLATE`은 제공될 때 반드시 절대 경로여야 합니다. `AVAILABLE_DOCS`는 `FEATURE_DIR` 하위에 위치하는 사용 가능한 문서 명칭/상대 경로 목록(예: `research.md` 또는 `contracts/`)입니다. "I'm Groot"와 같이 인자 값에 단일 인용부호가 들어가는 경우 이스케이프 구문을 사용합니다: 예: 'I'\''m Groot' (또는 가급적 큰따옴표 사용: "I'm Groot").

2. **설계 문서 로드**: FEATURE_DIR에서 문서를 읽습니다:
   - **필수**: plan.md (기술 스택, 라이브러리, 프로젝트 구조), spec.md (우선순위가 표시된 사용자 스토리)
   - **선택**: data-model.md (엔티티 명세), contracts/ (인터페이스 계약), research.md (결정 사항), quickstart.md (테스트 시나리오)
   - 참고: 모든 프로젝트에 이 모든 문서들이 존재하는 것은 아닙니다. 존재하는 문서들만을 기반으로 태스크를 생성하십시오.

3. **태스크 생성 워크플로우 실행**:
   - plan.md를 로드하여 기술 스택, 사용 라이브러리, 프로젝트 디렉토리 구조를 추출합니다.
   - spec.md를 로드하여 사용자 스토리와 각 우선순위(P1, P2, P3 등)를 추출합니다.
   - data-model.md가 존재하는 경우: 엔티티 구조를 추출하여 연관된 사용자 스토리에 매핑합니다.
   - contracts/가 존재하는 경우: 인터페이스 계약 정보를 연관된 사용자 스토리에 매핑합니다.
   - research.md가 존재하는 경우: 초기 셋업 태스크에 반영할 결정사항들을 추출합니다.
   - 각 사용자 스토리별로 그룹화된 구현 태스크를 생성합니다 (아래 '태스크 생성 규칙' 참조).
   - 사용자 스토리 간 완성 순서를 나타내는 의존성 그래프를 생성합니다.
   - 사용자 스토리별 병렬 실행 구조 예시를 설계합니다.
   - 태스크 완결성을 검증합니다 (각 사용자 스토리가 구현에 필요한 모든 독립 검증 가능한 태스크를 누락 없이 가지고 있는지 확인).

4. **tasks.md 생성**: TASKS_TEMPLATE(위의 JSON 출력 결과값)에서 지정한 태스크 템플릿 파일을 읽고 해당 포맷을 구조로 삼아 작성합니다. 만약 TASKS_TEMPLATE이 비어있는 경우 `.specify/templates/tasks-template.md`를 사용합니다. 템플릿 내에 다음 정보를 작성합니다:
   - plan.md에서 가져온 올바른 피처 명칭
   - Phase 1: 셋업 태스크 (프로젝트 초기화 및 구성)
   - Phase 2: 기반 마련 태스크 (모든 사용자 스토리의 기반이 되는 전제조건 및 블로킹 태스크)
   - Phase 3 이상: 각 사용자 스토리당 하나의 페이즈 할당 (spec.md의 우선순위 정렬 기준)
   - 각 페이즈 정보: 스토리 목표, 독립적인 테스트 기준, 테스트 명세(요청된 경우), 세부 구현 태스크
   - Final Phase: 마무리 조율 및 횡단 관심사(Polish & cross-cutting concerns) 처리
   - 모든 태스크는 엄격한 체크리스트 포맷을 준수해야 합니다 (아래 '태스크 생성 규칙' 참조).
   - 각 태스크에 구체적이고 명확한 소스 파일 경로를 명시합니다.
   - 스토리 완성 순서를 다이어그램으로 보여주는 의존성(Dependencies) 섹션을 작성합니다.
   - 스토리별 병렬 실행 구조 예시를 제공합니다.
   - 구현 전략(MVP 최우선, 점진적 인도 방식)을 설계하여 명시합니다.

5. **보고(Report)**: 생성된 tasks.md의 경로 및 요약 정보를 출력합니다:
   - 총 태스크 개수
   - 사용자 스토리별 태스크 수
   - 병렬 처리가 가능한 작업 구간 식별 내역
   - 스토리별 독립적 테스트/검증 기준
   - 추천 MVP 범위 제안 (통상적으로 가장 중요한 'User Story 1'만 해당)
   - 포맷 검증 결과 보고: 모든 태스크가 체크리스트 규칙(체크박스, ID, 라벨, 파일 경로 명시)을 예외 없이 지키고 있는지 검증 및 확인

6. **확장 기능 훅 확인**: tasks.md 파일이 정상 생성된 후, 프로젝트 루트에 `.specify/extensions.yml`이 존재하는지 확인합니다.
   - 존재할 경우, 파일을 읽고 `hooks.after_tasks` 키 아래의 항목들을 찾습니다.
   - YAML 파싱이 불가능하거나 유효하지 않은 경우, 훅 확인을 자동으로 건너뛰고 정상적으로 진행합니다.
   - `enabled`가 명시적으로 `false`인 훅은 제외합니다. `enabled` 필드가 없는 훅은 기본적으로 활성화된 것으로 간주합니다.
   - 남은 훅들에 대해, 훅의 `condition` 표현식을 해석하거나 평가하려고 시도하지 **마십시오**:
     - 훅에 `condition` 필드가 없거나 비어있는(null/empty) 경우, 실행 가능한 훅으로 처리합니다.
     - 훅에 비어있지 않은 `condition`이 정의되어 있다면, 훅 실행을 건너뛰고 조건 평가를 HookExecutor 구현체에 위임합니다.
   - 실행 가능한 각 훅에 대해 `optional` 플래그를 기준으로 아래 내용을 출력합니다:
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
   - 등록된 훅이 없거나 `.specify/extensions.yml`이 존재하지 않는 경우 자동으로 건너뜁니다.

태스크 생성 컨텍스트 정보: $ARGUMENTS

최종 생성되는 tasks.md는 즉시 완결성 있게 실행 가능해야 합니다. 각 태스크는 코딩 에이전트(LLM)가 추가적인 컨텍스트 탐색 없이도 지침서만 읽고 단번에 코딩을 마칠 수 있도록 정교하고 구체적으로 서술되어야 합니다.

## 태스크 생성 규칙 (Task Generation Rules)

**핵심**: 태스크들은 독립적인 개발과 테스트가 가능하도록 반드시 **사용자 스토리별로 그룹화 및 조직화**되어야 합니다.

**테스트 코딩 태스크는 선택 사항(OPTIONAL)입니다**: 오직 기능 명세서(`spec.md`)에 명시적으로 테스트 구현 요건이 규정되어 있거나, 사용자가 TDD(테스트 주도 개발) 방식의 구현을 요구한 경우에만 테스트 태스크를 생성하십시오.

### 체크리스트 포맷 규칙 (필수 준수)

모든 태스크는 다음의 엄격한 한 줄 체크리스트 형식만을 따라야 합니다:

```text
- [ ] [TaskID] [P?] [Story?] 구체적인 파일 경로가 포함된 작업 설명
```

**세부 구성 요소**:

1. **체크박스**: 항상 마크다운 체크박스 기호인 `- [ ]`로 시작해야 합니다.
2. **태스크 ID**: T001, T002, T003... 과 같이 순차적으로 정렬된 세 자리 수의 실행 순서 ID를 부여합니다.
3. **[P] 마커**: 해당 태스크가 다른 작업들과 병렬 처리가 가능한 경우(수정하는 파일이 아예 다르고, 미완성 상태의 다른 작업에 의존하지 않는 경우)에만 이 라벨을 붙입니다.
4. **[스토리] 라벨**: 사용자 스토리 구현 페이즈에 들어가는 태스크에만 **필수**로 붙입니다.
   - 포맷: [US1], [US2], [US3] 등 (spec.md의 스토리 번호와 1:1로 매핑)
   - 초기 셋업 페이즈(Setup Phase): 스토리 라벨을 붙이지 **않습니다**.
   - 기반 마련 페이즈(Foundational Phase): 스토리 라벨을 붙이지 **않습니다**.
   - 사용자 스토리 구현 페이즈(User Story Phases): **반드시** 매핑되는 스토리 라벨을 붙여야 합니다.
   - 다듬기 페이즈(Polish Phase): 스토리 라벨을 붙이지 **않습니다**.
5. **설명**: 수행할 정확한 코딩 명령과 함께 대상 소스 코드 파일 경로를 명시해야 합니다.

**포맷 작성 예시**:

- ✅ 올바른 예: `- [ ] T001 구현 계획서에 맞춰 기본 폴더 구조 구조 생성`
- ✅ 올바른 예: `- [ ] T005 [P] src/middleware/auth.py 경로에 인증 미들웨어 구현`
- ✅ 올바른 예: `- [ ] T012 [P] [US1] src/models/user.py 경로에 User 데이터 모델 구현`
- ✅ 올바른 예: `- [ ] T014 [US1] src/services/user_service.py 경로에 UserService 로직 구현`
- ❌ 잘못된 예: `- [ ] Create User model` (태스크 ID 및 스토리 라벨 누락)
- ❌ 잘못된 예: `T001 [US1] Create model` (체크박스 기호 누락)
- ❌ 잘못된 예: `- [ ] [US1] Create User model` (태스크 ID 누락)
- ❌ 잘못된 예: `- [ ] T001 [US1] Create model` (작업할 소스 파일 경로 누락)

### 태스크 구조 설계 원칙

1. **사용자 스토리 기반 (spec.md)** - 가장 최우선의 분류 기준:
   - 각 사용자 스토리(P1, P2, P3...)마다 별개의 페이즈(Phase)를 할당합니다.
   - 해당 스토리 완료를 위해 코딩해야 하는 모든 컴포넌트 태스크를 해당 페이즈 하위에 배정합니다:
     - 스토리 구동에 필요한 데이터 모델(Models)
     - 스토리 구동에 필요한 비즈니스 로직 서비스(Services)
     - 스토리 구동에 필요한 라우터 및 UI(Interfaces/UI)
     - 테스트 요건이 있는 경우: 해당 스토리에 특화된 검증 테스트 태스크
   - 스토리 간의 종속성을 명시합니다 (통상적으로 각 스토리는 가능한 서로 독립적이어야 합니다).

2. **인터페이스 계약(Contracts) 기반**:
   - 각 인터페이스 계약 사양을 해당 계약을 구현 및 처리하는 사용자 스토리 페이즈 하위에 매핑합니다.
   - 테스트 요건이 있는 경우: 각 인터페이스 계약별 계약 테스트 구현 태스크[P]를 해당 스토리 페이즈의 구현 태스크보다 먼저 실행하도록 배치합니다.

3. **데이터 모델(Data Model) 기반**:
   - 각 데이터 엔티티를 해당 데이터를 실제로 최초 활용하는 사용자 스토리 페이즈에 매핑합니다.
   - 특정 엔티티가 여러 스토리에 걸쳐 공통적으로 필요하다면, 가장 먼저 수행되는 스토리에 배치하거나 Setup 페이즈에 미리 넣어둡니다.
   - 데이터 간 관계 설계(Relationships) → 매핑되는 스토리 페이즈의 서비스 구현부 태스크로 연결합니다.

4. **인프라 및 시스템 셋업 기반**:
   - 시스템 전반에 공유되는 기본 인프라 설정 → Setup 페이즈(Phase 1)
   - 특정 스토리에 종속되지 않으나 전체 기능의 뼈대가 되는 공통 태스크 → Foundational 페이즈(Phase 2)
   - 스토리 전용의 사전 인프라 구성 → 해당 스토리 페이즈 하위에 배치

### 전체 페이즈 구조 설계

- **Phase 1**: Setup (프로젝트 구조 초기화 및 개발 도구 장착)
- **Phase 2**: Foundational (사용자 스토리 시작 전 완결되어야 하는 핵심 인프라 및 전제조건 태스크)
- **Phase 3+**: 사용자 스토리 우선순위별 페이즈 구성 (P1, P2, P3...)
  - 개별 스토리 내의 작업 순서: 테스트 사양 구현(요청 시) → 모델 코딩 → 비즈니스 서비스 로직 코딩 → 라우터 엔드포인트 코딩 → 최종 통합 확인
  - 각 사용자 스토리 페이즈는 완료 즉시 혼자서 독립적으로 테스트 및 검증이 가능한 온전한 소프트웨어 증분이어야 합니다.
- **최종 Phase**: Polish & Cross-Cutting Concerns (기능 조율, 다듬기, 성능 최적화 및 횡단 관심사 보완)
