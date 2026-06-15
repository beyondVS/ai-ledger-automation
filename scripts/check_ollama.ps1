# check_ollama.ps1
# 로컬 개발 환경에서 Ollama 서비스의 구동 여부 및 gemma4:e4b 모델 존재 여부를 검증합니다.

$OLLAMA_API = "http://localhost:11434"
$MODEL_NAME = "gemma4:e4b"

Write-Host "Checking Ollama status at $OLLAMA_API..." -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri "$OLLAMA_API/api/tags" -Method Get -TimeoutSec 5
    $models = $response.models

    if ($null -eq $models) {
        Write-Error "Ollama API returned an invalid response (no models list)."
        exit 1
    }

    $found = $false
    foreach ($model in $models) {
        if ($model.name -eq $MODEL_NAME -or $model.name -like "$MODEL_NAME*") {
            $found = $true
            break
        }
    }

    if ($found) {
        Write-Host "[OK] Ollama is running and model '$MODEL_NAME' is installed." -ForegroundColor Green
        exit 0
    } else {
        Write-Warning "Ollama is running, but model '$MODEL_NAME' was not found."
        Write-Host "Please pull the model first by running:" -ForegroundColor Yellow
        Write-Host "  ollama pull $MODEL_NAME" -ForegroundColor Yellow
        exit 1
    }
}
catch {
    Write-Error "Failed to connect to Ollama service. Ensure Ollama is running locally."
    Write-Host "Download and install from: https://ollama.com" -ForegroundColor Yellow
    exit 1
}
