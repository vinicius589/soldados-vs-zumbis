@echo off
setlocal
cd /d "%~dp0"
title Soldados vs Zumbis - Integracao Beta 4

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 main.py --integracao-beta4
) else (
    python main.py --integracao-beta4
)

if errorlevel 1 (
    echo.
    echo Nao foi possivel iniciar o teste integrado.
    echo Execute executar.bat uma vez para instalar as dependencias.
    pause
)
endlocal
