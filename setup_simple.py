"""
Simple setup script for py2app
"""

from setuptools import setup
import sys

if sys.platform != 'darwin':
    print("This script is for macOS only")
    sys.exit(1)

# Simple app setup
APP = ['ddquint_standalone.py']

OPTIONS = {
    'includes': ['tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox'],
    'packages': ['ddquint', 'matplotlib', 'numpy', 'pandas'],
    'excludes': ['test', 'tests', 'unittest', 'jupyter', 'IPython', 'zmq'],
    'argv_emulation': True,
    'plist': {
        'CFBundleName': 'ddQuint',
        'CFBundleDisplayName': 'ddQuint',
        'CFBundleIdentifier': 'com.ddquint.app',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
    }
}

setup(
    app=APP,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)