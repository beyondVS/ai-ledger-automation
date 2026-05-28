#!/usr/bin/env pwsh
# 피처를 위한 구현 계획 설정

[CmdletBinding()]
param(
    [switch]$Json,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

# 도움말 요청 시 표시
if ($Help) {
    Write-Output "사용법: ./setup-plan.ps1 [-Json] [-Help]"
    Write-Output "  -Json     결과를 JSON 형식으로 출력"
    Write-Output "  -Help     이 도움말 메시지 표시"
    exit 0
}

# 공통 함수 로드
. "$PSScriptRoot/common.ps1"

# 공통 함수로부터 모든 경로 및 변수 가져오기
$paths = Get-FeaturePathsEnv

# feature.json이 기존 피처 디렉토리를 고정하고 있는 경우, 브랜치 명명은 필요하지 않습니다.
if (-not (Test-FeatureJsonMatchesFeatureDir -RepoRoot $paths.REPO_ROOT -ActiveFeatureDir $paths.FEATURE_DIR)) {
    if (-not (Test-FeatureBranch -Branch $paths.CURRENT_BRANCH -HasGit $paths.HAS_GIT)) {
        exit 1
    }
}

# 피처 디렉토리가 존재하는지 확인
New-Item -ItemType Directory -Path $paths.FEATURE_DIR -Force | Out-Null

# 계획 템플릿이 존재하면 복사하고, 존재하지 않으면 기록하거나 빈 파일을 생성합니다.
$template = Resolve-Template -TemplateName 'plan-template' -RepoRoot $paths.REPO_ROOT
if ($template -and (Test-Path $template)) { 
    # BOM이 없는 UTF-8 인코딩으로 템플릿 내용을 읽어 구현 계획 파일에 씁니다.
    $content = [System.IO.File]::ReadAllText($template)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($paths.IMPL_PLAN, $content, $utf8NoBom)
} else {
    Write-Warning "계획 템플릿을 찾을 수 없습니다."
    # 템플릿이 존재하지 않으면 기본 계획 파일 생성
    New-Item -ItemType File -Path $paths.IMPL_PLAN -Force | Out-Null
}

# 결과 출력
if ($Json) {
    $result = [PSCustomObject]@{ 
        FEATURE_SPEC = $paths.FEATURE_SPEC
        IMPL_PLAN = $paths.IMPL_PLAN
        SPECS_DIR = $paths.FEATURE_DIR
        BRANCH = $paths.CURRENT_BRANCH
        HAS_GIT = $paths.HAS_GIT
    }
    $result | ConvertTo-Json -Compress
} else {
    Write-Output "FEATURE_SPEC: $($paths.FEATURE_SPEC)"
    Write-Output "IMPL_PLAN: $($paths.IMPL_PLAN)"
    Write-Output "SPECS_DIR: $($paths.FEATURE_DIR)"
    Write-Output "BRANCH: $($paths.CURRENT_BRANCH)"
    Write-Output "HAS_GIT: $($paths.HAS_GIT)"
}
