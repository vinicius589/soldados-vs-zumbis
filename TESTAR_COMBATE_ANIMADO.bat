@echo off
setlocal
cd /d "%~dp0"
title Soldados vs Zumbis - Teste de Combate

set "PYTHON_COMBATE="
if exist "%~dp0.venv\Scripts\python.exe" set "PYTHON_COMBATE=%~dp0.venv\Scripts\python.exe"
where py >nul 2>nul
if not defined PYTHON_COMBATE if not errorlevel 1 set "PYTHON_COMBATE=py -3"
if not defined PYTHON_COMBATE (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_COMBATE=python"
)
if not defined PYTHON_COMBATE (
    echo Python nao foi encontrado.
    pause
    exit /b 1
)

%PYTHON_COMBATE% "PROTOTIPO_COMBATE\prototipo_combate.py" %*
if errorlevel 1 goto erro
exit /b 0

:erro
echo.
echo Nao foi possivel abrir o teste de combate.
echo Instale as dependencias com: python -m pip install -r requirements.txt
pause
exit /b 1
