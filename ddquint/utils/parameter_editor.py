#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parameter editor utilities for ddQuint (GUI functionality removed).

Provides parameter loading/saving functionality without wx dependency.
The ddQuint macOS app uses Swift UI instead of wxPython for GUI.

Parameter Priority Order:
1. User parameters file (highest priority - trumps everything)
2. Config file specified with --config
3. Default config.py values (lowest priority)
"""

import os
import json
import sys
import logging

from ..config.exceptions import ConfigError

logger = logging.getLogger(__name__)

# Parameters file location
USER_SETTINGS_DIR = os.path.join(os.path.expanduser("~"), ".ddquint")
PARAMETERS_FILE = os.path.join(USER_SETTINGS_DIR, "parameters.json")


def open_parameter_editor(config_cls):
    """
    Open the parameter editor (fallback to console since wx removed).
    
    Args:
        config_cls: The Config class to edit parameters for
        
    Returns:
        True if parameters were saved, False if cancelled
        
    Raises:
        ConfigError: If GUI cannot be opened
    """
    logger.debug("Opening parameter editor GUI")
    
    # wx GUI functionality removed - ddQuint uses Swift UI instead
    logger.warning("GUI parameter editor not available - wx dependency removed")
    logger.info("Using console parameter editor instead...")
    return console_parameter_editor(config_cls)


def console_parameter_editor(config_cls):
    """
    Console-based parameter editor fallback.
    
    Args:
        config_cls: The Config class to edit parameters for
        
    Returns:
        True if parameters were saved, False if cancelled
    """
    print("\n" + "="*60)
    print("ddQuint Parameter Editor (Console Mode)")
    print("="*60)
    print("wxPython not available - using console input")
    print("For GUI parameter editing, use the ddQuint macOS app.")
    print("="*60)
    
    # Load existing parameters if they exist
    try:
        if os.path.exists(PARAMETERS_FILE):
            with open(PARAMETERS_FILE, 'r') as f:
                parameters = json.load(f)
            print(f"\nLoaded {len(parameters)} existing parameters from {PARAMETERS_FILE}")
        else:
            parameters = {}
            print(f"\nNo existing parameters found at {PARAMETERS_FILE}")
    except Exception as e:
        logger.error(f"Error loading parameters: {e}")
        parameters = {}
    
    print("\nConsole parameter editor is limited.")
    print("Use the ddQuint macOS app for full parameter editing capabilities.")
    
    return False  # Console editor doesn't save - use macOS app instead


def apply_parameters_to_config(config_cls):
    """
    Apply saved parameters to a config instance.
    
    Args:
        config_cls: The Config class to apply parameters to
    """
    logger.debug("Applying saved parameters to config")
    
    # Load parameters file
    parameters = {}
    try:
        if os.path.exists(PARAMETERS_FILE):
            with open(PARAMETERS_FILE, 'r') as f:
                parameters = json.load(f)
                logger.info(f"Loaded {len(parameters)} parameters from file")
        else:
            logger.debug("No parameters file found")
            return
    except Exception as e:
        logger.error(f"Error loading parameters file: {e}")
        return
    
    # Apply parameters to config
    applied_count = 0
    for key, value in parameters.items():
        try:
            if hasattr(config_cls, key):
                setattr(config_cls, key, value)
                applied_count += 1
                logger.debug(f"Applied parameter {key} = {value}")
            else:
                logger.warning(f"Unknown parameter: {key}")
        except Exception as e:
            logger.error(f"Error applying parameter {key}: {e}")
    
    logger.info(f"Applied {applied_count} parameters to config")


def load_parameters_if_exist(config_cls):
    """
    Load and apply parameters if the parameters file exists.
    
    Args:
        config_cls: The Config class to load parameters into
        
    Returns:
        True if parameters were loaded and applied, False otherwise
    """
    if parameters_exist():
        apply_parameters_to_config(config_cls)
        logger.info("Parameters loaded and applied successfully")
        return True
    else:
        logger.debug("No parameters file found - using defaults")
        return False


def get_parameters_file_path():
    """
    Get the path to the parameters file.
    
    Returns:
        Path to the parameters.json file
    """
    return PARAMETERS_FILE


def parameters_exist():
    """
    Check if parameters file exists.
    
    Returns:
        True if parameters file exists
    """
    return os.path.exists(PARAMETERS_FILE)


def delete_parameters():
    """
    Delete the parameters file.
    
    Returns:
        True if file was deleted successfully
    """
    try:
        if os.path.exists(PARAMETERS_FILE):
            os.remove(PARAMETERS_FILE)
            logger.info("Parameters file deleted")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting parameters file: {e}")
        return False