@echo off
title Iniciando WoodTools...
:: Espera 15 segundos para darle tiempo a Windows a conectar el WiFi/Red
timeout /t 15 /nobreak > NUL

:: Ejecuta tu actualizador principal con la orden "AUTO"
call "%~dp0ACTUALIZADOR.bat" AUTO
exit