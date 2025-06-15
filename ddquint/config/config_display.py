#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration display module for the ddQuint pipeline.

Provides formatted display functionality for configuration settings
with color-coded output and organized categorization for easy reading
and configuration management.
"""

import textwrap
import colorama
import logging
from colorama import Fore, Style

logger = logging.getLogger(__name__)

def display_config(config_cls):
    """
    Display all configuration settings in a structured, easy-to-read format.
    
    Organizes configuration settings into logical categories and displays
    them with color-coded formatting for improved readability.
    
    Args:
        config_cls: The Config class to display settings from
        
    Example:
        >>> from ddquint.config import Config
        >>> display_config(Config)
    """
    # Initialize colorama for cross-platform colored output
    colorama.init()
    
    try:
        settings = config_cls.get_all_settings()
        logger.debug(f"Displaying {len(settings)} configuration settings")
    except Exception as e:
        logger.error(f"Failed to get configuration settings: {str(e)}")
        logger.error(f"Error retrieving configuration settings: {str(e)}")
        return
    
    # Print header
    logger.info(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    logger.info(f"{Fore.CYAN}{'ddQuint Configuration Settings':^80}{Style.RESET_ALL}")
    logger.info(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    # Group settings by category
    categories = _get_setting_categories()
    
    # Print settings by category
    for category, keys in categories.items():
        _print_category_settings(category, keys, settings)
    
    # Print footer with usage instructions
    _print_usage_instructions()

def _get_setting_categories():
    """
    Get organized categories of configuration settings.
    
    Returns:
        Dictionary mapping category names to lists of setting keys
    """
    return {
        "Pipeline Mode Options": [
            "DEBUG_MODE"
        ],
        "Performance Settings": [
            "NUM_PROCESSES", "BATCH_SIZE", "SHOW_PROGRESS"
        ],
        "Clustering Settings": [
            "HDBSCAN_MIN_CLUSTER_SIZE", "HDBSCAN_MIN_SAMPLES", "HDBSCAN_EPSILON",
            "HDBSCAN_METRIC", "HDBSCAN_CLUSTER_SELECTION_METHOD", "MIN_POINTS_FOR_CLUSTERING"
        ],
        "Expected Centroids": [
            "EXPECTED_CENTROIDS"
        ],
        "Centroid Matching": [
            "BASE_TARGET_TOLERANCE", "SCALE_FACTOR_MIN", "SCALE_FACTOR_MAX"
        ],
        "Copy Number Settings": [
            "COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD", "COPY_NUMBER_BASELINE_MIN_CHROMS",
            "ANEUPLOIDY_DEVIATION_THRESHOLD", "EUPLOID_TOLERANCE", "ANEUPLOIDY_TOLERANCE"
        ],
        "Visualization Settings": [
            "COMPOSITE_FIGURE_SIZE", "INDIVIDUAL_FIGURE_SIZE", "COMPOSITE_PLOT_SIZE",
            "X_AXIS_MIN", "X_AXIS_MAX", "Y_AXIS_MIN", "Y_AXIS_MAX",
            "X_GRID_INTERVAL", "Y_GRID_INTERVAL", "TARGET_COLORS",
            "ANEUPLOIDY_FILL_COLOR", "ANEUPLOIDY_VALUE_FILL_COLOR"
        ],
        "File Management": [
            "GRAPHS_DIR_NAME", "RAW_DATA_DIR_NAME", "CSV_EXTENSION",
            "EXCEL_OUTPUT_FILENAME", "COMPOSITE_IMAGE_FILENAME"
        ],
        "Template Parsing": [
            "TEMPLATE_SEARCH_PARENT_LEVELS", "TEMPLATE_PATTERN"
        ],
        "Well Management": [
            "PLATE_ROWS", "PLATE_COLS", "WELL_FORMAT"
        ]
    }

def _print_category_settings(category, keys, settings):
    """
    Print settings for a specific category.
    
    Args:
        category: Category name to display
        keys: List of setting keys for this category
        settings: Dictionary of all settings
    """
    logger.info(f"{Fore.GREEN}{category}{Style.RESET_ALL}")
    logger.info(f"{Fore.GREEN}{'-' * len(category)}{Style.RESET_ALL}")
    
    for key in keys:
        if key in settings:
            value = settings[key]
            formatted_value = _format_setting_value(value)
            logger.info(f"{Fore.YELLOW}{key}{Style.RESET_ALL}: {formatted_value}")
        else:
            logger.warning(f"Setting key not found in configuration: {key}")
    logger.info("")

def _format_setting_value(value):
    """
    Format a setting value for display.
    
    Args:
        value: The setting value to format
        
    Returns:
        Formatted string representation of the value
    """
    # Format value for display based on type and length
    if isinstance(value, dict) and len(str(value)) > 60:
        return "\n" + textwrap.indent(str(value), " " * 4)
    elif isinstance(value, list) and len(str(value)) > 60:
        return "\n" + textwrap.indent(str(value), " " * 4)
    elif value is None:
        return "None"
    else:
        return str(value)

def _print_usage_instructions():
    """Print footer with configuration usage instructions."""
    logger.info(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    logger.info(f"\n{Fore.WHITE}Configuration Options:{Style.RESET_ALL}")
    logger.info(f"- View settings: {Fore.YELLOW}ddquint --config{Style.RESET_ALL}")
    logger.info(f"- Generate a template: {Fore.YELLOW}ddquint --config template{Style.RESET_ALL}")
    logger.info(f"- Generate template in specific directory: {Fore.YELLOW}ddquint --config template --output /path/to/dir{Style.RESET_ALL}")
    logger.info(f"- Use custom config: {Fore.YELLOW}ddquint --config your_config.json{Style.RESET_ALL}")
    logger.info(f"\nExample config file format:")
    logger.info(f"{Fore.BLUE}{{")
    logger.info(f'    "HDBSCAN_MIN_CLUSTER_SIZE": 4,')
    logger.info(f'    "HDBSCAN_MIN_SAMPLES": 70,')
    logger.info(f'    "EXPECTED_CENTROIDS": {{')
    logger.info(f'        "Negative": [800, 700],')
    logger.info(f'        "Chrom1": [800, 2300]')
    logger.info(f'    }},')
    logger.info(f'    "BASE_TARGET_TOLERANCE": 350')
    logger.info(f"}}{Style.RESET_ALL}\n")