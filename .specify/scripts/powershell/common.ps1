#!/usr/bin/env pwsh
# common.sh에 해당하는 공통 PowerShell 함수들

# .specify 디렉토리를 상위로 검색하여 저장소 루트 찾기
# 이것은 spec-kit 프로젝트의 기본 마커입니다.
function Find-SpecifyRoot {
    param([string]$StartDir = (Get-Location).Path)

    # 상대 경로 문제 예방을 위해 절대 경로로 정규화
    # 와일드카드 문자([, ], *, ?)가 포함된 경로 처리를 위해 -LiteralPath 사용
    $resolved = Resolve-Path -LiteralPath $StartDir -ErrorAction SilentlyContinue
    $current = if ($resolved) { $resolved.Path } else { $null }
    if (-not $current) { return $null }

    while ($true) {
        if (Test-Path -LiteralPath (Join-Path $current ".specify") -PathType Container) {
            return $current
        }
        $parent = Split-Path $current -Parent
        if ([string]::IsNullOrEmpty($parent) -or $parent -eq $current) {
            return $null
        }
        $current = $parent
    }
}

# git보다 .specify 디렉토리를 우선시하여 저장소 루트 가져오기
# spec-kit이 하위 디렉토리에 초기화된 경우 부모 git 저장소가 선택되는 것을 예방합니다.
function Get-RepoRoot {
    # 먼저 spec-kit 자체 마커인 .specify 디렉토리를 찾습니다.
    $specifyRoot = Find-SpecifyRoot
    if ($specifyRoot) {
        return $specifyRoot
    }

    # .specify가 감지되지 않으면 git으로 포백
    try {
        $result = git rev-parse --show-toplevel 2>$null
        if ($LASTEXITCODE -eq 0) {
            return $result
        }
    } catch {
        # Git 명령 실패
    }

    # git 저장소가 아닌 경우 최종적으로 스크립트 위치로 포백
    # 와일드카드 문자가 포함된 경로 처리를 위해 -LiteralPath 사용
    return (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "../../..")).Path
}

function Get-CurrentBranch {
    # 먼저 SPECIFY_FEATURE 환경 변수가 설정되었는지 확인
    if ($env:SPECIFY_FEATURE) {
        return $env:SPECIFY_FEATURE
    }

    # 그 후 부모가 아닌 spec-kit 루트 기준 git이 사용 가능한지 확인
    $repoRoot = Get-RepoRoot
    if (Test-HasGit) {
        try {
            $result = git -C $repoRoot rev-parse --abbrev-ref HEAD 2>$null
            if ($LASTEXITCODE -eq 0) {
                return $result
            }
        } catch {
            # Git 명령 실패
        }
    }

    # git 저장소가 아닌 경우, 가장 최신의 피처 디렉토리 찾기 시도
    $specsDir = Join-Path $repoRoot "specs"
    
    if (Test-Path $specsDir) {
        $latestFeature = ""
        $highest = 0
        $latestTimestamp = ""

        Get-ChildItem -Path $specsDir -Directory | ForEach-Object {
            if ($_.Name -match '^(\d{8}-\d{6})-') {
                # 타임스탬프 기반 브랜치: 사전 순으로 비교
                $ts = $matches[1]
                if ($ts -gt $latestTimestamp) {
                    $latestTimestamp = $ts
                    $latestFeature = $_.Name
                }
            } elseif ($_.Name -match '^(\d{3,})-') {
                $num = [long]$matches[1]
                if ($num -gt $highest) {
                    $highest = $num
                    # 타임스탬프 브랜치가 아직 감지되지 않은 경우에만 업데이트
                    if (-not $latestTimestamp) {
                        $latestFeature = $_.Name
                    }
                }
            }
        }

        if ($latestFeature) {
            return $latestFeature
        }
    }
    
    # 최종 포백
    return "main"
}

# spec-kit 루트 레벨에 git을 사용할 수 있는지 확인
# git이 설치되어 있고 저장소 루트가 git 작업 트리 내에 있는 경우에만 true 반환
# 일반 저장소(.git 디렉토리) 및 작업 트리/서브모듈(.git 파일) 모두 처리
function Test-HasGit {
    # (git을 사용하는 Get-RepoRoot 호출 전) 먼저 git 명령이 사용 가능한지 확인
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        return $false
    }
    $repoRoot = Get-RepoRoot
    # .git 존재 여부 확인 (작업 트리/서브모듈의 디렉토리 또는 파일)
    # 와일드카드 문자가 포함된 경로 처리를 위해 -LiteralPath 사용
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot ".git"))) {
        return $false
    }
    # 실제로 유효한 git 작업 트리인지 검증
    try {
        $null = git -C $repoRoot rev-parse --is-inside-work-tree 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

# 단일 선택적 경로 세그먼트를 분리합니다 (예: gitflow "feat/004-name" -> "004-name").
# 전체 이름이 슬래시가 없는 정확히 두 개의 세그먼트인 경우에만 해당하며, 그렇지 않으면 원본 이름을 반환합니다.
function Get-SpecKitEffectiveBranchName {
    param([string]$Branch)
    if ($Branch -match '^([^/]+)/([^/]+)$') {
        return $Matches[2]
    }
    return $Branch
}

function Test-FeatureBranch {
    param(
        [string]$Branch,
        [bool]$HasGit = $true
    )
    
    # git 저장소가 아닌 경우 브랜치 명명을 강제할 수 없지만 출력은 제공합니다.
    if (-not $HasGit) {
        Write-Warning "[specify] 경고: Git 저장소가 감지되지 않았습니다. 브랜치 유효성 검사를 건너뜁니다."
        return $true
    }

    $raw = $Branch
    $Branch = Get-SpecKitEffectiveBranchName $raw
    
    # 순차 접두사(3자리 이상)는 허용하되 잘못된 형식의 타임스탬프는 제외
    # 잘못된 형식: 뒤에 슬러그가 없는 7~8자리 날짜 + 6자리 시간 (예: "2026031-143022" 또는 "20260319-143022")
    $hasMalformedTimestamp = ($Branch -match '^[0-9]{7}-[0-9]{6}-') -or ($Branch -match '^(?:\d{7}|\d{8})-\d{6}$')
    $isSequential = ($Branch -match '^[0-9]{3,}-') -and (-not $hasMalformedTimestamp)
    if (-not $isSequential -and $Branch -notmatch '^\d{8}-\d{6}-') {
        [Console]::Error.WriteLine("오류: 피처 브랜치가 아닙니다. 현재 브랜치: $raw")
        [Console]::Error.WriteLine("피처 브랜치 이름은 다음과 같이 지정해야 합니다: 001-feature-name, 1234-feature-name, 또는 20260319-143022-feature-name")
        return $false
    }
    return $true
}

# .specify/feature.json이 Get-FeaturePathsEnv로부터 가져온 활성 FEATURE_DIR과 일치하는 기존 피처 디렉토리를 고정하고 있는 경우 True를 반환합니다. 
# (이를 통해 /speckit.plan이 git 브랜치 패턴 확인을 건너뛸 수 있음)
function Test-FeatureJsonMatchesFeatureDir {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$ActiveFeatureDir
    )

    $featureJson = Join-Path (Join-Path $RepoRoot '.specify') 'feature.json'
    if (-not (Test-Path -LiteralPath $featureJson -PathType Leaf)) {
        return $false
    }

    try {
        $raw = Get-Content -LiteralPath $featureJson -Raw
        $cfg = $raw | ConvertFrom-Json
    } catch {
        return $false
    }

    $fd = $cfg.feature_directory
    if ([string]::IsNullOrWhiteSpace([string]$fd)) {
        return $false
    }

    if (-not [System.IO.Path]::IsPathRooted($fd)) {
        $fd = Join-Path $RepoRoot $fd
    }

    if (-not (Test-Path -LiteralPath $fd -PathType Container)) {
        return $false
    }

    # 두 경로를 모두 정규 절대 경로 형식으로 분석합니다. Resolve-Path(심볼릭 링크 추적 및 canonical한 PS 권장 방식)를 우선적으로 사용하고,
    # Resolve-Path가 값을 출력할 수 없는 경우 [Path]::GetFullPath로 포백합니다. Find-SpecifyRoot에서 사용하는 패턴을 동일하게 적용합니다.
    $resolvedJson = Resolve-Path -LiteralPath $fd -ErrorAction SilentlyContinue
    if ($resolvedJson) {
        $normJson = $resolvedJson.Path
    } else {
        $normJson = [System.IO.Path]::GetFullPath($fd)
    }

    $resolvedActive = Resolve-Path -LiteralPath $ActiveFeatureDir -ErrorAction SilentlyContinue
    if ($resolvedActive) {
        $normActive = $resolvedActive.Path
    } else {
        $normActive = [System.IO.Path]::GetFullPath($ActiveFeatureDir)
    }

    # Windows에서만 대소문자 구분 없이 비교를 수행하며, POSIX 파일 시스템은 대소문자를 구분합니다.
    # PowerShell 5.1은 Windows 전용이고 $IsWindows를 정의하지 않으므로, 정의되지 않은 경우 "Windows 환경"으로 처리합니다.
    if ($null -ne $IsWindows) {
        $onWindows = $IsWindows
    } else {
        $onWindows = $true
    }

    if ($onWindows) {
        $comparison = [System.StringComparison]::OrdinalIgnoreCase
    } else {
        $comparison = [System.StringComparison]::Ordinal
    }

    return [string]::Equals($normJson, $normActive, $comparison)
}

# 숫자/타임스탬프 접두사로 specs/<feature-dir>를 분석합니다 (scripts/bash/common.sh의 find_feature_dir_by_prefix 함수 미러링).
function Find-FeatureDirByPrefix {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$Branch
    )
    $specsDir = Join-Path $RepoRoot 'specs'
    $branchName = Get-SpecKitEffectiveBranchName $Branch

    $prefix = $null
    if ($branchName -match '^(\d{8}-\d{6})-') {
        $prefix = $Matches[1]
    } elseif ($branchName -match '^(\d{3,})-') {
        $prefix = $Matches[1]
    } else {
        return (Join-Path $specsDir $branchName)
    }

    $dirMatches = @()
    if (Test-Path -LiteralPath $specsDir -PathType Container) {
        $dirMatches = @(Get-ChildItem -LiteralPath $specsDir -Filter "$prefix-*" -Directory -ErrorAction SilentlyContinue)
    }

    if ($dirMatches.Count -eq 0) {
        return (Join-Path $specsDir $branchName)
    }
    if ($dirMatches.Count -eq 1) {
        return $dirMatches[0].FullName
    }
    $names = ($dirMatches | ForEach-Object { $_.Name }) -join ' '
    [Console]::Error.WriteLine("오류: 접두사 '$prefix'를 사용하는 여러 스펙 디렉토리가 발견되었습니다: $names")
    [Console]::Error.WriteLine('접두사당 하나의 스펙 디렉토리만 존재하도록 구성하십시오.')
    return $null
}

# 브랜치 기반 접두사 분석. bash의 get_feature_paths 실패(stderr 출력 + exit 1)를 미러링.
function Get-FeatureDirFromBranchPrefixOrExit {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$CurrentBranch
    )
    $resolved = Find-FeatureDirByPrefix -RepoRoot $RepoRoot -Branch $CurrentBranch
    if ($null -eq $resolved) {
        [Console]::Error.WriteLine('오류: 피처 디렉토리 분석에 실패했습니다.')
        exit 1
    }
    return $resolved
}

function Get-FeaturePathsEnv {
    $repoRoot = Get-RepoRoot
    $currentBranch = Get-CurrentBranch
    $hasGit = Test-HasGit

    # 피처 디렉토리 분석. 우선순위:
    #   1. SPECIFY_FEATURE_DIRECTORY 환경 변수 (명시적 오버라이드)
    #   2. .specify/feature.json의 "feature_directory" 키 (/speckit.specify에서 생성)
    #   3. 브랜치 이름 기반의 접두사 조회 (scripts/bash/common.sh와 동일)
    $featureJson = Join-Path $repoRoot '.specify/feature.json'
    if ($env:SPECIFY_FEATURE_DIRECTORY) {
        $featureDir = $env:SPECIFY_FEATURE_DIRECTORY
        # 저장소 루트 기준 상대 경로를 절대 경로로 정규화
        if (-not [System.IO.Path]::IsPathRooted($featureDir)) {
            $featureDir = Join-Path $repoRoot $featureDir
        }
    } elseif (Test-Path $featureJson) {
        $featureJsonRaw = Get-Content -LiteralPath $featureJson -Raw
        try {
            $featureConfig = $featureJsonRaw | ConvertFrom-Json
        } catch {
            [Console]::Error.WriteLine("오류: .specify/feature.json 파싱에 실패했습니다: $_")
            exit 1
        }
        if ($featureConfig.feature_directory) {
            $featureDir = $featureConfig.feature_directory
            # 저장소 루트 기준 상대 경로를 절대 경로로 정규화
            if (-not [System.IO.Path]::IsPathRooted($featureDir)) {
                $featureDir = Join-Path $repoRoot $featureDir
            }
        } else {
            $featureDir = Get-FeatureDirFromBranchPrefixOrExit -RepoRoot $repoRoot -CurrentBranch $currentBranch
        }
    } else {
        $featureDir = Get-FeatureDirFromBranchPrefixOrExit -RepoRoot $repoRoot -CurrentBranch $currentBranch
    }
    
    [PSCustomObject]@{
        REPO_ROOT     = $repoRoot
        CURRENT_BRANCH = $currentBranch
        HAS_GIT       = $hasGit
        FEATURE_DIR   = $featureDir
        FEATURE_SPEC  = Join-Path $featureDir 'spec.md'
        IMPL_PLAN     = Join-Path $featureDir 'plan.md'
        TASKS         = Join-Path $featureDir 'tasks.md'
        RESEARCH      = Join-Path $featureDir 'research.md'
        DATA_MODEL    = Join-Path $featureDir 'data-model.md'
        QUICKSTART    = Join-Path $featureDir 'quickstart.md'
        CONTRACTS_DIR = Join-Path $featureDir 'contracts'
    }
}

function Test-FileExists {
    param([string]$Path, [string]$Description)
    if (Test-Path -Path $Path -PathType Leaf) {
        Write-Output "  ✓ $Description"
        return $true
    } else {
        Write-Output "  ✗ $Description"
        return $false
    }
}

function Test-DirHasFiles {
    param([string]$Path, [string]$Description)
    if ((Test-Path -Path $Path -PathType Container) -and (Get-ChildItem -Path $Path -ErrorAction SilentlyContinue | Where-Object { -not $_.PSIsContainer } | Select-Object -First 1)) {
        Write-Output "  ✓ $Description"
        return $true
    } else {
        Write-Output "  ✗ $Description"
        return $false
    }
}

# 사용 가능한 Python 3 실행 파일(python3, python, py -3)을 검색합니다.
# 검색된 명령/인수를 배열 형태로 반환하며, 검색되지 않는 경우 $null을 반환합니다.
function Get-Python3Command {
    if (Get-Command python3 -ErrorAction SilentlyContinue) { return @('python3') }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $ver = & python --version 2>&1
        if ($ver -match 'Python 3') { return @('python') }
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $ver = & py -3 --version 2>&1
        if ($ver -match 'Python 3') { return @('py', '-3') }
    }
    return $null
}

# 우선순위 스택을 사용하여 템플릿 이름을 파일 경로로 분석합니다:
#   1. .specify/templates/overrides/
#   2. .specify/presets/<preset-id>/templates/ (.registry에 정의된 우선순위 기준 정렬)
#   3. .specify/extensions/<ext-id>/templates/
#   4. .specify/templates/ (코어)
function Resolve-Template {
    param(
        [Parameter(Mandatory=$true)][string]$TemplateName,
        [Parameter(Mandatory=$true)][string]$RepoRoot
    )

    $base = Join-Path $RepoRoot '.specify/templates'

    # 우선순위 1: 프로젝트 오버라이드
    $override = Join-Path $base "overrides/$TemplateName.md"
    if (Test-Path $override) { return $override }

    # 우선순위 2: 설치된 프리셋 (.registry에 정의된 우선순위 기준 정렬)
    $presetsDir = Join-Path $RepoRoot '.specify/presets'
    if (Test-Path $presetsDir) {
        $registryFile = Join-Path $presetsDir '.registry'
        $sortedPresets = @()
        if (Test-Path $registryFile) {
            try {
                $registryData = Get-Content $registryFile -Raw | ConvertFrom-Json
                $presets = $registryData.presets
                if ($presets) {
                    $sortedPresets = $presets.PSObject.Properties |
                        Where-Object { $null -eq $_.Value.enabled -or $_.Value.enabled -ne $false } |
                        Sort-Object { if ($null -ne $_.Value.priority) { $_.Value.priority } else { 10 } } |
                        ForEach-Object { $_.Name }
                }
            } catch {
                # 포백: 디렉토리 알파벳순 정렬
                $sortedPresets = @()
            }
        }

        if ($sortedPresets.Count -gt 0) {
            foreach ($presetId in $sortedPresets) {
                $candidate = Join-Path $presetsDir "$presetId/templates/$TemplateName.md"
                if (Test-Path $candidate) { return $candidate }
            }
        } else {
            # 포백: 디렉토리 알파벳순 정렬
            foreach ($preset in Get-ChildItem -Path $presetsDir -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike '.*' }) {
                $candidate = Join-Path $preset.FullName "templates/$TemplateName.md"
                if (Test-Path $candidate) { return $candidate }
            }
        }
    }

    # 우선순위 3: 확장 도구가 제공한 템플릿
    $extDir = Join-Path $RepoRoot '.specify/extensions'
    if (Test-Path $extDir) {
        foreach ($ext in Get-ChildItem -Path $extDir -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike '.*' } | Sort-Object Name) {
            $candidate = Join-Path $ext.FullName "templates/$TemplateName.md"
            if (Test-Path $candidate) { return $candidate }
        }
    }

    # 우선순위 4: 코어 템플릿
    $core = Join-Path $base "$TemplateName.md"
    if (Test-Path $core) { return $core }

    return $null
}

# 구성 전략(prepend, append, wrap 등)을 기반으로 템플릿 명칭을 병합된 본문 내용으로 분석합니다.
# 프리셋 매니페스트로부터 병합(composition) 전략 정보를 읽어 다중 레이어를 병합합니다.
function Resolve-TemplateContent {
    param(
        [Parameter(Mandatory=$true)][string]$TemplateName,
        [Parameter(Mandatory=$true)][string]$RepoRoot
    )

    $base = Join-Path $RepoRoot '.specify/templates'

    # 모든 레이어를 수집합니다 (우선순위가 가장 높은 것부터 우선)
    $layerPaths = @()
    $layerStrategies = @()

    # 우선순위 1: 프로젝트 오버라이드 (항상 "replace" 전략)
    $override = Join-Path $base "overrides/$TemplateName.md"
    if (Test-Path $override) {
        $layerPaths += $override
        $layerStrategies += 'replace'
    }

    # 우선순위 2: 설치된 프리셋 (.registry에 정의된 우선순위 기준 정렬)
    $presetsDir = Join-Path $RepoRoot '.specify/presets'
    if (Test-Path $presetsDir) {
        $registryFile = Join-Path $presetsDir '.registry'
        $sortedPresets = @()
        if (Test-Path $registryFile) {
            try {
                $registryData = Get-Content $registryFile -Raw | ConvertFrom-Json
                $presets = $registryData.presets
                if ($presets) {
                    $sortedPresets = $presets.PSObject.Properties |
                        Where-Object { $null -eq $_.Value.enabled -or $_.Value.enabled -ne $false } |
                        Sort-Object { if ($null -ne $_.Value.priority) { $_.Value.priority } else { 10 } } |
                        ForEach-Object { $_.Name }
                }
            } catch {
                $sortedPresets = @()
            }
        }

        if ($sortedPresets.Count -gt 0) {
            $pyCmd = Get-Python3Command
            if (-not $pyCmd) {
                # 무시될 수 있는 strategy 필드를 가진 프리셋이 있는지 확인
                foreach ($pid in $sortedPresets) {
                    $mf = Join-Path $presetsDir "$pid/preset.yml"
                    if ((Test-Path $mf) -and (Select-String -Path $mf -Pattern 'strategy:' -Quiet -ErrorAction SilentlyContinue)) {
                        Write-Warning "Python 3를 찾을 수 없습니다. 프리셋 작성(composition) 전략이 무시됩니다."
                        break
                    }
                }
            }
            $yamlWarned = $false
            foreach ($presetId in $sortedPresets) {
                # 프리셋 매니페스트로부터 strategy 및 파일 경로 읽기
                $strategy = 'replace'
                $manifestFilePath = ''
                $manifest = Join-Path $presetsDir "$presetId/preset.yml"
                if ((Test-Path $manifest) -and $pyCmd) {
                    try {
                        # Python을 사용해 YAML 매니페스트에서 strategy 및 파일 경로 파싱
                        $pyArgs = if ($pyCmd.Count -gt 1) { $pyCmd[1..($pyCmd.Count-1)] } else { @() }
                        $pyStderrFile = [System.IO.Path]::GetTempFileName()
                        $stratResult = & $pyCmd[0] @pyArgs -c @"
import sys
try:
    import yaml
except ImportError:
    print('yaml_missing', file=sys.stderr)
    print('replace\t')
    sys.exit(0)
try:
    with open(sys.argv[1]) as f:
        data = yaml.safe_load(f)
    for t in data.get('provides', {}).get('templates', []):
        if t.get('name') == sys.argv[2] and t.get('type', 'template') == 'template':
            print(t.get('strategy', 'replace') + '\t' + t.get('file', ''))
            sys.exit(0)
    print('replace\t')
except Exception:
    print('replace\t')
"@ $manifest $TemplateName 2>$pyStderrFile
                        if ($stratResult) {
                            $parts = $stratResult.Trim() -split "`t", 2
                            $strategy = $parts[0].ToLowerInvariant()
                            if ($parts.Count -gt 1 -and $parts[1]) { $manifestFilePath = $parts[1] }
                        }
                        if (-not $yamlWarned -and (Test-Path $pyStderrFile) -and (Get-Content $pyStderrFile -Raw -ErrorAction SilentlyContinue) -match 'yaml_missing') {
                            Write-Warning "PyYAML을 사용할 수 없습니다. 작성(composition) 전략이 무시될 수 있습니다."
                            $yamlWarned = $true
                        }
                        Remove-Item $pyStderrFile -Force -ErrorAction SilentlyContinue
                    } catch {
                        $strategy = 'replace'
                        if ($pyStderrFile) { Remove-Item $pyStderrFile -Force -ErrorAction SilentlyContinue }
                    }
                }
                # 매니페스트 파일 경로를 먼저 시도하고, 그 후 관례적인(convention) 경로 시도
                $candidate = $null
                if ($manifestFilePath) {
                    # 절대 경로 및 상위 디렉토리 탐색(..) 거부
                    if ([System.IO.Path]::IsPathRooted($manifestFilePath) -or $manifestFilePath -match '\.\.[\\/]') {
                        $manifestFilePath = ''
                    }
                }
                if ($manifestFilePath) {
                    $mf = Join-Path $presetsDir "$presetId/$manifestFilePath"
                    if (Test-Path $mf) { $candidate = $mf }
                }
                if (-not $candidate) {
                    $cf = Join-Path $presetsDir "$presetId/templates/$TemplateName.md"
                    if (Test-Path $cf) { $candidate = $cf }
                }
                if ($candidate) {
                    $layerPaths += $candidate
                    $layerStrategies += $strategy
                }
            }
        } else {
            # 포백: 디렉토리 알파벳순 정렬 (레지스트리가 없거나 파싱 오류 발생 시)
            foreach ($preset in Get-ChildItem -Path $presetsDir -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike '.*' }) {
                $candidate = Join-Path $preset.FullName "templates/$TemplateName.md"
                if (Test-Path $candidate) {
                    $layerPaths += $candidate
                    $layerStrategies += 'replace'
                }
            }
        }
    }

    # 우선순위 3: 확장 기능이 제공한 템플릿 (항상 "replace" 전략)
    $extDir = Join-Path $RepoRoot '.specify/extensions'
    if (Test-Path $extDir) {
        foreach ($ext in Get-ChildItem -Path $extDir -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike '.*' } | Sort-Object Name) {
            $candidate = Join-Path $ext.FullName "templates/$TemplateName.md"
            if (Test-Path $candidate) {
                $layerPaths += $candidate
                $layerStrategies += 'replace'
            }
        }
    }

    # 우선순위 4: 코어 템플릿 (항상 "replace" 전략)
    $core = Join-Path $base "$TemplateName.md"
    if (Test-Path $core) {
        $layerPaths += $core
        $layerStrategies += 'replace'
    }

    if ($layerPaths.Count -eq 0) { return $null }

    # 최상위(가장 높은 우선순위) 레이어가 replace인 경우 완벽하게 승리하며, 하위 레이어는 해당 전략에 관계없이 무시됩니다.
    if ($layerStrategies[0] -eq 'replace') {
        return (Get-Content $layerPaths[0] -Raw)
    }

    # replace가 아닌 다른 전략을 사용하는 레이어가 있는지 확인
    $hasComposition = $false
    foreach ($s in $layerStrategies) {
        if ($s -ne 'replace') { $hasComposition = $true; break }
    }

    if (-not $hasComposition) {
        return (Get-Content $layerPaths[0] -Raw)
    }

    # 유효한 베이스 찾기: 가장 높은 우선순위(인덱스 0)부터 시작해 아래로 스캔하여 가장 가까운 replace 레이어를 찾습니다. 이 베이스 위의 레이어들만 병합합니다.
    $baseIdx = -1
    for ($i = 0; $i -lt $layerPaths.Count; $i++) {
        if ($layerStrategies[$i] -eq 'replace') {
            $baseIdx = $i
            break
        }
    }
    if ($baseIdx -lt 0) { return $null }

    $content = Get-Content $layerPaths[$baseIdx] -Raw

    for ($i = $baseIdx - 1; $i -ge 0; $i--) {
        $path = $layerPaths[$i]
        $strat = $layerStrategies[$i]
        $layerContent = Get-Content $path -Raw

        switch ($strat) {
            'replace' { $content = $layerContent }
            'prepend' { $content = "$layerContent`n`n$content" }
            'append'  { $content = "$content`n`n$layerContent" }
            'wrap'    {
                if (-not $layerContent.Contains('{CORE_TEMPLATE}')) {
                    throw "Wrap strategy missing {CORE_TEMPLATE} placeholder"
                }
                $content = $layerContent.Replace('{CORE_TEMPLATE}', $content)
            }
            default { throw "Unknown strategy: $strat" }
        }
    }

    return $content
}