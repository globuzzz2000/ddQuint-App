@echo off
:: ddQuint Python Bundle Setup (Easy)
:: Automatically bundles portable Python environment

echo.
echo ========================================
echo ddQuint Python Bundle Setup
echo ========================================
echo.

:: Handle UNC paths by working with the script directory directly
set "SCRIPT_DIR=%~dp0"
echo Current directory: %SCRIPT_DIR%
echo.

:: Check for UNC path and provide guidance
echo %SCRIPT_DIR% | findstr /C:\\\\ >nul
if %ERRORLEVEL% EQU 0 (
    echo WARNING: You are running from a network location \\\\
    echo For best results, copy this folder to a local drive like:
    echo - C:\ddQuint-win-x64
    echo - %USERPROFILE%\Desktop\ddQuint-win-x64
    echo.
    echo Press any key to continue anyway, or Ctrl+C to cancel and copy locally...
    pause >nul
    echo.
)

echo Configuring portable Python environment...
echo This will download and set up Python with all required dependencies.
echo.

:: Check if PowerShell is available
where powershell >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PowerShell is required but not found.
    echo Please ensure PowerShell is installed and in your PATH.
    pause
    exit /b 1
)

:: Check if the bundling engine script exists using full path
if not exist "%SCRIPT_DIR%bundle_python_engine.ps1" (
    echo ERROR: bundle_python_engine.ps1 not found in:
    echo %SCRIPT_DIR%
    echo Please ensure bundle_python.bat is in the ddQuint application directory.
    echo.
    echo Contents of current directory:
    dir "%SCRIPT_DIR%" /b
    pause
    exit /b 1
)

echo Running Python bundle setup...
echo.

:: Run the PowerShell script using full path
powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%bundle_python_engine.ps1" -DistDir "%SCRIPT_DIR%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Python bundle setup completed successfully!
    echo ========================================
    echo.
    echo ddQuint is now ready to use with bundled Python.
    echo You can launch the application by running ddQuint.exe
    echo.
    echo The Python environment is completely self-contained
    echo and can be moved to other Windows machines of the same architecture.
    echo.
) else (
    echo.
    echo ========================================
    echo Setup failed!
    echo ========================================
    echo.
    echo Please check the error messages above.
    echo You may need to:
    echo - Check internet connection (for downloading Python)
    echo - Run as administrator if permission issues occur
    echo - Ensure antivirus is not blocking the setup
    echo.
)

pause