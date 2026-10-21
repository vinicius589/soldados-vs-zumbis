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

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 main.py
) else (
    python main.py
)

if errorlevel 1 (
    echo.
    echo O jogo encontrou um erro. Envie a mensagem acima para correcao.
    pause
)
