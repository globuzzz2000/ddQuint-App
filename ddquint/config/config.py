#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration module for the ddQuint pipeline with dynamic chromosome support and buffer zone detection.

This module provides comprehensive configuration management for:
1. Clustering parameters and algorithm settings
2. Expected centroid definitions for up to 10 chromosomes
3. Copy number calculation and classification thresholds
4. Visualization settings and color schemes
5. File management and template parsing options

The Config class implements a singleton pattern to ensure consistent
settings across all pipeline modules.
"""

import os
import json
import logging
from multiprocessing import cpu_count
from typing import Dict, List, Any

from ..config.exceptions import ConfigError

logger = logging.getLogger(__name__)

class Config:
    """
    Central configuration settings for the ddQuint pipeline with singleton pattern.
    
    This class provides configuration management for clustering parameters,
    visualization settings, copy number thresholds, and file management.
    Implements singleton pattern to ensure consistent settings across modules.
    
    Attributes:
        DEBUG_MODE: Enable debug logging mode
        EXPECTED_CENTROIDS: Target centroids for clustering
        HDBSCAN_MIN_CLUSTER_SIZE: Minimum cluster size for HDBSCAN
        
    Example:
        >>> config = Config.get_instance()
        >>> config.DEBUG_MODE = True
        >>> chroms = config.get_chromosome_keys()
    """
    
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
    # HDBSCAN clustering parameters (from working version)
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
        "Negative": [900, 700],
        "Chrom1":   [900, 2300],
        "Chrom2":   [1700, 2000],
        "Chrom3":   [2400, 1750],
        "Chrom4":   [2900, 1250],
        "Chrom5":   [3400, 700]
    }
    
    # Tolerance for matching clusters to targets
    BASE_TARGET_TOLERANCE = 500
    
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
    
    # Expected copy number values for each chromosome (baseline for calculations)
    EXPECTED_COPY_NUMBERS = {
        "Chrom1": 0.9688,
        "Chrom2": 1.0066,
        "Chrom3": 1.0300,
        "Chrom4": 0.9890,
        "Chrom5": 1.0056,
        "Chrom6": 1.00,
        "Chrom7": 1.00,
        "Chrom8": 1.00,
        "Chrom9": 1.00,
        "Chrom10": 1.00
    }
    
    # Buffer zone settings
    EUPLOID_TOLERANCE = 0.08  # ±0.08 from expected value for euploid range
    ANEUPLOIDY_TOLERANCE = 0.08  # ±0.08 from aneuploidy targets for aneuploidy range
    
    # Aneuploidy target copy numbers (relative to expected)
    ANEUPLOIDY_TARGETS = {
        "low": 0.75,   # Deletion target (0.75 - 1 + expected)
        "high": 1.25   # Duplication target (1.25 - 1 + expected)
    }
    
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
        "Chrom1":   "#f59a23",  # orange
        "Chrom2":   "#7ec638",  # green
        "Chrom3":   "#16d9ff",  # cyan
        "Chrom4":   "#f65352",  # red
        "Chrom5":   "#82218b",  # purple
        "Chrom6":   "#8c564b",  # brown
        "Chrom7":   "#e377c2",  # pink
        "Chrom8":   "#7f7f7f",  # gray
        "Chrom9":   "#bcbd22",  # olive
        "Chrom10":  "#9edae5",  # light cyan
        "Unknown":  "#c7c7c7"   # light gray
    }
    
    # Copy number state highlighting colors
    ANEUPLOIDY_FILL_COLOR = "#E6B8E6"  # Light purple (for definitive aneuploidies)
    ANEUPLOIDY_VALUE_FILL_COLOR = "#D070D0"  # Darker purple (for aneuploidy values)
    BUFFER_ZONE_FILL_COLOR = "#B0B0B0"  # Dark grey (for buffer zone samples - entire row)
    BUFFER_ZONE_VALUE_FILL_COLOR = "#808080"  # Darker grey (for buffer zone values - not used now)
    
    #############################################################################
    #                           File Management
    #############################################################################
    # Default output directories
    GRAPHS_DIR_NAME = "Graphs"
    RAW_DATA_DIR_NAME = "Raw Data"
    
    # File name patterns
    CSV_EXTENSION = '.csv'
    
    # Excel report settings
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
            List of chromosome keys sorted numerically
            
        Example:
            >>> config = Config.get_instance()
            >>> chroms = config.get_chromosome_keys()
            >>> chroms
            ['Chrom1', 'Chrom2', 'Chrom3']
        """
        return sorted([key for key in cls.EXPECTED_CENTROIDS.keys() 
                      if key.startswith('Chrom')], 
                     key=lambda x: int(x.replace('Chrom', '')))
    
    @classmethod
    def get_ordered_labels(cls) -> List[str]:
        """
        Get ordered labels including all chromosomes.
        
        Returns:
            List of labels in processing order
        """
        return ['Negative'] + cls.get_chromosome_keys() + ['Unknown']
    
    @classmethod
    def classify_copy_number_state(cls, chrom_name: str, copy_number: float) -> str:
        """
        Classify a copy number value into euploid, buffer zone, or aneuploidy.
        
        Uses chromosome-specific expected values and tolerance ranges to
        determine the classification state for copy number analysis.
        
        Args:
            chrom_name: Chromosome name (e.g., 'Chrom1')
            copy_number: Copy number value to classify
            
        Returns:
            Classification string: 'euploid', 'buffer_zone', or 'aneuploidy'
            
        Raises:
            ConfigError: If chromosome not found in configuration
            
        Example:
            >>> config = Config.get_instance()
            >>> state = config.classify_copy_number_state('Chrom1', 1.0)
            >>> state
            'euploid'
        """
        if chrom_name not in cls.EXPECTED_COPY_NUMBERS:
            error_msg = f"Unknown chromosome: {chrom_name}"
            logger.error(error_msg)
            raise ConfigError(error_msg, config_key="EXPECTED_COPY_NUMBERS")
        
        expected = cls.EXPECTED_COPY_NUMBERS.get(chrom_name, 1.0)
        
        # Define euploid range
        euploid_min = expected - cls.EUPLOID_TOLERANCE
        euploid_max = expected + cls.EUPLOID_TOLERANCE
        
        # Define aneuploidy target ranges
        deletion_target = expected + (cls.ANEUPLOIDY_TARGETS["low"] - 1.0)
        duplication_target = expected + (cls.ANEUPLOIDY_TARGETS["high"] - 1.0)
        
        deletion_min = deletion_target - cls.ANEUPLOIDY_TOLERANCE
        deletion_max = deletion_target + cls.ANEUPLOIDY_TOLERANCE
        duplication_min = duplication_target - cls.ANEUPLOIDY_TOLERANCE
        duplication_max = duplication_target + cls.ANEUPLOIDY_TOLERANCE
        
        # Check if in euploid range
        if euploid_min <= copy_number <= euploid_max:
            return 'euploid'
        
        # Check if in aneuploidy ranges
        if (deletion_min <= copy_number <= deletion_max or 
            duplication_min <= copy_number <= duplication_max):
            return 'aneuploidy'
        
        # Otherwise, it's in the buffer zone
        return 'buffer_zone'
    
    @classmethod
    def get_copy_number_ranges(cls, chrom_name: str) -> Dict[str, tuple]:
        """
        Get copy number ranges for a specific chromosome.
        
        Args:
            chrom_name: Chromosome name (e.g., 'Chrom1')
            
        Returns:
            Dictionary with ranges for each classification
            
        Raises:
            ConfigError: If chromosome not found in configuration
        """
        if chrom_name not in cls.EXPECTED_COPY_NUMBERS:
            error_msg = f"Unknown chromosome: {chrom_name}"
            logger.error(error_msg)
            raise ConfigError(error_msg, config_key="EXPECTED_COPY_NUMBERS")
        
        expected = cls.EXPECTED_COPY_NUMBERS.get(chrom_name, 1.0)
        
        # Calculate ranges
        euploid_range = (
            expected - cls.EUPLOID_TOLERANCE,
            expected + cls.EUPLOID_TOLERANCE
        )
        
        deletion_target = expected + (cls.ANEUPLOIDY_TARGETS["low"] - 1.0)
        duplication_target = expected + (cls.ANEUPLOIDY_TARGETS["high"] - 1.0)
        
        deletion_range = (
            deletion_target - cls.ANEUPLOIDY_TOLERANCE,
            deletion_target + cls.ANEUPLOIDY_TOLERANCE
        )
        
        duplication_range = (
            duplication_target - cls.ANEUPLOIDY_TOLERANCE,
            duplication_target + cls.ANEUPLOIDY_TOLERANCE
        )
        
        return {
            'euploid': euploid_range,
            'deletion': deletion_range,
            'duplication': duplication_range
        }
    
    @classmethod
    def load_from_file(cls, filepath: str) -> bool:
        """
        Load settings from a configuration file.
        
        Supports JSON format configuration files with validation
        and error handling for malformed or missing files.
        
        Args:
            filepath: Path to the configuration file
            
        Returns:
            True if settings were loaded successfully
            
        Raises:
            ConfigError: If configuration file is invalid or cannot be loaded
        """
        if not os.path.exists(filepath):
            error_msg = f"Configuration file not found: {filepath}"
            logger.error(error_msg)
            raise ConfigError(error_msg, config_key="filepath")
        
        try:
            # Initialize the singleton if not already done
            cls.get_instance()
            
            # Load JSON configuration
            if filepath.endswith('.json'):
                return cls._load_from_json(filepath)
            else:
                error_msg = f"Unsupported config file format: {filepath}"
                logger.error(error_msg)
                raise ConfigError(error_msg, config_key="file_format")
                
        except Exception as e:
            error_msg = f"Error loading settings from {filepath}: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Error details: {str(e)}", exc_info=True)
            raise ConfigError(error_msg) from e
    
    @classmethod
    def _load_from_json(cls, filepath: str) -> bool:
        """
        Load settings from a JSON file.
        
        Args:
            filepath: Path to the JSON file
            
        Returns:
            True if settings were loaded successfully
        """
        logger.debug(f"Loading configuration from JSON file: {filepath}")
        
        try:
            with open(filepath, 'r') as f:
                settings = json.load(f)
            
            # Update class attributes based on JSON
            for key, value in settings.items():
                if key.startswith('#'):  # Skip comment keys
                    continue
                    
                if hasattr(cls, key):
                    old_value = getattr(cls, key)
                    setattr(cls, key, value)
                    logger.debug(f"Updated config: {key} = {value} (was: {old_value})")
                else:
                    logger.debug(f"Ignoring unknown config key: {key}")
            
            logger.debug(f"Successfully loaded configuration from {filepath}")
            return True
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON format in {filepath}: {str(e)}"
            logger.error(error_msg)
            raise ConfigError(error_msg, config_key="json_format") from e
        except Exception as e:
            error_msg = f"Error loading JSON settings from {filepath}: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Error details: {str(e)}", exc_info=True)
            raise ConfigError(error_msg) from e
    
    @classmethod
    def save_to_file(cls, filepath: str) -> bool:
        """
        Save current settings to a JSON file.
        
        Args:
            filepath: Path to save the configuration file
            
        Returns:
            True if settings were saved successfully
            
        Raises:
            ConfigError: If file cannot be written
        """
        logger.debug(f"Saving configuration to file: {filepath}")
        
        try:
            settings = cls.get_all_settings()
            
            with open(filepath, 'w') as f:
                json.dump(settings, f, indent=4)
            
            logger.info(f"Successfully saved configuration to {filepath}")
            return True
            
        except Exception as e:
            error_msg = f"Error saving settings to {filepath}: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Error details: {str(e)}", exc_info=True)
            raise ConfigError(error_msg) from e
    
    @classmethod
    def get_all_settings(cls) -> Dict[str, Any]:
        """
        Get all settings as a dictionary.
        
        Returns:
            Dictionary of all serializable settings
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
    def get_hdbscan_params(cls) -> Dict[str, Any]:
        """
        Get HDBSCAN clustering parameters.
        
        Returns:
            Dictionary of HDBSCAN parameters ready for clustering
        """
        return {
            'min_cluster_size': cls.HDBSCAN_MIN_CLUSTER_SIZE,
            'min_samples': cls.HDBSCAN_MIN_SAMPLES,
            'cluster_selection_epsilon': cls.HDBSCAN_EPSILON,
            'metric': cls.HDBSCAN_METRIC,
            'cluster_selection_method': cls.HDBSCAN_CLUSTER_SELECTION_METHOD,
            'core_dist_n_jobs': 1  # Use single core for reproducibility
        }
    
    @classmethod
    def get_target_tolerance(cls, scale_factor: float = 1.0) -> Dict[str, float]:
        """
        Get target tolerance values with scale factor applied.
        
        Args:
            scale_factor: Scale factor to apply to base tolerance
            
        Returns:
            Dictionary of target names to tolerance values
        """
        # Ensure scale factor is within limits
        scale_factor = max(cls.SCALE_FACTOR_MIN, min(cls.SCALE_FACTOR_MAX, scale_factor))
        
        # Apply scale factor to base tolerance for all targets
        return {target: cls.BASE_TARGET_TOLERANCE * scale_factor 
                for target in cls.EXPECTED_CENTROIDS.keys()}
    
    @classmethod
    def get_plot_dimensions(cls, for_composite: bool = False) -> tuple:
        """
        Get plot dimension settings.
        
        Args:
            for_composite: Whether to get dimensions for composite plot
            
        Returns:
            Figure size as (width, height) tuple
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
            Dictionary of axis limits for x and y axes
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
            Dictionary of grid intervals for x and y axes
        """
        return {
            'x': cls.X_GRID_INTERVAL,
            'y': cls.Y_GRID_INTERVAL
        }