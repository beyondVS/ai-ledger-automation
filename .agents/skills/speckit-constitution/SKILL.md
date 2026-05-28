---
name: "speckit-constitution"
description: "대화식 입력 또는 제공된 원칙 정보를 바탕으로 프로젝트 헌법을 수립 또는 업데이트하고, 이에 종속된 모든 템플릿들이 유기적으로 동기화되도록 제어합니다."
compatibility: "프로젝트 루트에 .specify/ 디렉토리가 있는 spec-kit 프로젝트 구조가 필요합니다."
metadata:
  author: "github-spec-kit"
  source: "templates/commands/constitution.md"
---


## 사용자 입력

```text
$ARGUMENTS
```

진행하기 전에 사용자 입력이 비어있지 않다면 **반드시** 고려해야 합니다.

## 실행 전 확인 사항

**확장 기능 훅 확인 (헌법 업데이트 전)**:
- 프로젝트 루트에 `.specify/extensions.yml`이 존재하는지 확인합니다.
- 존재할 경우, 파일을 읽고 `hooks.before_constitution` 키 아래의 항목들을 찾습니다.
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

귀하는 `.specify/memory/constitution.md` 경로에 위치한 프로젝트 헌법(Constitution)을 업데이트하고 있습니다. 이 파일은 대괄호 안에 자리표시자 토큰(예: `[PROJECT_NAME]`, `[PRINCIPLE_1_NAME]`)이 포함된 템플릿입니다. 귀하의 임무는 (a) 구체적인 값을 수집/도출하고, (b) 템플릿을 정밀하게 채워 넣으며, (c) 종속된 다른 템플릿들로 동기화하는 것입니다.

**참고**: 만약 `.specify/memory/constitution.md` 파일이 존재하지 않는다면, 프로젝트 초기 설정 과정에서 `.specify/templates/constitution-template.md` 파일로부터 초기화되어야 합니다. 파일이 누락되었다면 먼저 템플릿을 복사하십시오.

다음 실행 흐름을 엄수하십시오:

1. `.specify/memory/constitution.md`에 위치한 기존 헌법 문서를 로드합니다.
   - `[ALL_CAPS_IDENTIFIER]` 형식 of 모든 자리표시자(Placeholder) 토큰을 식별합니다.
   **중요**: 사용자는 템플릿에 명시된 원칙 수보다 적거나 더 많은 핵심 개발 원칙을 요구할 수 있습니다. 수량이 지정되었다면 이를 존중하여 전체 템플릿의 가이드에 맞춰 문서를 업데이트해야 합니다.

2. 자리표시자에 기입할 구체적인 값들을 수집/도출합니다:
   - 현재 대화 및 사용자 입력이 구체적인 값을 제공하는 경우 해당 값을 사용합니다.
   - 그렇지 않은 경우 기존 저장소의 맥락(README, docs 폴더 문서, 소스에 삽입되어 있는 이전 헌법 등)에서 합리적인 판단을 추론합니다.
   - 거버넌스 날짜의 경우: `RATIFICATION_DATE`(비준일)는 최초 채택 날짜를 기입하며 (확인이 어려운 경우 TODO 표시하거나 사용자에게 질의), `LAST_AMENDED_DATE`(최종 개정일)는 변경 내역이 발생하는 경우 오늘 날짜를 기입하고 그렇지 않은 경우 이전 날짜를 유지합니다.
   - `CONSTITUTION_VERSION`(버전) 정보는 시맨틱 버저닝(Semantic Versioning) 규칙에 맞춰 증가시킵니다:
     - MAJOR: 이전 사양과 하위 호환되지 않는 중대한 개발 원칙의 삭제 및 전면적 정의 수정
     - MINOR: 신규 핵심 개발 원칙/섹션 추가 또는 기존 가이드라인의 실질적 확장
     - PATCH: 모호한 자구 설명 수정, 오타 수정, 비실질적 마크다운 다듬기
   - 버전 판올림 종류가 애매한 경우, 결정 전에 사용자에게 타당한 추론 근거를 제시하십시오.

3. 업데이트할 헌법 초안을 작성합니다:
   - 모든 자리표시자를 실제 텍스트로 치환합니다 (의도적으로 보류해 둔 템플릿 슬롯을 제외하고는 대괄호 토큰이 남아있지 않아야 하며, 보류된 슬롯이 있다면 그 타당성을 명시해야 합니다).
   - 문서 헤더 구조를 완전하게 보존합니다. 치환이 성공적으로 완료되었다면 설명용 주석 라인들은 가독성을 위해 제거할 수 있습니다.
   - 작성할 원칙(Principle) 섹션 요건: 핵심 원칙명이 담긴 짦은 헤더 라인, 타협할 수 없는 엄격한 실천 규칙을 설명하는 한 단락(또는 글머리 목록), 명백하지 않은 사안에 대한 구체적 타당성(Rationale) 기술을 포함해야 합니다.
   - Ensure Governance section lists amendment procedure, versioning policy, and compliance review expectations.

4. 일관성 동기화 확인 사항 (체크리스트를 활성 검증 단계로 활용):
   - `.specify/templates/plan-template.md`를 읽고 "Constitution Check"(헌법 확인) 섹션이나 규칙들이 업데이트된 헌법 원칙과 일관되게 맞물리는지 검증합니다.
   - `.specify/templates/spec-template.md`를 읽고 개발 범위/요구사항 사양이 정렬되는지 확인하며, 헌법 문서에서 필수 섹션이나 규칙을 추가/제거한 경우 템플릿을 적절히 업데이트합니다.
   - `.specify/templates/tasks-template.md`를 읽고 헌법 원칙 중심의 태스크 유형(예: 모니터링, 버전 정책, 테스트 기강 요건 등)의 추가/삭제가 태스크 분류 구조에 정상적으로 반영되어 있는지 확인합니다.
   - `.specify/templates/commands/*.md` 경로 내의 모든 지침 명령서 파일(본 문서 포함)을 읽고 범용 가이드가 필요한 영역에 특정 AI 서비스명과 같은 구식 표기(예: CLAUDE 전용 명칭 등)가 남아있지 않은지 검증합니다.
   - 런타임 가이드 문서(예: `README.md`, `docs/quickstart.md` 등)를 확인하여 변경된 원칙에 맞춰 모든 참조를 유기적으로 업데이트합니다.

5. 동기화 영향 보고서(Sync Impact Report) 작성 (업데이트 완료 후 헌법 문서 최상단에 HTML 주석 `<!-- -->` 형태로 추가):
   - 버전 변경 내역: 이전 vX.Y.Z → 신규 vA.B.C
   - 수정된 원칙 요약 (원칙명이 바뀐 경우 이전명 → 신규명 명시)
   - 새로 추가된 세부 섹션
   - 삭제된 세부 섹션
   - 업데이트된 종속 템플릿 현황 (✅ 완료됨 / ⚠ 보류 중) 및 대상 파일 경로 기재
   - 의도적으로 보류해 둔 자리표시자가 있는 경우 후속 작업 TODO 내역 명시

6. 최종 출력 전 검증 (Validation):
   - 설명되지 않은 대괄호 `[]` 토큰이 본문에 전혀 남아있지 않은지 확인
   - 버전 표기가 보고서의 새 버전 정보와 완벽히 일치하는지 확인
   - 날짜 표기는 ISO 표준 형식인 `YYYY-MM-DD`를 따르고 있는지 확인
   - 모든 핵심 원칙은 선언적이고 검증 가능한 명확한 문장으로 기술되었는지 확인 (모호한 표현인 "해야 한다/좋다" 대신 "필수/엄격 준수" 등 강력한 규칙어로 기술)

7. 완성된 헌법 본문을 `.specify/memory/constitution.md` 파일에 저장합니다 (덮어쓰기).

8. 사용자에게 다음과 같은 요약 정보를 담아 최종 완료 보고를 출력합니다:
   - 신규 버전 정보 및 판올림 결정 근거
   - 수동 검토가 필요해 플래그 표시해 둔 파일 목록
   - 추천 커밋 메시지 (예: `docs: amend constitution to vX.Y.Z (principle additions + governance update)`)

서식 및 스타일 요구사항:
- 템플릿에 지정된 마크다운 헤더 수준(h1, h2, h3 등)을 한 레벨도 어긋나지 않게 원본 규격 그대로 준수하십시오.
- 타당성 설명 등 긴 라인은 가독성을 유지하도록 적절히 줄바꿈하되, 억지스럽고 부자연스럽게 강제 분리하지는 마십시오.
- 섹션과 섹션 사이에는 정확히 단 하나의 빈 줄만 두십시오.
- 문장 끝에 불필요한 공백 문자(trailing whitespace)를 남기지 마십시오.

사용자가 피처 헌법의 일부 항목만 부분 수정을 요청한 경우에도, 전체 헌법 품질 검증 및 버전 시맨틱 결정 단계를 완전하게 예외 없이 이행해야 합니다.

만약 필수 정보가 완전히 누락된 경우(예: 비준 날짜를 아예 추정할 수 없는 경우 등), `TODO(<FIELD_NAME>): 상세 설명` 토큰을 임시 기입하고 동기화 영향 보고서의 보류 항목 섹션에 이를 기재하십시오.

별개의 신규 헌법 문서를 새로 생성하지 말고, 반드시 기존에 존재하는 `.specify/memory/constitution.md` 파일을 정밀 가공하여 동작시키십시오.

## 실행 후 확인 사항

**확장 기능 훅 확인 (헌법 업데이트 완료 후)**:
프로젝트 루트에 `.specify/extensions.yml`이 존재하는지 확인합니다.
- 존재할 경우, 파일을 읽고 `hooks.after_constitution` 키 아래 of 항목들을 찾습니다.
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
- 등록된 훅이 없거나 `.specify/extensions.yml`이 존재하지 않는 경우 자동으로 건너뜁니다.t, skip silently
