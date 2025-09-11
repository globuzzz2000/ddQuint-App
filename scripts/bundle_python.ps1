# ddQuint Python Bundle Setup (PowerShell version)
# Alternative to batch file for better UNC path support

Write-Host ""
Write-Host "========================================"
Write-Host "ddQuint Python Bundle Setup"
Write-Host "========================================"
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "Script directory: $ScriptDir"

# Check if running from UNC path
if ($ScriptDir -like "\\*") {
    Write-Host "WARNING: Running from network location" -ForegroundColor Yellow
    Write-Host "For best performance, copy this folder to a local drive like:" -ForegroundColor Yellow
    Write-Host "- C:\ddQuint-win-x64" -ForegroundColor Yellow
    Write-Host "- $env:USERPROFILE\Desktop\ddQuint-win-x64" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Press Enter to continue anyway, or Ctrl+C to cancel..." -ForegroundColor Yellow
    Read-Host
    Write-Host ""
}

Write-Host "Configuring Python bundle environment..."
Write-Host "This will download and bundle Python with all required dependencies."
Write-Host ""

# Check if the bundling engine script exists
$BundleScript = Join-Path $ScriptDir "bundle_python_engine.ps1"
if (-not (Test-Path $BundleScript)) {
    Write-Host "ERROR: bundle_python_engine.ps1 not found in:" -ForegroundColor Red
    Write-Host $ScriptDir -ForegroundColor Red
    Write-Host ""
    Write-Host "Contents of directory:" -ForegroundColor Yellow
    Get-ChildItem $ScriptDir | Select-Object Name, Length | Format-Table
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Running portable Python setup..."
Write-Host ""

try {
    # Run the bundling script with explicit directory parameter
    & $BundleScript -DistDir $ScriptDir
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "Setup completed successfully!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "ddQuint is now ready to use with portable Python." -ForegroundColor Green
        Write-Host "You can launch the application by running ddQuint.exe" -ForegroundColor Green
        Write-Host ""
        Write-Host "The Python environment is completely self-contained" -ForegroundColor Cyan
        Write-Host "and can be moved to other Windows machines of the same architecture." -ForegroundColor Cyan
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Red
        Write-Host "Setup failed!" -ForegroundColor Red
        Write-Host "========================================" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please check the error messages above." -ForegroundColor Yellow
        Write-Host "You may need to:" -ForegroundColor Yellow
        Write-Host "- Check internet connection (for downloading Python)" -ForegroundColor Yellow
        Write-Host "- Run as administrator if permission issues occur" -ForegroundColor Yellow
        Write-Host "- Ensure antivirus is not blocking the setup" -ForegroundColor Yellow
        Write-Host ""
    }
} catch {
    Write-Host "ERROR: Failed to run setup script" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Read-Host "Press Enter to exit"