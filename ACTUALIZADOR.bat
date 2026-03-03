@echo off
color 0A
title Actualizador WoodTools

:: BLINDAJE: Viaja directo a la carpeta de tu proyecto
cd /d "C:\Users\WoodTools-02\Desktop\vscode\WhatsAppMessage"

echo Buscando actualizaciones en GitHub (rama main)...
git fetch origin main

FOR /F "tokens=*" %%a in ('git rev-parse HEAD') do SET LOCAL_VER=%%a
FOR /F "tokens=*" %%a in ('git rev-parse origin/main') do SET REMOTE_VER=%%a

if "%LOCAL_VER%"=="%REMOTE_VER%" (
    echo.
    echo ===================================
    echo    PROGRAMA SIN ACTUALIZACIONES
    echo ===================================
    timeout /t 2 > NUL
    :: Abre el programa usando el entorno virtual y cierra esta ventana negra
    start .\venv\Scripts\pythonw.exe interfaz.py
    exit
) else (
    echo.
    echo Descargando nuevos cambios...
    git pull origin main
    echo.
    echo ===================================
    echo    ACTUALIZACION COMPLETADA
    echo ===================================
    
    :: VERIFICAMOS SI VINO DEL INICIO AUTOMATICO DE WINDOWS
    if "%~1"=="AUTO" (
        echo Iniciando programa de forma automatica tras actualizar...
        timeout /t 2 > NUL
        start .\venv\Scripts\pythonw.exe interfaz.py
        exit
    ) else (
        echo El programa no se iniciara automaticamente para asentar los cambios.
        echo Por favor, vuelve a abrirlo desde tu acceso directo.
        echo.
        pause
        exit
    )
)