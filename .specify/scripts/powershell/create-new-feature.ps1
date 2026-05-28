#!/usr/bin/env pwsh
# 새로운 피처 생성
[CmdletBinding()]
param(
    [switch]$Json,
    [switch]$AllowExistingBranch,
    [switch]$DryRun,
    [string]$ShortName,
    [Parameter()]
    [long]$Number = 0,
    [switch]$Timestamp,
    [switch]$Help,
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$FeatureDescription
)
$ErrorActionPreference = 'Stop'

# 도움말 요청 시 표시
if ($Help) {
    Write-Host "사용법: ./create-new-feature.ps1 [-Json] [-DryRun] [-AllowExistingBranch] [-ShortName <name>] [-Number N] [-Timestamp] <feature description>"
    Write-Host ""
    Write-Host "옵션:"
    Write-Host "  -Json               JSON 형식으로 출력"
    Write-Host "  -DryRun             브랜치, 디렉토리 또는 파일을 생성하지 않고 브랜치 이름 및 경로만 계산"
    Write-Host "  -AllowExistingBranch  브랜치가 이미 존재하는 경우 오류를 생성하는 대신 해당 브랜치로 전환"
    Write-Host "  -ShortName <name>   브랜치에 대한 사용자 정의 짧은 이름(2~4단어)을 지정"
    Write-Host "  -Number N           브랜치 번호를 수동으로 지정 (자동 감지보다 우선함)"
    Write-Host "  -Timestamp          순차 번호 대신 타임스탬프 접두사 (YYYYMMDD-HHMMSS) 사용"
    Write-Host "  -Help               이 도움말 메시지 표시"
    Write-Host ""
    Write-Host "예시:"
    Write-Host "  ./create-new-feature.ps1 'Add user authentication system' -ShortName 'user-auth'"
    Write-Host "  ./create-new-feature.ps1 'Implement OAuth2 integration for API'"
    Write-Host "  ./create-new-feature.ps1 -Timestamp -ShortName 'user-auth' 'Add user authentication'"
    exit 0
}

# 피처 설명이 제공되었는지 확인
if (-not $FeatureDescription -or $FeatureDescription.Count -eq 0) {
    Write-Error "사용법: ./create-new-feature.ps1 [-Json] [-DryRun] [-AllowExistingBranch] [-ShortName <name>] [-Number N] [-Timestamp] <feature description>"
    exit 1
}

$featureDesc = ($FeatureDescription -join ' ').Trim()

# 트리밍 후 설명이 비어있지 않은지 검증 (예: 공백만 입력한 경우)
if ([string]::IsNullOrWhiteSpace($featureDesc)) {
    Write-Error "오류: 피처 설명은 비어있거나 공백만 포함할 수 없습니다."
    exit 1
}

function Get-HighestNumberFromSpecs {
    param([string]$SpecsDir)

    [long]$highest = 0
    if (Test-Path $SpecsDir) {
        Get-ChildItem -Path $SpecsDir -Directory | ForEach-Object {
            # 순차적 접두사(3자리 이상)를 찾되, 타임스탬프 디렉토리는 무시합니다.
            if ($_.Name -match '^(\d{3,})-' -and $_.Name -notmatch '^\d{8}-\d{6}-') {
                [long]$num = 0
                if ([long]::TryParse($matches[1], [ref]$num) -and $num -gt $highest) {
                    $highest = $num
                }
            }
        }
    }
    return $highest
}

# 브랜치/참조 명칭 목록에서 가장 큰 순차적 피처 번호를 추출합니다.
# Get-HighestNumberFromBranches 및 Get-HighestNumberFromRemoteRefs에서 공유됨.
function Get-HighestNumberFromNames {
    param([string[]]$Names)

    [long]$highest = 0
    foreach ($name in $Names) {
        if ($name -match '^(\d{3,})-' -and $name -notmatch '^\d{8}-\d{6}-') {
            [long]$num = 0
            if ([long]::TryParse($matches[1], [ref]$num) -and $num -gt $highest) {
                $highest = $num
            }
        }
    }
    return $highest
}

function Get-HighestNumberFromBranches {
    param()

    try {
        $branches = git branch -a 2>$null
        if ($LASTEXITCODE -eq 0 -and $branches) {
            $cleanNames = $branches | ForEach-Object {
                $_.Trim() -replace '^\*?\s+', '' -replace '^remotes/[^/]+/', ''
            }
            return Get-HighestNumberFromNames -Names $cleanNames
        }
    } catch {
        Write-Verbose "Git 브랜치를 확인할 수 없습니다: $_"
    }
    return 0
}

function Get-HighestNumberFromRemoteRefs {
    [long]$highest = 0
    try {
        $remotes = git remote 2>$null
        if ($remotes) {
            foreach ($remote in $remotes) {
                $env:GIT_TERMINAL_PROMPT = '0'
                $refs = git ls-remote --heads $remote 2>$null
                $env:GIT_TERMINAL_PROMPT = $null
                if ($LASTEXITCODE -eq 0 -and $refs) {
                    $refNames = $refs | ForEach-Object {
                        if ($_ -match 'refs/heads/(.+)$') { $matches[1] }
                    } | Where-Object { $_ }
                    $remoteHighest = Get-HighestNumberFromNames -Names $refNames
                    if ($remoteHighest -gt $highest) { $highest = $remoteHighest }
                }
            }
        }
    } catch {
        Write-Verbose "원격 참조를 쿼리할 수 없습니다: $_"
    }
    return $highest
}

# 다음 사용 가능한 브랜치 번호를 반환합니다. SkipFetch가 true이면 remotes를
# ls-remote(읽기 전용)를 통해 쿼리합니다.
function Get-NextBranchNumber {
    param(
        [string]$SpecsDir,
        [switch]$SkipFetch
    )

    if ($SkipFetch) {
        # 부작용 없음: ls-remote를 통해 원격 저장소 쿼리
        $highestBranch = Get-HighestNumberFromBranches
        $highestRemote = Get-HighestNumberFromRemoteRefs
        $highestBranch = [Math]::Max($highestBranch, $highestRemote)
    } else {
        # 최신 브랜치 정보를 얻기 위해 모든 원격 저장소를 패치합니다(원격 저장소가 없는 경우 오류 억제)
        try {
            git fetch --all --prune 2>$null | Out-Null
        } catch {
            # 패치 오류 무시
        }
        $highestBranch = Get-HighestNumberFromBranches
    }

    # 단지 짧은 이름만 매칭하는 것이 아니라 모든 스펙 중에서 가장 큰 번호 가져오기
    $highestSpec = Get-HighestNumberFromSpecs -SpecsDir $SpecsDir

    # 둘 중 최대값을 선택
    $maxNum = [Math]::Max($highestBranch, $highestSpec)

    # 다음 번호 반환
    return $maxNum + 1
}

function ConvertTo-CleanBranchName {
    param([string]$Name)

    return $Name.ToLower() -replace '[^a-z0-9]', '-' -replace '-{2,}', '-' -replace '^-', '' -replace '-$', ''
}
# 공통 함수 로드 (Get-RepoRoot, Test-HasGit, Resolve-Template 포함)
. "$PSScriptRoot/common.ps1"

# git보다 .specify를 우선시하는 common.ps1 함수 사용
$repoRoot = Get-RepoRoot

# 이 저장소 루트에 git을 사용할 수 있는지 확인 (부모 디렉토리가 아닌 저장소 루트 기준)
$hasGit = Test-HasGit

Set-Location $repoRoot

$specsDir = Join-Path $repoRoot 'specs'
if (-not $DryRun) {
    New-Item -ItemType Directory -Path $specsDir -Force | Out-Null
}

# 불용어 필터링 및 길이 필터링을 사용하여 브랜치 이름을 생성하는 함수
function Get-BranchName {
    param([string]$Description)

    # 필터링할 일반 불용어
    $stopWords = @(
        'i', 'a', 'an', 'the', 'to', 'for', 'of', 'in', 'on', 'at', 'by', 'with', 'from',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'should', 'could', 'can', 'may', 'might', 'must', 'shall',
        'this', 'that', 'these', 'those', 'my', 'your', 'our', 'their',
        'want', 'need', 'add', 'get', 'set'
    )

    # 소문자로 변환하고 단어 추출 (영문자 및 숫자만)
    $cleanName = $Description.ToLower() -replace '[^a-z0-9\s]', ' '
    $words = $cleanName -split '\s+' | Where-Object { $_ }

    # 단어 필터링: 불용어를 제거하고 3글자보다 짧은 단어를 제외 (원본에서 대문자 두문자어인 경우는 제외)
    $meaningfulWords = @()
    foreach ($word in $words) {
        # 불용어 제외
        if ($stopWords -contains $word) { continue }

        # 길이가 3 이상이거나 원본에 대문자로 표시된 단어(두문자어일 확률이 높음)는 유지
        if ($word.Length -ge 3) {
            $meaningfulWords += $word
        } elseif ($Description -match "\b$($word.ToUpper())\b") {
            # 원본에 대문자로 표시된 경우 짧은 단어도 유지 (두문자어일 확률이 높음)
            $meaningfulWords += $word
        }
    }

    # 의미 있는 단어가 있으면 그 중 첫 3-4개 사용
    if ($meaningfulWords.Count -gt 0) {
        $maxWords = if ($meaningfulWords.Count -eq 4) { 4 } else { 3 }
        $result = ($meaningfulWords | Select-Object -First $maxWords) -join '-'
        return $result
    } else {
        # 의미 있는 단어를 찾지 못한 경우 원래 로직으로 포백
        $result = ConvertTo-CleanBranchName -Name $Description
        $fallbackWords = ($result -split '-') | Where-Object { $_ } | Select-Object -First 3
        return [string]::Join('-', $fallbackWords)
    }
}

# 브랜치 이름 생성
if ($ShortName) {
    # 제공된 짧은 이름을 사용하며 정리만 수행
    $branchSuffix = ConvertTo-CleanBranchName -Name $ShortName
} else {
    # 스마트 필터링을 활용해 설명에서 생성
    $branchSuffix = Get-BranchName -Description $featureDesc
}

# -Number와 -Timestamp가 모두 지정된 경우 경고
if ($Timestamp -and $Number -ne 0) {
    Write-Warning "[specify] 경고: -Timestamp가 사용되면 -Number는 무시됩니다."
    $Number = 0
}

# 브랜치 접두사 확인
if ($Timestamp) {
    $featureNum = Get-Date -Format 'yyyyMMdd-HHmmss'
    $branchName = "$featureNum-$branchSuffix"
} else {
    # 브랜치 번호 확인
    if ($Number -eq 0) {
        if ($DryRun -and $hasGit) {
            # 드라이 런: ls-remote를 통해 원격 저장소 쿼리 (부작용 없음, fetch하지 않음)
            $Number = Get-NextBranchNumber -SpecsDir $specsDir -SkipFetch
        } elseif ($DryRun) {
            # git 없이 드라이 런: 로컬 스펙 디렉토리만 확인
            $Number = (Get-HighestNumberFromSpecs -SpecsDir $specsDir) + 1
        } elseif ($hasGit) {
            # 원격 저장소의 기존 브랜치 확인
            $Number = Get-NextBranchNumber -SpecsDir $specsDir
        } else {
            # 로컬 디렉토리 확인으로 포백
            $Number = (Get-HighestNumberFromSpecs -SpecsDir $specsDir) + 1
        }
    }

    $featureNum = ('{0:000}' -f $Number)
    $branchName = "$featureNum-$branchSuffix"
}

# GitHub은 브랜치 이름에 대해 244바이트 한도를 적용합니다.
# 필요한 경우 검증 및 자르기
$maxBranchLength = 244
if ($branchName.Length -gt $maxBranchLength) {
    # 접미사에서 잘라내야 할 양 계산
    # 접두사 길이 반영: 타임스탬프 (15) + 하이픈 (1) = 16, 또는 순차 번호 (3) + 하이픈 (1) = 4
    $prefixLength = $featureNum.Length + 1
    $maxSuffixLength = $maxBranchLength - $prefixLength

    # 접미사 자르기
    $truncatedSuffix = $branchSuffix.Substring(0, [Math]::Min($branchSuffix.Length, $maxSuffixLength))
    # 자르기로 인해 끝에 하이픈이 생긴 경우 제거
    $truncatedSuffix = $truncatedSuffix -replace '-$', ''

    $originalBranchName = $branchName
    $branchName = "$featureNum-$truncatedSuffix"

    Write-Warning "[specify] 브랜치 이름이 GitHub의 244바이트 한도를 초과했습니다."
    Write-Warning "[specify] 원본: $originalBranchName ($($originalBranchName.Length) 바이트)"
    Write-Warning "[specify] 다음으로 단축됨: $branchName ($($branchName.Length) 바이트)"
}

$featureDir = Join-Path $specsDir $branchName
$specFile = Join-Path $featureDir 'spec.md'

if (-not $DryRun) {
    if ($hasGit) {
        $branchCreated = $false
        $branchCreateError = ''
        try {
            $branchCreateError = git checkout -q -b $branchName 2>&1 | Out-String
            if ($LASTEXITCODE -eq 0) {
                $branchCreated = $true
            }
        } catch {
            $branchCreateError = $_.Exception.Message
        }

        if (-not $branchCreated) {
            $currentBranch = ''
            try { $currentBranch = (git rev-parse --abbrev-ref HEAD 2>$null).Trim() } catch {}
            # 기존 브랜치가 이미 존재하는지 확인
            $existingBranch = git branch --list $branchName 2>$null
            if ($existingBranch) {
                if ($AllowExistingBranch) {
                    # 이미 해당 브랜치에 있는 경우 체크아웃을 다시 하지 않고 계속 진행합니다.
                    if ($currentBranch -eq $branchName) {
                        # 이미 대상 브랜치에 있음 — 조치 불필요
                    } else {
                        # 그렇지 않으면 실패하는 대신 기존 브랜치로 전환합니다.
                        $switchBranchError = git checkout -q $branchName 2>&1 | Out-String
                        if ($LASTEXITCODE -ne 0) {
                            if ($switchBranchError) {
                                Write-Error "오류: '$branchName' 브랜치가 존재하지만 체크아웃할 수 없습니다.`n$($switchBranchError.Trim())"
                            } else {
                                Write-Error "오류: '$branchName' 브랜치가 존재하지만 체크아웃할 수 없습니다. 커밋되지 않은 변경 사항이나 충돌을 해결한 후 다시 시도하십시오."
                            }
                            exit 1
                        }
                    }
                } elseif ($Timestamp) {
                    Write-Error "오류: '$branchName' 브랜치가 이미 존재합니다. 다시 실행하여 새 타임스탬프를 얻거나 다른 -ShortName을 사용하십시오."
                    exit 1
                } else {
                    Write-Error "오류: '$branchName' 브랜치가 이미 존재합니다. 다른 피처 이름을 사용하거나 -Number로 다른 번호를 지정하십시오."
                    exit 1
                }
            } else {
                if ($branchCreateError) {
                    Write-Error "오류: git 브랜치 '$branchName' 생성에 실패했습니다.`n$($branchCreateError.Trim())"
                } else {
                    Write-Error "오류: git 브랜치 '$branchName' 생성에 실패했습니다. git 설정을 확인하고 다시 시도하십시오."
                }
                exit 1
            }
        }
    } else {
        Write-Warning "[specify] 경고: Git 저장소가 감지되지 않았습니다. $branchName 브랜치 생성을 건너뜁니다."
    }

    New-Item -ItemType Directory -Path $featureDir -Force | Out-Null

    if (-not (Test-Path -PathType Leaf $specFile)) {
        $template = Resolve-Template -TemplateName 'spec-template' -RepoRoot $repoRoot
        if ($template -and (Test-Path $template)) {
            # BOM이 없는 UTF-8 인코딩으로 템플릿 내용을 읽어 스펙 파일에 씁니다.
            $content = [System.IO.File]::ReadAllText($template)
            $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
            [System.IO.File]::WriteAllText($specFile, $content, $utf8NoBom)
        } else {
            New-Item -ItemType File -Path $specFile -Force | Out-Null
        }
    }

    # 현재 세션에 대해 SPECIFY_FEATURE environment variable 설정
    $env:SPECIFY_FEATURE = $branchName
}

if ($Json) {
    $obj = [PSCustomObject]@{
        BRANCH_NAME = $branchName
        SPEC_FILE = $specFile
        FEATURE_NUM = $featureNum
        HAS_GIT = $hasGit
    }
    if ($DryRun) {
        $obj | Add-Member -NotePropertyName 'DRY_RUN' -NotePropertyValue $true
    }
    $obj | ConvertTo-Json -Compress
} else {
    Write-Output "BRANCH_NAME: $branchName"
    Write-Output "SPEC_FILE: $specFile"
    Write-Output "FEATURE_NUM: $featureNum"
    Write-Output "HAS_GIT: $hasGit"
    if (-not $DryRun) {
        Write-Output "SPECIFY_FEATURE 환경 변수가 다음으로 설정되었습니다: $branchName"
    }
}
