@echo off
setlocal
cd /d "%~dp0"
title Soldados vs Zumbis

if not exist ".ambiente-pronto" goto preparar_primeiro
if not exist ".venv\Scripts\python.exe" goto preparar_primeiro

".venv\Scripts\python.exe" -c "import pygame, OpenGL" >nul 2>nul
if errorlevel 1 goto preparar_primeiro

echo Abrindo Soldados vs Zumbis...
".venv\Scripts\python.exe" main.py %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo O jogo fechou com um erro. Consulte o registro em:
  echo %LOCALAPPDATA%\SoldadosVsZumbis\jogo.log
  echo.
  pause
)
exit /b %RC%

:preparar_primeiro
echo.
echo ================================================
echo        AMBIENTE AINDA NAO PREPARADO
echo ================================================
echo Voce precisa preparar o jogo antes de jogar.
echo.
echo 1. Feche esta janela.
echo 2. Execute PREPARAR_AMBIENTE.bat.
echo 3. Aguarde a mensagem de sucesso.
echo 4. Volte aqui e execute JOGAR.bat novamente.
echo.
pause
exit /b 1
