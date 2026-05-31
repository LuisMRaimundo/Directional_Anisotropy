@echo off
title Anisotropia Direcional - Install (Windows)
cd /d "%~dp0"

echo.
echo  ========================================
echo   Anisotropia Direcional
echo   One-click install for Windows 10/11
echo  ========================================
echo.
echo  This will install Python (if needed), set up the app,
echo  and open it in your web browser.
echo.
pause

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installers\windows\Install-Anisotropia.ps1"
if errorlevel 1 (
    echo.
    echo  Installation failed. Read the messages above.
    echo  You can also install Python from https://www.python.org/downloads/
    echo  then run this file again.
    echo.
    pause
    exit /b 1
)
