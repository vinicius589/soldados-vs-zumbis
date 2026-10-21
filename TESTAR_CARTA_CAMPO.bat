@echo off
setlocal
cd /d "%~dp0"
title Soldados vs Zumbis - Carta e Campo

set "PYTHON_PROTO="
if exist "%~dp0.venv\Scripts\python.exe" set "PYTHON_PROTO=%~dp0.venv\Scripts\python.exe"
where py >nul 2>nul
if not defined PYTHON_PROTO if not errorlevel 1 set "PYTHON_PROTO=py -3"
if not defined PYTHON_PROTO (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_PROTO=python"
)
if not defined PYTHON_PROTO (
    echo Python nao foi encontrado.
    pause
    exit /b 1
)

%PYTHON_PROTO% "PROTOTIPO_CARTA_CAMPO\prototipo_carta_campo.py" %*
if errorlevel 1 goto erro
exit /b 0

:erro
echo.
echo Nao foi possivel abrir o prototipo.
echo Instale as dependencias com: python -m pip install -r requirements.txt
pause
exit /b 1
