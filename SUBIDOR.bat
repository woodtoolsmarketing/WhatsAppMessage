@echo off
color 0A
title Subidor WoodTools
cd /d "%~dp0"

echo Revisando si hay archivos modificados...

:: Revisa el estado de git y lo guarda temporalmente
git status --porcelain > temp_status.txt

:: Comprueba si el archivo temporal está vacío (es decir, si no hay cambios)
for %%A in (temp_status.txt) do if %%~zA==0 goto SIN_CAMBIOS

:CON_CAMBIOS
del temp_status.txt
echo.
echo Preparando la subida de los nuevos cambios...

:: Obtener la fecha y hora exacta
for /f "delims=" %%a in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Date -format 'yyyy-MM-dd-[HH-mm]'"') do set FECHA_HORA=%%a

:: Agregar y empaquetar los cambios
git add .
git commit -m "actualizacion-code-[%FECHA_HORA%]"

echo.
echo Sincronizando y subiendo a GitHub (rama prueba)...
git pull origin prueba
git push origin prueba

echo.
echo ===================================
echo   SUBIDA COMPLETADA CON EXITO
echo ===================================
timeout /t 2 > NUL
goto FIN

:SIN_CAMBIOS
del temp_status.txt
echo.
echo ===================================
echo      NO HAY CAMBIOS PARA SUBIR
echo ===================================
timeout /t 2 > NUL
goto FIN

:FIN
exit