@echo off
REM Internal helper — use instalers/windows/INSTALL.bat or INSTALL-WINDOWS.bat at repo root.
cd /d "%~dp0\..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-Anisotropia.ps1"
if errorlevel 1 (
    echo.
    echo Install failed. See messages above.
    pause
    exit /b 1
)
