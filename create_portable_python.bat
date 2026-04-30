@echo off
echo ==============================================
echo Building Portable Python Environment for LeMoVi
echo ==============================================

set P_DIR=portable_python
if exist %P_DIR% echo Removing old python... && rmdir /S /Q %P_DIR%
if exist WPy64-31180 echo Removing stray folder... && rmdir /S /Q WPy64-31180
mkdir %P_DIR%

echo [1/3] Downloading WinPython (Minimal)...
curl --ssl-no-revoke -L -o winpython.exe "https://github.com/winpython/winpython/releases/download/7.1.20240203final/Winpython64-3.11.8.0dot.exe"

echo [2/3] Extracting Python to %P_DIR%...
winpython.exe -y -o"%P_DIR%"
del winpython.exe

echo [3/3] Installing required packages into Portable Python...
set PYTHON_EXE="%P_DIR%\WPy64-31180\python-3.11.8.amd64\python.exe"

:: Use --no-cache-dir to avoid corrupted local caches
%PYTHON_EXE% -m pip install --no-cache-dir PyQt5 PyQtWebEngine PyQt5-sip
echo Installing Chemical Informatics dependencies (RDKit)...
%PYTHON_EXE% -m pip install --no-cache-dir rdkit

echo.
echo [VERIFICATION] Checking installation...
%PYTHON_EXE% -c "import rdkit; import PyQt5; print('Verification: RDKit and PyQt5 ready.')"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Installation verification failed! Some packages are corrupted.
    echo Please try running this script again.
    pause
    exit /b 1
)

echo.
echo ==============================================
echo Portable Python created successfully in %P_DIR%!
echo ==============================================
pause

