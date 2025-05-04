#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration template generator for the ddQuint pipeline.
"""

import os
import json
import sys
from datetime import datetime
import colorama
from colorama import Fore, Style

def generate_config_template(config_cls, filename=None, output_dir=None):
    """
    Generate a template configuration file based on current settings.
    
    Args:
        config_cls: The Config class
        filename (str, optional): Filename to save the template. If None, uses default name.
        output_dir (str, optional): Directory to save the template. If None, uses current directory.
        
    Returns:
        str: Path to the generated template file
    """
    # Initialize colorama for cross-platform colored output
    colorama.init()
    
    # Determine output directory
    if output_dir is None:
        output_dir = os.getcwd()
    else:
        # Create the directory if it doesn't exist
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                print(f"{Fore.GREEN}Created output directory: {output_dir}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Error creating output directory: {str(e)}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Using current directory instead.{Style.RESET_ALL}")
                output_dir = os.getcwd()
    
    # If no filename is provided, create a default one
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"ddquint_config_template_{timestamp}.json"
    
    # Make sure filename has .json extension
    if not filename.lower().endswith('.json'):
        filename += '.json'
    
    # Create full path
    filepath = os.path.join(output_dir, filename)
    
    # Helper function to safely get attributes
    def safe_get_attr(obj, attr, default=None):
        return getattr(obj, attr, default)
    
    # Create template dictionary with commonly modified settings
    template = {
        # Performance Settings
        "NUM_PROCESSES": safe_get_attr(config_cls, "NUM_PROCESSES", 4),
        "BATCH_SIZE": safe_get_attr(config_cls, "BATCH_SIZE", 100),
        "SHOW_PROGRESS": safe_get_attr(config_cls, "SHOW_PROGRESS", True),
        
        # Clustering Settings
        "HDBSCAN_MIN_CLUSTER_SIZE": safe_get_attr(config_cls, "HDBSCAN_MIN_CLUSTER_SIZE", 4),
        "HDBSCAN_MIN_SAMPLES": safe_get_attr(config_cls, "HDBSCAN_MIN_SAMPLES", 70),
        "HDBSCAN_EPSILON": safe_get_attr(config_cls, "HDBSCAN_EPSILON", 0.06),
        "HDBSCAN_METRIC": safe_get_attr(config_cls, "HDBSCAN_METRIC", "euclidean"),
        "HDBSCAN_CLUSTER_SELECTION_METHOD": safe_get_attr(config_cls, "HDBSCAN_CLUSTER_SELECTION_METHOD", "eom"),
        "MIN_POINTS_FOR_CLUSTERING": safe_get_attr(config_cls, "MIN_POINTS_FOR_CLUSTERING", 50),
        
        # Expected Centroids
        "EXPECTED_CENTROIDS": safe_get_attr(config_cls, "EXPECTED_CENTROIDS", {
            "Negative": [800, 700],
            "Chrom1": [800, 2300],
            "Chrom2": [1700, 2100],
            "Chrom3": [2700, 1700],
            "Chrom4": [3300, 1250],
            "Chrom5": [3700, 700]
        }),
        
        # Centroid Matching
        "BASE_TARGET_TOLERANCE": safe_get_attr(config_cls, "BASE_TARGET_TOLERANCE", 350),
        "SCALE_FACTOR_MIN": safe_get_attr(config_cls, "SCALE_FACTOR_MIN", 0.5),
        "SCALE_FACTOR_MAX": safe_get_attr(config_cls, "SCALE_FACTOR_MAX", 1.0),
        
        # Copy Number Settings
        "COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD": safe_get_attr(config_cls, "COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD", 0.15),
        "COPY_NUMBER_BASELINE_MIN_CHROMS": safe_get_attr(config_cls, "COPY_NUMBER_BASELINE_MIN_CHROMS", 3),
        "ANEUPLOIDY_DEVIATION_THRESHOLD": safe_get_attr(config_cls, "ANEUPLOIDY_DEVIATION_THRESHOLD", 0.15),
        
        # Visualization Settings
        "TARGET_COLORS": safe_get_attr(config_cls, "TARGET_COLORS", {
            "Negative": "#1f77b4",  # blue
            "Chrom1": "#ff7f0e",    # orange
            "Chrom2": "#2ca02c",    # green
            "Chrom3": "#17becf",    # cyan
            "Chrom4": "#d62728",    # red
            "Chrom5": "#9467bd",    # purple
            "Unknown": "#c7c7c7"    # light gray
        }),
        "ANEUPLOIDY_FILL_COLOR": safe_get_attr(config_cls, "ANEUPLOIDY_FILL_COLOR", "#E6B8E6"),
        "ANEUPLOIDY_VALUE_FILL_COLOR": safe_get_attr(config_cls, "ANEUPLOIDY_VALUE_FILL_COLOR", "#D070D0"),
    }
    
    # Add comments as string values at the top of the template
    template_with_comments = {
        "# ddQuint Configuration Template": "Generated on " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "# Instructions": "Modify the values below and save this file. Use it with: ddquint --config your_config.json",
        "# For full settings list": "Run 'ddquint --config'",
        "# Documentation": "Visit https://github.com/yourusername/ddquint for full documentation",
    }
    
    # Merge comments with actual settings
    template_with_comments.update(template)
    
    # Write to file
    try:
        with open(filepath, 'w') as f:
            json.dump(template_with_comments, f, indent=4)
        
        print(f"\n{Fore.GREEN}Configuration template generated successfully!{Style.RESET_ALL}")
        print(f"Template saved to: {Fore.YELLOW}{filepath}{Style.RESET_ALL}")
        print(f"\nTo use this template:")
        print(f"1. Edit the file with your preferred settings")
        print(f"2. Run: {Fore.YELLOW}ddquint --config {filepath}{Style.RESET_ALL}")
        print()
        
        return filepath
    except Exception as e:
        print(f"\n{Fore.RED}Error generating template: {str(e)}{Style.RESET_ALL}")
        return None