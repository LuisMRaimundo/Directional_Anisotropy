@echo off
cd /d "%~dp0"
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
if not exist ".venv\Scripts\python.exe" (
    echo Run INSTALL-WINDOWS.bat first.
    pause
    exit /b 1
)
echo Starting Directional_Anisotropy...
echo Close this window to stop the app.
".venv\Scripts\python.exe" -m streamlit run Anisotropia.py
pause
