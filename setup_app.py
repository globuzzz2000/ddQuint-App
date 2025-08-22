"""
Setup script for creating macOS .app bundle using py2app
"""

from setuptools import setup
import sys
import os

# Ensure we're on macOS
if sys.platform != 'darwin':
    print("This setup is for macOS only")
    sys.exit(1)

# Main app script
APP_SCRIPT = """
#!/usr/bin/env python3
import sys
import os

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
    sys.exit(1)
"""

# Write the app script
with open('ddquint_app.py', 'w') as f:
    f.write(APP_SCRIPT)

# App configuration
APP = ['ddquint_app.py']
DATA_FILES = [
    # Include any data files your app needs
    ('', ['README.md', 'LICENSE']),
    ('docs', ['README_GUI.md']),
]

OPTIONS = {
    'argv_emulation': True,
    'plist': {
        'CFBundleName': 'ddQuint',
        'CFBundleDisplayName': 'ddQuint - Digital Droplet PCR Analysis',
        'CFBundleGetInfoString': 'Digital Droplet PCR Multiplex Analysis Tool',
        'CFBundleIdentifier': 'com.ddquint.app',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        'NSHumanReadableCopyright': 'Copyright © 2024 Jakob Wimmer',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.14',
        'NSRequiresAquaSystemAppearance': False,
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeExtensions': ['csv'],
                'CFBundleTypeName': 'CSV Files',
                'CFBundleTypeRole': 'Viewer',
                'LSHandlerRank': 'None',
            }
        ],
    },
    'packages': [
        'ddquint',
        'matplotlib',
        'numpy',
        'pandas',
        'sklearn',
        'hdbscan',
        'openpyxl',
    ],
    'includes': [
        'ddquint.core',
        'ddquint.utils', 
        'ddquint.visualization',
        'ddquint.config',
        'ddquint.gui',
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
    ],
    'excludes': [
        'test',
        'tests',
        'unittest',
        'distutils',
        'PyQt4',
        'PyQt5',
        'PySide',
        'wx',
        'zmq',
        'IPython',
        'jupyter',
        'notebook',
        'tornado',
        'django',
        'flask',
        'twisted',
        'sphinx',
        'pytest',
    ],
    'optimize': 2,
    'no_strip': True,
    'semi_standalone': False,
    'site_packages': True,
}

setup(
    name='ddQuint',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    install_requires=[
        'pandas>=1.0.0',
        'numpy>=1.18.0', 
        'matplotlib>=3.3.0',
        'scikit-learn>=0.24.0',
        'hdbscan>=0.8.27',
        'openpyxl>=3.0.5',
    ],
)