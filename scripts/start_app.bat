@echo off
chcp 65001 >nul
title AI 가계부 자동화 프로그램 실행기

echo ==========================================================
echo       AI 가계부 자동화 프로그램 실행기 (Windows)
echo ==========================================================
echo.

:: 1. Docker 실행 여부 검사
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] Docker Desktop이 실행되고 있지 않습니다!
    echo Docker Desktop 프로그램을 먼저 켠 뒤 다시 이 스크립트를 실행해주세요.
    echo.
    pause
    exit /b 1
)

:: 2. 환경 변수 파일 (.env.docker) 존재 여부 검사 및 복사
set "ENV_FILE=%~dp0..\backend\.env.docker"
set "ENV_EXAMPLE=%~dp0..\backend\.env.docker.example"

if not exist "%ENV_FILE%" (
    if exist "%ENV_EXAMPLE%" (
        echo [안내] 설정 파일(.env.docker)이 없습니다. 기본 템플릿으로 복사합니다.
        copy "%ENV_EXAMPLE%" "%ENV_FILE%" >nul
        echo [경고] API 키 등 상세 설정을 하려면 backend\.env.docker 파일을 메모장으로 수정해주세요.
    ) else (
        echo [오류] 설정 파일 템플릿(backend\.env.docker.example)이 존재하지 않습니다!
        pause
        exit /b 1
    )
)

:: 3. 컨테이너 빌드 및 실행
echo [진행] Docker 컨테이너를 빌드하고 실행합니다. 잠시만 기다려주세요...
echo.
docker compose -f "%~dp0..\docker-compose.yml" up -d --build
if %errorlevel% neq 0 (
    echo.
    echo [오류] 프로그램 기동 중 에러가 발생했습니다.
    pause
    exit /b 1
)

echo.
echo ==========================================================
echo   ✔ 프로그램이 성공적으로 실행되었습니다!
echo ==========================================================
echo.
echo   * 프론트엔드 웹 앱: http://localhost:5173
echo   * 백엔드 API 서버: http://localhost:8000
echo.
echo   웹 브라우저를 열어 http://localhost:5173 에 접속하시면 됩니다.
echo   프로그램을 종료하려면 scripts/stop_app.bat 을 실행해주세요.
echo ==========================================================
echo.

:: 자동으로 브라우저 열기
start http://localhost:5173

pause
