@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"

set "PYTHON_ENTRADAS="
if exist "..\.venv\Scripts\python.exe" set "PYTHON_ENTRADAS=..\.venv\Scripts\python.exe"
where py >nul 2>nul
if not defined PYTHON_ENTRADAS if not errorlevel 1 set "PYTHON_ENTRADAS=py -3"
if not defined PYTHON_ENTRADAS (
  where python >nul 2>nul
  if not errorlevel 1 set "PYTHON_ENTRADAS=python"
)
if not defined PYTHON_ENTRADAS (
  echo Python nao foi encontrado.
  pause
  exit /b 1
)

%PYTHON_ENTRADAS% preparar_cenarios.py
if errorlevel 1 goto erro
%PYTHON_ENTRADAS% limpar_piras_egito.py
if errorlevel 1 goto erro
%PYTHON_ENTRADAS% visualizar_cenarios.py %*
if errorlevel 1 goto erro
exit /b 0

:erro
echo.
echo Nao foi possivel abrir as entradas animadas.
echo Instale pygame-ce 2.5.8 e Pillow 12.3.0 e tente novamente.
pause
exit /b 1
