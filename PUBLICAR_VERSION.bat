@echo off
color 0E
title Publicar version - WoodTools
setlocal

:: Viaja a la carpeta del proyecto
cd /d "C:\Users\WoodTools-02\Desktop\vscode\WhatsAppMessage"

echo ============================================================
echo   PUBLICAR UNA VERSION NUEVA EN GITHUB
echo   (esto es lo que hace que se actualice a todos solo)
echo ============================================================
echo.

:: --- 1) Ubicar GitHub CLI (gh): primero en el PATH, sino en la carpeta de winget ---
set "GH="
where gh >nul 2>&1 && for /f "delims=" %%g in ('where gh') do set "GH=%%g"
if not defined GH for /f "delims=" %%g in ('powershell -NoProfile -Command "$p=Get-ChildItem $env:LOCALAPPDATA\Microsoft\WinGet\Packages -Recurse -Filter gh.exe -ErrorAction SilentlyContinue ^| Select-Object -First 1 -ExpandProperty FullName; if($p){$p}"') do set "GH=%%g"
if not defined GH (
    echo [ERROR] No se encontro GitHub CLI ^(gh^).
    echo Instalalo con:   winget install --id GitHub.cli
    pause & exit /b 1
)
echo GitHub CLI: "%GH%"

:: --- 2) Verificar sesion de GitHub (si no hay, iniciarla una sola vez) ---
"%GH%" auth status >nul 2>&1
if errorlevel 1 (
    echo.
    echo No hay sesion de GitHub iniciada. La iniciamos una sola vez.
    echo Se te mostrara un codigo y se abrira el navegador para autorizar.
    echo.
    "%GH%" auth login --hostname github.com --git-protocol https --web
    "%GH%" auth status >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] No se completo el inicio de sesion. Proba de nuevo.
        pause & exit /b 1
    )
)

:: --- 3) Leer la version desde VERSION_APP en mainCode.py ---
set "VER="
for /f "delims=" %%v in ('powershell -NoProfile -Command "(Select-String -Path mainCode.py -Pattern 'VERSION_APP\s*=\s*\"([\d.]+)\"').Matches.Groups[1].Value"') do set "VER=%%v"
if not defined VER (
    echo [ERROR] No pude leer VERSION_APP de mainCode.py
    pause & exit /b 1
)
set "SETUP=Instalador\Instalador_GestorMarketing_WoodTools_v%VER%.exe"
if not exist "%SETUP%" (
    echo [ERROR] No existe el instalador:  %SETUP%
    echo Primero genera el instalador con  CONSTRUIR_INSTALADOR.bat
    pause & exit /b 1
)

echo.
echo Version a publicar:  v%VER%
echo Archivo:             %SETUP%
echo.

:: --- 4) Chequear que no exista ya ese release ---
"%GH%" release view "v%VER%" --repo woodtoolsmarketing/WhatsAppMessage >nul 2>&1
if not errorlevel 1 (
    echo [AVISO] Ya existe un release v%VER% en GitHub.
    echo Si queres sacar una version nueva, subi el numero en mainCode.py,
    echo volve a generar el instalador con CONSTRUIR_INSTALADOR.bat y corre esto de nuevo.
    pause & exit /b 1
)

:: --- 5) Pedir las novedades (lo veran los usuarios al actualizar) ---
echo Escribi las NOVEDADES de esta version (una linea). Lo veran los usuarios.
set "NOTAS="
set /p "NOTAS=Novedades: "
if not defined NOTAS set "NOTAS=Version %VER%"

:: --- 6) Publicar el release con el instalador adjunto ---
echo.
echo Publicando release v%VER% ...
"%GH%" release create "v%VER%" "%SETUP%" --repo woodtoolsmarketing/WhatsAppMessage --title "Version %VER%" --notes "%NOTAS%"
if errorlevel 1 (
    echo.
    echo [ERROR] Fallo la publicacion. Revisa los mensajes de arriba.
    pause & exit /b 1
)

echo.
echo ============================================================
echo   RELEASE v%VER% PUBLICADO CON EXITO!
echo   Quien tenga una version anterior instalada lo recibira
echo   solo, la proxima vez que abra la app.
echo ============================================================
echo.
pause
