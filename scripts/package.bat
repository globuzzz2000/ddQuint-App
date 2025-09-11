@echo off
setlocal enabledelayedexpansion

echo ========================================
echo ddQuint Packaging Script
echo ========================================
echo.

REM Check if PowerShell is available
powershell -Command "Write-Host 'PowerShell is available'" >nul 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo ERROR: PowerShell is required but not available.
    echo Please ensure PowerShell 5.0 or later is installed.
    pause
    exit /b 1
)

REM Get script directory
set SCRIPT_DIR=%~dp0

REM Run the PowerShell packaging script
echo Running PowerShell packaging script...
echo.
powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%package.ps1" %*

REM Check if successful
if !ERRORLEVEL! EQU 0 (
    echo.
    echo ========================================
    echo Packaging completed successfully!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo Packaging failed!
    echo ========================================
)

pause