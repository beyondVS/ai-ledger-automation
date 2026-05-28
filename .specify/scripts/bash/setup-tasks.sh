#!/usr/bin/env bash

set -e

# Parse command line arguments
JSON_MODE=false

for arg in "$@"; do
    case "$arg" in
        --json) JSON_MODE=true ;;
        --help|-h)
            echo "사용법: $0 [--json] [--help]"
            echo "  --json    결과를 JSON 형식으로 출력"
            echo "  --help    이 도움말 메시지 표시"
            exit 0
            ;;
        *) echo "오류: 알 수 없는 옵션 '$arg'입니다." >&2; exit 1 ;;
    esac
done

# Source common functions
SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Get feature paths
_paths_output=$(get_feature_paths) || { echo "오류: 피처 경로 분석에 실패했습니다." >&2; exit 1; }
eval "$_paths_output"
unset _paths_output

# Validate branch
# If feature.json pins an existing feature directory, branch naming is not required.
if ! feature_json_matches_feature_dir "$REPO_ROOT" "$FEATURE_DIR"; then
    check_feature_branch "$CURRENT_BRANCH" "$HAS_GIT" || exit 1
fi

if [[ ! -f "$IMPL_PLAN" ]]; then
    echo "오류: $FEATURE_DIR 에서 plan.md를 찾을 수 없습니다." >&2
    echo "먼저 /speckit-plan 을 실행하여 구현 계획을 생성하십시오." >&2
    exit 1
fi

if [[ ! -f "$FEATURE_SPEC" ]]; then
    echo "오류: $FEATURE_DIR 에서 spec.md를 찾을 수 없습니다." >&2
    echo "먼저 /speckit-specify 를 실행하여 피처 구조를 생성하십시오." >&2
    exit 1
fi

# Build available docs list
docs=()
[[ -f "$RESEARCH" ]] && docs+=("research.md")
[[ -f "$DATA_MODEL" ]] && docs+=("data-model.md")
if [[ -d "$CONTRACTS_DIR" ]] && [[ -n "$(ls -A "$CONTRACTS_DIR" 2>/dev/null)" ]]; then
    docs+=("contracts/")
fi
[[ -f "$QUICKSTART" ]] && docs+=("quickstart.md")

# Resolve tasks template through override stack
TASKS_TEMPLATE=$(resolve_template "tasks-template" "$REPO_ROOT") || true
if [[ -z "$TASKS_TEMPLATE" ]] || [[ ! -f "$TASKS_TEMPLATE" ]]; then
    echo "오류: 저장소 루트에서 태스크 템플릿을 찾을 수 없습니다: $REPO_ROOT" >&2
    echo "템플릿 확인 순서: 오버라이드 -> 프리셋 -> 확장 -> 코어. 예상되는 코어 템플릿 위치: $REPO_ROOT/.specify/templates/tasks-template.md. 계속 진행하려면 'tasks-template.md'가 '.specify/templates/overrides/', 프리셋 템플릿, 확장 템플릿에 존재하는지 확인하거나 공유/코어 템플릿을 복원하십시오 (예: 'specify init'을 재실행하여 '.specify/templates/tasks-template.md'가 존재하도록 함)." >&2
    exit 1
fi

# Output results
if $JSON_MODE; then
    if has_jq; then
        if [[ ${#docs[@]} -eq 0 ]]; then
            json_docs="[]"
        else
            json_docs=$(printf '%s\n' "${docs[@]}" | jq -R . | jq -s .)
        fi
        jq -cn \
            --arg feature_dir "$FEATURE_DIR" \
            --argjson docs "$json_docs" \
            --arg tasks_template "${TASKS_TEMPLATE:-}" \
            '{FEATURE_DIR:$feature_dir,AVAILABLE_DOCS:$docs,TASKS_TEMPLATE:$tasks_template}'
    else
        if [[ ${#docs[@]} -eq 0 ]]; then
            json_docs="[]"
        else
            json_docs=$(for d in "${docs[@]}"; do printf '"%s",' "$(json_escape "$d")"; done)
            json_docs="[${json_docs%,}]"
        fi
        printf '{"FEATURE_DIR":"%s","AVAILABLE_DOCS":%s,"TASKS_TEMPLATE":"%s"}\n' \
            "$(json_escape "$FEATURE_DIR")" "$json_docs" "$(json_escape "${TASKS_TEMPLATE:-}")"
    fi
else
    echo "FEATURE_DIR: $FEATURE_DIR"
    echo "TASKS_TEMPLATE: ${TASKS_TEMPLATE:-찾을 수 없음}"
    echo "AVAILABLE_DOCS:"
    check_file "$RESEARCH" "research.md"
    check_file "$DATA_MODEL" "data-model.md"
    check_dir "$CONTRACTS_DIR" "contracts/"
    check_file "$QUICKSTART" "quickstart.md"
fi
