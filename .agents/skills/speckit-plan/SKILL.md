---
name: "speckit-plan"
description: "기능 구현 계획 템플릿을 사용하여 구현 계획 수립 워크플로우를 실행하고 설계 결과물을 생성합니다."
compatibility: "프로젝트 루트에 .specify/ 디렉토리가 있는 spec-kit 프로젝트 구조가 필요합니다."
metadata:
  author: "github-spec-kit"
  source: "templates/commands/plan.md"
---


## 사용자 입력

```text
$ARGUMENTS
```

진행하기 전에 사용자 입력이 비어있지 않다면 **반드시** 고려해야 합니다.

## 실행 전 확인 사항

**확장 기능 훅 확인 (계획 수립 전)**:
- 프로젝트 루트에 `.specify/extensions.yml`이 존재하는지 확인합니다.
- 존재할 경우, 파일을 읽고 `hooks.before_plan` 키 아래의 항목들을 찾습니다.
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

1. **설정(Setup)**: 저장소 루트에서 `.specify/scripts/powershell/setup-plan.ps1 -Json`을 실행하고 JSON 결과를 파싱하여 FEATURE_SPEC, IMPL_PLAN, SPECS_DIR, BRANCH를 가져옵니다. "I'm Groot"와 같이 인자 값에 단일 인용부호가 들어가는 경우 이스케이프 구문을 사용합니다: 예: 'I'\''m Groot' (또는 가급적 큰따옴표 사용: "I'm Groot").

2. **컨텍스트 로드**: FEATURE_SPEC 및 `.specify/memory/constitution.md`를 읽습니다. (이미 복사된) IMPL_PLAN 템플릿을 로드합니다.

3. **계획 수립 워크플로우 실행**: IMPL_PLAN 템플릿의 구조를 따라 다음을 수행합니다:
   - 기술 컨텍스트(Technical Context) 작성 (알 수 없는 정보는 "NEEDS CLARIFICATION"으로 표시)
   - 헌법(Constitution)으로부터 헌법 확인(Constitution Check) 섹션 작성
   - 게이트(Gate) 평가 (정당화되지 않은 위반 사항이 있는 경우 오류 처리)
   - Phase 0: research.md 생성 (모든 NEEDS CLARIFICATION 해결)
   - Phase 1: data-model.md, contracts/, quickstart.md 생성
   - Phase 1: 에이전트 스크립트를 실행하여 에이전트 컨텍스트 업데이트
   - 설계 완료 후 헌법 확인 재평가

4. **중단 및 보고**: Phase 2 계획 수립 후에 명령이 종료됩니다. 브랜치명, IMPL_PLAN 경로, 그리고 생성된 결과물을 보고하십시오.

5. **확장 기능 훅 확인**: 보고 완료 후, 프로젝트 루트에 `.specify/extensions.yml`이 존재하는지 확인합니다.
   - 존재할 경우, 파일을 읽고 `hooks.after_plan` 키 아래의 항목들을 찾습니다.
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

## 단계 (Phases)

### Phase 0: 개요 및 연구 (Outline & Research)

1. **위의 기술 컨텍스트(Technical Context)에서 미확정 사항 추출**:
   - 각 NEEDS CLARIFICATION 대상 → 연구(research) 태스크 생성
   - 각 종속성 대상 → 모범 사례(best practices) 태스크 생성
   - 각 통합 대상 → 패턴(patterns) 태스크 생성

2. **연구 에이전트 생성 및 발송**:

   ```text
   기술 컨텍스트의 각 미확정 사항에 대해:
     태스크: "Research {unknown} for {feature context}"
   각 기술 선택안에 대해:
     태스크: "Find best practices for {tech} in {domain}"
   ```

3. **조사 결과 정리**: 다음 형식을 사용하여 `research.md`에 결과를 정리합니다:
   - 결정사항 (Decision): [선택된 기술/방안]
   - 타당성 (Rationale): [선택 이유]
   - 고려된 대안 (Alternatives considered): [함께 평가된 다른 대안]

**결과물**: 모든 NEEDS CLARIFICATION이 해결된 research.md 파일

### Phase 1: 설계 및 계약 (Design & Contracts)

**사전 조건:** `research.md` 작성 완료

1. **기능 명세에서 엔티티 추출** → `data-model.md`:
   - 엔티티 이름, 필드, 관계 구성
   - 요구사항에 기반한 유효성 검사 규칙
   - 적용 가능한 경우 상태 전이(State transitions) 정의

2. **인터페이스 계약 정의** (프로젝트에 외부 인터페이스가 있는 경우) → `/contracts/`:
   - 프로젝트가 사용자나 다른 시스템에 노출하는 인터페이스 식별
   - 프로젝트 유형에 적절한 계약 형식 문서화
   - 예시: 라이브러리용 공개 API, CLI 도구용 커맨드 스키마, 웹 서비스용 엔드포인트, 파서용 문법, 애플리케이션용 UI 계약 등
   - 프로젝트가 순수하게 내부용(빌드 스크립트, 일회성 도구 등)인 경우 건너뜁니다.

3. **에이전트 컨텍스트 업데이트**:
   - `AGENTS.md` 파일에서 `<!-- SPECKIT START -->`와 `<!-- SPECKIT END -->` 마커 사이에 있는 계획 참조 정보를 1단계에서 생성된 계획 파일 경로(IMPL_PLAN 경로)를 가리키도록 업데이트합니다.

**결과물**: data-model.md, /contracts/*, quickstart.md, 업데이트된 에이전트 컨텍스트 파일

## 핵심 규칙

- 파일 시스템 작업 시에는 절대 경로를 사용하고, 문서 및 에이전트 컨텍스트 파일 내의 참조에는 프로젝트 상대 경로를 사용하십시오.
- 게이트 평가 실패 또는 해결되지 않은 명확화 사항이 있는 경우 오류(ERROR) 처리합니다.
