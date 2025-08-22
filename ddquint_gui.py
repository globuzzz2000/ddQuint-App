#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ddQuint GUI Launcher

Standalone launcher for the macOS GUI application.
This replaces the command-line interface with a clean, native macOS GUI.
"""

import sys
import os
from pathlib import Path

try:
    from ddquint.gui import main
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"Error importing ddQuint GUI: {e}")
    print("Please ensure all dependencies are installed:")
    print("  pip install tkinter matplotlib pandas numpy scikit-learn hdbscan openpyxl")
    sys.exit(1)