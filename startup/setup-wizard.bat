@echo off
REM Jengo Business - Setup Wizard
REM Handles onboarding (new org/person) and machine configuration (new device)

setlocal enabledelayedexpansion

echo ========================================
echo Jengo Business - Setup Wizard
echo ========================================
echo.

REM Check arguments
if "%1"=="" (
    echo ERROR: Missing argument
    echo.
    echo Usage:
    echo   setup-wizard.bat onboarding  ^(create new organization/person identity^)
    echo   setup-wizard.bat machine     ^(configure new device for existing identity^)
    echo.
    pause
    exit /b 1
)

set MODE=%1

REM Check for Python
where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python not found
    echo Please install Python 3.10 or higher
    pause
    exit /b 1
)

REM Check for Git
where git >nul 2>nul
if errorlevel 1 (
    echo ERROR: Git not found
    echo Please install Git
    pause
    exit /b 1
)

if "%MODE%"=="onboarding" (
    echo Mode: ONBOARDING - Creating new identity
    echo.
    echo This will:
    echo   1. Ask for organization or individual details
    echo   2. Create identity repository
    echo   3. Configure inheritance chain
    echo   4. Generate launch scripts
    echo.
    set /p CONFIRM="Continue? (y/n): "
    if /i not "!CONFIRM!"=="y" (
        echo Cancelled.
        pause
        exit /b 0
    )

    echo.
    python startup\onboarding\onboard-wizard.py

) else if "%MODE%"=="machine" (
    echo Mode: MACHINE CONFIG - Configuring new device
    echo.
    echo This will:
    echo   1. Detect existing identity from parent layer
    echo   2. Create device-specific repository
    echo   3. Configure git remotes
    echo   4. Generate launch scripts
    echo.
    set /p CONFIRM="Continue? (y/n): "
    if /i not "!CONFIRM!"=="y" (
        echo Cancelled.
        pause
        exit /b 0
    )

    echo.
    python startup\onboarding\machine-config.py

) else (
    echo ERROR: Invalid mode "%MODE%"
    echo.
    echo Valid modes:
    echo   onboarding  - Create new organization/person identity
    echo   machine     - Configure new device
    echo.
    pause
    exit /b 1
)

REM --- Thought Stream Setup (always runs after successful setup) ---
echo.
echo [thought-stream] Setting up cross-session continuity...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0register-stream-task.ps1"
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Thought stream task registration may require administrator rights.
    echo Run startup\register-stream-task.ps1 manually as administrator to complete this step.
    echo (Non-fatal: Jengo works without the nightly synthesis task)
    echo.
)

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.
echo Jengo is ready. What was set up:
echo   - Identity and knowledge layers configured
echo   - Cross-session thought continuity (thought-stream + active-synthesis)
echo   - Nightly synthesis task (if admin rights were available)
echo.
echo Next steps:
echo   1. Review configuration: %USERPROFILE%\.jengo\config.yaml
echo   2. Launch Jengo: jengo_claudecode.bat
echo.
pause
