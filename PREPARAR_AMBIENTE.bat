@echo off
setlocal
cd /d "%~dp0"
title Fábrica dos Mortos - Preparar ambiente
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0PREPARAR_AMBIENTE.ps1"
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%
