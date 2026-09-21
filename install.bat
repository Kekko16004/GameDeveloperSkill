@echo off
setlocal EnableExtensions
cd /d "%~dp0game-developer"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0game-developer\install.ps1" %*
exit /b %ERRORLEVEL%
