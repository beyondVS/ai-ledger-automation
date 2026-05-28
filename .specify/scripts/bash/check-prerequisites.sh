#!/usr/bin/env bash

# 통합 사전 준비 사항 확인 스크립트
#
# 이 스크립트는 스펙 기반 개발(Spec-Driven Development) 워크플로우를 위한 통합 사전 준비 사항 확인 기능을 제공합니다.
# 기존에 여러 스크립트에 분산되어 있던 기능을 하나로 통합했습니다.
#
# 사용법: ./check-prerequisites.sh [옵션]
#
# 옵션:
#   --json              JSON 형식으로 결과 출력
#   --require-tasks     tasks.md 파일 존재 필수 요구 (구현 단계에서 사용)
#   --include-tasks     AVAILABLE_DOCS 목록에 tasks.md 파일 포함
#   --paths-only        경로 변수만 출력 (사전 검증 생략)
#   --help, -h          도움말 메시지 표시
#
# 출력:
#   JSON 모드: {"FEATURE_DIR":"...", "AVAILABLE_DOCS":["..."]}
#   텍스트 모드: FEATURE_DIR:... \n AVAILABLE_DOCS: \n ✓/✗ file.md
#   경로 전용 모드: REPO_ROOT: ... \n BRANCH: ... \n FEATURE_DIR: ... 등

set -e

# Parse command line arguments
JSON_MODE=false
REQUIRE_TASKS=false
INCLUDE_TASKS=false
PATHS_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --json)
            JSON_MODE=true
            ;;
        --require-tasks)
            REQUIRE_TASKS=true
            ;;
        --include-tasks)
            INCLUDE_TASKS=true
            ;;
        --paths-only)
            PATHS_ONLY=true
            ;;
        --help|-h)
            cat << 'EOF'
사용법: check-prerequisites.sh [옵션]

스펙 기반 개발(Spec-Driven Development) 워크플로우를 위한 통합 사전 준비 사항 확인 스크립트입니다.

옵션:
  --json              JSON 형식으로 결과 출력
  --require-tasks     tasks.md 파일 존재 필수 요구 (구현 단계에서 사용)
  --include-tasks     AVAILABLE_DOCS 목록에 tasks.md 파일 포함
  --paths-only        경로 변수만 출력 (사전 준비 사항 검증 생략)
  --help, -h          이 도움말 메시지 표시

예시:
  # 태스크 사전 준비 사항 확인 (plan.md 필요)
  ./check-prerequisites.sh --json
  
  # 구현 사전 준비 사항 확인 (plan.md + tasks.md 필요)
  ./check-prerequisites.sh --json --require-tasks --include-tasks
  
  # 피처 경로만 가져오기 (검증 생략)
  ./check-prerequisites.sh --paths-only
  
EOF
            exit 0
            ;;
        *)
            echo "오류: 알 수 없는 옵션 '$arg'입니다. 사용법은 --help를 참조하십시오." >&2
            exit 1
            ;;
    esac
done

# Source common functions
SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# 피처 경로 가져오기
_paths_output=$(get_feature_paths) || { echo "오류: 피처 경로 분석에 실패했습니다." >&2; exit 1; }
eval "$_paths_output"
unset _paths_output

# If paths-only mode, output paths and exit (no validation)
if $PATHS_ONLY; then
    if $JSON_MODE; then
        # Minimal JSON paths payload (no validation performed)
        if has_jq; then
            jq -cn \
                --arg repo_root "$REPO_ROOT" \
                --arg branch "$CURRENT_BRANCH" \
                --arg feature_dir "$FEATURE_DIR" \
                --arg feature_spec "$FEATURE_SPEC" \
                --arg impl_plan "$IMPL_PLAN" \
                --arg tasks "$TASKS" \
                '{REPO_ROOT:$repo_root,BRANCH:$branch,FEATURE_DIR:$feature_dir,FEATURE_SPEC:$feature_spec,IMPL_PLAN:$impl_plan,TASKS:$tasks}'
        else
            printf '{"REPO_ROOT":"%s","BRANCH":"%s","FEATURE_DIR":"%s","FEATURE_SPEC":"%s","IMPL_PLAN":"%s","TASKS":"%s"}\n' \
                "$(json_escape "$REPO_ROOT")" "$(json_escape "$CURRENT_BRANCH")" "$(json_escape "$FEATURE_DIR")" "$(json_escape "$FEATURE_SPEC")" "$(json_escape "$IMPL_PLAN")" "$(json_escape "$TASKS")"
        fi
    else
        echo "REPO_ROOT: $REPO_ROOT"
        echo "BRANCH: $CURRENT_BRANCH"
        echo "FEATURE_DIR: $FEATURE_DIR"
        echo "FEATURE_SPEC: $FEATURE_SPEC"
        echo "IMPL_PLAN: $IMPL_PLAN"
        echo "TASKS: $TASKS"
    fi
    exit 0
fi

# Validate branch name
check_feature_branch "$CURRENT_BRANCH" "$HAS_GIT" || exit 1

# 필수 디렉토리 및 파일 검증
if [[ ! -d "$FEATURE_DIR" ]]; then
    echo "오류: 피처 디렉토리를 찾을 수 없습니다: $FEATURE_DIR" >&2
    echo "먼저 /speckit-specify 를 실행하여 피처 구조를 생성하십시오." >&2
    exit 1
fi

if [[ ! -f "$IMPL_PLAN" ]]; then
    echo "오류: $FEATURE_DIR 에서 plan.md를 찾을 수 없습니다." >&2
    echo "먼저 /speckit-plan 을 실행하여 구현 계획을 생성하십시오." >&2
    exit 1
fi

# 필요한 경우 tasks.md 확인
if $REQUIRE_TASKS && [[ ! -f "$TASKS" ]]; then
    echo "오류: $FEATURE_DIR 에서 tasks.md를 찾을 수 없습니다." >&2
    echo "먼저 /speckit-tasks 를 실행하여 태스크 목록을 생성하십시오." >&2
    exit 1
fi

# Build list of available documents
docs=()

# Always check these optional docs
[[ -f "$RESEARCH" ]] && docs+=("research.md")
[[ -f "$DATA_MODEL" ]] && docs+=("data-model.md")

# Check contracts directory (only if it exists and has files)
if [[ -d "$CONTRACTS_DIR" ]] && [[ -n "$(ls -A "$CONTRACTS_DIR" 2>/dev/null)" ]]; then
    docs+=("contracts/")
fi

[[ -f "$QUICKSTART" ]] && docs+=("quickstart.md")

# Include tasks.md if requested and it exists
if $INCLUDE_TASKS && [[ -f "$TASKS" ]]; then
    docs+=("tasks.md")
fi

# Output results
if $JSON_MODE; then
    # Build JSON array of documents
    if has_jq; then
        if [[ ${#docs[@]} -eq 0 ]]; then
            json_docs="[]"
        else
            json_docs=$(printf '%s\n' "${docs[@]}" | jq -R . | jq -s .)
        fi
        jq -cn \
            --arg feature_dir "$FEATURE_DIR" \
            --argjson docs "$json_docs" \
            '{FEATURE_DIR:$feature_dir,AVAILABLE_DOCS:$docs}'
    else
        if [[ ${#docs[@]} -eq 0 ]]; then
            json_docs="[]"
        else
            json_docs=$(for d in "${docs[@]}"; do printf '"%s",' "$(json_escape "$d")"; done)
            json_docs="[${json_docs%,}]"
        fi
        printf '{"FEATURE_DIR":"%s","AVAILABLE_DOCS":%s}\n' "$(json_escape "$FEATURE_DIR")" "$json_docs"
    fi
else
    # Text output
    echo "FEATURE_DIR:$FEATURE_DIR"
    echo "AVAILABLE_DOCS:"
    
    # Show status of each potential document
    check_file "$RESEARCH" "research.md"
    check_file "$DATA_MODEL" "data-model.md"
    check_dir "$CONTRACTS_DIR" "contracts/"
    check_file "$QUICKSTART" "quickstart.md"
    
    if $INCLUDE_TASKS; then
        check_file "$TASKS" "tasks.md"
    fi
fi
