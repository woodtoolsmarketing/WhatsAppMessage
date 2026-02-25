@echo off
color 0A
title Actualizador WoodTools
cd /d "%~dp0"

echo Buscando actualizaciones en GitHub...
git fetch origin prueba

FOR /F "tokens=*" %%a in ('git rev-parse HEAD') do SET LOCAL_VER=%%a
FOR /F "tokens=*" %%a in ('git rev-parse origin/prueba') do SET REMOTE_VER=%%a

if "%LOCAL_VER%"=="%REMOTE_VER%" (
    echo.
    echo ===================================
    echo    PROGRAMA SIN ACTUALIZACIONES
    echo ===================================
    timeout /t 2 > NUL
) else (
    echo.
    echo Descargando nuevos cambios...
    git pull origin prueba
    echo Actualizacion completada.
    timeout /t 2 > NUL
)

:: Abre el programa usando el entorno virtual y cierra esta ventana negra
start .\venv\Scripts\pythonw.exe interfaz.py
exit