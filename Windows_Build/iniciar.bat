@echo off
title PWA Simulator
cd /d "%~dp0\.."
echo Iniciando PWA Simulator...
python main.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] La aplicacion se cerro con codigo de error %ERRORLEVEL%.
    pause
)
