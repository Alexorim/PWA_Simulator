@echo off
title Compilando PWA Simulator...
echo ========================================================
echo         COMPILACION DE PWA SIMULATOR A EXE
echo ========================================================
echo.

echo [1/2] Verificando dependencias...
pip install pyinstaller -q

echo.
echo [2/2] Compilando con PyInstaller...
pyinstaller --noconfirm --clean PWASimulator.spec

echo.
if exist "dist\PWASimulator.exe" (
    echo [OK] Compilacion exitosa! El archivo ejecutable esta en: dist\PWASimulator.exe
) else (
    echo [ERROR] Hubo un problema durante la compilacion.
)
echo.
pause
