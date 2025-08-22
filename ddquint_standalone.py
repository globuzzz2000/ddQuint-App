#!/usr/bin/env python3
"""
Standalone ddQuint macOS application
"""

import sys
import os
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

# Ensure we can import ddquint
try:
    import ddquint
    from ddquint.gui.macos_native import main
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    import tkinter as tk
    from tkinter import messagebox
    
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("ddQuint Error", 
                        f"Failed to import ddQuint modules:\n{e}\n\n"
                        "Please ensure ddQuint is properly installed.")
    sys.exit(1)
except Exception as e:
    import tkinter as tk
    from tkinter import messagebox
    
    root = tk.Tk() 
    root.withdraw()
    messagebox.showerror("ddQuint Error", f"Application error:\n{e}")
    sys.exit(1)