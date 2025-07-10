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
    logger.debug("Starting configuration display")
    
    try:
        # Initialize colorama for cross-platform colored output
        colorama.init()
        
        settings = config_cls.get_all_settings()
        logger.debug(f"Retrieved {len(settings)} configuration settings")
        
        # Print header
        print(f"\n{Fore.WHITE}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{'ddQuint Configuration Settings':^80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{'='*80}{Style.RESET_ALL}\n")
        
        # Group settings by category
        categories = _get_setting_categories()
        
        # Create "Other" category for any settings not explicitly categorized
        categorized_keys = []
        for keys in categories.values():
            categorized_keys.extend(keys)
        
        other_keys = [key for key in settings.keys() if key not in categorized_keys 
                     and not key.startswith('_')]
        
        if other_keys:
            categories["Other"] = other_keys
        
        # Print settings by category
        for category, keys in categories.items():
            print(f"{Fore.WHITE}{category}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}{'-' * len(category)}{Style.RESET_ALL}")
            
            # Add special explanations for buffer zone settings
            if category == "Buffer Zone & Classification Settings":
                print(f"{Fore.CYAN}Buffer Zone Implementation:{Style.RESET_ALL}")
                print(f"  - Samples are classified as euploid, aneuploidy, or buffer zone")
                print(f"  - Buffer zones identify uncertain copy numbers requiring manual review")
                print(f"  - Classification uses chromosome-specific expected values\n")
            
            for key in keys:
                if key in settings:
                    value = settings[key]
                    formatted_value = _format_setting_value(value, key)
                    
                    # Add explanations for specific buffer zone settings
                    explanation = _get_setting_explanation(key)
                    if explanation:
                        print(f"{Fore.CYAN}{key}{Style.RESET_ALL}: {formatted_value}")
                        print(f"  {Fore.YELLOW}→ {explanation}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.CYAN}{key}{Style.RESET_ALL}: {formatted_value}")
            print()
        
        # Print footer with usage instructions
        print(f"{Fore.WHITE}{'-'*80}{Style.RESET_ALL}")
        print(f"\n{Fore.WHITE}Configuration Options:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}View settings: {Fore.CYAN}ddquint --config{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Generate a template: {Fore.CYAN}ddquint --config template{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Generate template in specific directory: {Fore.CYAN}ddquint --config template --output /path/to/dir{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Use custom config: {Fore.CYAN}ddquint --config your_config.json{Style.RESET_ALL}")
        
        print(f"\n{Fore.WHITE}Buffer Zone Configuration:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Adjust {Fore.CYAN}EUPLOID_TOLERANCE{Style.RESET_ALL} to change normal range size")
        print(f"{Fore.WHITE}Modify {Fore.CYAN}ANEUPLOIDY_TOLERANCE{Style.RESET_ALL} to adjust aneuploidy detection sensitivity")
        print(f"{Fore.WHITE}Update {Fore.CYAN}EXPECTED_COPY_NUMBERS{Style.RESET_ALL} for assay-specific baselines")
        print(f"{Fore.WHITE}Change {Fore.CYAN}ANEUPLOIDY_TARGETS{Style.RESET_ALL} for different deletion/duplication thresholds")
        
        print(f"\nExample config file format:")
        print(f"{Fore.BLUE}{{")
        print(f'    "HDBSCAN_MIN_CLUSTER_SIZE": 4,')
        print(f'    "HDBSCAN_MIN_SAMPLES": 70,')
        print(f'    "EXPECTED_CENTROIDS": {{')
        print(f'        "Negative": [1000, 800],')
        print(f'        "Chrom1": [1000, 2500]')
        print(f'    }},')
        print(f'    "BASE_TARGET_TOLERANCE": 500,')
        print(f'    "EUPLOID_TOLERANCE": 0.08,')
        print(f'    "ANEUPLOIDY_TOLERANCE": 0.08')
        print(f"}}{Style.RESET_ALL}")
        print(f"\n{Fore.WHITE}{'='*80}{Style.RESET_ALL}")
        print(f"{Style.RESET_ALL}\n")
        
        logger.debug("Configuration display completed successfully")
        
    except Exception as e:
        error_msg = f"Configuration display failed"
        logger.error(error_msg)
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        raise ConfigDisplayError(error_msg) from e

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
            "COMPOSITE_IMAGE_FILENAME"
        ],
        "Template Parsing": [
            "TEMPLATE_SEARCH_PARENT_LEVELS", "TEMPLATE_PATTERN"
        ],
        "Well Management": [
            "PLATE_ROWS", "PLATE_COLS", "WELL_FORMAT"
        ]
    }

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


class ConfigDisplayError(Exception):
    """Error during configuration display operations."""
    pass