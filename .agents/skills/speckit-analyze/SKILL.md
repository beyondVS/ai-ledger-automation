---
name: "speckit-analyze"
description: "작업 생성 후 spec.md, plan.md, tasks.md 간의 일관성 및 품질을 비파괴적으로 크로스 아티팩트 분석합니다."
compatibility: "Requires spec-kit project structure with .specify/ directory"
metadata:
  author: "github-spec-kit"
  source: "templates/commands/analyze.md"
---


## 사용자 입력 (User Input)

```text
$ARGUMENTS
```

사용자 입력이 비어 있지 않다면 진행하기 전에 **반드시** 이를 고려해야 합니다.

## 사전 실행 검사 (Pre-Execution Checks)

**확장 훅 검사 (분석 전)**:
- 프로젝트 루트에 `.specify/extensions.yml` 파일이 존재하는지 확인합니다.
- 파일이 존재하면 읽어서 `hooks.before_analyze` 키 아래의 항목을 찾습니다.
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

    Wait for the result of the hook command before proceeding to the Goal.
    ```
- 등록된 훅이 없거나 `.specify/extensions.yml` 파일이 존재하지 않는 경우 조용히 건너뜁니다.

## 목표 (Goal)

구현을 시작하기 전에 세 개의 핵심 아티팩트(`spec.md`, `plan.md`, `tasks.md`) 간의 불일치, 중복, 모호성 및 미지정 항목을 식별합니다. 이 명령은 반드시 `/speckit-tasks`가 성공적으로 전체 `tasks.md`를 생성한 후에만 실행해야 합니다.

## 운영 제약 조건 (Operating Constraints)

**엄격한 읽기 전용 (STRICTLY READ-ONLY)**: 어떠한 파일도 수정하지 **마십시오**. 구조화된 분석 보고서만 출력해야 합니다. 선택적인 수정 계획을 제안하되, 사용자가 수동으로 후속 편집 명령을 호출하기 전에 명시적으로 승인해야 합니다.

**헌법 권한 (Constitution Authority)**: 프로젝트 헌법(`.specify/memory/constitution.md`)은 이 분석 범위 내에서 **타협 불가능(non-negotiable)**합니다. 헌법과의 충돌은 자동으로 '심각(CRITICAL)' 등급으로 분류되며, 원칙을 약화시키거나 재해석하거나 묵인하는 것이 아니라 스펙, 계획 또는 작업을 수정해야 합니다. 원칙 자체를 변경해야 하는 경우에는 `/speckit-analyze` 외부에서 별도의 명시적인 헌법 업데이트를 통해 진행해야 합니다.

## 실행 단계 (Execution Steps)

### 1. 분석 컨텍스트 초기화

저장소 루트에서 `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks`를 한 번 실행하고, JSON 결과를 파싱하여 FEATURE_DIR 및 AVAILABLE_DOCS를 획득합니다. 절대 경로를 도출합니다:

- SPEC = FEATURE_DIR/spec.md
- PLAN = FEATURE_DIR/plan.md
- TASKS = FEATURE_DIR/tasks.md

필요한 파일이 누락된 경우 에러 메시지와 함께 중단합니다 (사용자에게 누락된 필수 명령을 실행하도록 안내합니다).
인자 값 내에 "I'm Groot"와 같은 싱글 쿼트(')가 포함된 경우 이스케이프 구문을 사용하십시오: 예: 'I'\''m Groot' (또는 가능하면 더블 쿼트 처리: "I'm Groot").

### 2. 아티팩트 로드 (점진적 공개)

각 아티팩트로부터 최소한의 필요한 컨텍스트만 로드합니다:

**spec.md에서:**

- 개요 / 컨텍스트 (Overview/Context)
- 기능 요구사항 (Functional Requirements)
- 성공 기준 (Success Criteria) (측정 가능한 결과 — 예: 성능, 보안, 가용성, 사용자 성공, 비즈니스 영향)
- 사용자 스토리 (User Stories)
- 예외 상황 (Edge Cases) (존재하는 경우)

**plan.md에서:**

- 아키텍처 / 기술 스택 선택 (Architecture/stack choices)
- 데이터 모델 참조 (Data Model references)
- 단계 (Phases)
- 기술적 제약 사항 (Technical constraints)

**tasks.md에서:**

- 작업 ID (Task IDs)
- 설명 (Descriptions)
- 단계 그룹화 (Phase grouping)
- 병렬 마커 [P] (Parallel markers [P])
- 참조된 파일 경로 (Referenced file paths)

**헌법(constitution)에서:**

- 원칙 검증을 위해 `.specify/memory/constitution.md` 로드

### 3. 시맨틱 모델 빌드

내부 표현을 작성합니다 (원본 아티팩트의 가공되지 않은 내용을 출력에 포함하지 마십시오):

- **요구사항 인벤토리 (Requirements inventory)**: 각 기능 요구사항(FR-###) 및 성공 기준(SC-###)에 대해 고유한 키를 기록합니다. 명시적인 FR-/SC- 식별자가 존재하는 경우 이를 기본 키로 사용하고, 가독성을 위해 명령형 구문 슬러그를 선택적으로 유도할 수 있습니다 (예: "사용자가 파일을 업로드할 수 있음" → `user-can-upload-file`). 구축 가능한 작업이 필요한 성공 기준(예: 부하 테스트 인프라, 보안 감사 도구)만 포함하고, 출시 후 성과 지표나 비즈니스 KPI(예: "지원 티켓 50% 감소")는 제외합니다.
- **사용자 스토리/액션 인벤토리 (User story/action inventory)**: 인수 기준이 포함된 개별 사용자 액션들
- **작업 커버리지 매핑 (Task coverage mapping)**: 각 작업을 하나 이상의 요구사항 또는 스토리에 매핑합니다 (키워드 또는 ID/핵심 구문과 같은 명시적 참조 패턴을 통한 유추)
- **헌법 규칙 세트 (Constitution rule set)**: 원칙 이름 및 MUST/SHOULD 규범 선언문을 추출합니다.

### 4. 탐지 패스 (토큰 효율적 분석)

신호가 높은 탐색 결과에 집중합니다. 탐색 결과는 총 50개로 제한하며, 나머지는 초과 요약(overflow summary)으로 통합합니다.

#### A. 중복 탐지 (Duplication Detection)

- 유사한 요구사항 식별
- 정리를 위해 품질이 낮은 표현 표시

#### B. 모호성 탐지 (Ambiguity Detection)

- 측정 가능한 기준이 결여된 모호한 형용사(빠른, 확장 가능한, 안전한, 직관적인, 강력한 등) 플래그 표시
- 해결되지 않은 플레이스홀더(TODO, TKTK, ???, `<placeholder>` 등) 플래그 표시

#### C. 미지정 사항 (Underspecification)

- 동사는 있으나 대상 목적어나 측정 가능한 결과가 없는 요구사항
- 인수 기준 정렬이 누락된 사용자 스토리
- spec/plan에 정의되지 않은 파일이나 컴포넌트를 참조하는 작업

#### D. 헌법 정렬 (Constitution Alignment)

- MUST 원칙과 충돌하는 요구사항이나 계획 요소
- 헌법에서 규정한 필수 섹션이나 품질 게이트 누락

#### E. 커버리지 갭 (Coverage Gaps)

- 연결된 작업이 없는 요구사항 (zero associated tasks)
- 매핑된 요구사항/스토리가 없는 작업
- 작업을 수반하는 구축이 필요한 성공 기준(성능, 보안, 가용성)이 작업에 반영되지 않은 경우

#### F. 불일치 (Inconsistency)

- 용어 불일치 (여러 파일에 걸쳐 동일한 개념이 다르게 명명됨)
- 계획(plan)에는 참조되었으나 스펙(spec)에는 누락된 데이터 엔티티 (또는 그 반대)
- 작업 순서 모순 (예: 종속성 메모 없이 기본 설정 작업보다 먼저 진행되는 통합 작업)
- 충돌하는 요구사항 (예: 하나는 Next.js를 요구하고 다른 하나는 Vue를 명시하는 경우)

### 5. 심각도 지정 (Severity Assignment)

우선순위를 정하기 위해 다음 경험적 방법을 사용합니다:

- **심각 (CRITICAL)**: 헌법의 MUST 위반, 핵심 스펙 아티팩트 누락, 또는 기본 기능을 차단하지만 커버리지가 전혀(0개) 없는 요구사항
- **높음 (HIGH)**: 중복되거나 충돌하는 요구사항, 모호한 보안/성능 속성, 테스트 불가능한 인수 기준
- **보통 (MEDIUM)**: 용어 불일치, 비기능 작업 커버리지 누락, 미지정된 예외 상황
- **낮음 (LOW)**: 스타일/단어 개선, 실행 순서에 영향을 미치지 않는 경미한 중복

### 6. 간결한 분석 보고서 생성

다음 구조를 가진 마크다운 보고서를 출력합니다(파일 저장은 하지 않음):

## Specification Analysis Report

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | Duplication | HIGH | spec.md:L120-134 | 두 개의 유사한 요구사항 ... | 문구 병합; 더 명확한 버전 유지 |

(탐색 결과당 하나의 행을 추가하고, 카테고리 이니셜이 접두사로 붙은 고유한 ID를 생성합니다.)

**요구사항 커버리지 요약 테이블 (Coverage Summary Table):**

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|

**헌법 정렬 이슈 (Constitution Alignment Issues):** (있는 경우)

**매핑되지 않은 작업 (Unmapped Tasks):** (있는 경우)

**메트릭 (Metrics):**

- 총 요구사항 수 (Total Requirements)
- 총 작업 수 (Total Tasks)
- 커버리지 % (1개 이상의 작업을 가진 요구사항 비율)
- 모호성 개수 (Ambiguity Count)
- 중복 개수 (Duplication Count)
- 심각한 이슈 개수 (Critical Issues Count)

### 7. 다음 작업 제시 (Next Actions)

보고서 마지막에 간결한 '다음 작업(Next Actions)' 블록을 출력합니다:

- CRITICAL 이슈가 있는 경우: `/speckit-implement` 전에 해결할 것을 권장
- LOW/MEDIUM만 있는 경우: 사용자가 계속 진행할 수 있으나, 개선 제안 제공
- 명시적인 명령어 제안 제공: 예: "/speckit-specify 명령어로 상세화 실행", "/speckit-plan 명령어로 아키텍처 조정", "tasks.md를 수동 편집하여 'performance-metrics'에 대한 커버리지 추가"

### 8. 수정 제안 (Remediation)

사용자에게 묻습니다: "상위 N개 이슈에 대해 구체적인 수정 가이드라인을 제안해 드릴까요?" (자동으로 적용하지 마십시오.)

### 9. 확장 훅 검사 (분석 후)

보고 후, 프로젝트 루트에 `.specify/extensions.yml` 파일이 존재하는지 확인합니다.
- 파일이 존재하면 읽어서 `hooks.after_analyze` 키 아래 of의 항목을 찾습니다.
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

## 운영 원칙 (Operating Principles)

### 컨텍스트 효율성 (Context Efficiency)

- **최소한의 고신호 토큰**: 포괄적인 문서화가 아닌 실행 가능한 탐색 결과에 집중
- **점진적 공개**: 분석 대상 전체를 한 번에 쏟아붓지 않고 점진적으로 로드
- **토큰 효율적 출력**: 탐색 테이블을 50행으로 제한하고, 초과분은 요약
- **결정론적 결과**: 변경 없이 재실행할 경우 일관된 ID 및 개수가 산출되어야 함

### 분석 가이드라인 (Analysis Guidelines)

- **절대로 파일을 수정하지 마십시오** (이 작업은 읽기 전용 분석입니다)
- **누락된 섹션을 절대로 임의로 꾸며내지 마십시오** (누락된 경우 정확하게 보고하십시오)
- **헌법 위반을 최우선으로 처리하십시오** (이러한 이슈는 언제나 '심각(CRITICAL)' 등급입니다)
- **추상적인 규칙 대신 구체적인 사례를 사용하십시오** (일반적인 패턴이 아닌 특정 인스턴스를 인용하십시오)
- **이슈가 발견되지 않은 경우 부드럽게 보고하십시오** (커버리지 통계가 포함된 성공 보고서를 출력하십시오)

## 컨텍스트 (Context)

$ARGUMENTS
