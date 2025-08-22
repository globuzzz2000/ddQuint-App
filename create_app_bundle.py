#!/usr/bin/env python3
"""
Create a simple macOS .app bundle manually for ddQuint
This approach creates a basic app bundle structure without py2app complications.
"""

import os
import shutil
import stat
import json
from pathlib import Path

def create_app_bundle():
    """Create a macOS .app bundle manually."""
    
    app_name = "ddQuint.app"
    app_path = Path("dist") / app_name
    
    print(f"🚀 Creating {app_name}")
    
    # Remove existing app
    if app_path.exists():
        shutil.rmtree(app_path)
    
    # Create directory structure
    contents_dir = app_path / "Contents"
    macos_dir = contents_dir / "MacOS"
    resources_dir = contents_dir / "Resources"
    
    os.makedirs(macos_dir, exist_ok=True)
    os.makedirs(resources_dir, exist_ok=True)
    
    # Create Info.plist
    info_plist = {
        "CFBundleName": "ddQuint",
        "CFBundleDisplayName": "ddQuint - Digital Droplet PCR Analysis",
        "CFBundleIdentifier": "com.ddquint.app",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleExecutable": "ddQuint",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "10.14",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundlePackageType": "APPL",
    }
    
    # Write Info.plist as XML
    plist_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>ddQuint</string>
    <key>CFBundleDisplayName</key>
    <string>ddQuint - Digital Droplet PCR Analysis</string>
    <key>CFBundleIdentifier</key>
    <string>com.ddquint.app</string>
    <key>CFBundleVersion</key>
    <string>0.1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>0.1.0</string>
    <key>CFBundleExecutable</key>
    <string>ddQuint</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSMinimumSystemVersion</key>
    <string>10.14</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
</dict>
</plist>"""
    
    with open(contents_dir / "Info.plist", "w") as f:
        f.write(plist_content)
    
    # Create the main executable script
    executable_script = f"""#!/bin/bash
# ddQuint macOS App Launcher

# Get the directory where this script is located
DIR="$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" &> /dev/null && pwd )"
APP_DIR="$DIR/.."

# Set up Python path to include the app's Python environment
export PYTHONPATH="$APP_DIR/Resources:$PYTHONPATH"

# Try to find Python
PYTHON=""
if command -v python3 &> /dev/null; then
    PYTHON="python3"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    echo "Error: Python not found. Please install Python 3.10 or later."
    exit 1
fi

# Check if ddquint is available
if ! $PYTHON -c "import ddquint" 2>/dev/null; then
    echo "Error: ddQuint is not installed. Please install ddQuint first:"
    echo "pip install -e /path/to/ddQuint"
    echo ""
    echo "Or run the GUI directly with:"
    echo "python -m ddquint.gui"
    exit 1
fi

# Launch the GUI
cd "$APP_DIR/Resources"
exec $PYTHON -c "
import sys
import os
sys.path.insert(0, os.getcwd())
try:
    from ddquint.gui.macos_native import main
    main()
except Exception as e:
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror('ddQuint Error', f'Failed to start ddQuint: {{e}}')
    sys.exit(1)
"
"""
    
    # Write the executable script
    executable_path = macos_dir / "ddQuint"
    with open(executable_path, "w") as f:
        f.write(executable_script)
    
    # Make the script executable
    os.chmod(executable_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    
    # Copy ddQuint source to Resources (optional - for self-contained app)
    # For now, we'll just create a launcher that uses the installed ddQuint
    
    # Create a README in Resources
    readme_content = f"""ddQuint macOS Application

This app requires ddQuint to be installed in your Python environment.

To install ddQuint:
1. Install Python 3.10 or later
2. Install ddQuint: pip install -e /path/to/ddQuint

Or you can run the GUI directly:
python -m ddquint.gui

Created: {os.path.basename(__file__)}
"""
    
    with open(resources_dir / "README.txt", "w") as f:
        f.write(readme_content)
    
    print(f"✅ Created {app_path}")
    print(f"📦 App size: {get_dir_size(app_path)} KB")
    print(f"\nTo test the app:")
    print(f"  open {app_path}")
    print(f"\nTo install the app:")
    print(f"  cp -r {app_path} /Applications/")
    
    return app_path

def get_dir_size(path):
    """Get directory size in KB."""
    total = sum(f.stat().st_size for f in Path(path).rglob('*') if f.is_file())
    return round(total / 1024, 1)

def create_dmg(app_path):
    """Create a DMG file for distribution."""
    dmg_name = "ddQuint-0.1.0.dmg"
    
    print(f"\n💿 Creating {dmg_name}")
    
    # Remove existing DMG
    if os.path.exists(dmg_name):
        os.remove(dmg_name)
    
    # Create DMG
    cmd = [
        "hdiutil", "create",
        "-volname", "ddQuint",
        "-srcfolder", str(app_path.parent),
        "-ov", "-format", "UDZO",
        dmg_name
    ]
    
    import subprocess
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ Created {dmg_name}")
        
        # Get DMG size
        dmg_size = round(os.path.getsize(dmg_name) / (1024 * 1024), 1)
        print(f"📦 DMG size: {dmg_size} MB")
        
        return dmg_name
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create DMG: {e}")
        return None

def main():
    """Main function."""
    print("🚀 ddQuint macOS App Bundle Creator")
    print("=" * 50)
    
    # Create the app bundle
    app_path = create_app_bundle()
    
    # Ask about creating DMG
    try:
        create_dmg_choice = input("\n📦 Create DMG file for distribution? (y/n): ").lower().strip()
        if create_dmg_choice in ['y', 'yes']:
            create_dmg(app_path)
    except KeyboardInterrupt:
        print("\nSkipping DMG creation.")
    
    print("\n" + "=" * 50)
    print("🎉 App bundle creation complete!")
    print("\nNext steps:")
    print("1. Test the app: open dist/ddQuint.app")
    print("2. Install: cp -r dist/ddQuint.app /Applications/")
    print("3. Make sure ddQuint is installed: pip install -e .")

if __name__ == "__main__":
    main()