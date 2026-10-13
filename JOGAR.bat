@echo off
cd /d "%~dp0"
if not exist "SoldadosVsZumbis.exe" (
    echo O executavel nao foi encontrado. Extraia o pacote completo antes de jogar.
    pause
    exit /b 1
)
start "" "%~dp0SoldadosVsZumbis.exe"
