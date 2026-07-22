@echo off
color 0B
title Constructor de Instalador WoodTools
setlocal

:: Viaja a la carpeta del proyecto
cd /d "C:\Users\WoodTools-02\Desktop\vscode\WhatsAppMessage"

echo ============================================================
echo   PASO 1 de 2: Compilando la aplicacion (.exe) con el codigo actual
echo   Esto puede tardar 1-2 minutos. NO cierres esta ventana.
echo ============================================================
echo.

:: Limpia la basura vieja para evitar errores de bloqueo
if exist "build" rmdir /s /q "build"
if exist "dist\Gestor de Mensajes Difusion.exe" del /f /q "dist\Gestor de Mensajes Difusion.exe"

:: Compila el .exe usando el entorno virtual de esta PC
.\venv\Scripts\pyinstaller.exe "Gestor de Mensajes Difusion.spec" --noconfirm --clean
if not exist "dist\Gestor de Mensajes Difusion.exe" (
    echo.
    echo [ERROR] No se genero el .exe. Revisa los mensajes de arriba.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   PASO 2 de 2: Empaquetando el instalador (setup.exe)
echo ============================================================
echo.

:: Ubica el compilador de Inno Setup (ISCC)
set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo [ERROR] No se encontro Inno Setup ^(ISCC.exe^). Instalalo con:
    echo    winget install --id JRSoftware.InnoSetup
    pause
    exit /b 1
)

:: Lee la version desde VERSION_APP en mainCode.py (unica fuente de la version)
for /f "delims=" %%v in ('powershell -NoProfile -Command "(Select-String -Path mainCode.py -Pattern 'VERSION_APP\s*=\s*\"([\d.]+)\"').Matches.Groups[1].Value"') do set "VER=%%v"
if "%VER%"=="" set "VER=12.2"
echo Version detectada: %VER%

"%ISCC%" /DMiVersion=%VER% "instalador.iss"
if errorlevel 1 (
    echo.
    echo [ERROR] Fallo la compilacion del instalador.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   LISTO! El instalador quedo en la carpeta:  Instalador\
echo   Ese setup.exe es el que le pasas a la persona.
echo.
echo   Para que se actualice A TODOS SOLO, ademas publicalo en
echo   GitHub Releases (ver COMO_PUBLICAR_UNA_ACTUALIZACION.md).
echo ============================================================
echo.

:: Abre la carpeta con el instalador ya generado
start "" "Instalador"
pause
