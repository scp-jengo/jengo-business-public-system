@echo off
REM Jengo Business Setup Wizard
REM Handles both onboarding (new org/person) and machine configuration (new device)

setlocal enabledelayedexpansion

echo ========================================
echo JENGO BUSINESS - SETUP WIZARD
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.9+ and try again.
    exit /b 1
)

REM Determine setup mode
set MODE=%1

if "%MODE%"=="" (
    echo What type of setup do you need?
    echo.
    echo [1] Onboarding - First time setup for new organization or person
    echo [2] Machine   - Configure this machine for existing identity
    echo [3] Exit
    echo.
    set /p CHOICE="Enter choice (1-3): "

    if "!CHOICE!"=="1" set MODE=onboarding
    if "!CHOICE!"=="2" set MODE=machine
    if "!CHOICE!"=="3" exit /b 0
)

if "%MODE%"=="onboarding" (
    echo.
    echo ========================================
    echo ONBOARDING MODE
    echo ========================================
    echo.
    echo This will create a new identity layer.
    echo.
    python tools/setup/onboarding_wizard.py
) else if "%MODE%"=="machine" (
    echo.
    echo ========================================
    echo MACHINE CONFIGURATION MODE
    echo ========================================
    echo.
    echo This will configure this machine for an existing identity.
    echo.
    python tools/setup/machine_config.py
) else (
    echo ERROR: Invalid mode. Use 'onboarding' or 'machine'
    exit /b 1
)

if %errorlevel% neq 0 (
    echo.
    echo Setup failed. Check errors above.
    exit /b 1
)

REM --- Thought Stream Setup (always runs after successful onboarding or machine config) ---
echo.
echo [thought-stream] Setting up cross-session continuity...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0startup\register-stream-task.ps1"
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Thought stream setup failed or requires manual admin step.
    echo See startup\register-stream-task.ps1 for details.
    echo You can run it later manually as administrator.
    echo.
    REM Non-fatal: continue setup
)

echo.
echo ========================================
echo SETUP COMPLETE!
echo ========================================
echo.
echo Launcher scripts have been created:
echo.
echo   jengo.bat             - Auto-detect best available AI
echo   jengo_claudecode.bat  - Launch with Claude Code
echo   jengo_codex.bat       - Launch with OpenAI Codex
echo.
echo Thought stream (cross-session continuity):
echo   logs\thought-stream.md      - In-session insights (append-only)
echo   state\active-synthesis.md   - Read at startup Phase 2.5
echo   Task: Jengo-StreamSynthesize - Nightly 03:07 (if registered)
echo.
echo To start Jengo, run:  jengo.bat
echo.

exit /b 0
