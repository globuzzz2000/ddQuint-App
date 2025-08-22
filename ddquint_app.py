
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
    messagebox.showerror("ddQuint Error", f"Failed to start ddQuint:\n{e}")
    sys.exit(1)
