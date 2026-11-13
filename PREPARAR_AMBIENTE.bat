@echo off
setlocal
cd /d "%~dp0"
title Soldados vs Zumbis - Preparar ambiente
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0PREPARAR_AMBIENTE.ps1"
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%
