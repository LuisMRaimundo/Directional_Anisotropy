@echo off
cd /d "%~dp0"
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

if exist ".venv\Scripts\python.exe" (
    echo A iniciar Directional_Anisotropy...
    ".venv\Scripts\python.exe" -m streamlit run Anisotropia.py
) else (
    echo Virtual environment not found.
    echo Double-click INSTALL-WINDOWS.bat for one-click setup.
    pause
    exit /b 1
)
pause
