# Portable Python Environment Creator for ddQuint Windows
# Creates a truly portable Python environment using embedded distribution
# Works from build directory - detects architecture automatically

param(
    [string]$DistDir
)

$ErrorActionPreference = "Stop"

Write-Host "Creating Portable Python Environment for ddQuint" -ForegroundColor Cyan
Write-Host "==============================================="
Write-Host "Script revision: rev-2025-portable" -ForegroundColor Magenta

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Auto-detect architecture from directory structure
function Get-TargetArchitecture {
    param([string]$BaseDir)
    
    $CurrentDir = Split-Path -Leaf $BaseDir
    if ($CurrentDir -match "arm64") {
        return "arm64"
    } elseif ($CurrentDir -match "x64") {
        return "x64"
    }
    
    # Check parent directory names
    $ParentPath = $BaseDir
    while ($ParentPath -and $ParentPath -ne [System.IO.Path]::GetPathRoot($ParentPath)) {
        $DirName = Split-Path -Leaf $ParentPath
        if ($DirName -match "arm64") { return "arm64" }
        if ($DirName -match "x64") { return "x64" }
        $ParentPath = Split-Path -Parent $ParentPath
    }
    
    # Fallback: check for ddQuint executable architecture
    $ExePath = Join-Path $BaseDir "ddQuint.exe"
    if (Test-Path $ExePath) {
        try {
            $FileInfo = Get-ItemProperty $ExePath
            # This is a simple heuristic - in practice, you might want to check PE headers
            if ((Get-Item $ExePath).Length -gt 3000000) {
                return "x64"  # Larger files typically indicate x64
            }
        } catch { }
    }
    
    Write-Host "WARNING: Could not detect architecture, defaulting to x64" -ForegroundColor Yellow
    return "x64"
}

# Determine distribution directory and architecture
function Resolve-DistDir {
    param([string]$BaseDir)

    if ($PSBoundParameters.ContainsKey('DistDir') -and $DistDir) {
        if (-not (Test-Path $DistDir)) {
            throw "Specified DistDir not found: $DistDir"
        }
        return (Resolve-Path $DistDir).Path
    }

    # If running from inside a published folder
    if (Test-Path (Join-Path $BaseDir 'ddQuint.exe')) {
        return $BaseDir
    }

    # Look for build directories
    $x64 = Join-Path $BaseDir 'dist\win-x64-standalone'
    $arm = Join-Path $BaseDir 'dist\win-arm64-standalone'
    
    if (Test-Path $x64) { return $x64 }
    if (Test-Path $arm) { return $arm }

    throw "Could not locate dist folder. Expected: $x64 or $arm, or current folder with ddQuint.exe"
}

$DistDir = Resolve-DistDir -BaseDir $ProjectDir
$TargetArch = Get-TargetArchitecture -BaseDir $DistDir
$PythonBundleDir = Join-Path $DistDir 'Python'

Write-Host "Project directory: $ProjectDir" -ForegroundColor Yellow
Write-Host "Distribution directory: $DistDir" -ForegroundColor Yellow
Write-Host "Target architecture: $TargetArch" -ForegroundColor Yellow
Write-Host "Python bundle directory: $PythonBundleDir" -ForegroundColor Yellow

# Python version and URLs
$PythonVersion = "3.12.9"
$EmbedUrls = @{
    "x64" = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
    "arm64" = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-arm64.zip"
}

# Dependencies
$Dependencies = @(
    "pandas>=1.0.0",
    "numpy>=1.18.0", 
    "matplotlib>=3.3.0",
    "scikit-learn>=0.24.0",
    "hdbscan>=0.8.27",
    "openpyxl>=3.0.5",
    "Send2Trash>=1.8.2",
    "colorama>=0.4.4",
    "tqdm>=4.60.0"
)

# Cache directory for downloads
$CacheRoot = if ($env:LOCALAPPDATA) {
    Join-Path $env:LOCALAPPDATA "ddQuint\python\portable\$PythonVersion"
} else {
    Join-Path $env:TEMP "ddQuint-python-portable-$PythonVersion"
}
New-Item -ItemType Directory -Path $CacheRoot -Force | Out-Null

# Check for ARM64 wheels directory
$ProjectWheelDir = Join-Path $DistDir "resources\arm64_wheels"
$UseLocalWheels = (Test-Path $ProjectWheelDir) -and ($TargetArch -eq "arm64")
if ($UseLocalWheels) {
    Write-Host "Using local ARM64 wheels from: $ProjectWheelDir" -ForegroundColor Green
} else {
    Write-Host "No local wheels directory found (or not ARM64), will use PyPI" -ForegroundColor Yellow
}

# Set up Python bundle directory (preserve any staged content)
Write-Host "Setting up Python bundle directory..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path $PythonBundleDir -Force | Out-Null

# Download and extract Python embedded distribution
$EmbedUrl = $EmbedUrls[$TargetArch]
$EmbedZip = Join-Path $CacheRoot "python-$PythonVersion-embed-$TargetArch.zip"

Write-Host "Downloading Python $PythonVersion embedded distribution ($TargetArch)..." -ForegroundColor Cyan
if (-not (Test-Path $EmbedZip)) {
    try {
        Invoke-WebRequest -Uri $EmbedUrl -OutFile $EmbedZip -UseBasicParsing
        Write-Host "Downloaded: $EmbedZip" -ForegroundColor Green
    } catch {
        Write-Host "ERROR: Failed to download Python embedded distribution" -ForegroundColor Red
        Write-Host "URL: $EmbedUrl" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Using cached embedded distribution: $EmbedZip" -ForegroundColor Green
}

Write-Host "Extracting Python embedded distribution..." -ForegroundColor Cyan
try {
    Expand-Archive -Path $EmbedZip -DestinationPath $PythonBundleDir -Force
    Write-Host "Python extracted to: $PythonBundleDir" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Failed to extract Python embedded distribution" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# Enable site-packages in embedded Python
Write-Host "Configuring embedded Python for package installation..." -ForegroundColor Cyan
$PthFiles = Get-ChildItem -Path $PythonBundleDir -Filter "python*._pth"
if ($PthFiles) {
    $PthFile = $PthFiles[0].FullName
    Write-Host "Configuring: $($PthFiles[0].Name)" -ForegroundColor Yellow
    
    # Read content as bytes to avoid BOM issues, then convert to string
    $ContentBytes = [System.IO.File]::ReadAllBytes($PthFile)
    $Content = [System.Text.Encoding]::UTF8.GetString($ContentBytes)
    
    # Split into lines and process
    $Lines = $Content -split "`r`n|`r|`n"
    $NewLines = @()
    
    foreach ($Line in $Lines) {
        if ($Line -eq '#import site') {
            $NewLines += 'import site'
            Write-Host "  Enabled site-packages" -ForegroundColor Green
        } else {
            $NewLines += $Line
        }
    }
    
    # Add current directory to Python path for relative imports
    $NewLines += ""
    $NewLines += "# Enable relative imports for bundled ddquint package"
    $NewLines += "."
    
    # Write back as ASCII/UTF-8 without BOM
    $NewContent = $NewLines -join "`r`n"
    [System.IO.File]::WriteAllText($PthFile, $NewContent, [System.Text.Encoding]::ASCII)
    
    Write-Host "  Added relative import support" -ForegroundColor Green
    Write-Host "Python path configuration updated successfully" -ForegroundColor Green
} else {
    Write-Host "WARNING: No ._pth file found in embedded distribution" -ForegroundColor Yellow
}

# Verify Python installation
$PythonExe = Join-Path $PythonBundleDir "python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "ERROR: Python executable not found at $PythonExe" -ForegroundColor Red
    exit 1
}

# Test basic Python functionality first
Write-Host "Testing Python installation..." -ForegroundColor Cyan
try {
    $TestResult = & $PythonExe -c "import sys; print('Python OK:', sys.version_info[:2])" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Python test failed:" -ForegroundColor Red
        Write-Host $TestResult -ForegroundColor Red
        Write-Host ""
        Write-Host "This usually indicates a corrupted embedded distribution." -ForegroundColor Yellow
        Write-Host "Try deleting the cache directory and re-running:" -ForegroundColor Yellow
        Write-Host "$CacheRoot" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Python test passed: $TestResult" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Cannot run Python executable" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# Install pip in embedded Python (embedded distributions don't include ensurepip)
Write-Host "Installing pip in embedded Python..." -ForegroundColor Cyan

# Try ensurepip first (some embedded distributions include it)
$PipInstalled = $false
try {
    Write-Host "Trying ensurepip..." -ForegroundColor Yellow
    $PipOutput = & $PythonExe -m ensurepip --default-pip --upgrade 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Pip installed via ensurepip" -ForegroundColor Green
        $PipInstalled = $true
    }
} catch {
    Write-Host "ensurepip not available in this embedded distribution" -ForegroundColor Yellow
}

# If ensurepip failed, use get-pip.py
if (-not $PipInstalled) {
    Write-Host "Installing pip via get-pip.py..." -ForegroundColor Yellow
    
    $GetPipUrl = "https://bootstrap.pypa.io/get-pip.py"
    $GetPipPath = Join-Path $CacheRoot "get-pip.py"
    
    # Download get-pip.py
    if (-not (Test-Path $GetPipPath)) {
        try {
            Write-Host "Downloading get-pip.py..." -ForegroundColor Gray
            Invoke-WebRequest -Uri $GetPipUrl -OutFile $GetPipPath -UseBasicParsing
        } catch {
            Write-Host "ERROR: Failed to download get-pip.py" -ForegroundColor Red
            Write-Host $_.Exception.Message -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "Using cached get-pip.py" -ForegroundColor Gray
    }
    
    # Install pip using get-pip.py
    try {
        $PipOutput = & $PythonExe $GetPipPath --no-warn-script-location 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: get-pip.py failed with exit code $LASTEXITCODE" -ForegroundColor Red
            Write-Host "Output:" -ForegroundColor Yellow
            Write-Host $PipOutput -ForegroundColor Yellow
            throw "get-pip.py installation failed"
        }
        Write-Host "Pip installed successfully via get-pip.py" -ForegroundColor Green
        $PipInstalled = $true
    } catch {
        Write-Host "ERROR: Failed to install pip via get-pip.py" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        exit 1
    }
}

if (-not $PipInstalled) {
    Write-Host "ERROR: Could not install pip through any method" -ForegroundColor Red
    exit 1
}

# Verify pip is working and upgrade if needed
Write-Host "Verifying pip installation..." -ForegroundColor Cyan
try {
    $PipVersion = & $PythonExe -m pip --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Pip version: $PipVersion" -ForegroundColor Green
        
        # Upgrade pip to latest
        Write-Host "Upgrading pip to latest version..." -ForegroundColor Yellow
        & $PythonExe -m pip install --upgrade pip --no-warn-script-location
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Pip upgraded successfully" -ForegroundColor Green
        } else {
            Write-Host "Warning: Pip upgrade failed, but continuing with existing version" -ForegroundColor Yellow
        }
    } else {
        throw "Pip verification failed"
    }
} catch {
    Write-Host "ERROR: Pip is not working properly" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# Install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Cyan

# Special handling for ARM64 with local wheels
if ($UseLocalWheels) {
    Write-Host "Installing ARM64-specific packages from local wheels..." -ForegroundColor Yellow
    
    # Helper function to find wheels
    function Get-WheelPath {
        param([string]$Pattern)
        $Wheel = Get-ChildItem -Path $ProjectWheelDir -Filter $Pattern -File | Select-Object -First 1
        if ($Wheel) { return $Wheel.FullName }
        return $null
    }
    
    # Install NumPy first (required by others)
    $NumpyWheel = Get-WheelPath "numpy-*-cp312-cp312-win_arm64.whl"
    if ($NumpyWheel) {
        Write-Host "Installing NumPy from local wheel..." -ForegroundColor Yellow
        & $PythonExe -m pip install $NumpyWheel
    }
    
    # Install SciPy
    $ScipyWheel = Get-WheelPath "scipy-*-cp312-cp312-win_arm64.whl"
    if ($ScipyWheel) {
        Write-Host "Installing SciPy from local wheel..." -ForegroundColor Yellow
        & $PythonExe -m pip install $ScipyWheel
    }
    
    # Install scikit-learn
    $SklearnWheel = Get-WheelPath "scikit_learn-*-cp312-cp312-win_arm64.whl"
    if ($SklearnWheel) {
        Write-Host "Installing scikit-learn dependencies..." -ForegroundColor Yellow
        & $PythonExe -m pip install joblib threadpoolctl
        
        Write-Host "Installing scikit-learn from local wheel..." -ForegroundColor Yellow
        & $PythonExe -m pip install $SklearnWheel
    }
    
    # Install hdbscan if available
    $HdbscanWheel = Get-WheelPath "hdbscan-*-cp312-cp312-win_arm64.whl"
    if ($HdbscanWheel) {
        Write-Host "Installing hdbscan from local wheel..." -ForegroundColor Yellow
        & $PythonExe -m pip install $HdbscanWheel
    }
}

# Install remaining dependencies (or all if no local wheels)
foreach ($Dep in $Dependencies) {
    # Skip if already installed from local wheels
    if ($UseLocalWheels) {
        if ($Dep -like 'numpy*' -or $Dep -like 'scipy*' -or $Dep -like 'scikit-learn*' -or $Dep -like 'hdbscan*') {
            $PackageName = ($Dep -split '>=')[0]
            
            # Map package names to their import names
            $ImportName = $PackageName
            if ($PackageName -eq 'scikit-learn') { $ImportName = 'sklearn' }
            elseif ($PackageName -eq 'Send2Trash') { $ImportName = 'send2trash' }
            else { $ImportName = $PackageName.Replace('-', '_') }
            
            try {
                $CheckResult = & $PythonExe -c "import $ImportName; print('installed')" 2>$null
                if ($CheckResult -eq 'installed') {
                    Write-Host "Skipping $Dep (already installed from local wheel)" -ForegroundColor DarkGray
                    continue
                }
            } catch {
                # If import check fails, continue with installation
            }
        }
    }
    
    Write-Host "Installing $Dep..." -ForegroundColor Yellow
    & $PythonExe -m pip install $Dep
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: Failed to install $Dep" -ForegroundColor Yellow
    }
}

# Install ddQuint package
Write-Host "Installing ddQuint package..." -ForegroundColor Cyan

# Find ddQuint source
$PossibleDdquintPaths = @(
    (Join-Path $ProjectDir "src\ddQuint.Desktop\Python\ddquint"),
    (Join-Path $DistDir "Python\ddquint"),
    (Join-Path $DistDir "ddquint")
)

$DdquintSrc = $null
foreach ($Path in $PossibleDdquintPaths) {
    if (Test-Path $Path) {
        $DdquintSrc = $Path
        break
    }
}

if (-not $DdquintSrc) {
    Write-Host "ddQuint package not pre-staged. Attempting to copy from source..." -ForegroundColor Yellow
    
    # Try to find the source in the original project structure
    $OriginalSource = Join-Path $ProjectDir "src\ddQuint.Desktop\Python\ddquint"
    if (Test-Path $OriginalSource) {
        Write-Host "Found original source, copying to staging area..." -ForegroundColor Yellow
        $StagingDir = Join-Path $DistDir "Python\ddquint"
        
        try {
            # Create the staging directory structure
            $StagingParent = Join-Path $DistDir "Python"
            New-Item -ItemType Directory -Path $StagingParent -Force | Out-Null
            
            # Copy the ddQuint package
            Copy-Item -Path $OriginalSource -Destination $StagingDir -Recurse -Force
            $DdquintSrc = $StagingDir
            Write-Host "ddQuint package staged successfully" -ForegroundColor Green
        } catch {
            Write-Host "ERROR: Failed to stage ddQuint package: $($_.Exception.Message)" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "ERROR: ddQuint source package not found anywhere" -ForegroundColor Red
        Write-Host "Searched locations:" -ForegroundColor Red
        $PossibleDdquintPaths | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
        Write-Host "Original source location: $OriginalSource" -ForegroundColor Red
        Write-Host ""
        Write-Host "This means the build script didn't properly stage the ddQuint Python package." -ForegroundColor Yellow
        Write-Host "Please run the build script again: ./build.sh" -ForegroundColor Yellow
        exit 1
    }
}

# Copy ddQuint package to Python's site-packages equivalent (Lib/site-packages)
$SitePackagesDir = Join-Path $PythonBundleDir "Lib\site-packages"
if (-not (Test-Path $SitePackagesDir)) {
    New-Item -ItemType Directory -Path $SitePackagesDir -Force | Out-Null
}

$DdquintDest = Join-Path $SitePackagesDir "ddquint"
Copy-Item -Path $DdquintSrc -Destination $DdquintDest -Recurse -Force

Write-Host "ddQuint package installed from: $DdquintSrc" -ForegroundColor Green

# Create portable launcher
Write-Host "Creating portable Python launcher..." -ForegroundColor Cyan

$LauncherContent = @"
@echo off
REM Portable Python launcher for ddQuint
REM Uses bundled Python embedded distribution

setlocal
set "BUNDLE_DIR=%~dp0"
set "PYTHON_EXE=%BUNDLE_DIR%python.exe"

REM Ensure we're using the bundled Python
set "PYTHONHOME=%BUNDLE_DIR%"
set "PYTHONPATH=%BUNDLE_DIR%Lib;%BUNDLE_DIR%Lib\site-packages"

REM Run Python with all passed arguments
"%PYTHON_EXE%" %*
"@

$LauncherPath = Join-Path $PythonBundleDir "python_launcher.bat"
Set-Content -Path $LauncherPath -Value $LauncherContent -Encoding ASCII

# Test the installation
Write-Host "Testing portable Python environment..." -ForegroundColor Cyan

$TestScript = @'
import sys
print("Python version:", sys.version)
print("Python executable:", sys.executable)
print("Python path:", sys.path)

try:
    import ddquint
    print("SUCCESS: ddQuint imported from:", ddquint.__file__)
    
    # Test key imports
    from ddquint.config import Config
    from ddquint.core.file_processor import process_directory
    print("SUCCESS: Key ddQuint modules imported")
    
    # Test config
    config = Config.get_instance()
    print("SUCCESS: Config initialized")
    
except ImportError as e:
    print("ERROR: Import failed:", e)
    sys.exit(1)

print("=== Portable Python environment test PASSED ===")
'@

$TestFile = Join-Path $env:TEMP "ddquint_portable_test.py"
Set-Content -Path $TestFile -Value $TestScript -Encoding UTF8

try {
    $TestResult = & $PythonExe $TestFile
    Write-Host "Test Results:" -ForegroundColor Green
    Write-Host $TestResult -ForegroundColor Gray
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Portable Python environment created successfully!" -ForegroundColor Green
    } else {
        Write-Host "❌ Environment test failed!" -ForegroundColor Red
        exit 1
    }
} finally {
    Remove-Item -Path $TestFile -Force -ErrorAction SilentlyContinue
}

# Cleanup to reduce size
Write-Host "Cleaning up to reduce bundle size..." -ForegroundColor Cyan

$CleanupPaths = @(
    (Join-Path $PythonBundleDir "Lib\site-packages\pip"),
    (Join-Path $PythonBundleDir "Lib\site-packages\setuptools")
)

foreach ($Path in $CleanupPaths) {
    if (Test-Path $Path) {
        try {
            Remove-Item -Path $Path -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "Removed: $(Split-Path -Leaf $Path)" -ForegroundColor DarkGray
        } catch { }
    }
}

# Remove .pyc files and __pycache__ directories
Get-ChildItem -Path $PythonBundleDir -Filter "*.pyc" -Recurse | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $PythonBundleDir -Filter "__pycache__" -Directory -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Display final information
$BundleSize = (Get-ChildItem -Path $PythonBundleDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB

Write-Host ""
Write-Host "🎉 Portable Python Environment Created!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host "Location: $PythonBundleDir" -ForegroundColor Yellow
Write-Host "Size: $([math]::Round($BundleSize, 1)) MB" -ForegroundColor Yellow
Write-Host "Architecture: $TargetArch" -ForegroundColor Yellow
Write-Host "Launcher: $LauncherPath" -ForegroundColor Yellow
Write-Host ""
Write-Host "This Python environment is fully portable and can be copied to any Windows $TargetArch machine!" -ForegroundColor Cyan