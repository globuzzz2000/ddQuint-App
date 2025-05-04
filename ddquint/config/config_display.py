#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration display module for the ddQuint pipeline.
"""

import textwrap
import colorama
from colorama import Fore, Style
from typing import Dict, Any

def display_config(config_cls):
    """
    Display all configuration settings in a structured, easy-to-read format.
    
    Args:
        config_cls: The Config class
    """
    # Initialize colorama for cross-platform colored output
    colorama.init()
    
    settings = config_cls.get_all_settings()
    
    # Print header
    print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'ddQuint Configuration Settings':^80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    # Group settings by category
    categories = {
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
            "ANEUPLOIDY_DEVIATION_THRESHOLD"
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
    
    # Print settings by category
    for category, keys in categories.items():
        print(f"{Fore.GREEN}{category}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'-' * len(category)}{Style.RESET_ALL}")
        
        for key in keys:
            if key in settings:
                value = settings[key]
                # Format value for display
                if isinstance(value, dict) and len(str(value)) > 60:
                    formatted_value = "\n" + textwrap.indent(str(value), " " * 4)
                elif isinstance(value, list) and len(str(value)) > 60:
                    formatted_value = "\n" + textwrap.indent(str(value), " " * 4)
                elif isinstance(value, str) and value is None:
                    formatted_value = "None"
                else:
                    formatted_value = str(value)
                
                print(f"{Fore.YELLOW}{key}{Style.RESET_ALL}: {formatted_value}")
        print()
    
    # Print footer with usage instructions
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    print(f"\n{Fore.WHITE}Configuration Options:{Style.RESET_ALL}")
    print(f"- View settings: {Fore.YELLOW}ddquint --config{Style.RESET_ALL}")
    print(f"- Generate a template: {Fore.YELLOW}ddquint --config template{Style.RESET_ALL}")
    print(f"- Generate template in specific directory: {Fore.YELLOW}ddquint --config template --output /path/to/dir{Style.RESET_ALL}")
    print(f"- Use custom config: {Fore.YELLOW}ddquint --config your_config.json{Style.RESET_ALL}")
    print(f"\nExample config file format:")
    print(f"{Fore.BLUE}{{")
    print(f'    "HDBSCAN_MIN_CLUSTER_SIZE": 4,')
    print(f'    "HDBSCAN_MIN_SAMPLES": 70,')
    print(f'    "EXPECTED_CENTROIDS": {{')
    print(f'        "Negative": [800, 700],')
    print(f'        "Chrom1": [800, 2300]')
    print(f'    }},')
    print(f'    "BASE_TARGET_TOLERANCE": 350')
    print(f"}}{Style.RESET_ALL}\n")