#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logging configuration module for ddQuint.
"""

import os
import sys
import datetime
import logging
import glob

def cleanup_old_log_files(log_dir, max_files=10):
    """
    Keep only the most recent log files, remove older ones.
    
    Args:
        log_dir: Directory containing log files
        max_files: Maximum number of log files to keep
    """
    try:
        # Get all log files matching the pattern
        log_pattern = os.path.join(log_dir, "ddquint_*.log")
        log_files = glob.glob(log_pattern)
        
        if len(log_files) <= max_files:
            return
        
        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        # Remove old files
        files_to_remove = log_files[max_files:]
        for old_file in files_to_remove:
            try:
                os.remove(old_file)
                logger = logging.getLogger(__name__)
                logger.debug(f"Removed old log file: {os.path.basename(old_file)}")
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.debug(f"Could not remove old log file {os.path.basename(old_file)}: {e}")
                
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.debug(f"Error during log cleanup: {e}")

def setup_logging(debug=False):
    """
    Configure logging for the application.
    
    Sets up both file and console logging with appropriate formatting
    and log levels based on debug mode settings.
    
    Args:
        debug: Enable debug mode with detailed logging
        
    Returns:
        Path to the log file for reference
        
    Raises:
        RuntimeError: If logging setup fails
    """
    # Console log level based on debug mode
    console_log_level = logging.DEBUG if debug else logging.INFO
    
    # Always use detailed format for file logging
    file_log_format = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    
    # Simple format for console when not in debug mode
    if debug:
        console_log_format = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    else:
        console_log_format = '%(message)s'
    
    # Set up logging to file
    log_dir = os.path.join(os.path.expanduser("~"), ".ddquint", "logs")
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception as e:
        raise RuntimeError(f"Failed to create log directory: {log_dir}") from e
        
    log_file = os.path.join(log_dir, f"ddquint_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    # Create file handler - ALWAYS DEBUG level for file logging
    try:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Always DEBUG for file
        file_handler.setFormatter(logging.Formatter(file_log_format))
    except Exception as e:
        raise RuntimeError(f"Failed to create log file handler: {log_file}") from e
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_log_level)
    console_handler.setFormatter(logging.Formatter(console_log_format))
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Always DEBUG at root level
    
    # Clear existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add the handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # SUPPRESS MATPLOTLIB FONT MANAGER DEBUG MESSAGES
    # Set matplotlib loggers to WARNING level to prevent font debug spam
    matplotlib_loggers = [
        'matplotlib.font_manager',
        'matplotlib.fontconfig_pattern',
        'matplotlib.pyplot',
        'matplotlib.figure',
        'matplotlib.backends',
        'PIL.PngImagePlugin'  # Also suppress PIL debug messages
    ]
    
    for logger_name in matplotlib_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    # Configure our specific logger
    logger = logging.getLogger(__name__)
    
    if debug:
        logger.debug(f"Debug mode enabled")
        logger.debug(f"Log file: {log_file}")
        logger.debug(f"Python version: {sys.version}")
        logger.debug(f"Platform: {sys.platform}")
    
    # Clean up old log files
    cleanup_old_log_files(log_dir, max_files=10)
    
    return log_file