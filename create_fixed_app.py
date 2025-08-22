#!/usr/bin/env python3
"""
Create a working macOS .app bundle for ddQuint with proper launcher
"""

import os
import shutil
import stat
import sys
from pathlib import Path

def create_fixed_app_bundle():
    """Create a macOS .app bundle that actually works."""
    
    app_name = "ddQuint.app"
    app_path = Path("dist") / app_name
    
    print(f"🚀 Creating fixed {app_name}")
    
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
    <key>LSUIElement</key>
    <false/>
</dict>
</plist>"""
    
    with open(contents_dir / "Info.plist", "w") as f:
        f.write(plist_content)
    
    # Get the current Python executable and ddQuint path
    current_python = sys.executable
    current_dir = str(Path(__file__).parent.absolute())
    
    # Create a much simpler, more reliable launcher script
    executable_script = f"""#!/bin/bash
# ddQuint macOS App Launcher (Fixed)

# Set the working directory to the ddQuint source
cd "{current_dir}"

# Use the current Python environment
PYTHON="{current_python}"

# Set up environment
export PYTHONPATH="{current_dir}:$PYTHONPATH"

# Launch the GUI with full error reporting
$PYTHON -c "
import sys
import os
import traceback

# Add the ddQuint directory to Python path
sys.path.insert(0, '{current_dir}')

try:
    # Import and run the GUI
    from ddquint.gui.macos_native import main
    print('Starting ddQuint GUI...')
    main()
except ImportError as e:
    print(f'Import error: {{e}}')
    print('Python path:', sys.path)
    print('Current directory:', os.getcwd())
    traceback.print_exc()
    
    # Fallback: try to show an error dialog
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror('ddQuint Error', f'Failed to import ddQuint modules: {{e}}\\n\\nPlease ensure ddQuint is properly installed.')
        root.destroy()
    except:
        pass
    sys.exit(1)
except Exception as e:
    print(f'Runtime error: {{e}}')
    traceback.print_exc()
    
    # Show error dialog
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror('ddQuint Error', f'Application error: {{e}}')
        root.destroy()
    except:
        pass
    sys.exit(1)
"
"""
    
    # Write the executable script
    executable_path = macos_dir / "ddQuint"
    with open(executable_path, "w") as f:
        f.write(executable_script)
    
    # Make the script executable
    os.chmod(executable_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    
    print(f"✅ Created {app_path}")
    print(f"📦 Using Python: {current_python}")
    print(f"📁 Using ddQuint path: {current_dir}")
    
    return app_path

def main():
    """Main function."""
    print("🚀 ddQuint macOS App Bundle Creator (Fixed Version)")
    print("=" * 55)
    
    # Create the app bundle
    app_path = create_fixed_app_bundle()
    
    print("\n" + "=" * 55)
    print("🎉 Fixed app bundle created!")
    print(f"\nTo test the app:")
    print(f"  open {app_path}")
    print(f"\nTo install the app:")
    print(f"  cp -r {app_path} /Applications/")
    print("\nThe app now uses your current Python environment and")
    print("points directly to this ddQuint installation.")

if __name__ == "__main__":
    main()