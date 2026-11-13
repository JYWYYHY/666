@echo off
chcp 65001 >nul
setlocal EnableExtensions
title BAT Encoding Fix

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

echo ============================================
echo   BAT / CMD Encoding Fix Tool
echo   Target: %SCRIPT_DIR%
echo ============================================
echo.

if not exist "%~dp0Fix-BatEncoding.ps1" (
    echo [ERROR] Fix-BatEncoding.ps1 not found.
    echo Please put both files in the same folder.
    echo.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Fix-BatEncoding.ps1" -TargetDir "%SCRIPT_DIR%" -ExcludeFile "FixBAT.bat"

echo.
echo Press any key to exit...
pause >nul