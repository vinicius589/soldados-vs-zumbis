@echo off
setlocal
cd /d "%~dp0\CENARIOS_BETA4_CONCEITOS"
title Soldados vs Zumbis - Cenarios Beta 4

set "PYTHON_CENARIO="
if exist "%~dp0\.venv\Scripts\python.exe" set "PYTHON_CENARIO=%~dp0\.venv\Scripts\python.exe"
where py >nul 2>nul
if not defined PYTHON_CENARIO if not errorlevel 1 set "PYTHON_CENARIO=py -3"
if not defined PYTHON_CENARIO (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CENARIO=python"
)
if not defined PYTHON_CENARIO (
    echo Python nao foi encontrado.
    pause
    exit /b 1
)

%PYTHON_CENARIO% preparar_cenarios.py
if errorlevel 1 goto erro
%PYTHON_CENARIO% limpar_piras_egito.py
if errorlevel 1 goto erro
%PYTHON_CENARIO% visualizar_cenarios.py %*
if errorlevel 1 goto erro
exit /b 0

:erro
echo.
echo Nao foi possivel abrir a galeria de cenarios.
pause
exit /b 1
