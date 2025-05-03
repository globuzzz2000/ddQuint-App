"""
Final fixed GUI utilities for ddQuint
Provides dialog functions with persistent memory and proper cleanup
"""

import os
import sys
import json
import platform
import contextlib
import time

# Path to store configuration - ensure lowercase for consistency
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".ddquint")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

@contextlib.contextmanager
def _silence_stderr():
    """Temporarily redirect stderr to /dev/null to suppress wxPython warnings."""
    if platform.system() == "Darwin":
        import os
        old_fd = os.dup(2)
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, 2)
            os.close(devnull)
            yield
        finally:
            os.dup2(old_fd, 2)
            os.close(old_fd)
    else:
        yield

def get_config():
    """
    Load configuration from file.
    
    Returns:
        dict: Configuration dictionary
    """
    config = {}
    
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
    except Exception as e:
        print(f"Warning: Could not load config: {str(e)}")
    
    return config

def save_config(config):
    """
    Save configuration to file with explicit sync to ensure disk writing.
    
    Args:
        config (dict): Configuration dictionary
    """
    try:
        # Create directory with explicit permissions
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR, mode=0o755, exist_ok=True)
        
        # Write config with explicit sync to ensure disk writing
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
            f.flush()
            os.fsync(f.fileno())
        
        # Verify the file was written
        if not os.path.exists(CONFIG_FILE):
            print(f"Warning: Config file not created after save attempt")
    except Exception as e:
        print(f"Warning: Could not save config: {str(e)}")

def select_directory():
    """
    Show directory selection dialog with memory of the last directory.
    
    Returns:
        str: Selected directory path, or None if cancelled
    """
    # Load saved configuration
    config = get_config()
    last_dir = config.get('last_directory')
    
    # Get parent directory of last directory if it exists
    # Otherwise use a sensible default
    if last_dir and os.path.isdir(last_dir):
        # Get the parent directory (one level up)
        parent_dir = os.path.dirname(last_dir)
        # Check if parent directory exists and is accessible
        if parent_dir and os.path.isdir(parent_dir):
            default_path = parent_dir
        else:
            default_path = last_dir
            print(f"Parent directory not valid, using last directory: {default_path}")
    else:
        default_path = find_default_directory()
    
    # Create a global app instance to prevent early cleanup
    global _wx_app, _keep_alive
    
    # Try using wxPython dialog
    try:
        import wx
        
        # Create a persistent application instance and store globally
        _wx_app = wx.App(False)
        
        # Suppress stderr output to avoid NSOpenPanel warning on macOS
        with _silence_stderr():
            # Don't hide from dock on macOS during selection
            
            style = wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
            
            # Create and show dialog
            dlg = wx.DirDialog(
                None, 
                message="Select folder with ddPCR CSV files", 
                defaultPath=default_path if default_path else "", 
                style=style
            )
            
            directory = None
            if dlg.ShowModal() == wx.ID_OK:
                directory = dlg.GetPath()
            
            dlg.Destroy()
            
            # Close the application now that we're done
            if platform.system() == "Darwin":
                try:
                    import AppKit
                    NSApplication = AppKit.NSApplication.sharedApplication()
                    # Hide the application after selection is complete
                    NSApplication.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
                except:
                    pass
        
        # Make sure wx.App is properly cleaned up
        _wx_app = None
        _keep_alive = False
        
        if directory:
            # Save the selected directory for next time
            config['last_directory'] = directory
            save_config(config)
            
            # Double-check that the config was saved for debugging
            verify_config = get_config()
            if verify_config.get('last_directory') != directory:
                print(f"Warning: Config verification failed. Expected: {directory}, Got: {verify_config.get('last_directory')}")
            
            return directory
            
    except ImportError:
        print("wxPython not available, falling back to console input.")
    except Exception as e:
        print(f"Error in GUI dialog: {str(e)}")
        print("Falling back to console input.")
    
    # Fall back to CLI mode if GUI failed
    print("\nEnter full path to directory containing CSV files:")
    directory = input("> ").strip()
    
    # If the user just pressed Enter, use the default path
    if not directory and default_path:
        directory = default_path
    
    # Validate the input directory
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a valid directory.")
        return None
    
    # Save this choice for next time
    config['last_directory'] = directory
    save_config(config)
    
    return directory

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
    # Load saved configuration
    config = get_config()
    last_dir = config.get('last_directory')
    
    # If no default path was provided, try to use parent of last directory from config
    if default_path is None:
        if last_dir and os.path.isdir(last_dir):
            # Get the parent directory (one level up)
            parent_dir = os.path.dirname(last_dir)
            # Check if parent directory exists and is accessible
            if parent_dir and os.path.isdir(parent_dir):
                default_path = parent_dir
            else:
                default_path = last_dir
        else:
            default_path = find_default_directory()
    
    # Create a global app instance to prevent early cleanup
    global _wx_app, _keep_alive
    
    # Try using wxPython dialog
    try:
        import wx
        
        # Create a persistent application instance and store globally
        _wx_app = wx.App(False)
        
        # Suppress stderr output
        with _silence_stderr():
            # Don't hide the app from dock during selection
            
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
                
                # Save the selected directory for next time
                config['last_directory'] = os.path.dirname(file_path)
                save_config(config)
            
            dlg.Destroy()
            
            # Close the application now that we're done
            if platform.system() == "Darwin":
                try:
                    import AppKit
                    NSApplication = AppKit.NSApplication.sharedApplication()
                    # Hide the application after selection is complete
                    NSApplication.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
                except:
                    pass
        
        # Make sure wx.App is properly cleaned up
        _wx_app = None
        _keep_alive = False
        
        if file_path:
            return file_path
            
    except ImportError:
        print("wxPython not available, falling back to console input.")
    except Exception as e:
        print(f"Error in GUI dialog: {str(e)}")
        print("Falling back to console input.")
    
    # Fallback to manual input
    print(f"\nEnter full path to file ({wildcard.split('|')[0]}):")
    print(f"[Previous directory: {default_path}]") if default_path else None
    file_path = input("> ").strip()
    
    # Validate the input file
    if not os.path.isfile(file_path):
        print(f"Error: '{file_path}' is not a valid file.")
        return None
    
    # Save this choice for next time
    config['last_directory'] = os.path.dirname(file_path)
    save_config(config)
    
    return file_path

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

# Initialize global variables for wxPython instance management
_wx_app = None
_keep_alive = False