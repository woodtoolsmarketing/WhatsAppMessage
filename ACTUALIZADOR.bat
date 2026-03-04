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
    
    :: Abre el EXE directamente si existe, sino usa el entorno virtual por defecto
    if exist "dist\Gestor de Mensajes Difusion.exe" (
        start "" "dist\Gestor de Mensajes Difusion.exe"
    ) else (
        start .\venv\Scripts\pythonw.exe interfaz.py
    )
    exit
) else (
    echo.
    echo Descargando nuevos cambios...
    git pull origin main
    echo.
    
    echo ===================================
    echo    COMPILANDO NUEVA VERSION...
    echo  Esto puede tardar un minuto. Por favor, 
    echo  NO cierres esta ventana.
    echo ===================================
    
    :: 1. Limpiamos la basura vieja para evitar el WinError 5
    if exist "build" rmdir /s /q "build"
    if exist "dist\Gestor de Mensajes Difusion.exe" del /f /q "dist\Gestor de Mensajes Difusion.exe"

    :: 2. Ejecutamos PyInstaller usando el entorno virtual de esta PC
    .\venv\Scripts\pyinstaller.exe --noconsole --onefile --hidden-import pandas --hidden-import gspread --hidden-import oauth2client --hidden-import google_auth_oauthlib --name "Gestor de Mensajes Difusion" --icon "Imagenes/logo.ico" --add-data "Imagenes;Imagenes" --add-data "credenciales.json;." interfaz.py

    echo.
    echo ===================================
    echo   ACTUALIZACION Y COMPILACION LISTA
    echo ===================================
    
    :: VERIFICAMOS SI VINO DEL INICIO AUTOMATICO DE WINDOWS
    if "%~1"=="AUTO" (
        echo Iniciando programa de forma automatica tras actualizar...
        timeout /t 2 > NUL
        start "" "dist\Gestor de Mensajes Difusion.exe"
        exit
    ) else (
        echo El programa no se iniciara automaticamente para asentar los cambios.
        echo Por favor, vuelve a abrirlo desde tu acceso directo.
        echo.
        pause
        exit
    )
)