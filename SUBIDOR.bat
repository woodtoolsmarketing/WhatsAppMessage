@echo off
color 0A
title Subidor WoodTools
cd /d "%~dp0"

:: 1. SALVAVIDAS: Borra el candado si quedó trabado de un error anterior
if exist .git\index.lock (
    del /f /q .git\index.lock
)

echo Revisando si hay archivos modificados...
git status --porcelain > temp_status.txt
for %%A in (temp_status.txt) do set SIZE=%%~zA
del temp_status.txt

if %SIZE%==0 (
    echo.
    echo ===================================
    echo      NO HAY CAMBIOS PARA SUBIR
    echo ===================================
    timeout /t 2 > NUL
    exit
)

echo.
echo Preparando la subida de los nuevos cambios...

:: 2. SALVAVIDAS: Obtiene la hora al instante sin usar PowerShell
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set dt=%%I
set FECHA_HORA=%dt:~0,4%-%dt:~4,2%-%dt:~6,2%-[%dt:~8,2%-%dt:~10,2%]

git add .
git commit -m "actualizacion-code-[%FECHA_HORA%]"

echo.
echo Sincronizando con GitHub (rama prueba)...
:: 3. SALVAVIDAS: --no-edit evita que Git se pause abriendo un editor de texto
git pull origin prueba --no-edit

echo.
echo Subiendo a la nube...
git push origin prueba

echo.
echo ===================================
echo   SUBIDA COMPLETADA CON EXITO
echo ===================================
timeout /t 3 > NUL
exit