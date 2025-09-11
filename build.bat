@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Building ddQuint Windows Application
echo ========================================

set PROJECT_DIR=%~dp0
set DIST_DIR=%PROJECT_DIR%dist
set SOLUTION_FILE=%PROJECT_DIR%ddQuint.sln

echo Project directory: %PROJECT_DIR%
echo Distribution directory: %DIST_DIR%
echo Solution file: %SOLUTION_FILE%

:: Clean previous builds
echo.
echo [1/5] Cleaning previous builds...
if exist "%DIST_DIR%" (
    echo Removing existing dist directory...
    rmdir /s /q "%DIST_DIR%"
)
mkdir "%DIST_DIR%"

:: Restore NuGet packages
echo.
echo [2/5] Restoring NuGet packages...
dotnet restore "%SOLUTION_FILE%"
if %errorlevel% neq 0 (
    echo ERROR: Failed to restore NuGet packages
    exit /b %errorlevel%
)

:: Build solution
echo.
echo [3/5] Building solution...
dotnet build "%SOLUTION_FILE%" --configuration Release --no-restore
if %errorlevel% neq 0 (
    echo ERROR: Build failed
    exit /b %errorlevel%
)

:: Publish application
echo.
echo [4/5] Publishing application...
set PUBLISH_DIR=%DIST_DIR%\ddQuint
dotnet publish "%PROJECT_DIR%src\ddQuint.Desktop\ddQuint.Desktop.csproj" ^
    --configuration Release ^
    --output "%PUBLISH_DIR%" ^
    --self-contained false ^
    --no-restore

if %errorlevel% neq 0 (
    echo ERROR: Publish failed
    exit /b %errorlevel%
)

:: Copy additional files
echo.
echo [5/5] Copying additional files...

:: Copy ARM64 wheels for bundling
echo Copying ARM64 wheels...
if exist "%PROJECT_DIR%resources\arm64_wheels" (
    if not exist "%PUBLISH_DIR%\resources" mkdir "%PUBLISH_DIR%\resources"
    xcopy /E /I /Y "%PROJECT_DIR%resources\arm64_wheels" "%PUBLISH_DIR%\resources\arm64_wheels" >nul
    echo ARM64 wheels copied to %PUBLISH_DIR%\resources\arm64_wheels
) else (
    echo WARNING: ARM64 wheels not found at %PROJECT_DIR%resources\arm64_wheels
)

:: Pre-stage ddquint Python package so bundler can copy into venv
echo Staging ddquint Python package...
set PY_STAGING_DIR=%PUBLISH_DIR%\Python
if not exist "%PY_STAGING_DIR%" mkdir "%PY_STAGING_DIR%"
if exist "%PROJECT_DIR%..\ddquint" (
    xcopy /E /I /Y "%PROJECT_DIR%..\ddquint" "%PY_STAGING_DIR%\ddquint" >nul
    echo ddquint staged at %PY_STAGING_DIR%\ddquint
) else (
    echo WARNING: ddquint source not found at %PROJECT_DIR%..\ddquint
)

:: Copy icon if it exists
if exist "%PROJECT_DIR%..\icon.png" (
    copy "%PROJECT_DIR%..\icon.png" "%PUBLISH_DIR%\ddQuint.ico"
    echo Icon copied
)

:: Create launcher script
echo.
echo Creating launcher script...
set LAUNCHER=%DIST_DIR%\ddQuint.bat
echo @echo off > "%LAUNCHER%"
echo cd /d "%%~dp0ddQuint" >> "%LAUNCHER%"
echo dotnet ddQuint.Desktop.dll >> "%LAUNCHER%"

:: Success message
echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Application built to: %PUBLISH_DIR%
echo Launcher created at: %LAUNCHER%
echo.
echo To run the application:
echo   1. Double-click %LAUNCHER%
echo   2. Or navigate to %PUBLISH_DIR% and run: dotnet ddQuint.Desktop.dll
echo.
echo Note: Requires .NET 8 Runtime to be installed on target machine
echo Download from: https://dotnet.microsoft.com/download/dotnet/8.0
echo.

pause
