@echo off
REM Jengo Business - Claude Code Launcher
REM Launches Jengo with Claude Code CLI

echo ========================================
echo Jengo Business - Claude Code Mode
echo ========================================
echo.

REM Check for Claude Code
where claude >nul 2>nul
if errorlevel 1 (
    echo ERROR: Claude Code CLI not found
    echo.
    echo Install from: https://claude.ai/code
    echo Or use generic launcher: jengo.bat
    pause
    exit /b 1
)

REM Check for configuration — redirect to wizard if not configured
if not exist "%USERPROFILE%\.jengo\config.yaml" (
    echo Jengo is not yet configured on this machine.
    echo Starting setup wizard...
    echo.
    call "%~dp0setup-wizard.bat" machine
    if not exist "%USERPROFILE%\.jengo\config.yaml" (
        echo Setup did not complete. Run setup-wizard.bat manually.
        pause
        exit /b 1
    )
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

REM Build system prompt
python startup\build-system-prompt.py > %TEMP%\jengo-system-prompt.txt

REM Launch Claude Code with system prompt
echo Starting Claude Code session...
echo.
claude --system-prompt-file=%TEMP%\jengo-system-prompt.txt

REM Cleanup
del %TEMP%\jengo-system-prompt.txt

echo.
echo Session ended.
pause
