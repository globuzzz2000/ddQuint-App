#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration template generator for the ddQuint pipeline.

Provides functionality to generate customizable configuration templates
based on current settings, with intelligent defaults and comprehensive
documentation for easy configuration management.
"""

import os
import json
import sys
import logging
from datetime import datetime
import colorama
from colorama import Fore, Style

from ..config.exceptions import ConfigError

logger = logging.getLogger(__name__)

def generate_config_template(config_cls, filename=None, output_dir=None):
    """
    Generate a template configuration file based on current settings.
    
    Creates a JSON configuration template with commonly modified settings
    and helpful comments for user customization.
    
    Args:
        config_cls: The Config class to generate template from
        filename: Filename to save the template (auto-generated if None)
        output_dir: Directory to save the template (current dir if None)
        
    Returns:
        Path to the generated template file
        
    Raises:
        ConfigError: If template generation fails
        
    Example:
        >>> from ddquint.config import Config
        >>> path = generate_config_template(Config, 'my_config.json', '/tmp')
        >>> print(f"Template saved to: {path}")
    """
    # Initialize colorama for cross-platform colored output
    colorama.init()
    
    logger.debug("Generating configuration template")
    
    # Determine output directory
    output_dir = _prepare_output_directory(output_dir)
    
    # Create filename if not provided
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"ddquint_config_template_{timestamp}.json"
    
    # Ensure .json extension
    if not filename.lower().endswith('.json'):
        filename += '.json'
    
    # Create full path
    filepath = os.path.join(output_dir, filename)
    logger.debug(f"Template will be saved to: {filepath}")
    
    try:
        # Create template dictionary
        template = _create_template_dictionary(config_cls)
        
        # Write template to file
        _write_template_file(template, filepath)
        
        # Print success message
        _print_success_message(filepath)
        
        logger.info(f"Configuration template generated: {filepath}")
        return filepath
        
    except Exception as e:
        error_msg = f"Error generating template: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        logger.error(f"{error_msg}")
        raise ConfigError(error_msg) from e

def _prepare_output_directory(output_dir):
    """
    Prepare and validate the output directory.
    
    Args:
        output_dir: Requested output directory or None for current dir
        
    Returns:
        Validated output directory path
        
    Raises:
        ConfigError: If directory creation fails
    """
    if output_dir is None:
        return os.getcwd()
    
    # Create the directory if it doesn't exist
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            logger.info(f"Created output directory: {output_dir}")
            logger.debug(f"Created output directory: {output_dir}")
        except Exception as e:
            error_msg = f"Error creating output directory: {output_dir}"
            logger.error(error_msg)
            logger.debug(f"Error details: {str(e)}", exc_info=True)
            logger.error(f"{error_msg}")
            logger.info(f"Using current directory instead.")
            return os.getcwd()
    
    return output_dir

def _safe_get_attr(obj, attr, default=None):
    """
    Safely get attribute from object with default fallback.
    
    Args:
        obj: Object to get attribute from
        attr: Attribute name
        default: Default value if attribute doesn't exist
        
    Returns:
        Attribute value or default
    """
    try:
        return getattr(obj, attr, default)
    except Exception as e:
        logger.warning(f"Failed to get attribute {attr}: {str(e)}")
        return default

def _create_template_dictionary(config_cls):
    """
    Create the template configuration dictionary.
    
    Args:
        config_cls: Config class to extract settings from
        
    Returns:
        Dictionary with template configuration
    """
    # Create template dictionary with commonly modified settings
    template = {
        # Performance Settings
        "NUM_PROCESSES": _safe_get_attr(config_cls, "NUM_PROCESSES", 4),
        "BATCH_SIZE": _safe_get_attr(config_cls, "BATCH_SIZE", 100),
        "SHOW_PROGRESS": _safe_get_attr(config_cls, "SHOW_PROGRESS", True),
        
        # Clustering Settings
        "HDBSCAN_MIN_CLUSTER_SIZE": _safe_get_attr(config_cls, "HDBSCAN_MIN_CLUSTER_SIZE", 4),
        "HDBSCAN_MIN_SAMPLES": _safe_get_attr(config_cls, "HDBSCAN_MIN_SAMPLES", 70),
        "HDBSCAN_EPSILON": _safe_get_attr(config_cls, "HDBSCAN_EPSILON", 0.06),
        "HDBSCAN_METRIC": _safe_get_attr(config_cls, "HDBSCAN_METRIC", "euclidean"),
        "HDBSCAN_CLUSTER_SELECTION_METHOD": _safe_get_attr(config_cls, "HDBSCAN_CLUSTER_SELECTION_METHOD", "eom"),
        "MIN_POINTS_FOR_CLUSTERING": _safe_get_attr(config_cls, "MIN_POINTS_FOR_CLUSTERING", 50),
        
        # Expected Centroids
        "EXPECTED_CENTROIDS": _safe_get_attr(config_cls, "EXPECTED_CENTROIDS", {
            "Negative": [800, 700],
            "Chrom1": [800, 2300],
            "Chrom2": [1700, 2100],
            "Chrom3": [2700, 1700],
            "Chrom4": [3300, 1250],
            "Chrom5": [3700, 700]
        }),
        
        # Centroid Matching
        "BASE_TARGET_TOLERANCE": _safe_get_attr(config_cls, "BASE_TARGET_TOLERANCE", 350),
        "SCALE_FACTOR_MIN": _safe_get_attr(config_cls, "SCALE_FACTOR_MIN", 0.5),
        "SCALE_FACTOR_MAX": _safe_get_attr(config_cls, "SCALE_FACTOR_MAX", 1.0),
        
        # Copy Number Settings
        "COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD": _safe_get_attr(config_cls, "COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD", 0.15),
        "COPY_NUMBER_BASELINE_MIN_CHROMS": _safe_get_attr(config_cls, "COPY_NUMBER_BASELINE_MIN_CHROMS", 3),
        "ANEUPLOIDY_DEVIATION_THRESHOLD": _safe_get_attr(config_cls, "ANEUPLOIDY_DEVIATION_THRESHOLD", 0.15),
        "EUPLOID_TOLERANCE": _safe_get_attr(config_cls, "EUPLOID_TOLERANCE", 0.08),
        "ANEUPLOIDY_TOLERANCE": _safe_get_attr(config_cls, "ANEUPLOIDY_TOLERANCE", 0.08),
        
        # Visualization Settings
        "TARGET_COLORS": _safe_get_attr(config_cls, "TARGET_COLORS", {
            "Negative": "#1f77b4",  # blue
            "Chrom1": "#ff7f0e",    # orange
            "Chrom2": "#2ca02c",    # green
            "Chrom3": "#17becf",    # cyan
            "Chrom4": "#d62728",    # red
            "Chrom5": "#9467bd",    # purple
            "Unknown": "#c7c7c7"    # light gray
        }),
        "ANEUPLOIDY_FILL_COLOR": _safe_get_attr(config_cls, "ANEUPLOIDY_FILL_COLOR", "#E6B8E6"),
        "ANEUPLOIDY_VALUE_FILL_COLOR": _safe_get_attr(config_cls, "ANEUPLOIDY_VALUE_FILL_COLOR", "#D070D0"),
    }
    
    # Add comments as string values at the top of the template
    template_with_comments = {
        "# ddQuint Configuration Template": "Generated on " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "# Instructions": "Modify the values below and save this file. Use it with: ddquint --config your_config.json",
        "# For full settings list": "Run 'ddquint --config'",
        "# Documentation": "Visit https://github.com/yourusername/ddquint for full documentation",
        "# Note": "Remove comment lines (starting with #) before using this file",
    }
    
    # Merge comments with actual settings
    template_with_comments.update(template)
    
    logger.debug(f"Created template with {len(template)} settings")
    return template_with_comments

def _write_template_file(template, filepath):
    """
    Write the template dictionary to a JSON file.
    
    Args:
        template: Template dictionary to write
        filepath: Output file path
        
    Raises:
        ConfigError: If file writing fails
    """
    try:
        with open(filepath, 'w') as f:
            json.dump(template, f, indent=4)
        logger.debug(f"Template written to file: {filepath}")
    except Exception as e:
        error_msg = f"Failed to write template file: {filepath}"
        logger.error(error_msg)
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        raise ConfigError(error_msg) from e

def _print_success_message(filepath):
    """
    Print success message with usage instructions.
    
    Args:
        filepath: Path to the generated template file
    """
    logger.info(f"Configuration template generated successfully!")
    logger.info(f"Template saved to: {filepath}")
    logger.info(f"\nTo use this template:")
    logger.info(f"1. Edit the file with your preferred settings")
    logger.info(f"2. Remove comment lines (starting with #)")
    logger.info(f"3. Run: ddquint --config {filepath}")
    logger.info(f"\nConfiguration Tips:")
    logger.info(f"- Adjust EXPECTED_CENTROIDS for your specific assay")
    logger.info(f"- Modify clustering parameters if needed (HDBSCAN_*)")
    logger.info(f"- Customize copy number thresholds for your analysis")
    logger.info(f"- Set TARGET_COLORS to match your preferred color scheme")