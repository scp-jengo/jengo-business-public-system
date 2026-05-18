@echo off
REM Jengo Business - OpenAI Codex Launcher
REM Launches Jengo with OpenAI Codex integration

echo ========================================
echo Jengo Business - Codex Mode
echo ========================================
echo.

REM Check for OpenAI API key
if "%OPENAI_API_KEY%"=="" (
    echo ERROR: OPENAI_API_KEY not set
    echo.
    echo Set environment variable:
    echo   set OPENAI_API_KEY=your-key-here
    echo.
    echo Or add to: %USERPROFILE%\.jengo\config.yaml
    pause
    exit /b 1
)

REM Check for configuration
if not exist "%USERPROFILE%\.jengo\config.yaml" (
    echo ERROR: Jengo not configured
    echo Please run: setup-wizard.bat onboarding
    pause
    exit /b 1
)

REM Load identity
echo Loading identity and knowledge...
python -m jengo.tools.inheritance_loader --load

REM Get identity info
for /f "delims=" %%i in ('python startup\get-identity.py name') do set IDENTITY_NAME=%%i
for /f "delims=" %%i in ('python startup\get-identity.py layer') do set IDENTITY_LAYER=%%i

echo.
echo Identity: %IDENTITY_NAME%
echo Layer: %IDENTITY_LAYER%
echo.
echo Constitutional AI: ACTIVE (L1/L2/L3)
echo Policy Engine: LOADED
echo.

REM Launch Codex integration
echo Starting Codex session...
echo.
python -m jengo.integrations.codex_launcher

echo.
echo Session ended.
pause
