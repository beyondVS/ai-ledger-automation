# Windows PowerShell Script to run PDF Extractor tests
$ErrorActionPreference = "Stop"
Write-Host "Running PDF Lossless Extraction Unit Tests..." -ForegroundColor Cyan

# backend 폴더로 이동하여 pytest 실행
try {
    uv run pytest backend/tests/unit/test_pdf_extractor.py -v
} catch {
    Write-Error "Tests failed!"
    exit 1
}
