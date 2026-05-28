---
name: "speckit-specify"
description: "자연어로 작성된 기능 설명으로부터 기능 명세서(Feature Specification)를 생성하거나 업데이트합니다."
compatibility: "프로젝트 루트에 .specify/ 디렉토리가 있는 spec-kit 프로젝트 구조가 필요합니다."
metadata:
  author: "github-spec-kit"
  source: "templates/commands/specify.md"
---


## 사용자 입력

```text
$ARGUMENTS
```

진행하기 전에 사용자 입력이 비어있지 않다면 **반드시** 고려해야 합니다.

## 실행 전 확인 사항

**확장 기능 훅 확인 (기능 명세 작성 전)**:
- 프로젝트 루트에 `.specify/extensions.yml`이 존재하는지 확인합니다.
- 존재할 경우, 파일을 읽고 `hooks.before_specify` 키 아래의 항목들을 찾습니다.
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

트리거 메시지에서 `/speckit-specify` 뒤에 입력된 텍스트가 **바로** 기능 설명(feature description)입니다. 아래에 `$ARGUMENTS`가 리터럴로 표시되더라도 본 대화에서 항상 기능 설명이 제공된다고 가정하십시오. 명령어가 완전히 비어있지 않는 한 사용자에게 반복 입력을 요청하지 마십시오.

기능 설명이 주어지면 다음 단계를 수행하십시오:

1. **간결한 짧은 이름 생성** (2~4단어):
   - 기능 설명을 분석하고 가장 의미 있는 키워드를 추출합니다.
   - 기능의 본질을 담는 2~4 단어의 짧은 이름을 만듭니다.
   - 가능하면 동사-명사 형식을 사용합니다 (예: "add-user-auth", "fix-payment-bug").
   - 기술 용어 및 두문자어(OAuth2, API, JWT 등)는 그대로 유지합니다.
   - 간결하면서도 한눈에 기능을 파악할 수 있도록 서술적으로 만듭니다.
   - 예시:
     - "I want to add user authentication" (사용자 인증을 추가하고 싶음) → "user-auth"
     - "Implement OAuth2 integration for the API" (API용 OAuth2 연동 구현) → "oauth2-api-integration"
     - "Create a dashboard for analytics" (분석용 대시보드 제작) → "analytics-dashboard"
     - "Fix payment processing timeout bug" (결제 처리 타임아웃 버그 수정) → "fix-payment-timeout"

2. **브랜치 생성** (선택 사항, 훅 경유):
   - 위의 '실행 전 확인 사항'에서 `before_specify` 훅이 성공적으로 실행되었다면, 해당 훅이 git 브랜치를 생성/전환하고 `BRANCH_NAME` 및 `FEATURE_NUM`을 담은 JSON을 출력했을 것입니다. 이 값들을 참고용으로 기록해 두되, 브랜치명이 명세(spec) 디렉토리명을 전적으로 강제하지는 않습니다.
   - 사용자가 명시적으로 `GIT_BRANCH_NAME`을 제공한 경우, 브랜치 스크립트가 해당 값을 브랜치명으로 그대로 사용하도록 훅으로 전달하십시오 (이 경우 접두사/접미사 자동 생성을 건너뜁니다).

3. **기능 명세 디렉토리 생성**:
   - 사용자가 명시적으로 `SPECIFY_FEATURE_DIRECTORY`를 제공하지 않는 한, 명세서는 기본 `specs/` 디렉토리 하위에 위치합니다.
   
   **`SPECIFY_FEATURE_DIRECTORY` 결정 순서**:
   1. 사용자가 명시적으로 `SPECIFY_FEATURE_DIRECTORY`를 제공한 경우 (예: 환경 변수, 인자, 또는 환경 설정 등을 통해), 제공된 값을 그대로 사용합니다.
   2. 그렇지 않은 경우, `specs/` 하위에 디렉토리를 자동 생성합니다:
      - `.specify/init-options.json` 파일에서 `branch_numbering` 방식을 확인합니다.
      - `"timestamp"`인 경우: 접두사는 `YYYYMMDD-HHMMSS` (현재 타임스탬프)로 지정합니다.
      - `"sequential"`이거나 설정이 없는 경우: 접두사는 `NNN` (기존 `specs/` 디렉토리를 스캔한 후 다음으로 사용 가능한 3자리 순차 번호)으로 지정합니다.
      - 디렉토리명을 구성합니다: `<prefix>-<short-name>` (예: `003-user-auth` 또는 `20260319-143022-user-auth`).
      - `SPECIFY_FEATURE_DIRECTORY`를 `specs/<directory-name>`으로 설정합니다.

   **디렉토리 및 명세 파일 생성**:
   - `mkdir -p SPECIFY_FEATURE_DIRECTORY`를 실행합니다.
   - 시작점으로 사용할 `.specify/templates/spec-template.md` 파일을 `SPECIFY_FEATURE_DIRECTORY/spec.md`로 복사합니다.
   - `SPEC_FILE`을 `SPECIFY_FEATURE_DIRECTORY/spec.md`로 설정합니다.
   - 결정된 경로를 `.specify/feature.json` 파일에 저장합니다:
     ```json
     {
       "feature_directory": "<resolved feature dir>"
     }
     ```
     리터럴 문자열 `SPECIFY_FEATURE_DIRECTORY`가 아니라, 실제로 해석된 디렉토리 경로 값(예: `specs/003-user-auth`)을 기록하십시오.
     이를 통해 후속 명령어들(`/speckit-plan`, `/speckit-tasks` 등)이 git 브랜치 이름 규칙에 의존하지 않고도 피처 디렉토리를 탐색할 수 있습니다.

   **중요 사항**:
   - 하나의 `/speckit-specify` 호출당 단 하나의 피처만 생성해야 합니다.
   - 명세 디렉토리명과 git 브랜치명은 서로 독립적입니다. 동일하게 일치시킬 수 있으나 이는 사용자의 선택에 달렸습니다.
   - 명세 디렉토리와 파일은 항상 본 코어 명령을 통해 생성되며, 훅을 통해 생성되지 않습니다.

4. `.specify/templates/spec-template.md`를 로드하여 필수 구성 섹션들을 파악합니다.

5. 다음 실행 흐름을 엄수하십시오:
   1. 인자값에서 사용자 설명을 파싱합니다. 비어있는 경우: ERROR "No feature description provided"
   2. 설명에서 핵심 개념(행동자, 행동, 데이터, 제약 조건)을 식별 및 추출합니다.
   3. 모호한 지점이 있는 경우:
      - 문맥과 산업 표준을 기반으로 합리적인 기본값(Assumption)을 추론하여 채워 넣습니다.
      - 오직 다음의 경우에만 `[NEEDS CLARIFICATION: 구체적인 질문]` 마커를 표시하십시오:
        - 해당 선택안이 피처의 범위나 사용자 경험에 중대한 영향을 미치는 경우
        - 서로 다른 파급 효과를 가진 여러 타당한 해석이 공존하는 경우
        - 합리적인 기본 추론이 존재하지 않는 경우
      - **제한 사항: 총 [NEEDS CLARIFICATION] 마커는 최대 3개까지만 허용됩니다.**
      - 모호한 사항의 우선순위는 영향도 기준으로 정합니다: 범위(Scope) > 보안/개인정보 > 사용자 경험 > 기술적 세부사항
   4. '사용자 시나리오 및 테스트(User Scenarios & Testing)' 섹션을 작성합니다. 명확한 사용자 흐름이 식별되지 않는 경우: ERROR "Cannot determine user scenarios"
   5. 기능 요구사항(Functional Requirements)을 생성합니다. 각 요구사항은 검증 및 테스트가 가능해야 합니다. 명시되지 않은 세부사항은 합리적인 기본 가정을 적용하고, '가정(Assumptions)' 섹션에 이를 문서화하십시오.
   6. 성공 기준(Success Criteria)을 정의합니다. 기술에 구애받지 않는 측정 가능한 비즈니스 결과를 수립하십시오. 정량적 지표(시간, 성능, 볼륨)와 정성적 지표(사용자 만족도, 태스크 완료율)를 모두 포함해야 하며, 구현 정보 없이 검증 가능해야 합니다.
   7. 관련 데이터가 연관된 경우 주요 엔티티(Key Entities)를 작성합니다.
   8. 완료 시: SUCCESS (계획 수립이 준비된 기능 명세 완료)

6. 템플릿 구조를 기반으로 기능 명세 내용들을 `SPEC_FILE`에 작성하십시오. 기능 설명(arguments)에서 도출한 구체적인 내용들로 플레이스홀더를 채워 넣되, 섹션의 순서와 헤더는 엄격히 유지하십시오.

7. **명세서 품질 검증 (Specification Quality Validation)**: 초기 명세를 작성한 후, 품질 기준에 맞춰 자가 검증을 실행합니다:

   a. **명세 품질 체크리스트 생성**: `SPECIFY_FEATURE_DIRECTORY/checklists/requirements.md` 경로에 체크리스트 템플릿 구조를 활용해 다음 검증 항목을 담은 파일을 생성합니다:

      ```markdown
      # Specification Quality Checklist: [FEATURE NAME]
      
      **목적**: 계획 수립 단계로 넘어가기 전 기능 명세의 완성도와 품질을 검증
      **작성일**: [DATE]
      **대상 기능**: [Link to spec.md]
      
      ## 콘텐츠 품질 (Content Quality)
      
      - [ ] 구현 세부사항(언어, 프레임워크, 특정 API 등)이 제외되어 있는가
      - [ ] 사용자 가치 및 비즈니스 요구사항에 집중하고 있는가
      - [ ] 비기술적 이해관계자도 쉽게 이해할 수 있게 작성되었는가
      - [ ] 모든 필수 섹션이 누락 없이 작성되었는가
      
      ## 요구사항 완결성 (Requirement Completeness)
      
      - [ ] [NEEDS CLARIFICATION] 마커가 더 이상 존재하지 않는가
      - [ ] 요구사항들이 모호하지 않고 테스트 가능한 수준인가
      - [ ] 성공 기준들이 명확히 측정 가능한가
      - [ ] 성공 기준이 특정 기술 사양에 종속적이지 않은가 (구현 세부사항 배제)
      - [ ] 모든 인수 시나리오(Acceptance Scenarios)가 정의되었는가
      - [ ] 예외 케이스(Edge cases)들이 식별되었는가
      - [ ] 기능의 범위가 명확하게 경계 지어졌는가
      - [ ] 종속성 및 가정이 올바르게 파악되었는가
      
      ## 기능 준비성 (Feature Readiness)
      
      - [ ] All functional requirements have clear acceptance criteria
      - [ ] User scenarios cover primary flows
      - [ ] Feature meets measurable outcomes defined in Success Criteria
      - [ ] No implementation details leak into specification
      
      ## 비고 (Notes)
      
      - 미완료 항목(체크 안 됨)은 `/speckit-clarify` 또는 `/speckit-plan`을 실행하기 전에 보완되어야 합니다.
      ```

   b. **품질 검증 실행**: 명세서 내용을 위 체크리스트의 각 항목과 비교 검토합니다:
      - 각 검증 항목의 통과(Pass)/실패(Fail) 여부를 판별합니다.
      - 발견된 문제점을 명시하고, 관련된 명세서 본문을 인용하여 기록합니다.

   c. **품증 결과 처리**:

      - **모든 항목이 통과된 경우**: 체크리스트를 완결 상태로 채우고 8단계로 진행합니다.

      - **실패 항목이 있는 경우 ([NEEDS CLARIFICATION] 제외)**:
        1. 실패한 항목들과 구체적인 문제점들을 나열합니다.
        2. 식별된 문제들을 해결하도록 명세서(`spec.md`) 본문을 업데이트합니다.
        3. 모든 항목이 통과될 때까지 검증을 재실행합니다 (최대 3회 반복).
        4. 3회 반복 후에도 실패 항목이 있다면, 남은 문제를 체크리스트 비고(Notes)란에 기록하고 사용자에게 주의 경고를 출력합니다.

      - **[NEEDS CLARIFICATION] 마커가 남아있는 경우**:
        1. 명세서에서 모든 `[NEEDS CLARIFICATION: ...]` 마커를 추출합니다.
        2. **제한 사항 확인**: 만약 3개보다 많은 마커가 존재한다면, 가장 크리티컬한(범위/보안/UX에 영향이 큰) 3개만 남기고 나머지는 합리적인 기본값으로 추론하여 대체하십시오.
        3. 피드백이 필요한 각 명확화 항목(최대 3개)에 대해 사용자에게 다음 형식으로 질문을 제시합니다:

           ```markdown
           ## 질문 [N]: [주제]
           
           **맥락 (Context)**: [관련된 명세서 본문 구절 인용]
           
           **확인이 필요한 내용**: [NEEDS CLARIFICATION 마커의 구체적 질문 사항]
           
           **추천 답변 옵션**:
           
           | 옵션 | 답변 | 비즈니스 영향 / 고려 사항 |
           |------|------|---------------------------|
           | A    | [첫 번째 추천 답변] | [이 선택지가 기능에 미치는 영향] |
           | B    | [두 번째 추천 답변] | [이 선택지가 기능에 미치는 영향] |
           | C    | [세 번째 추천 답변] | [이 선택지가 기능에 미치는 영향] |
           | Custom | 직접 답변 작성 | [원하는 요구사항을 자유롭게 작성하는 방법 설명] |
           
           **답변 선택**: _[사용자의 입력을 대기합니다]_
           ```

        4. **핵심 - 표 포맷 준수**: 마크다운 테이블이 올바르게 렌더링되도록 격자 띄어쓰기를 철저히 확인하십시오:
           - 열 파이프(|) 간격을 일정하게 정렬합니다.
           - 각 셀 내부에는 공백을 양옆에 추가하십시오 (예: `|Content|` 대신 `| Content |` 사용).
           - 헤더 분리 줄은 최소 3개 이상의 대시를 사용하십시오 (예: `|--------|`).
           - 마크다운 뷰어에서 표가 올바르게 렌더링되는지 확인하십시오.
        5. 질문들에 1부터 3까지 일관된 번호를 매깁니다 (Q1, Q2, Q3 - 최대 3개).
        6. 사용자의 피드백을 기다리기 전, 모든 질문을 한 화면에 일괄적으로 제시하십시오.
        7. 사용자가 모든 질문에 대해 선택한 답변 정보(예: "Q1: A, Q2: 직접 작성 - [상세], Q3: B")를 회신할 때까지 기다립니다.
        8. 회신이 수신되면, 명세서 본문의 각 `[NEEDS CLARIFICATION]` 마커를 사용자가 선택하거나 제공한 답변 내용으로 교체하여 업데이트합니다.
        9. 모든 모호한 사항이 명확히 해결된 후 품질 검증 프로세스를 다시 실행합니다.

   d. **체크리스트 업데이트**: 매 품질 검증 반복 시마다, 체크리스트 파일에 현재 통과/실패 항목 상태를 최신화하여 기록합니다.

8. **완료 보고**: 다음과 같은 정보를 담아 사용자에게 최종 완료를 보고합니다:
   - `SPECIFY_FEATURE_DIRECTORY` — 피처 디렉토리 경로
   - `SPEC_FILE` — 기능 명세 파일 경로
   - 품질 체크리스트 검증 결과 요약
   - 다음 단계인 구현 계획 수립(`/speckit-clarify` 또는 `/speckit-plan`)을 시작할 준비 상태 보고

9. **확장 기능 훅 확인**: 보고 완료 후, 프로젝트 루트에 `.specify/extensions.yml`이 존재하는지 확인합니다.
   - 존재할 경우, 파일을 읽고 `hooks.after_specify` 키 아래의 항목들을 찾습니다.
   - YAML 파싱이 불가능하거나 유효하지 않은 경우, 훅 확인을 자동으로 건너뛰고 정상적으로 진행합니다.
   - `enabled`가 명시적으로 `false`인 훅은 제외합니다. `enabled` 필드가 없는 훅은 기본적으로 활성화된 것으로 간주합니다.
   - 남은 훅들에 대해, 훅의 `condition` 표현식을 해석하거나 평가하려고 시도하지 **마십시오**:
     - 훅에 `condition` field가 없거나 비어있는(null/empty) 경우, 실행 가능한 훅으로 처리합니다.
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

**참고:** 브랜치 생성은 `before_specify` 훅(git 확장 기능)이 담당합니다. 피처 명세 디렉토리 및 파일 생성은 항상 본 코어 명령어가 처리합니다.

## 빠른 안내 지침

- 사용자가 **무엇(WHAT)**을 원하고 그 이유인 **왜(WHY)**에 전적으로 포커스를 맞춥니다.
- **어떻게(HOW)** 구현할지에 대한 구체적 기술은 배제하십시오 (프레임워크, API 설계, 소스 코드 구조 제외).
- 개발자가 아닌 비즈니스 이해관계자 대상의 직관적인 용어로 작성되어야 합니다.
- 명세서 파일 본문에 체크리스트를 포함해서는 안 됩니다. 체크리스트는 별도 명령어로 처리됩니다.

### 섹션 요구사항

- **필수 섹션**: 모든 기능 사양서 작성 시 반드시 기재되어야 합니다.
- **선택 섹션**: 피처 기능에 연관되어 있거나 의미가 있을 때만 작성하십시오.
- 특정 섹션이 불필요한 경우 "N/A"나 빈 상태로 두지 말고 아예 해당 섹션을 명세서에서 완전히 제거하십시오.

### AI 생성 최적화 지침

사용자 프롬프트로부터 기능 명세서를 자동 생성할 때:

1. **지능적인 추론을 수행하십시오**: 문맥, 보편적 개발 업계 표준, 상용 비즈니스 패턴을 분석해 비어있는 요건 정보를 지능적으로 채워 넣습니다.
2. **가정 정의**: 추론을 통해 결정된 기본 설정이나 판단 내역들을 '가정(Assumptions)' 섹션에 누락 없이 문서화해 두십시오.
3. **명확화 요청 한도 엄수**: `[NEEDS CLARIFICATION]` 마커는 최대 3개까지만 제한하여 적용해야 합니다. 오직 다음의 비즈니스적 크리티컬 판단에만 제한해 할당하십시오:
   - 피처의 개발 범위나 최종 사용자 여정에 지대한 파급효과가 있는 경우
   - 타당한 구현 대안들이 많으며 각각 장단점과 비즈니스 영향이 상이한 경우
   - 일반적인 기본 추론 사양이 작동하지 않는 특이 케이스
4. **명확화 우선순위화**: 범위(Scope) > 보안/개인정보 > 사용자 경험 > 기술적 세부사항
5. **테스터의 시각 견지**: 모호하거나 두루뭉술한 사양은 체크리스트의 "비모호성 및 테스트 가능성" 항목에서 탈락시켜 명확히 고치십시오.
6. **주요 모호 대상** (합리적 유추가 도저히 안 될 때만 질문할 것):
   - 피처 개발의 정밀한 경계선 및 수용 범위 (특정 기능 수용 여부)
   - 사용자 계정 권한 및 역할 그룹 (다양한 대안이 존재할 때)
   - 개인정보 보호 규정이나 규제 컴플라이언스 연관 사안

**합리적 기본 유추 대안 예시** (사용자에게 굳이 질문하지 말고 아래 기준으로 추론할 것):
- 데이터 보존(Data retention): 해당 도메인의 보편적인 규정 준수 가이드라인
- 성능 목표치: 일반적인 모바일/웹 앱의 반응성 표준 요구사항
- 에러 복구 및 처리: 사용자 친화적인 알림 레이어 제공 및 기본 동작 복구
- 로그인 및 인증 방식: 프로젝트 표준 세션 인증 또는 보편적인 OAuth2 연동
- 통합 설계 패턴: 프로젝트 성격에 맞춰 자동 구성 (웹 서비스는 REST/GraphQL, 모듈은 클래스/함수 호출, CLI는 표준 인자)

### 성공 기준 정의 표준 (Success Criteria Guidelines)

성공 기준은 반드시 다음과 같아야 합니다:

1. **측정 가능성**: 구체적인 데이터 지표(시간, 백분율 %, 빈도, 누적 처리량)를 포함합니다.
2. **기술 중립성**: 소스 코드 기술, 특정 DB, 웹 프레임워크나 내부 툴에 대해 언급하지 않습니다.
3. **사용자 중심적 관점**: 시스템의 물리적 자원 부하가 아닌 사용자 체감 시간이나 사업적 목표치를 사용합니다.
4. **객관적 검증 가능성**: 소스 코드를 몰라도 누구나 외부에서 검증할 수 있는 형태여야 합니다.

**올바른 성공 기준 예시 (Good)**:
- "사용자가 3분 이내에 결제 과정을 마칠 수 있어야 합니다."
- "동시 사용자 10,000명을 원활히 수용할 수 있어야 합니다."
- "검색 요청 시 95% 이상의 요청에 대해 1초 내로 화면이 갱신되어야 합니다."
- "최종 사용자 업무 소요 시간이 기존 대비 40% 이상 단축되어야 합니다."

**피해야 할 예시 (Bad - 구현 종속적)**:
- "API 응답 속도가 200ms 미만이어야 합니다." (지나치게 기술적, "화면이 즉시 갱신되어야 함" 권장)
- "데이터베이스가 1000 TPS를 견뎌내야 합니다." (구현 디테일, 최종 사용자 체감 성능 지표로 대체 권장)
- "리액트 컴포넌트가 최적화되어 렌더링되어야 합니다." (특정 프레임워크 언급)
- "레디스 캐시 히트율이 80%를 넘어야 합니다." (특정 인프라 언급)logy-specific)
