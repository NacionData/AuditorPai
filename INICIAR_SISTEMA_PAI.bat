@echo off
title Sistema PAI Risaralda - Servidor Local
setlocal enabledelayedexpansion

set "PY_EXE=%LOCALAPPDATA%\Python\bin\python.exe"
if not exist "!PY_EXE!" (
    for /f "delims=" %%I in ('where py.exe 2^>nul') do (
        set "PY_EXE=%%I"
    )
)
if not exist "!PY_EXE!" (
    set "PY_EXE=python"
)

cd /d "%~dp0"
echo ========================================================
echo   SISTEMA AUDITOR Y CONSOLIDADOR PAI RISARALDA
echo   Secretaria de Salud Departamental de Risaralda
echo ========================================================
echo.
echo Iniciando servidor en: http://localhost:8000
echo Portal Municipal:      http://localhost:8000
echo Tablero Departamental: http://localhost:8000/departamental
echo.
echo Presiona Ctrl + C en esta ventana para detener el servidor.
echo ========================================================
echo.

start "" "http://localhost:8000/departamental"

"!PY_EXE!" main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Ocurrio un error al ejecutar el servidor PAI.
    pause
)
