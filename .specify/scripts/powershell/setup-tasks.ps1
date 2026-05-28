#!/usr/bin/env pwsh

[CmdletBinding()]
param(
    [switch]$Json,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help) {
    Write-Output "사용법: setup-tasks.ps1 [-Json] [-Help]"
    exit 0
}

# 공통 함수 로드
. "$PSScriptRoot/common.ps1"

# 피처 경로 가져오기 및 브랜치 유효성 검사
$paths = Get-FeaturePathsEnv

# feature.json이 기존 피처 디렉토리를 고정하고 있는 경우, 브랜치 명명은 필요하지 않습니다.
if (-not (Test-FeatureJsonMatchesFeatureDir -RepoRoot $paths.REPO_ROOT -ActiveFeatureDir $paths.FEATURE_DIR)) {
    if (-not (Test-FeatureBranch -Branch $paths.CURRENT_BRANCH -HasGit $paths.HAS_GIT)) {
        exit 1
    }
}

if (-not (Test-Path $paths.IMPL_PLAN -PathType Leaf)) {
    [Console]::Error.WriteLine("오류: $($paths.FEATURE_DIR) 에서 plan.md를 찾을 수 없습니다.")
    [Console]::Error.WriteLine("먼저 /speckit.plan 을 실행하여 구현 계획을 생성하십시오.")
    exit 1
}

if (-not (Test-Path $paths.FEATURE_SPEC -PathType Leaf)) {
    [Console]::Error.WriteLine("오류: $($paths.FEATURE_DIR) 에서 spec.md를 찾을 수 없습니다.")
    [Console]::Error.WriteLine("먼저 /speckit.specify 를 실행하여 피처 구조를 생성하십시오.")
    exit 1
}

# 사용 가능한 문서 목록 생성
$docs = @()
if (Test-Path $paths.RESEARCH) { $docs += 'research.md' }
if (Test-Path $paths.DATA_MODEL) { $docs += 'data-model.md' }
if ((Test-Path $paths.CONTRACTS_DIR) -and (Get-ChildItem -Path $paths.CONTRACTS_DIR -ErrorAction SilentlyContinue | Select-Object -First 1)) {
    $docs += 'contracts/'
}
if (Test-Path $paths.QUICKSTART) { $docs += 'quickstart.md' }

# 오버라이드 스택을 통해 태스크 템플릿 확인
$tasksTemplate = Resolve-Template -TemplateName 'tasks-template' -RepoRoot $paths.REPO_ROOT
if (-not $tasksTemplate -or -not (Test-Path -LiteralPath $tasksTemplate -PathType Leaf)) {
    $expectedCoreTemplate = Join-Path $paths.REPO_ROOT '.specify/templates/tasks-template.md'
    [Console]::Error.WriteLine("오류: 저장소 루트에서 태스크 템플릿을 찾을 수 없습니다: $($paths.REPO_ROOT)`n템플릿 확인 순서: 오버라이드 -> 프리셋 -> 확장 -> 코어.`n예상되는 코어 템플릿 위치: $expectedCoreTemplate`n계속 진행하려면 'tasks-template.md'가 '.specify/templates/overrides/', 프리셋 템플릿, 확장 템플릿에 존재하는지 확인하거나 공유/코어 템플릿을 복원하십시오(예: 'specify init'을 재실행하여 '.specify/templates/tasks-template.md'가 존재하도록 함).")
    exit 1
}
$tasksTemplate = (Resolve-Path -LiteralPath $tasksTemplate).Path

# 결과 출력
if ($Json) {
    [PSCustomObject]@{
        FEATURE_DIR    = $paths.FEATURE_DIR
        AVAILABLE_DOCS = $docs
        TASKS_TEMPLATE = $tasksTemplate
    } | ConvertTo-Json -Compress
} else {
    Write-Output "FEATURE_DIR: $($paths.FEATURE_DIR)"
    Write-Output "TASKS_TEMPLATE: $(if ($tasksTemplate) { $tasksTemplate } else { '찾을 수 없음' })"
    Write-Output "AVAILABLE_DOCS:"
    Test-FileExists -Path $paths.RESEARCH -Description 'research.md' | Out-Null
    Test-FileExists -Path $paths.DATA_MODEL -Description 'data-model.md' | Out-Null
    Test-DirHasFiles -Path $paths.CONTRACTS_DIR -Description 'contracts/' | Out-Null
    Test-FileExists -Path $paths.QUICKSTART -Description 'quickstart.md' | Out-Null
}
