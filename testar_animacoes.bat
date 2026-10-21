@echo off
setlocal
cd /d "%~dp0"
title Soldados vs Zumbis - Laboratorio de Animacao

where python >nul 2>nul
if errorlevel 1 (
    echo Python nao foi encontrado. Instale o Python e marque a opcao Add Python to PATH.
    pause
    exit /b 1
)

python animation_lab.py
if errorlevel 1 (
    echo.
    echo O laboratorio encontrou um erro. A mensagem completa aparece acima.
    pause
)

endlocal
