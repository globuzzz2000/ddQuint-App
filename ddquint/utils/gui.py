"""
GUI utilities for ddQuint with proper GUI lifecycle management
"""

import os
import sys
import json
import platform
import contextlib
import time
import logging

# Path to store user settings - separate from main config
USER_SETTINGS_DIR = os.path.join(os.path.expanduser("~"), ".ddquint")
USER_SETTINGS_FILE = os.path.join(USER_SETTINGS_DIR, "user_settings.json")

# Optional import for wxPython file dialogs
try:
    import wx
    HAS_WX = True
except ImportError:
    HAS_WX = False

@contextlib.contextmanager
def _silence_stderr():
    """Temporarily redirect stderr to /dev/null to suppress wxPython warnings."""
    logger = logging.getLogger("ddQuint")
    
    if platform.system() == "Darwin":
        logger.debug("Silencing stderr for macOS wxPython warnings")
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
            logger.debug("Restored stderr")
    else:
        logger.debug("Non-macOS platform, no stderr silencing needed")
        yield

def get_user_settings():
    """
    Load user settings from file.
    
    Returns:
        dict: User settings dictionary with separate keys for different directory types
    """
    logger = logging.getLogger("ddQuint")
    logger.debug(f"Loading user settings from {USER_SETTINGS_FILE}")
    
    default_settings = {
        'last_input_directory': None,
        'last_template_directory': None,
        'last_output_directory': None
    }
    
    try:
        if os.path.exists(USER_SETTINGS_FILE):
            with open(USER_SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
            logger.debug(f"Loaded user settings: {settings}")
            # Merge with defaults to ensure all keys exist
            default_settings.update(settings)
        else:
            logger.debug(f"User settings file does not exist: {USER_SETTINGS_FILE}")
    except Exception as e:
        logger.error(f"Error loading user settings: {str(e)}")
        logger.debug("Error details:", exc_info=True)
    
    return default_settings

def save_user_settings(settings):
    """
    Save user settings to file with explicit sync to ensure disk writing.
    
    Args:
        settings (dict): User settings dictionary
    """
    logger = logging.getLogger("ddQuint")
    logger.debug(f"Saving user settings to {USER_SETTINGS_FILE}")
    logger.debug(f"Settings to save: {settings}")
    
    try:
        # Create directory with explicit permissions
        if not os.path.exists(USER_SETTINGS_DIR):
            logger.debug(f"Creating user settings directory: {USER_SETTINGS_DIR}")
            os.makedirs(USER_SETTINGS_DIR, mode=0o755, exist_ok=True)
        
        # Write settings with explicit sync to ensure disk writing
        with open(USER_SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        
        # Verify the file was written
        if not os.path.exists(USER_SETTINGS_FILE):
            logger.error(f"User settings file not created after save attempt")
        else:
            logger.debug(f"User settings file successfully saved to {USER_SETTINGS_FILE}")
    except Exception as e:
        logger.error(f"Error saving user settings: {str(e)}")
        logger.debug("Error details:", exc_info=True)

# Global variables for GUI management
_wx_app = None
_is_macos = platform.system() == "Darwin"
_has_pyobjc = False

if _is_macos:
    try:
        import Foundation
        import AppKit
        _has_pyobjc = True
    except ImportError:
        _has_pyobjc = False

def initialize_wx_app():
    """
    Initialize the wxPython app if it doesn't exist yet.
    
    Creates a wxPython application instance for file dialogs,
    with proper error handling and logging.
    """
    global _wx_app
    logger = logging.getLogger("ddQuint")
    
    if HAS_WX and _wx_app is None:
        try:
            with _silence_stderr():
                _wx_app = wx.App(False)
                logger.debug("wxPython app initialized successfully")
        except Exception as e:
            error_msg = f"Failed to initialize wxPython app: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Error details: {str(e)}", exc_info=True)
            raise Exception(error_msg) from e

def hide_app():
    """
    Hide the wxPython app without destroying it.
    
    This is safer on macOS and avoids segmentation faults by hiding
    the application from the dock rather than destroying it.
    """
    logger = logging.getLogger("ddQuint")
    
    if _is_macos and _has_pyobjc and _wx_app is not None:
        try:
            import AppKit
            # Hide from Dock
            NSApplication = AppKit.NSApplication.sharedApplication()
            NSApplication.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
            logger.debug("App hidden from macOS dock")
        except Exception as e:
            logger.warning(f"Error hiding app from dock: {str(e)}")
            logger.debug(f"Error details: {str(e)}", exc_info=True)

def mark_selection_complete():
    """
    Mark that all file selections are complete and hide the app from the dock.
    
    Should be called when file selection operations are finished to clean
    up the GUI application properly.
    """
    logger = logging.getLogger("ddQuint")
    logger.debug("File selection process marked as complete")
    hide_app()

def select_directory():
    """
    Show directory selection dialog with memory of the last input directory.
    
    Returns:
        str: Selected directory path, or None if cancelled
    """
    logger = logging.getLogger("ddQuint")
    logger.debug("Starting directory selection")
    
    # Load saved user settings
    settings = get_user_settings()
    last_input_dir = settings.get('last_input_directory')
    logger.debug(f"Last used input directory: {last_input_dir}")
    
    # Get parent directory of last directory if it exists
    # Otherwise use a sensible default
    if last_input_dir and os.path.isdir(last_input_dir):
        # Get the parent directory (one level up)
        parent_dir = os.path.dirname(last_input_dir)
        # Check if parent directory exists and is accessible
        if parent_dir and os.path.isdir(parent_dir):
            default_path = parent_dir
            logger.debug(f"Using parent directory: {default_path}")
        else:
            default_path = last_input_dir
            logger.debug(f"Parent directory not valid, using last directory: {default_path}")
    else:
        default_path = find_default_directory()
        logger.debug(f"Found default directory: {default_path}")
    
    # Try using wxPython dialog
    try:
        logger.debug("Importing wxPython")
        
        if not HAS_WX:
            raise ImportError("wxPython not available")
        
        # Initialize the wx.App if it doesn't exist yet
        initialize_wx_app()
        
        # Suppress stderr output to avoid NSOpenPanel warning on macOS
        with _silence_stderr():
            style = wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
            
            # Create and show dialog
            dlg = wx.DirDialog(
                None, 
                message="Select folder with ddPCR CSV files", 
                defaultPath=default_path if default_path else "", 
                style=style
            )
            
            logger.debug("Showing directory dialog")
            directory = None
            if dlg.ShowModal() == wx.ID_OK:
                directory = dlg.GetPath()
                logger.debug(f"Selected directory: {directory}")
            else:
                logger.debug("Dialog cancelled")
            
            dlg.Destroy()
        
        if directory:
            # Save the selected directory for next time
            settings['last_input_directory'] = directory
            save_user_settings(settings)
            
            # Double-check that the settings were saved for debugging
            verify_settings = get_user_settings()
            if verify_settings.get('last_input_directory') != directory:
                logger.error(f"Settings verification failed. Expected: {directory}, Got: {verify_settings.get('last_input_directory')}")
            
            return directory
            
    except ImportError:
        logger.info("wxPython not available, falling back to console input")
    except Exception as e:
        logger.error(f"Error in GUI dialog: {str(e)}")
        logger.debug("Error details:", exc_info=True)
        logger.info("Falling back to console input")
    
    # Fall back to CLI mode if GUI failed
    print("\nEnter full path to directory containing CSV files:")
    directory = input("> ").strip()
    
    # If the user just pressed Enter, use the default path
    if not directory and default_path:
        directory = default_path
        print(f"Using default path: {directory}")
    
    # Validate the input directory
    if not os.path.isdir(directory):
        logger.error(f"Invalid directory: {directory}")
        print(f"Error: '{directory}' is not a valid directory.")
        return None
    
    # Save this choice for next time
    settings['last_input_directory'] = directory
    save_user_settings(settings)
    
    return directory

def select_file(default_path=None, title="Select file", wildcard="CSV files (*.csv)|*.csv", file_type="template"):
    """
    Display a file selection dialog and return the selected path.
    
    Args:
        default_path (str): Default directory path to start in
        title (str): Dialog title
        wildcard (str): File filter pattern
        file_type (str): Type of file being selected ('template', 'input', 'output')
        
    Returns:
        str: Selected file path or None if canceled
    """
    logger = logging.getLogger("ddQuint")
    logger.debug(f"Starting file selection. Title: {title}, Wildcard: {wildcard}, Type: {file_type}")
    
    # Load saved user settings
    settings = get_user_settings()
    
    # Get the appropriate last directory based on file type
    if file_type == "template":
        last_dir = settings.get('last_template_directory')
    elif file_type == "output":
        last_dir = settings.get('last_output_directory')
    else:
        last_dir = settings.get('last_input_directory')
    
    # If no default path was provided, try to use last directory from settings
    if default_path is None:
        if last_dir and os.path.isdir(last_dir):
            # For template files, use the last template directory directly
            # For other files, use parent directory
            if file_type == "template":
                default_path = last_dir
                logger.debug(f"Using last {file_type} directory: {default_path}")
            else:
                # Get the parent directory (one level up) for input files
                parent_dir = os.path.dirname(last_dir)
                if parent_dir and os.path.isdir(parent_dir):
                    default_path = parent_dir
                    logger.debug(f"Using parent directory: {default_path}")
                else:
                    default_path = last_dir
                    logger.debug(f"Using last directory: {default_path}")
        else:
            default_path = find_default_directory()
            logger.debug(f"Found default directory: {default_path}")
    
    # Try using wxPython dialog
    try:
        logger.debug("Importing wxPython for file dialog")
        
        if not HAS_WX:
            raise ImportError("wxPython not available")
        
        # Initialize the wx.App if it doesn't exist yet
        initialize_wx_app()
        
        # Suppress stderr output
        with _silence_stderr():
            style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            
            dlg = wx.FileDialog(
                None,
                message=title,
                defaultDir=default_path if default_path else "",
                defaultFile="",
                wildcard=wildcard,
                style=style
            )
            
            logger.debug("Showing file dialog")
            file_path = None
            if dlg.ShowModal() == wx.ID_OK:
                file_path = dlg.GetPath()
                logger.debug(f"Selected file: {file_path}")
                
                # Save the selected directory for next time based on file type
                selected_dir = os.path.dirname(file_path)
                if file_type == "template":
                    settings['last_template_directory'] = selected_dir
                elif file_type == "output":
                    settings['last_output_directory'] = selected_dir
                else:
                    settings['last_input_directory'] = selected_dir
                
                save_user_settings(settings)
                logger.debug(f"Saved {file_type} directory: {selected_dir}")
            else:
                logger.debug("File dialog cancelled")
            
            dlg.Destroy()
        
        if file_path:
            return file_path
            
    except ImportError:
        logger.info("wxPython not available, falling back to console input")
    except Exception as e:
        logger.error(f"Error in GUI dialog: {str(e)}")
        logger.debug("Error details:", exc_info=True)
        logger.info("Falling back to console input")
    
    # Fallback to manual input
    print(f"\nEnter full path to file ({wildcard.split('|')[0]}):")
    print(f"[Previous directory: {default_path}]") if default_path else None
    file_path = input("> ").strip()
    
    # Validate the input file
    if not os.path.isfile(file_path):
        logger.error(f"Invalid file: {file_path}")
        print(f"Error: '{file_path}' is not a valid file.")
        return None
    
    # Save this choice for next time based on file type
    selected_dir = os.path.dirname(file_path)
    if file_type == "template":
        settings['last_template_directory'] = selected_dir
    elif file_type == "output":
        settings['last_output_directory'] = selected_dir
    else:
        settings['last_input_directory'] = selected_dir
    
    save_user_settings(settings)
    
    return file_path

def find_default_directory():
    """
    Find a sensible default directory based on the OS.
    
    Returns:
        str: Default directory path or None if not found
    """
    logger = logging.getLogger("ddQuint")
    logger.debug("Finding default directory")
    
    # Check common locations
    potential_paths = []
    
    home_dir = os.path.expanduser("~")
    logger.debug(f"Home directory: {home_dir}")
    
    # Add OS-specific common locations
    if sys.platform == 'win32':  # Windows
        potential_paths.extend([
            os.path.join(home_dir, "Downloads"),
            os.path.join(home_dir, "Documents"),
            os.path.join(home_dir, "Desktop"),
            "C:\\Data"
        ])
        logger.debug("Added Windows-specific paths")
    elif sys.platform == 'darwin':  # macOS
        potential_paths.extend([
            os.path.join(home_dir, "Downloads"),
            os.path.join(home_dir, "Documents"),
            os.path.join(home_dir, "Desktop"),
            os.path.join(home_dir, "Library", "Mobile Documents"),
            "/Volumes"
        ])
        logger.debug("Added macOS-specific paths")
    else:  # Linux/Unix
        potential_paths.extend([
            os.path.join(home_dir, "Downloads"),
            os.path.join(home_dir, "Documents"),
            os.path.join(home_dir, "Desktop"),
            "/mnt",
            "/media"
        ])
        logger.debug("Added Linux-specific paths")
    
    # Check if script is running from a valid directory
    current_dir = os.getcwd()
    potential_paths.insert(0, current_dir)
    logger.debug(f"Added current directory: {current_dir}")
    
    # Return the first valid directory
    for path in potential_paths:
        if os.path.exists(path) and os.path.isdir(path):
            logger.debug(f"Found valid directory: {path}")
            return path
        else:
            logger.debug(f"Path not valid: {path}")
    
    # If no valid directories found, return home directory
    logger.debug(f"Using home directory as fallback: {home_dir}")
    return home_dir