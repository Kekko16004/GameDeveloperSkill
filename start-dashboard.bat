@echo off
cd /d "%~dp0"

python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo Python non trovato. Serve Python 3.10 o successivo.
    pause
    exit /b 1
)

python game-developer\tools\tui\gds_tui.py
echo.
pause
