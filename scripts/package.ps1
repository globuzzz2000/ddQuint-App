# Package ddQuint for End-User Distribution
# Creates pre-bundled distributions ready for installation
# Usage: .\package.ps1

param(
    [switch]$SkipSFX = $false
)

$ErrorActionPreference = "Stop"

Write-Host "Packaging ddQuint for End-User Distribution..." -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

$ProjectDir = Split-Path -Parent $PSScriptRoot
$ScriptsDir = "$ProjectDir\scripts"
$PackageDir = "$ProjectDir\packages"
$PythonStoreDir = "$ProjectDir\python_store"

# Clean and create package directory
if (Test-Path $PackageDir) {
    Remove-Item -Recurse -Force $PackageDir
}
New-Item -ItemType Directory -Path $PackageDir -Force | Out-Null

function Package-Runtime {
    param([string]$Runtime)
    
    $DistDir = "$ProjectDir\dist\$Runtime-standalone"
    $PackageName = "ddQuint-$Runtime"
    $TempDir = "$PackageDir\temp-$Runtime"
    $StoredPythonDir = "$PythonStoreDir\$Runtime"
    
    Write-Host ""
    Write-Host "Packaging $Runtime..." -ForegroundColor Yellow
    Write-Host "Source: $DistDir" -ForegroundColor Gray
    Write-Host "Python store: $StoredPythonDir" -ForegroundColor Gray
    
    if (!(Test-Path $DistDir)) {
        Write-Host "ERROR: Distribution not found: $DistDir" -ForegroundColor Red
        Write-Host "   Run build.sh or build.bat first" -ForegroundColor Red
        return $false
    }
    
    # Create temporary packaging directory
    New-Item -ItemType Directory -Path $TempDir -Force | Out-Null
    
    # Copy all application files (exclude bundling scripts from final package)
    Write-Host "Copying application files..." -ForegroundColor Green
    robocopy "$DistDir" "$TempDir" /E /XF "bundle_python*.bat" "bundle_python*.ps1" /NFL /NDL /NJH /NJS | Out-Null
    
    # Copy pre-stored Python environment if available
    if (Test-Path $StoredPythonDir) {
        Write-Host "Copying pre-bundled Python environment..." -ForegroundColor Green
        $pythonDestDir = "$TempDir\Python"
        New-Item -ItemType Directory -Path $pythonDestDir -Force | Out-Null
        robocopy "$StoredPythonDir" "$pythonDestDir" /E /NFL /NDL /NJH /NJS | Out-Null
        Write-Host "SUCCESS: Python environment copied from store" -ForegroundColor Green
    } else {
        Write-Host "WARNING: No pre-stored Python found at: $StoredPythonDir" -ForegroundColor Yellow
        Write-Host "   Creating fallback installer scripts..." -ForegroundColor Yellow
        Create-BundleOnInstallScript -TargetDir $TempDir
    }
    
    # Copy packaging-specific scripts
    Write-Host "Adding installer scripts..." -ForegroundColor Green
    Create-InstallScript -TargetDir $TempDir
    
    # Create ZIP distribution
    Write-Host "Creating ZIP package..." -ForegroundColor Green
    $zipPath = "$PackageDir\$PackageName.zip"
    Compress-Archive -Path "$TempDir\*" -DestinationPath $zipPath -Force
    
    # Create self-extracting installer (if 7z available and not skipped)
    if (!$SkipSFX -and (Get-Command "7z" -ErrorAction SilentlyContinue)) {
        Write-Host "Creating self-extracting installer..." -ForegroundColor Green
        $sfxPath = "$PackageDir\$PackageName-Setup.exe"
        
        # Create SFX config
        $sfxConfigPath = "$TempDir\sfx_config.txt"
        @"
;!@Install@!UTF-8!
Title="ddQuint Installation"
BeginPrompt="Install ddQuint Digital Droplet PCR Analysis Software?"
RunProgram="install.bat"
;!@InstallEnd@!
"@ | Out-File -FilePath $sfxConfigPath -Encoding ASCII
        
        # Try to find Windows SFX module
        $sfxModulePaths = @(
            "${env:ProgramFiles}\7-Zip\7z.sfx",
            "${env:ProgramFiles(x86)}\7-Zip\7z.sfx"
        )
        
        $sfxModule = $null
        foreach ($path in $sfxModulePaths) {
            if (Test-Path $path) {
                $sfxModule = $path
                break
            }
        }
        
        if ($sfxModule) {
            # Use 7z to create self-extracting archive
            & 7z a -sfx"$sfxModule" "$sfxPath" "$TempDir\*" -mx=9 | Out-Null
            
            if (Test-Path $sfxPath) {
                Write-Host "SUCCESS: Self-extracting installer created: $(Split-Path -Leaf $sfxPath)" -ForegroundColor Green
            } else {
                Write-Host "WARNING: SFX creation failed - only ZIP package available" -ForegroundColor Yellow
            }
        } else {
            Write-Host "WARNING: 7-Zip SFX module not found - only ZIP package available" -ForegroundColor Yellow
        }
        
        # Clean up temp config file
        if (Test-Path $sfxConfigPath) { Remove-Item $sfxConfigPath -Force }
    } elseif ($SkipSFX) {
        Write-Host "INFO: SFX creation skipped (-SkipSFX flag used)" -ForegroundColor Cyan
    } else {
        Write-Host "INFO: 7z not available - skipping self-extracting installer" -ForegroundColor Cyan
    }
    
    # Get package size
    $zipSize = [math]::Round((Get-Item $zipPath).Length / 1MB, 1)
    Write-Host "SUCCESS: ZIP package created: $(Split-Path -Leaf $zipPath) ($zipSize MB)" -ForegroundColor Green
    
    # Cleanup temp directory
    Remove-Item -Recurse -Force $TempDir
    
    return $true
}

# Create install script
function Create-InstallScript {
    param([string]$TargetDir)
    
    $installScript = @'
@echo off
setlocal enabledelayedexpansion

echo.
echo ========================================
echo ddQuint Installation
echo ========================================
echo.

REM Get installation directory
set "INSTALL_DIR=%ProgramFiles%\ddQuint"

echo Installing to: !INSTALL_DIR!
echo.

REM Create installation directory
if not exist "!INSTALL_DIR!" (
    echo Creating installation directory...
    mkdir "!INSTALL_DIR!" 2>nul
    if !ERRORLEVEL! NEQ 0 (
        echo ERROR: Could not create installation directory.
        echo Please run as Administrator or choose a different location.
        pause
        exit /b 1
    )
)

REM Copy files
echo Copying application files...
xcopy /E /I /Y /Q "*.*" "!INSTALL_DIR!\" > nul
if !ERRORLEVEL! NEQ 0 (
    echo ERROR: Failed to copy files. Please run as Administrator.
    pause
    exit /b 1
)

REM Run Python bundling if needed
if not exist "!INSTALL_DIR!\Python\python.exe" (
    echo Setting up Python environment...
    cd /d "!INSTALL_DIR!"
    if exist "bundle_python.bat" (
        call bundle_python.bat
    )
    cd /d "%~dp0"
)

REM Create desktop shortcut
echo Creating desktop shortcut...
powershell -Command "& {$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut('%USERPROFILE%\Desktop\ddQuint.lnk'); $s.TargetPath='!INSTALL_DIR!\ddQuint.exe'; $s.WorkingDirectory='!INSTALL_DIR!'; $s.Description='ddQuint - Digital Droplet PCR Analysis'; $s.Save()}" 2>nul

REM Create start menu entry
echo Creating Start Menu entry...
set "START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
if not exist "%START_MENU%" set "START_MENU=%USERPROFILE%\Start Menu\Programs"
powershell -Command "& {$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut('%START_MENU%\ddQuint.lnk'); $s.TargetPath='!INSTALL_DIR!\ddQuint.exe'; $s.WorkingDirectory='!INSTALL_DIR!'; $s.Description='ddQuint - Digital Droplet PCR Analysis'; $s.Save()}" 2>nul

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo ddQuint has been installed to:
echo !INSTALL_DIR!
echo.
echo You can now:
echo - Launch from Desktop shortcut
echo - Launch from Start Menu
echo - Run: !INSTALL_DIR!\ddQuint.exe
echo.

choice /C YN /M "Launch ddQuint now"
if !ERRORLEVEL! EQU 1 (
    echo Starting ddQuint...
    start "" "!INSTALL_DIR!\ddQuint.exe"
)

pause
'@
    
    $installScript | Out-File -FilePath "$TargetDir\install.bat" -Encoding ASCII
}

# Create bundle-on-install fallback
function Create-BundleOnInstallScript {
    param([string]$TargetDir)
    
    Write-Host "Adding Python bundling scripts for install-time setup..." -ForegroundColor Green
    Copy-Item "$ScriptsDir\bundle_python_engine.ps1" "$TargetDir\" -Force
    Copy-Item "$ScriptsDir\bundle_python.bat" "$TargetDir\" -Force
}

# Package both architectures
Write-Host "Looking for built distributions..." -ForegroundColor Cyan
$success = $true
$success = (Package-Runtime "win-arm64") -and $success
$success = (Package-Runtime "win-x64") -and $success

Write-Host ""
Write-Host "Packaging completed!" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green
Write-Host ""
Write-Host "Packages created in: $PackageDir" -ForegroundColor Cyan

if (Test-Path $PackageDir) {
    Write-Host "Available packages:" -ForegroundColor Cyan
    Get-ChildItem -Path $PackageDir -Filter "*.zip" | ForEach-Object {
        $size = [math]::Round($_.Length / 1MB, 1)
        Write-Host "   - $($_.Name) ($size MB)" -ForegroundColor Gray
    }
    Get-ChildItem -Path $PackageDir -Filter "*.exe" | ForEach-Object {
        $size = [math]::Round($_.Length / 1MB, 1)
        Write-Host "   - $($_.Name) ($size MB)" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Distribution files ready for end users!" -ForegroundColor Green
Write-Host "   - ZIP files: Extract and run install.bat" -ForegroundColor Gray
Write-Host "   - EXE files: Self-extracting installers" -ForegroundColor Gray
Write-Host ""

if (!$success) {
    Write-Host "WARNING: Some packages failed to create. Check output above for details." -ForegroundColor Yellow
    exit 1
}