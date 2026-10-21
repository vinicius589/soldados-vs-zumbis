@echo off
setlocal
cd /d "%~dp0"
title Recortar Sprite Sheets - Soldados vs Zumbis

set "PYTHON_SPRITES="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON_SPRITES=py -3"
if not defined PYTHON_SPRITES (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_SPRITES=python"
)

if not defined PYTHON_SPRITES (
    echo Python 3 nao foi encontrado.
    pause
    exit /b 1
)

%PYTHON_SPRITES% -c "import pygame" >nul 2>nul
if errorlevel 1 (
    echo Instalando pygame-ce para realizar o recorte...
    %PYTHON_SPRITES% -m pip install --disable-pip-version-check pygame-ce==2.5.8
    if errorlevel 1 (
        echo Nao foi possivel instalar o pygame-ce.
        pause
        exit /b 1
    )
)

%PYTHON_SPRITES% split_sheets.py
if errorlevel 1 (
    echo O recorte encontrou um erro.
    pause
    exit /b 1
)

echo.
echo Quadros individuais gerados com sucesso na pasta frames.
pause
endlocal
