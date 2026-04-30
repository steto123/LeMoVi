@echo off
echo ========================================================
echo LeMoVi Installer Compilation
echo ========================================================
echo This script uses Inno Setup Compiler to build the installer.
echo Make sure Inno Setup is installed at:
echo "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
echo.

set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if not exist %ISCC% (
    echo [ERROR] Inno Setup Compiler not found!
    echo Please download and install Inno Setup 6 from:
    echo https://jrsoftware.org/isdl.php
    pause
    exit /b
)

echo Compiling build_installer.iss...
%ISCC% "build_installer.iss"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Installer successfully created in the 'Installer' folder!
) else (
    echo.
    echo [ERROR] Compilation failed.
)
pause
