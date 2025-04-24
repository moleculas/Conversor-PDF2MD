@echo off
title Iniciar PDF2MD
color 0A

echo ===================================
echo    Iniciando aplicación PDF2MD
echo ===================================
echo.

echo Nota: Este script asume que Docker Desktop ya está en ejecución.
echo.

:: Comprobar si Docker está disponible
docker info >NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker no está disponible.
    echo Por favor, inicie Docker Desktop manualmente y vuelva a ejecutar este script.
    echo.
    pause
    exit /b 1
)

echo Docker está disponible. Continuando...

:: Navegar al directorio del proyecto
cd /d D:\SOURCE\REACT-VITE\pdf2md

:: Iniciar los contenedores
echo Iniciando contenedores PDF2MD...
docker-compose up -d

:: Esperar un momento
echo Esperando a que los servicios estén disponibles...
timeout /t 10 /nobreak > NUL

:: Abrir el navegador
echo Abriendo la aplicación en el navegador...
start http://localhost:8000/

echo.
echo ===================================
echo   PDF2MD está ejecutándose ahora
echo   URL: http://localhost:8000/
echo ===================================
echo.
echo Para detener la aplicación, ejecute: docker-compose down
echo en el directorio D:\SOURCE\REACT-VITE\pdf2md
echo.
pause