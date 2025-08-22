#!/usr/bin/env python3
"""
Build script for creating macOS .app bundle

This script provides an easy way to build the ddQuint macOS application
with proper error handling and cleanup.
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

def run_command(cmd, description):
    """Run a command with error handling."""
    print(f"\n{'='*50}")
    print(f"🔨 {description}")
    print(f"{'='*50}")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(f"✅ Output:\n{result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stdout:
            print(f"Stdout: {e.stdout}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        return False

def check_requirements():
    """Check if all requirements are installed."""
    print("🔍 Checking requirements...")
    
    try:
        import py2app
        print("✅ py2app is installed")
    except ImportError:
        print("❌ py2app is not installed. Installing...")
        if not run_command([sys.executable, "-m", "pip", "install", "py2app"], "Installing py2app"):
            return False
    
    # Check if package is installed in development mode
    try:
        import ddquint
        print("✅ ddquint package is available")
    except ImportError:
        print("❌ ddquint package not found. Installing in development mode...")
        if not run_command([sys.executable, "-m", "pip", "install", "-e", "."], "Installing ddquint"):
            return False
    
    return True

def clean_build():
    """Clean previous build artifacts."""
    print("\n🧹 Cleaning previous builds...")
    
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Removing {dir_name}/")
            shutil.rmtree(dir_name)
    
    print("✅ Cleaned build directories")

def build_app():
    """Build the macOS application."""
    print("\n🏗️  Building macOS application...")
    
    cmd = [sys.executable, "setup_app.py", "py2app"]
    
    if not run_command(cmd, "Building .app bundle"):
        return False
    
    # Check if app was created
    app_path = Path("dist/ddquint_gui.app")
    if app_path.exists():
        print(f"✅ Application built successfully: {app_path.absolute()}")
        
        # Get app size
        size = sum(f.stat().st_size for f in app_path.rglob('*') if f.is_file())
        size_mb = size / (1024 * 1024)
        print(f"📦 App size: {size_mb:.1f} MB")
        
        return True
    else:
        print("❌ Application was not created")
        return False

def create_dmg():
    """Create a DMG file for distribution."""
    print("\n💿 Creating DMG for distribution...")
    
    app_path = "dist/ddquint_gui.app"
    dmg_name = "ddQuint-0.1.0.dmg"
    
    # Create DMG using hdiutil (built into macOS)
    cmd = [
        "hdiutil", "create",
        "-volname", "ddQuint",
        "-srcfolder", "dist",
        "-ov", "-format", "UDZO",
        dmg_name
    ]
    
    if run_command(cmd, "Creating DMG file"):
        print(f"✅ DMG created: {dmg_name}")
        return True
    else:
        print("❌ Failed to create DMG")
        return False

def main():
    """Main build process."""
    print("🚀 ddQuint macOS App Builder")
    print("=" * 50)
    
    # Check if we're on macOS
    if sys.platform != 'darwin':
        print("❌ This script must be run on macOS")
        sys.exit(1)
    
    # Step 1: Check requirements
    if not check_requirements():
        print("❌ Requirements check failed")
        sys.exit(1)
    
    # Step 2: Clean previous builds
    clean_build()
    
    # Step 3: Build the app
    if not build_app():
        print("❌ Build failed")
        sys.exit(1)
    
    # Step 4: Create DMG (optional)
    create_dmg_choice = input("\n📦 Create DMG file for distribution? (y/n): ").lower().strip()
    if create_dmg_choice in ['y', 'yes']:
        create_dmg()
    
    print("\n" + "=" * 50)
    print("🎉 Build process completed!")
    print("\nTo run the app:")
    print("  open dist/ddquint_gui.app")
    print("\nTo install the app:")
    print("  cp -r dist/ddquint_gui.app /Applications/")
    print("=" * 50)

if __name__ == "__main__":
    main()