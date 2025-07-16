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
    logger.debug(f"Generating config template: filename={filename}, output_dir={output_dir}")
    
    try:
        # Initialize colorama for cross-platform colored output
        colorama.init()
        
        # Determine output directory
        if output_dir is None:
            output_dir = os.getcwd()
            logger.debug("Using current directory as output")
        else:
            # Create the directory if it doesn't exist
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir)
                    print(f"{Fore.GREEN}Created output directory: {output_dir}{Style.RESET_ALL}")
                    logger.debug(f"Created output directory: {output_dir}")
                except Exception as e:
                    error_msg = f"Failed to create output directory: {output_dir}"
                    logger.error(error_msg)
                    logger.debug(f"Error details: {str(e)}", exc_info=True)
                    print(f"{Fore.RED}Error creating output directory: {str(e)}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Using current directory instead.{Style.RESET_ALL}")
                    output_dir = os.getcwd()
        
        # Generate default filename if none provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"ddquint_config_template_{timestamp}.json"
            logger.debug(f"Generated default filename: {filename}")
        
        # Ensure filename has .json extension
        if not filename.lower().endswith('.json'):
            filename += '.json'
            logger.debug(f"Added .json extension: {filename}")
        
        # Create full path
        filepath = os.path.join(output_dir, filename)
        logger.debug(f"Full template path: {filepath}")
        
        # Create template dictionary with commonly modified settings
        template = _create_template_dictionary(config_cls)
        logger.debug(f"Built template with {len(template)} settings")
        
        # Write to file
        try:
            with open(filepath, 'w') as f:
                json.dump(template, f, indent=4)
            print(f"\n{Fore.WHITE}{'='*80}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}Configuration Template File Generator")
            print(f"{Fore.WHITE}{'='*80}{Style.RESET_ALL}")
            print(f"\nTemplate saved to: {Fore.CYAN}{filepath}{Style.RESET_ALL}")
            print(f"\nTo use this template:")
            print(f"1. Edit the file with your preferred settings")
            print(f"2. Run: {Fore.CYAN}ddquint --config {filepath}{Style.RESET_ALL}")
            
            print(f"\n{Fore.WHITE}Key Settings to Consider:{Style.RESET_ALL}")
            print(f"• {Fore.CYAN}EXPECTED_CENTROIDS{Style.RESET_ALL}: Update for your assay's target positions")
            print(f"• {Fore.CYAN}EXPECTED_COPY_NUMBERS{Style.RESET_ALL}: Adjust baseline values for your chromosomes")
            print(f"• {Fore.CYAN}HDBSCAN_*{Style.RESET_ALL}: Tune clustering parameters for your data density")
            print(f"• {Fore.CYAN}EUPLOID_TOLERANCE{Style.RESET_ALL}: Set acceptable range for normal copy numbers")
            print(f"• {Fore.CYAN}ML_*{Style.RESET_ALL}: Configure maximum likelihood estimation behavior")
            
            print(f"\n{Fore.WHITE}{'='*80}{Style.RESET_ALL}\n")
            
            logger.debug("Template generation completed successfully")
            return filepath
            
        except Exception as e:
            error_msg = f"Template file creation failed at {filepath}: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Error details: {str(e)}", exc_info=True)
            print(f"\n{Fore.RED}Error generating template: {str(e)}{Style.RESET_ALL}")
            raise TemplateGenerationError(error_msg) from e
            
    except Exception as e:
        error_msg = f"Template generation failed"
        logger.error(error_msg)
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        if not isinstance(e, TemplateGenerationError):
            raise TemplateGenerationError(error_msg) from e
        raise

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
        logger.debug(f"Failed to get attribute {attr}: {str(e)}")
        return default

def _create_template_dictionary(config_cls):
    """
    Create the template configuration dictionary.
    
    Args:
        config_cls: Config class to extract settings from
        
    Returns:
        Dictionary with template configuration
    """
    logger.debug("Building template dictionary from config class")
    
    try:
        # Create template dictionary with commonly modified settings
        # Using actual values from config.py instead of hardcoded ones
        template = {
            # Pipeline Mode Options
            "DEBUG_MODE": _safe_get_attr(config_cls, "DEBUG_MODE", False),
            
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
            
            # Expected Centroids - use actual config values
            "EXPECTED_CENTROIDS": _safe_get_attr(config_cls, "EXPECTED_CENTROIDS", {
                "Negative": [1000, 800],
                "Chrom1": [1000, 2500],
                "Chrom2": [1900, 2300],
                "Chrom3": [2700, 1850],
                "Chrom4": [3300, 1400],
                "Chrom5": [3600, 900]
            }),
            
            # Centroid Matching - use actual config values
            "BASE_TARGET_TOLERANCE": _safe_get_attr(config_cls, "BASE_TARGET_TOLERANCE", 500),
            "SCALE_FACTOR_MIN": _safe_get_attr(config_cls, "SCALE_FACTOR_MIN", 0.5),
            "SCALE_FACTOR_MAX": _safe_get_attr(config_cls, "SCALE_FACTOR_MAX", 1.0),
            
            # Copy Number Settings
            "MIN_USABLE_DROPLETS": _safe_get_attr(config_cls, "MIN_USABLE_DROPLETS", 3000),
            "COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD": _safe_get_attr(config_cls, "COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD", 0.15),
            "COPY_NUMBER_BASELINE_MIN_CHROMS": _safe_get_attr(config_cls, "COPY_NUMBER_BASELINE_MIN_CHROMS", 3),
            
            # Expected Copy Numbers - use actual config values
            "EXPECTED_COPY_NUMBERS": _safe_get_attr(config_cls, "EXPECTED_COPY_NUMBERS", {
                "Chrom1": 0.9688,
                "Chrom2": 1.0066,
                "Chrom3": 1.0300,
                "Chrom4": 0.9890,
                "Chrom5": 1.0056
            }),
            
            # Buffer Zone & Classification Settings
            "EUPLOID_TOLERANCE": _safe_get_attr(config_cls, "EUPLOID_TOLERANCE", 0.08),
            "ANEUPLOIDY_TOLERANCE": _safe_get_attr(config_cls, "ANEUPLOIDY_TOLERANCE", 0.08),
            "ANEUPLOIDY_TARGETS": _safe_get_attr(config_cls, "ANEUPLOIDY_TARGETS", {
                "low": 0.75,
                "high": 1.25
            }),
            
            # Maximum Likelihood Estimation Parameters
            "ML_MAX_ITERATIONS": _safe_get_attr(config_cls, "ML_MAX_ITERATIONS", 1000),
            "ML_CONVERGENCE_TOLERANCE": _safe_get_attr(config_cls, "ML_CONVERGENCE_TOLERANCE", 1e-9),
            "ML_INITIAL_LAMBDA_MIN": _safe_get_attr(config_cls, "ML_INITIAL_LAMBDA_MIN", 0.001),
            "ML_LAMBDA_MAX_BOUND": _safe_get_attr(config_cls, "ML_LAMBDA_MAX_BOUND", 10.0),
            "ML_NUMERICAL_EPSILON": _safe_get_attr(config_cls, "ML_NUMERICAL_EPSILON", 1e-8),
            "ML_OPTIMIZATION_METHOD": _safe_get_attr(config_cls, "ML_OPTIMIZATION_METHOD", "L-BFGS-B"),
            "ML_FALLBACK_TO_SIMPLE": _safe_get_attr(config_cls, "ML_FALLBACK_TO_SIMPLE", True),
            "ML_LOG_OPTIMIZATION_FAILURES": _safe_get_attr(config_cls, "ML_LOG_OPTIMIZATION_FAILURES", True),
            
            # Visualization Settings - use actual config values
            "COMPOSITE_FIGURE_SIZE": _safe_get_attr(config_cls, "COMPOSITE_FIGURE_SIZE", [16, 11]),
            "INDIVIDUAL_FIGURE_SIZE": _safe_get_attr(config_cls, "INDIVIDUAL_FIGURE_SIZE", [6, 5]),
            "COMPOSITE_PLOT_SIZE": _safe_get_attr(config_cls, "COMPOSITE_PLOT_SIZE", [5, 5]),
            "X_AXIS_MIN": _safe_get_attr(config_cls, "X_AXIS_MIN", 0),
            "X_AXIS_MAX": _safe_get_attr(config_cls, "X_AXIS_MAX", 3000),
            "Y_AXIS_MIN": _safe_get_attr(config_cls, "Y_AXIS_MIN", 0),
            "Y_AXIS_MAX": _safe_get_attr(config_cls, "Y_AXIS_MAX", 5000),
            "X_GRID_INTERVAL": _safe_get_attr(config_cls, "X_GRID_INTERVAL", 500),
            "Y_GRID_INTERVAL": _safe_get_attr(config_cls, "Y_GRID_INTERVAL", 1000),
            
            # Target Colors - use actual config values
            "TARGET_COLORS": _safe_get_attr(config_cls, "TARGET_COLORS", {
                "Negative": "#1f77b4",
                "Chrom1": "#f59a23",
                "Chrom2": "#7ec638",
                "Chrom3": "#16d9ff",
                "Chrom4": "#f65352",
                "Chrom5": "#82218b",
                "Chrom6": "#8c564b",
                "Chrom7": "#e377c2",
                "Chrom8": "#7f7f7f",
                "Chrom9": "#bcbd22",
                "Chrom10": "#9edae5",
                "Unknown": "#c7c7c7"
            }),
            
            # Copy Number State Colors
            "ANEUPLOIDY_FILL_COLOR": _safe_get_attr(config_cls, "ANEUPLOIDY_FILL_COLOR", "#E6B8E6"),
            "ANEUPLOIDY_VALUE_FILL_COLOR": _safe_get_attr(config_cls, "ANEUPLOIDY_VALUE_FILL_COLOR", "#D070D0"),
            "BUFFER_ZONE_FILL_COLOR": _safe_get_attr(config_cls, "BUFFER_ZONE_FILL_COLOR", "#B0B0B0"),
            "BUFFER_ZONE_VALUE_FILL_COLOR": _safe_get_attr(config_cls, "BUFFER_ZONE_VALUE_FILL_COLOR", "#808080"),
            
            # File Management
            "GRAPHS_DIR_NAME": _safe_get_attr(config_cls, "GRAPHS_DIR_NAME", "Graphs"),
            "RAW_DATA_DIR_NAME": _safe_get_attr(config_cls, "RAW_DATA_DIR_NAME", "Raw Data"),
            "CSV_EXTENSION": _safe_get_attr(config_cls, "CSV_EXTENSION", ".csv"),
            "COMPOSITE_IMAGE_FILENAME": _safe_get_attr(config_cls, "COMPOSITE_IMAGE_FILENAME", "Graph_Overview.png"),
            
            # Template Parsing
            "TEMPLATE_SEARCH_PARENT_LEVELS": _safe_get_attr(config_cls, "TEMPLATE_SEARCH_PARENT_LEVELS", 2),
            "TEMPLATE_PATTERN": _safe_get_attr(config_cls, "TEMPLATE_PATTERN", "{dir_name}.csv"),
            
            # Well Management
            "PLATE_ROWS": _safe_get_attr(config_cls, "PLATE_ROWS", ["A","B","C","D","E","F","G","H"]),
            "PLATE_COLS": _safe_get_attr(config_cls, "PLATE_COLS", ["1","2","3","4","5","6","7","8","9","10","11","12"]),
            "WELL_FORMAT": _safe_get_attr(config_cls, "WELL_FORMAT", "{row}{col:02d}")
        }
        
        logger.debug(f"Template dictionary built with {len(template)} settings")
        return template
        
    except Exception as e:
        error_msg = f"Failed to build template dictionary"
        logger.error(error_msg)
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        raise TemplateGenerationError(error_msg) from e


class TemplateGenerationError(Exception):
    """Error during configuration template generation."""
    pass