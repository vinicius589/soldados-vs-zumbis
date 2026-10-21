@echo off
setlocal
cd /d "%~dp0"
title Soldados vs Zumbis - Testar Todas as Animacoes

set "PYTHON_ANIM="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON_ANIM=py -3"

if not defined PYTHON_ANIM (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_ANIM=python"
)

if not defined PYTHON_ANIM (
    echo.
    echo Python nao foi encontrado neste computador.
    echo Instale o Python 3 e marque a opcao Add Python to PATH.
    echo.
    pause
    exit /b 1
)

%PYTHON_ANIM% -c "import pygame" >nul 2>nul
if errorlevel 1 (
    echo.
    echo Preparando o Pygame automaticamente. Isso acontece apenas na primeira vez.
    %PYTHON_ANIM% -m pip install --disable-pip-version-check pygame-ce==2.5.8
    if errorlevel 1 (
        echo.
        echo Nao foi possivel preparar o Pygame.
        echo Verifique sua conexao com a internet e execute este arquivo novamente.
        echo.
        pause
        exit /b 1
    )
)

%PYTHON_ANIM% laboratorio_animacoes.py %*
if errorlevel 1 (
    echo.
    echo O laboratorio encontrou um erro. A mensagem completa esta acima.
    echo.
    pause
)

endlocal
