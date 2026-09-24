@echo off
REM GameDeveloperSkill - Installer Principale
REM Installa skill, dipendenze, e configura tutto

echo ========================================
echo   GameDeveloperSkill v2.0 Installer
echo ========================================
echo.

REM Check admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Run as Administrator required
    pause
    exit /b 1
)

echo [1/4] Installing skill...
powershell -ExecutionPolicy Bypass -File "%~dp0game-developer\install.ps1"

echo.
echo [2/4] Setting up Git LFS...
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\setup-git-lfs.ps1"

echo.
echo [3/4] Checking dependencies...
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\check-dependencies.ps1"

echo.
echo [4/4] Setup complete!
echo.
echo Next steps:
echo   1. Run: start-dashboard.bat (console: progetto, FabCLI, DesignerSkill)
echo   2. Copia game-developer\config.example.json in game-developer\config.json se manca
echo   3. FabCLI: scarica fabcli.exe e impostalo nella console, schermata Fab
echo.
pause
