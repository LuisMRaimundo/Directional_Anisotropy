@echo off
REM Same as INSTALL.bat - use INSTALL.bat or START-HERE.bat
cd /d "%~dp0"
call "%~dp0INSTALL.bat"
exit /b %ERRORLEVEL%
