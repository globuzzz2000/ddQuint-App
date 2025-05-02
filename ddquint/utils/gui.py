"""
GUI utilities for ddQuint
Provides dialog functions for selecting directories and files
"""

import os
import sys

def select_directory(default_path=None, title="Select directory containing CSV files"):
    """
    Display a directory selection dialog and return the selected path.
    
    Args:
        default_path (str): Default directory path to start in
        title (str): Dialog title
        
    Returns:
        str: Selected directory path or None if canceled
    """
    # If no default path provided, try to find a sensible one
    if default_path is None:
        default_path = find_default_directory()
        
    # Try using wxPython dialog first
    try:
        import wx
        app = wx.App(False)
        
        style = wx.DD_DEFAULT_STYLE
        if default_path and os.path.isdir(default_path):
            style |= wx.DD_DIR_MUST_EXIST
        
        dlg = wx.DirDialog(
            None, 
            message=title, 
            defaultPath=default_path if default_path else "", 
            style=style
        )
        
        directory = None
        if dlg.ShowModal() == wx.ID_OK:
            directory = dlg.GetPath()
            print(f"Selected directory: {directory}")
        
        dlg.Destroy()
        app.Destroy()
        
        if directory:
            return directory
            
    except ImportError:
        print("wxPython not available, falling back to console input.")
    except Exception as e:
        print(f"Error in GUI dialog: {str(e)}")
        print("Falling back to console input.")
    
    # If GUI failed or was canceled, try using default path
    if default_path and os.path.isdir(default_path):
        print(f"Using default directory: {default_path}")
        confirm = input(f"Use '{default_path}'? [Y/n]: ").strip().lower()
        if not confirm or confirm.startswith('y'):
            return default_path
    
    # Fallback to manual input
    print("\nEnter full path to directory containing CSV files:")
    directory = input("> ").strip()
    
    # Validate the input directory
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a valid directory.")
        return select_directory(default_path, title)
    
    return directory

def find_default_directory():
    """
    Find a sensible default directory based on the OS.
    
    Returns:
        str: Default directory path or None if not found
    """
    # Check common locations
    potential_paths = []
    
    home_dir = os.path.expanduser("~")
    
    # Add OS-specific common locations
    if sys.platform == 'win32':  # Windows
        potential_paths.extend([
            os.path.join(home_dir, "Downloads"),
            os.path.join(home_dir, "Documents"),
            os.path.join(home_dir, "Desktop"),
            "C:\\Data"
        ])
    elif sys.platform == 'darwin':  # macOS
        potential_paths.extend([
            os.path.join(home_dir, "Downloads"),
            os.path.join(home_dir, "Documents"),
            os.path.join(home_dir, "Desktop"),
            os.path.join(home_dir, "Library", "Mobile Documents"),
            "/Volumes"
        ])
    else:  # Linux/Unix
        potential_paths.extend([
            os.path.join(home_dir, "Downloads"),
            os.path.join(home_dir, "Documents"),
            os.path.join(home_dir, "Desktop"),
            "/mnt",
            "/media"
        ])
    
    # Check if script is running from a valid directory
    current_dir = os.getcwd()
    potential_paths.insert(0, current_dir)
    
    # Return the first valid directory
    for path in potential_paths:
        if os.path.exists(path) and os.path.isdir(path):
            return path
    
    # If no valid directories found, return home directory
    return home_dir

def select_file(default_path=None, title="Select file", wildcard="CSV files (*.csv)|*.csv"):
    """
    Display a file selection dialog and return the selected path.
    
    Args:
        default_path (str): Default directory path to start in
        title (str): Dialog title
        wildcard (str): File filter pattern
        
    Returns:
        str: Selected file path or None if canceled
    """
    # If no default path provided, try to find a sensible one
    if default_path is None:
        default_path = find_default_directory()
        
    # Try using wxPython dialog first
    try:
        import wx
        app = wx.App(False)
        
        style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        
        dlg = wx.FileDialog(
            None,
            message=title,
            defaultDir=default_path if default_path else "",
            defaultFile="",
            wildcard=wildcard,
            style=style
        )
        
        file_path = None
        if dlg.ShowModal() == wx.ID_OK:
            file_path = dlg.GetPath()
            print(f"Selected file: {file_path}")
        
        dlg.Destroy()
        app.Destroy()
        
        if file_path:
            return file_path
            
    except ImportError:
        print("wxPython not available, falling back to console input.")
    except Exception as e:
        print(f"Error in GUI dialog: {str(e)}")
        print("Falling back to console input.")
    
    # Fallback to manual input
    print(f"\nEnter full path to file ({wildcard.split('|')[0]}):")
    file_path = input("> ").strip()
    
    # Validate the input file
    if not os.path.isfile(file_path):
        print(f"Error: '{file_path}' is not a valid file.")
        return select_file(default_path, title, wildcard)
    