@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo Starting LeMoVi...

set "PYTHON_PORTABLE=portable_python\WPy64-31180\python-3.11.8.amd64\pythonw.exe"
set "PYTHON_VENV=venv\Scripts\pythonw.exe"

if exist "%PYTHON_PORTABLE%" (
    echo [INFO] Using Portable Python...
    start "" "%PYTHON_PORTABLE%" "app.py"
    exit /b
)

if exist "%PYTHON_VENV%" (
    echo [INFO] Using local VENV...
    start "" "%PYTHON_VENV%" "app.py"
    exit /b
)

echo.
echo [ERROR] No Python environment found!
echo Please run 'create_portable_python.bat' if this is the first start.
echo.
pause
