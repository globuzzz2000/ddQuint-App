"""
Minimal setup script for creating macOS .app bundle using py2app
"""

from setuptools import setup
import sys
import os

# Ensure we're on macOS
if sys.platform != 'darwin':
    print("This setup is for macOS only")
    sys.exit(1)

# Main app script
APP_SCRIPT = """#!/usr/bin/env python3
import sys
import os
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

# Add current directory to path for imports
app_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, app_dir)

try:
    from ddquint.gui.macos_native import main
    main()
except Exception as e:
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("ddQuint Error", f"Failed to start ddQuint:\\n{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""

# Write the app script
with open('ddquint_minimal.py', 'w') as f:
    f.write(APP_SCRIPT)

# App configuration
APP = ['ddquint_minimal.py']
DATA_FILES = []

OPTIONS = {
    'argv_emulation': True,
    'plist': {
        'CFBundleName': 'ddQuint',
        'CFBundleDisplayName': 'ddQuint',
        'CFBundleGetInfoString': 'Digital Droplet PCR Analysis Tool',
        'CFBundleIdentifier': 'com.ddquint.app',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        'NSHumanReadableCopyright': 'Copyright © 2024 Jakob Wimmer',
        'NSHighResolutionCapable': True,
    },
    'includes': [
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'matplotlib',
        'matplotlib.backends.backend_tkagg',
        'numpy',
        'pandas',
    ],
    'packages': [
        'ddquint',
    ],
    'excludes': [
        'wx',
        'PyQt4',
        'PyQt5',
        'PySide',
        'test',
        'tests',
        'unittest',
        'jupyter',
        'ipython',
        'zmq',
        'IPython',
        'notebook',
    ],
    'resources': [],
    'site_packages': True,
}

setup(
    name='ddQuint',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)