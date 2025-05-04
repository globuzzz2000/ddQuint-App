#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration module for the ddQuint pipeline with dynamic chromosome support.
"""

import os
import json
import logging
from multiprocessing import cpu_count
from typing import Dict, List, Union, Any, Optional

class Config:
    """Central configuration settings for the ddQuint pipeline with singleton pattern."""
    
    # Singleton instance
    _instance = None
    
    #############################################################################
    #                           Pipeline Mode Options
    #############################################################################
    DEBUG_MODE = False                   # Debug logging mode (enable with --debug flag)
    
    #############################################################################
    #                           Performance Settings
    #############################################################################
    NUM_PROCESSES = max(1, int(cpu_count() * 0.75))  # Use 75% of cores
    BATCH_SIZE = 100
    SHOW_PROGRESS = True
    
    #############################################################################
    #                           Clustering Settings
    #############################################################################
    # HDBSCAN clustering parameters
    HDBSCAN_MIN_CLUSTER_SIZE = 4
    HDBSCAN_MIN_SAMPLES = 70
    HDBSCAN_EPSILON = 0.06
    HDBSCAN_METRIC = 'euclidean'
    HDBSCAN_CLUSTER_SELECTION_METHOD = 'eom'
    
    # Minimum data points required for clustering
    MIN_POINTS_FOR_CLUSTERING = 50
    
    #############################################################################
    #                           Expected Centroids
    #############################################################################
    # Define expected centroids for targets (maximum 10 chromosomes)
    # Format: { "target_name": [Ch1Amplitude, Ch2Amplitude] }
    EXPECTED_CENTROIDS = {
        "Negative": [800, 700],
        "Chrom1":   [800, 2300],
        "Chrom2":   [1700, 2100],
        "Chrom3":   [2700, 1850],
        "Chrom4":   [3200, 1250],
        "Chrom5":   [3700, 700]
    }
    
    # Tolerance for matching clusters to targets
    BASE_TARGET_TOLERANCE = 350
    
    # Scale factor limits for adaptive tolerance
    SCALE_FACTOR_MIN = 0.5
    SCALE_FACTOR_MAX = 1.0
    
    #############################################################################
    #                           Copy Number Settings
    #############################################################################
    # Copy number calculation parameters
    COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD = 0.15  # 15% deviation threshold
    COPY_NUMBER_BASELINE_MIN_CHROMS = 3  # Minimum chromosomes for baseline calc
    ANEUPLOIDY_DEVIATION_THRESHOLD = 0.15 
    
    #############################################################################
    #                           Visualization Settings
    #############################################################################
    # Plot dimensions and settings
    COMPOSITE_FIGURE_SIZE = (16, 11)
    INDIVIDUAL_FIGURE_SIZE = (6, 5)
    COMPOSITE_PLOT_SIZE = (5, 5)
    
    # Axis limits
    X_AXIS_MIN = 0
    X_AXIS_MAX = 3000
    Y_AXIS_MIN = 0
    Y_AXIS_MAX = 5000
    
    # Grid settings
    X_GRID_INTERVAL = 500
    Y_GRID_INTERVAL = 1000
    
    # Color scheme for targets (up to 10 chromosomes)
    TARGET_COLORS = {
        "Negative": "#1f77b4",  # blue
        "Chrom1":   "#ff7f0e",  # orange
        "Chrom2":   "#2ca02c",  # green
        "Chrom3":   "#17becf",  # cyan
        "Chrom4":   "#d62728",  # red
        "Chrom5":   "#9467bd",  # purple
        "Chrom6":   "#8c564b",  # brown
        "Chrom7":   "#e377c2",  # pink
        "Chrom8":   "#7f7f7f",  # gray
        "Chrom9":   "#bcbd22",  # olive
        "Chrom10":  "#9edae5",  # light cyan
        "Unknown":  "#c7c7c7"   # light gray
    }
    
    # Aneuploidy highlighting colors
    ANEUPLOIDY_FILL_COLOR = "#E6B8E6"  # Light purple
    ANEUPLOIDY_VALUE_FILL_COLOR = "#D070D0"  # Darker purple
    
    #############################################################################
    #                           File Management
    #############################################################################
    # Default output directories
    GRAPHS_DIR_NAME = "Graphs"
    RAW_DATA_DIR_NAME = "Raw Data"
    
    # File name patterns
    CSV_EXTENSION = '.csv'
    
    # Excel report settings
    EXCEL_OUTPUT_FILENAME = "Plate_Results.xlsx"
    COMPOSITE_IMAGE_FILENAME = "Graph_Overview.png"
    
    #############################################################################
    #                           Template Parsing
    #############################################################################
    # Template search parameters
    TEMPLATE_SEARCH_PARENT_LEVELS = 2  # How many parent directories to search up
    TEMPLATE_PATTERN = "{dir_name}.xlsx"  # Template file naming pattern
    
    #############################################################################
    #                           Well Management
    #############################################################################
    # 96-well plate layout
    PLATE_ROWS = list('ABCDEFGH')
    PLATE_COLS = [str(i) for i in range(1, 13)]
    WELL_FORMAT = "{row}{col:02d}"  # e.g., "A01"
    
    def __init__(self):
        """Initialize Config instance with default values."""
        pass
    
    @classmethod
    def get_instance(cls) -> 'Config':
        """
        Get the singleton instance of Config.
        
        Returns:
            Config: Singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def get_chromosome_keys(cls) -> List[str]:
        """
        Get all chromosome keys from expected centroids.
        
        Returns:
            List[str]: Sorted list of chromosome keys
        """
        return sorted([key for key in cls.EXPECTED_CENTROIDS.keys() 
                      if key.startswith('Chrom')], 
                     key=lambda x: int(x.replace('Chrom', '')))
    
    @classmethod
    def get_ordered_labels(cls) -> List[str]:
        """
        Get ordered labels including all chromosomes.
        
        Returns:
            List[str]: List of labels in order
        """
        return ['Negative'] + cls.get_chromosome_keys() + ['Unknown']
    
    @classmethod
    def load_from_file(cls, filepath: str) -> bool:
        """
        Load settings from a configuration file.
        Supports both JSON format.
        
        Args:
            filepath: Path to the settings file
            
        Returns:
            bool: True if settings were loaded successfully
        """
        logger = logging.getLogger("ddQuint")
        
        try:
            # Initialize the singleton if not already done
            cls.get_instance()
            
            # Load JSON configuration
            if filepath.endswith('.json'):
                return cls._load_from_json(filepath)
            else:
                logger.error(f"Unsupported config file format: {filepath}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading settings from {filepath}: {e}")
            logger.debug("Error details:", exc_info=True)
            return False
    
    @classmethod
    def _load_from_json(cls, filepath: str) -> bool:
        """
        Load settings from a JSON file.
        
        Args:
            filepath: Path to the JSON file
            
        Returns:
            bool: True if settings were loaded successfully
        """
        logger = logging.getLogger("ddQuint")
        logger.debug(f"Loading configuration from JSON file: {filepath}")
        
        try:
            with open(filepath, 'r') as f:
                settings = json.load(f)
            
            # Update class attributes based on JSON
            for key, value in settings.items():
                if hasattr(cls, key):
                    old_value = getattr(cls, key)
                    setattr(cls, key, value)
                    logger.debug(f"Updated config: {key} = {value} (was: {old_value})")
                else:
                    logger.debug(f"Ignoring unknown config key: {key}")
            
            logger.debug(f"Successfully loaded configuration from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading JSON settings from {filepath}: {e}")
            logger.debug("Error details:", exc_info=True)
            return False
    
    @classmethod
    def save_to_file(cls, filepath: str) -> bool:
        """
        Save current settings to a JSON file.
        
        Args:
            filepath: Path to save the settings
            
        Returns:
            bool: True if settings were saved successfully
        """
        logger = logging.getLogger("ddQuint")
        logger.debug(f"Saving configuration to file: {filepath}")
        
        try:
            settings = cls.get_all_settings()
            
            with open(filepath, 'w') as f:
                json.dump(settings, f, indent=4)
            
            logger.info(f"Successfully saved configuration to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving settings to {filepath}: {e}")
            logger.debug("Error details:", exc_info=True)
            return False
    
    @classmethod
    def get_all_settings(cls) -> Dict[str, Any]:
        """
        Get all settings as a dictionary.
        
        Returns:
            dict: Dictionary of all settings
        """
        settings = {}
        
        # Add all class variables that don't start with underscore
        for key in dir(cls):
            if not key.startswith('_') and not callable(getattr(cls, key)):
                value = getattr(cls, key)
                # Only include serializable types
                if isinstance(value, (str, int, float, bool, list, dict, tuple)) or value is None:
                    settings[key] = value
        
        return settings
    
    @classmethod
    def debug(cls, message: str) -> None:
        """
        Print debug messages if debug mode is enabled.
        
        Args:
            message: The debug message to print
        """
        if cls.DEBUG_MODE:
            logger = logging.getLogger("ddQuint")
            logger.debug(message)
    
    @classmethod
    def get_hdbscan_params(cls) -> Dict[str, Any]:
        """
        Get HDBSCAN clustering parameters.
        
        Returns:
            dict: Dictionary of HDBSCAN parameters
        """
        return {
            'min_cluster_size': cls.HDBSCAN_MIN_CLUSTER_SIZE,
            'min_samples': cls.HDBSCAN_MIN_SAMPLES,
            'cluster_selection_epsilon': cls.HDBSCAN_EPSILON,
            'metric': cls.HDBSCAN_METRIC,
            'cluster_selection_method': cls.HDBSCAN_CLUSTER_SELECTION_METHOD,
            'core_dist_n_jobs': 1  # Use all available cores
        }
    
    @classmethod
    def get_target_tolerance(cls, scale_factor: float = 1.0) -> Dict[str, float]:
        """
        Get target tolerance values with scale factor applied.
        
        Args:
            scale_factor: Scale factor to apply to base tolerance
            
        Returns:
            dict: Dictionary of target names to tolerance values
        """
        # Ensure scale factor is within limits
        scale_factor = max(cls.SCALE_FACTOR_MIN, min(cls.SCALE_FACTOR_MAX, scale_factor))
        
        # Apply scale factor to base tolerance for all targets
        return {target: cls.BASE_TARGET_TOLERANCE * scale_factor for target in cls.EXPECTED_CENTROIDS.keys()}
    
    @classmethod
    def get_plot_dimensions(cls, for_composite: bool = False) -> tuple:
        """
        Get plot dimension settings.
        
        Args:
            for_composite: Whether to get dimensions for composite plot
            
        Returns:
            tuple: Figure size as (width, height)
        """
        if for_composite:
            return cls.COMPOSITE_PLOT_SIZE
        else:
            return cls.INDIVIDUAL_FIGURE_SIZE
    
    @classmethod
    def get_axis_limits(cls) -> Dict[str, tuple]:
        """
        Get axis limit settings.
        
        Returns:
            dict: Dictionary of axis limits
        """
        return {
            'x': (cls.X_AXIS_MIN, cls.X_AXIS_MAX),
            'y': (cls.Y_AXIS_MIN, cls.Y_AXIS_MAX)
        }
    
    @classmethod
    def get_grid_intervals(cls) -> Dict[str, int]:
        """
        Get grid interval settings.
        
        Returns:
            dict: Dictionary of grid intervals
        """
        return {
            'x': cls.X_GRID_INTERVAL,
            'y': cls.Y_GRID_INTERVAL
        }