@echo off
cd /d "%~dp0"

if exist "..\..\verificar_recursos.py" (
    where py >nul 2>nul
    if errorlevel 1 (
        python "..\..\verificar_recursos.py" .
    ) else (
        py -3 "..\..\verificar_recursos.py" .
    )
    if errorlevel 1 (
        pause
        exit /b 2
    )
)
py -3 main.py 2>nul || python main.py
pause
