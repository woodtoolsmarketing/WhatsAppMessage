@echo off
title Actualizacion en Segundo Plano - WoodTools

:: 1. Espera 15 segundos para darle tiempo a Windows a conectar el WiFi
timeout /t 15 /nobreak > NUL

:: 2. Se ubica en la carpeta exacta donde está instalado el programa
cd /d "%~dp0"

:: 3. Busca en GitHub si hay algo nuevo (de forma silenciosa)
git fetch origin prueba > NUL 2>&1

:: 4. Compara la version de tu PC con la de GitHub
FOR /F "tokens=*" %%a in ('git rev-parse HEAD') do SET LOCAL_VER=%%a
FOR /F "tokens=*" %%a in ('git rev-parse origin/prueba') do SET REMOTE_VER=%%a

:: 5. Si detecta que son distintas, descarga los cambios silenciosamente
if NOT "%LOCAL_VER%"=="%REMOTE_VER%" (
    git pull origin prueba > NUL 2>&1
)

:: 6. Termina el proceso y cierra la ventana negra al instante. ¡No abre el programa!
exit