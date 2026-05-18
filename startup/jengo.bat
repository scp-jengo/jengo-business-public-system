@echo off
REM Jengo Business - Generic Launcher
REM Auto-detects best available AI model and launches

echo ========================================
echo Jengo Business - Starting...
echo ========================================
echo.

REM Check for configuration
if not exist "%USERPROFILE%\.jengo\config.yaml" (
    echo ERROR: Jengo not configured
    echo.
    echo Please run setup wizard first:
    echo   setup-wizard.bat onboarding  (for first time)
    echo   setup-wizard.bat machine     (for new device)
    echo.
    pause
    exit /b 1
)

REM Load configuration
echo [1/5] Loading configuration...
python startup\load-config.py
if errorlevel 1 (
    echo ERROR: Failed to load configuration
    pause
    exit /b 1
)

REM Sync inheritance chain
echo [2/5] Syncing knowledge from parent layers...
python -m jengo.tools.inheritance_loader --sync
if errorlevel 1 (
    echo WARNING: Some parent layers failed to sync
    echo Continuing with cached knowledge...
)

REM Validate constitutional AI
echo [3/5] Validating constitutional AI framework...
python -m jengo.constitutional.validate
if errorlevel 1 (
    echo ERROR: Constitutional AI validation failed
    echo Cannot proceed without L1/L2/L3 framework
    pause
    exit /b 1
)

REM Detect best available model
echo [4/5] Detecting available AI models...
python startup\detect-model.py > %TEMP%\jengo-model.txt
set /p JENGO_MODEL=<%TEMP%\jengo-model.txt
del %TEMP%\jengo-model.txt

echo Found: %JENGO_MODEL%
echo.

REM Launch
echo [5/5] Launching Jengo with %JENGO_MODEL%...
echo.

if "%JENGO_MODEL%"=="claudecode" (
    call jengo_claudecode.bat
) else if "%JENGO_MODEL%"=="codex" (
    call jengo_codex.bat
) else if "%JENGO_MODEL%"=="claude-api" (
    python -m jengo.api.main
) else (
    echo ERROR: No compatible AI model found
    echo.
    echo Please install one of:
    echo   - Claude Code CLI (https://claude.ai/code)
    echo   - OpenAI Codex
    echo   - Configure Anthropic API key
    pause
    exit /b 1
)
