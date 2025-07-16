#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI utilities for ddQuint with proper GUI lifecycle management.

Provides file and directory selection dialogs with persistent user settings
and cross-platform compatibility. Handles wxPython initialization and cleanup
with proper error handling.
"""

import os
import sys
import json
import platform
import contextlib
import logging

from ..config import FileProcessingError

logger = logging.getLogger(__name__)

# Path to store user settings - separate from main config
USER_SETTINGS_DIR = os.path.join(os.path.expanduser("~"), ".ddquint")
USER_SETTINGS_FILE = os.path.join(USER_SETTINGS_DIR, "user_settings.json")

# Optional import for wxPython file dialogs
try:
    import wx
    HAS_WX = True
except ImportError:
    HAS_WX = False

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


@contextlib.contextmanager
def _silence_stderr():
    """Temporarily redirect stderr to suppress wxPython warnings on macOS."""
    if _is_macos:
        logger.debug("Silencing stderr for macOS wxPython warnings")
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
        logger.debug(f"Error details: {str(e)}", exc_info=True)
    
    return default_settings


def save_user_settings(settings):
    """
    Save user settings to file with explicit sync to ensure disk writing.
    
    Args:
        settings (dict): User settings dictionary
        
    Raises:
        FileProcessingError: If settings cannot be saved
    """
    logger.debug(f"Saving user settings to {USER_SETTINGS_FILE}")
    logger.debug(f"Settings to save: {settings}")
    
    try:
        # Create directory with explicit permissions
        if not os.path.exists(USER_SETTINGS_DIR):
            logger.debug(f"Creating user settings directory: {USER_SETTINGS_DIR}")
            os.makedirs(USER_SETTINGS_DIR, mode=0o755, exist_ok=True)
        
        # Write settings with explicit sync
        with open(USER_SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        
        # Verify the file was written
        if not os.path.exists(USER_SETTINGS_FILE):
            logger.error("User settings file not created after save attempt")
        else:
            logger.debug(f"User settings file successfully saved to {USER_SETTINGS_FILE}")
            
    except Exception as e:
        error_msg = f"Error saving user settings: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        raise FileProcessingError(error_msg) from e


def initialize_wx_app():
    """
    Initialize the wxPython app if it doesn't exist yet.
    
    Creates a wxPython application instance for file dialogs,
    with proper error handling and logging.
    
    Raises:
        FileProcessingError: If wxPython app initialization fails
    """
    global _wx_app
    
    if HAS_WX and _wx_app is None:
        try:
            with _silence_stderr():
                _wx_app = wx.App(False)
                logger.debug("wxPython app initialized successfully")
        except Exception as e:
            error_msg = f"Failed to initialize wxPython app: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Error details: {str(e)}", exc_info=True)
            raise FileProcessingError(error_msg) from e


def hide_app():
    """
    Hide the wxPython app without destroying it.
    
    This is safer on macOS and avoids segmentation faults by hiding
    the application from the dock rather than destroying it.
    """
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
    logger.debug("File selection process marked as complete")
    hide_app()


def select_directory():
    """
    Show directory selection dialog with memory of the last input directory.
    
    Returns:
        str: Selected directory path, or None if cancelled or invalid
    """
    logger.debug("Starting directory selection")
    
    # Load saved user settings
    settings = get_user_settings()
    last_input_dir = settings.get('last_input_directory')
    logger.debug(f"Last used input directory: {last_input_dir}")
    
    # Determine default path
    default_path = _get_default_input_path(last_input_dir)
    
    # Try using wxPython dialog
    directory = _try_gui_directory_selection(default_path)
    
    if directory is None:
        # Fall back to CLI mode if GUI failed
        directory = _cli_directory_selection(default_path)
    
    if directory and os.path.isdir(directory):
        # Save the selected directory for next time
        settings['last_input_directory'] = directory
        save_user_settings(settings)
        
        # Verify settings were saved
        verify_settings = get_user_settings()
        if verify_settings.get('last_input_directory') != directory:
            logger.error(f"Settings verification failed. Expected: {directory}, "
                        f"Got: {verify_settings.get('last_input_directory')}")
        
        return directory
    else:
        logger.error(f"Invalid directory selected: {directory}")
        return None


def select_multiple_directories():
    """
    Show multiple directory selection dialog with memory of the last input directory.
    
    Returns:
        list: List of selected directory paths, or empty list if cancelled
    """
    logger.debug("Starting multiple directory selection")
    
    # Load saved user settings
    settings = get_user_settings()
    last_input_dir = settings.get('last_input_directory')
    logger.debug(f"Last used input directory: {last_input_dir}")
    
    # Determine default path
    default_path = _get_default_input_path(last_input_dir)
    
    # Try using wxPython dialog
    directories = _try_gui_multiple_directory_selection(default_path)
    
    if directories is None:
        # Fall back to CLI mode if GUI failed
        directories = _cli_multiple_directory_selection(default_path)
    
    # Filter valid directories
    valid_directories = [d for d in directories if d and os.path.isdir(d)]
    
    if valid_directories:
        # Save the first selected directory for next time
        settings['last_input_directory'] = valid_directories[0]
        save_user_settings(settings)
        
        return valid_directories
    else:
        logger.error(f"No valid directories selected from: {directories}")
        return []


def select_file(default_path=None, title="Select file", wildcard="CSV files (*.csv)|*.csv", file_type="template"):
    """
    Display a file selection dialog and return the selected path.
    
    Args:
        default_path (str, optional): Default directory path to start in
        title (str): Dialog title
        wildcard (str): File filter pattern
        file_type (str): Type of file being selected ('template', 'input', 'output')
        
    Returns:
        str: Selected file path or None if canceled or invalid
    """
    logger.debug(f"Starting file selection. Title: {title}, Type: {file_type}")
    
    # Load saved user settings and determine default path
    settings = get_user_settings()
    if default_path is None:
        default_path = _get_default_file_path(settings, file_type)
    
    # Try using wxPython dialog
    file_path = _try_gui_file_selection(default_path, title, wildcard)
    
    if file_path is None:
        # Fallback to manual input
        file_path = _cli_file_selection(title, wildcard, default_path)
    
    if file_path and os.path.isfile(file_path):
        # Save directory for next time based on file type
        _save_file_directory(settings, file_path, file_type)
        return file_path
    else:
        logger.error(f"Invalid file selected: {file_path}")
        return None


def find_default_directory():
    """
    Find a sensible default directory based on the OS.
    
    Returns:
        str: Default directory path
    """
    logger.debug("Finding default directory")
    
    home_dir = os.path.expanduser("~")
    logger.debug(f"Home directory: {home_dir}")
    
    # Check common locations based on OS
    potential_paths = [os.getcwd()]  # Start with current directory
    
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


def _get_default_input_path(last_input_dir):
    """Get default path for input directory selection."""
    if last_input_dir and os.path.isdir(last_input_dir):
        # Get the parent directory (one level up)
        parent_dir = os.path.dirname(last_input_dir)
        if parent_dir and os.path.isdir(parent_dir):
            logger.debug(f"Using parent directory: {parent_dir}")
            return parent_dir
        else:
            logger.debug(f"Parent directory not valid, using last directory: {last_input_dir}")
            return last_input_dir
    else:
        default_path = find_default_directory()
        logger.debug(f"Found default directory: {default_path}")
        return default_path


def _get_default_file_path(settings, file_type):
    """Get default path for file selection based on type."""
    if file_type == "template":
        last_dir = settings.get('last_template_directory')
    elif file_type == "output":
        last_dir = settings.get('last_output_directory')
    else:
        last_dir = settings.get('last_input_directory')
    
    if last_dir and os.path.isdir(last_dir):
        if file_type == "template":
            logger.debug(f"Using last {file_type} directory: {last_dir}")
            return last_dir
        else:
            # Get the parent directory for input files
            parent_dir = os.path.dirname(last_dir)
            if parent_dir and os.path.isdir(parent_dir):
                logger.debug(f"Using parent directory: {parent_dir}")
                return parent_dir
            else:
                logger.debug(f"Using last directory: {last_dir}")
                return last_dir
    else:
        return find_default_directory()


def _try_gui_directory_selection(default_path):
    """Try to use wxPython for directory selection."""
    try:
        logger.debug("Attempting wxPython directory selection")
        
        if not HAS_WX:
            raise ImportError("wxPython not available")
        
        # Initialize the wx.App if it doesn't exist yet
        initialize_wx_app()
        
        # Suppress stderr output to avoid NSOpenPanel warning on macOS
        with _silence_stderr():
            style = wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
            
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
            return directory
            
    except ImportError:
        logger.info("wxPython not available, falling back to console input")
        return None
    except Exception as e:
        logger.error(f"Error in GUI directory dialog: {str(e)}")
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        logger.info("Falling back to console input")
        return None


def _try_gui_multiple_directory_selection(default_path):
    """Try to use wxPython for multiple directory selection."""
    try:
        logger.debug("Attempting wxPython multiple directory selection")
        
        if not HAS_WX:
            raise ImportError("wxPython not available")
        
        # Initialize the wx.App if it doesn't exist yet
        initialize_wx_app()
        
        selected_dirs = []
        
        with _silence_stderr():
            while True:
                style = wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
                
                if not selected_dirs:
                    message = "Select folders with ddPCR CSV files (first folder)"
                else:
                    message = f"Select additional folders ({len(selected_dirs)} selected) or Cancel to finish"
                
                dlg = wx.DirDialog(
                    None, 
                    message=message,
                    defaultPath=default_path if default_path else "", 
                    style=style
                )
                
                logger.debug(f"Showing directory dialog (iteration {len(selected_dirs) + 1})")
                
                if dlg.ShowModal() == wx.ID_OK:
                    directory = dlg.GetPath()
                    logger.debug(f"Selected directory: {directory}")
                    
                    if directory not in selected_dirs:
                        selected_dirs.append(directory)
                        logger.debug(f"Added directory: {directory}")
                    else:
                        logger.debug(f"Directory already selected: {directory}")
                else:
                    logger.debug("Dialog cancelled")
                    dlg.Destroy()
                    break
                
                dlg.Destroy()
                
                # If this is the first selection, continue the loop
                # If user cancels on subsequent selections, we exit
        
        logger.debug(f"Final selected directories: {selected_dirs}")
        return selected_dirs
            
    except ImportError:
        logger.info("wxPython not available, falling back to console input")
        return None
    except Exception as e:
        logger.error(f"Error in GUI multiple directory dialog: {str(e)}")
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        logger.info("Falling back to console input")
        return None


def _try_gui_file_selection(default_path, title, wildcard):
    """Try to use wxPython for file selection."""
    try:
        logger.debug("Attempting wxPython file selection")
        
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
            else:
                logger.debug("File dialog cancelled")
            
            dlg.Destroy()
            return file_path
            
    except ImportError:
        logger.info("wxPython not available, falling back to console input")
        return None
    except Exception as e:
        logger.error(f"Error in GUI file dialog: {str(e)}")
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        logger.info("Falling back to console input")
        return None


def _cli_directory_selection(default_path):
    """Handle directory selection via command line input."""
    print("\nEnter full path to directory containing CSV files:")
    if default_path:
        print(f"[Default: {default_path}]")
    
    directory = input("> ").strip()
    
    # If the user just pressed Enter, use the default path
    if not directory and default_path:
        directory = default_path
        print(f"Using default path: {directory}")
    
    return directory


def _cli_multiple_directory_selection(default_path):
    """Handle multiple directory selection via command line input."""
    print("\nEnter full paths to directories containing CSV files (one per line, empty line to finish):")
    if default_path:
        print(f"[Default first directory: {default_path}]")
    
    directories = []
    first_input = True
    
    while True:
        if first_input:
            prompt = "> "
            first_input = False
        else:
            prompt = f"[{len(directories)} selected] > "
        
        directory = input(prompt).strip()
        
        if not directory:
            if not directories and default_path:
                # First input is empty, use default
                directories.append(default_path)
                print(f"Using default path: {default_path}")
            break
        
        if directory not in directories:
            directories.append(directory)
        else:
            print(f"Already selected: {directory}")
    
    return directories


def _cli_file_selection(title, wildcard, default_path):
    """Handle file selection via command line input."""
    print(f"\nEnter full path to file ({wildcard.split('|')[0]}):")
    if default_path:
        print(f"[Previous directory: {default_path}]")
    
    file_path = input("> ").strip()
    return file_path


def _save_file_directory(settings, file_path, file_type):
    """Save the directory of the selected file based on file type."""
    selected_dir = os.path.dirname(file_path)
    
    if file_type == "template":
        settings['last_template_directory'] = selected_dir
    elif file_type == "output":
        settings['last_output_directory'] = selected_dir
    else:
        settings['last_input_directory'] = selected_dir
    
    save_user_settings(settings)
    logger.debug(f"Saved {file_type} directory: {selected_dir}")