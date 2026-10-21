@echo off
setlocal
cd /d "%~dp0"
title Soldados vs Zumbis - Preparar ambiente

echo ================================================
echo       SOLDADOS VS ZUMBIS - PREPARACAO
echo ================================================
echo.
echo Este passo prepara as bibliotecas necessarias.
echo A primeira vez precisa de internet e pode demorar.
echo.

where py >nul 2>nul
if errorlevel 1 goto sem_python

py -3.12 --version >nul 2>nul
if errorlevel 1 goto versao_errada

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Criando ambiente isolado...
  py -3.12 -m venv .venv
  if errorlevel 1 goto erro
)

echo [2/3] Atualizando o instalador de bibliotecas...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto erro

echo [3/3] Instalando as bibliotecas do jogo...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto erro

".venv\Scripts\python.exe" -c "import pygame, OpenGL" >nul 2>nul
if errorlevel 1 goto verificacao_falhou

>".ambiente-pronto" echo SVZ_ENVIRONMENT_READY_V1

echo.
echo Ambiente preparado com sucesso!
echo Agora voce pode abrir JOGAR.bat.
echo.
pause
exit /b 0

:sem_python
echo ERRO: o Python 3.12 x64 nao foi encontrado.
echo Instale Python 3.12 x64 e marque a opcao para instalar o Python Launcher.
echo Depois execute este arquivo novamente.
pause
exit /b 1

:versao_errada
echo ERRO: este projeto precisa do Python 3.12.
echo Instale o Python 3.12 x64 e execute este arquivo novamente.
pause
exit /b 1

:verificacao_falhou
echo ERRO: a instalacao terminou, mas a verificacao das bibliotecas falhou.
del ".ambiente-pronto" >nul 2>nul
goto erro

:erro
echo.
echo A preparacao nao foi concluida. O jogo nao sera marcado como pronto.
echo Confira a conexao com a internet e as mensagens acima.
echo Execute PREPARAR_AMBIENTE.bat novamente depois de corrigir o problema.
pause
exit /b 1
