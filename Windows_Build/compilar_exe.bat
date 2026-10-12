@echo off
title Compilando PWA Simulator...
cd /d "%~dp0\.."
echo ========================================================
echo         COMPILACION DE PWA SIMULATOR A EXE
echo ========================================================
echo.

echo [1/3] Verificando dependencias...
python -m pip install pyinstaller -q

echo.
echo [2/3] Compilando con PyInstaller (limpio)...
python -m PyInstaller --noconfirm --clean Windows_Build\PWASimulator.spec

echo.
if exist "dist\PWASimulator\PWASimulator.exe" (
    echo [3/3] Actualizando carpeta distribuible portable...
    xcopy /E /I /Y "dist\PWASimulator\*" "PWASimulator_Portable\PWASimulator\" >nul
    echo.
    echo ========================================================
    echo [OK] Compilacion y empaquetado exitoso!
    echo Carpeta portable lista: PWASimulator_Portable\PWASimulator\PWASimulator.exe
    echo ========================================================
) else (
    echo [ERROR] Hubo un problema durante la compilacion.
)
echo.
pause
