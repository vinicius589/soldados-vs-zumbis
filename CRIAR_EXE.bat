@echo off
setlocal
cd /d "%~dp0"
title Soldados vs Zumbis - Construir executavel
if not exist ".venv\Scripts\python.exe" (
  echo Execute PREPARAR_AMBIENTE.bat primeiro.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info[:2] == (3, 12)"
if errorlevel 1 goto erro
".venv\Scripts\python.exe" -m pip install -r requirements-test-lock.txt
if errorlevel 1 goto erro
".venv\Scripts\python.exe" tools/manage.py build
if errorlevel 1 goto erro
echo Executavel criado: SoldadosVsZumbis.exe
echo Mantenha assets e _internal junto do executavel.
pause
exit /b 0
:erro
echo A construcao falhou. Confira as mensagens acima.
pause
exit /b 1
