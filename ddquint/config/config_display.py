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
            "ANEUPLOIDY_DEVIATION_THRESHOLD", "EXPECTED_COPY_NUMBERS"
        ],
        "Buffer Zone & Classification Settings": [
            "EUPLOID_TOLERANCE", "ANEUPLOIDY_TOLERANCE", "ANEUPLOIDY_TARGETS"
        ],
        "Visualization Settings": [
            "COMPOSITE_FIGURE_SIZE", "INDIVIDUAL_FIGURE_SIZE", "COMPOSITE_PLOT_SIZE",
            "X_AXIS_MIN", "X_AXIS_MAX", "Y_AXIS_MIN", "Y_AXIS_MAX",
            "X_GRID_INTERVAL", "Y_GRID_INTERVAL", "TARGET_COLORS",
            "ANEUPLOIDY_FILL_COLOR", "ANEUPLOIDY_VALUE_FILL_COLOR", 
            "BUFFER_ZONE_FILL_COLOR", "BUFFER_ZONE_VALUE_FILL_COLOR"
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
    
    # Add special explanations for buffer zone settings
    if category == "Buffer Zone & Classification Settings":
        logger.info(f"{Fore.CYAN}Buffer Zone Implementation:{Style.RESET_ALL}")
        logger.info(f"  - Samples are classified as euploid, aneuploidy, or buffer zone")
        logger.info(f"  - Buffer zones identify uncertain copy numbers requiring manual review")
        logger.info(f"  - Classification uses chromosome-specific expected values\n")
    
    for key in keys:
        if key in settings:
            value = settings[key]
            formatted_value = _format_setting_value(value, key)
            
            # Add explanations for specific buffer zone settings
            explanation = _get_setting_explanation(key)
            if explanation:
                logger.info(f"{Fore.YELLOW}{key}{Style.RESET_ALL}: {formatted_value}")
                logger.info(f"  {Fore.CYAN}→ {explanation}{Style.RESET_ALL}")
            else:
                logger.info(f"{Fore.YELLOW}{key}{Style.RESET_ALL}: {formatted_value}")
        else:
            logger.warning(f"Setting key not found in configuration: {key}")
    logger.info("")

def _get_setting_explanation(key):
    """
    Get explanation text for specific settings.
    
    Args:
        key: Setting key name
        
    Returns:
        Explanation string or None
    """
    explanations = {
        "EUPLOID_TOLERANCE": "Tolerance around expected values for euploid classification (±0.08 = ±8%)",
        "ANEUPLOIDY_TOLERANCE": "Tolerance around aneuploidy targets for clear gain/loss classification",
        "ANEUPLOIDY_TARGETS": "Target copy numbers: 'low' for deletions (0.75×), 'high' for duplications (1.25×)",
        "EXPECTED_COPY_NUMBERS": "Chromosome-specific expected copy number values for accurate classification",
        "BUFFER_ZONE_FILL_COLOR": "Excel highlighting color for entire rows with buffer zone samples",
        "BUFFER_ZONE_VALUE_FILL_COLOR": "Excel highlighting color for individual buffer zone values (currently unused)"
    }
    return explanations.get(key)

def _format_setting_value(value, key=None):
    """
    Format a setting value for display.
    
    Args:
        value: The setting value to format
        key: The setting key for context-specific formatting
        
    Returns:
        Formatted string representation of the value
    """
    # Special formatting for specific keys
    if key == "ANEUPLOIDY_TARGETS":
        if isinstance(value, dict):
            formatted = "{\n"
            for k, v in value.items():
                formatted += f"      {k}: {v} ({'deletion target' if k == 'low' else 'duplication target'})\n"
            formatted += "    }"
            return formatted
    
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
    
    logger.info(f"\n{Fore.WHITE}Buffer Zone Configuration:{Style.RESET_ALL}")
    logger.info(f"- Adjust {Fore.YELLOW}EUPLOID_TOLERANCE{Style.RESET_ALL} to change normal range size")
    logger.info(f"- Modify {Fore.YELLOW}ANEUPLOIDY_TOLERANCE{Style.RESET_ALL} to adjust aneuploidy detection sensitivity")
    logger.info(f"- Update {Fore.YELLOW}EXPECTED_COPY_NUMBERS{Style.RESET_ALL} for assay-specific baselines")
    logger.info(f"- Change {Fore.YELLOW}ANEUPLOIDY_TARGETS{Style.RESET_ALL} for different deletion/duplication thresholds")
    
    logger.info(f"\nExample config file format:")
    logger.info(f"{Fore.BLUE}{{")
    logger.info(f'    "HDBSCAN_MIN_CLUSTER_SIZE": 4,')
    logger.info(f'    "HDBSCAN_MIN_SAMPLES": 70,')
    logger.info(f'    "EXPECTED_CENTROIDS": {{')
    logger.info(f'        "Negative": [800, 700],')
    logger.info(f'        "Chrom1": [800, 2300]')
    logger.info(f'    }},')
    logger.info(f'    "BASE_TARGET_TOLERANCE": 350,')
    logger.info(f'    "EUPLOID_TOLERANCE": 0.08,')
    logger.info(f'    "ANEUPLOIDY_TOLERANCE": 0.08')
    logger.info(f"}}{Style.RESET_ALL}\n")