#!/bin/bash

# Package ddQuint for End-User Distribution
# Creates pre-bundled distributions ready for installation
# Usage: ./package.sh

set -e

echo "📦 Packaging ddQuint for End-User Distribution..."
echo "================================================="

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
SCRIPTS_DIR="$PROJECT_DIR/scripts"
PACKAGE_DIR="$PROJECT_DIR/packages"
PYTHON_STORE_DIR="$PROJECT_DIR/python_store"

# Clean and create package directory
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

package_runtime() {
  local runtime="$1"
  local dist_dir="$PROJECT_DIR/dist/${runtime}-standalone"
  local package_name="ddQuint-${runtime}"
  local temp_dir="$PACKAGE_DIR/temp-$runtime"
  local stored_python_dir="$PYTHON_STORE_DIR/${runtime}"
  
  echo ""
  echo "📦 Packaging $runtime..."
  echo "Source: $dist_dir"
  echo "Python store: $stored_python_dir"
  
  if [ ! -d "$dist_dir" ]; then
    echo "❌ Distribution not found: $dist_dir"
    echo "   Run ./build.sh first"
    return 1
  fi
  
  # Create temporary packaging directory
  mkdir -p "$temp_dir"
  
  # Copy all application files (exclude bundling scripts from final package)
  echo "📋 Copying application files..."
  rsync -a --exclude "bundle_python*.bat" --exclude "bundle_python*.ps1" "$dist_dir/" "$temp_dir/"
  
  # Copy pre-stored Python environment if available
  if [ -d "$stored_python_dir" ]; then
    echo "🐍 Copying pre-bundled Python environment..."
    rsync -a "$stored_python_dir/" "$temp_dir/Python/"
    echo "✅ Python environment copied from store"
  else
    echo "⚠️  No pre-stored Python found at: $stored_python_dir"
    echo "   Creating fallback installer scripts..."
    create_bundle_on_install_script "$temp_dir"
  fi
  
  # Copy packaging-specific scripts
  echo "📋 Adding installer scripts..."
  create_install_script "$temp_dir"
  
  # Create ZIP distribution
  echo "📦 Creating ZIP package..."
  local zip_path="$PACKAGE_DIR/${package_name}.zip"
  cd "$temp_dir"
  zip -r "$zip_path" . -q
  cd "$PROJECT_DIR"
  
  # Create self-extracting installer (if 7z with SFX module available)
  if command -v 7z &> /dev/null; then
    # Check if SFX module exists (common locations on different systems)
    local sfx_module=""
    local possible_sfx_paths=(
      "/usr/lib/p7zip/7z.sfx"
      "/usr/local/lib/p7zip/7z.sfx" 
      "/opt/homebrew/lib/p7zip/7z.sfx"
      "/opt/homebrew/Cellar/p7zip/17.06/lib/p7zip/7zCon.sfx"
      "/usr/share/p7zip/7z.sfx"
      "7z.sfx"
    )
    
    for sfx_path_candidate in "${possible_sfx_paths[@]}"; do
      if [ -f "$sfx_path_candidate" ]; then
        sfx_module="$sfx_path_candidate"
        break
      fi
    done
    
    if [ -n "$sfx_module" ]; then
      echo "📦 Creating self-extracting installer..."
      local sfx_path="$PACKAGE_DIR/${package_name}-Setup.exe"
      
      # Create SFX config
      cat > "$temp_dir/sfx_config.txt" << EOF
;!@Install@!UTF-8!
Title="ddQuint Installation"
BeginPrompt="Install ddQuint Digital Droplet PCR Analysis Software?"
RunProgram="install.bat"
;!@InstallEnd@!
EOF
      
      7z a -sfx"$sfx_module" "$sfx_path" "$temp_dir/*" -mx=9 -mf=on 2>/dev/null
      
      if [ -f "$sfx_path" ]; then
        echo "✅ Self-extracting installer created: $(basename "$sfx_path")"
      else
        echo "⚠️  SFX creation failed - only ZIP package available"
      fi
    else
      echo "ℹ️  7z SFX module not found - skipping self-extracting installer"
      echo "   Install with: brew install p7zip (may need additional SFX module)"
    fi
  else
    echo "ℹ️  7z not available - skipping self-extracting installer"
  fi
  
  # Get package size
  local zip_size=$(du -h "$zip_path" | cut -f1)
  echo "✅ ZIP package created: $(basename "$zip_path") ($zip_size)"
  
  # Cleanup temp directory
  rm -rf "$temp_dir"
}

# Create install script if it doesn't exist
create_install_script() {
  local target_dir="$1"
  cat > "$target_dir/install.bat" << 'EOF'
@echo off
setlocal enabledelayedexpansion

echo.
echo ========================================
echo ddQuint Installation
echo ========================================
echo.

REM Get installation directory
set "INSTALL_DIR=%ProgramFiles%\ddQuint"
if defined PROGRAMFILES(X86) (
    REM 64-bit system, use regular Program Files
    set "INSTALL_DIR=%ProgramFiles%\ddQuint"
) else (
    REM 32-bit system
    set "INSTALL_DIR=%ProgramFiles%\ddQuint"
)

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
EOF
}

# Create bundle-on-install fallback
create_bundle_on_install_script() {
  local target_dir="$1"
  echo "📋 Adding Python bundling scripts for install-time setup..."
  cp "$SCRIPTS_DIR/bundle_python_engine.ps1" "$target_dir/"
  cp "$SCRIPTS_DIR/bundle_python.bat" "$target_dir/"
}

# Package both architectures
echo "🔍 Looking for built distributions..."
package_runtime win-arm64
package_runtime win-x64

echo ""
echo "🎉 Packaging completed!"
echo "======================================="
echo ""
echo "📁 Packages created in: $PACKAGE_DIR"
if [ -d "$PACKAGE_DIR" ]; then
  echo "📦 Available packages:"
  ls -lh "$PACKAGE_DIR"/*.zip "$PACKAGE_DIR"/*.exe 2>/dev/null || echo "   No packages found"
fi
echo ""
echo "🚀 Distribution files ready for end users!"
echo "   - ZIP files: Extract and run install.bat"
echo "   - EXE files: Self-extracting installers"
echo ""
echo "💡 Python Environment Storage:"
echo "   Store pre-bundled Python environments in:"
echo "   - $PYTHON_STORE_DIR/win-arm64/"
echo "   - $PYTHON_STORE_DIR/win-x64/"
echo "   To create these, run bundling on Windows and copy the Python/ directory"
echo ""