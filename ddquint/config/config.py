#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration module for the ddQuint pipeline with standard deviation-based tolerances.

This module provides comprehensive configuration management for:
1. Clustering parameters and algorithm settings
2. Expected centroid definitions for up to 10 chromosomes
3. Standard deviation-based copy number classification with tolerance multiplier
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
    #                           Expected Centroids
    #############################################################################
    # Define expected centroids for targets (maximum 10 chromosomes)
    # Format: { "target_name": [Ch1Amplitude, Ch2Amplitude] }
    EXPECTED_CENTROIDS = {
        "Negative": [1000, 900],
        "Chrom1":   [1000, 2300],
        "Chrom2":   [1800, 2200],
        "Chrom3":   [2400, 1750],
        "Chrom4":   [3100, 1300],
        "Chrom5":   [3500, 900]
    }
    
    # Tolerance for matching clusters to targets
    BASE_TARGET_TOLERANCE = 750
    
    

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
    #                    Standard Deviation-Based Copy Number Settings
    #############################################################################
    # Copy number calculation parameters
    MIN_USABLE_DROPLETS = 3000
    COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD = 0.15  # 15% deviation threshold
    
    # Number of chromosomes to analyze (1-10)
    CHROMOSOME_COUNT = 5
    
    # Expected copy number values for each chromosome (baseline for calculations)
    EXPECTED_COPY_NUMBERS = {
        "Chrom1": 1.0,
        "Chrom2": 1.0,
        "Chrom3": 1.0,
        "Chrom4": 1.0,
        "Chrom5": 1.0
    }
    
    # Standard deviation for each chromosome (empirically determined)
    EXPECTED_STANDARD_DEVIATION = {
        "Chrom1": 0.03,
        "Chrom2": 0.03,
        "Chrom3": 0.03,
        "Chrom4": 0.03,
        "Chrom5": 0.03
    }
    
    # Tolerance multiplier for standard deviation-based classification
    TOLERANCE_MULTIPLIER = 3
    
    # Copy number multiplier - applied to all relative copy number results
    COPY_NUMBER_MULTIPLIER = 4
    
    # Copy number analysis control
    ENABLE_COPY_NUMBER_ANALYSIS = True  # Enable copy number analysis and buffer zone detection
    CLASSIFY_CNV_DEVIATIONS = True      # Enable copy number deviation classification
    
    # Target name customization
    TARGET_NAMES = {}                   # Custom names for targets (e.g., {"Target1": "BRCA1", "Target2": "TP53"})
    
    # Deviation targets (multiplicative factors for expected values)
    LOWER_DEVIATION_TARGET = 0.75  # Lower deviation target (expected * 0.75)
    UPPER_DEVIATION_TARGET = 1.25  # Upper deviation target (expected * 1.25)

    #############################################################################
    #                           Visualization Settings
    #############################################################################
    # Plot dimensions and settings
    COMPOSITE_FIGURE_SIZE = (16, 11)
    INDIVIDUAL_FIGURE_SIZE = (6, 5)
    COMPOSITE_PLOT_SIZE = (5, 5)
    
    # DPI settings for different plot types
    INDIVIDUAL_PLOT_DPI = 300      # High resolution for standalone plots
    PLACEHOLDER_PLOT_DPI = 150     # Lower resolution for placeholder plots
    
    # Axis limits
    X_AXIS_MIN = 0
    X_AXIS_MAX = 3000
    Y_AXIS_MIN = 0
    Y_AXIS_MAX = 5000
    
    # Grid settings
    X_GRID_INTERVAL = 500
    Y_GRID_INTERVAL = 1000
    
    # Color scheme for targets (up to 10 chromosomes)
    DEFAULT_COLOR_PALETTE = [
        "#f59a23", "#7ec638", "#16d9ff", "#f65352",
        "#82218b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    ]
    SPECIAL_COLOR_DEFAULTS = {
        "Negative": "#1f77b4",
        "Unknown":  "#c7c7c7",
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
    COMPOSITE_IMAGE_FILENAME = "Graph_Overview.png"
    CSV_EXTENSION = '.csv'        # File name patterns
    
    #############################################################################
    #                           Template Parsing
    #############################################################################
    # Template search parameters
    TEMPLATE_SEARCH_PARENT_LEVELS = 2  # How many parent directories to search up
    TEMPLATE_PATTERN = "{dir_name}.csv"  # Template file naming pattern
    
    #############################################################################
    #                           Well Management
    #############################################################################
    # 96-well plate layout
    PLATE_ROWS = list('ABCDEFGH')
    PLATE_COLS = [str(i) for i in range(1, 13)]
    WELL_FORMAT = "{row}{col:02d}"  # e.g., "A01"
    
    def __init__(self):
        """Initialize Config instance with default values."""
        logger.info("DEBUG: Config.__init__() called")
        self._well_context = None  # Current well context for parameter switching
        self._well_parameters = {}  # Well-specific parameter overrides
        self.finalize_colors()
    
    def __getattribute__(self, name):
        """
        Override attribute access to implement context-aware parameter access.
        
        For parameter attributes, use the context system to get well-specific values.
        This allows per-well parameter customization while maintaining backwards compatibility.
        """
        # List of parameters that should use context-aware access
        PARAMETER_ATTRS = {
            # HDBSCAN clustering parameters
            'HDBSCAN_MIN_CLUSTER_SIZE', 'HDBSCAN_MIN_SAMPLES', 'HDBSCAN_EPSILON',
            'HDBSCAN_METRIC', 'HDBSCAN_CLUSTER_SELECTION_METHOD', 'MIN_POINTS_FOR_CLUSTERING',
            # Plot/visualization parameters  
            'INDIVIDUAL_PLOT_DPI', 'PLACEHOLDER_PLOT_DPI',
            'X_AXIS_MIN', 'X_AXIS_MAX', 'Y_AXIS_MIN', 'Y_AXIS_MAX',
            'X_GRID_INTERVAL', 'Y_GRID_INTERVAL',
            'COMPOSITE_FIGURE_SIZE', 'INDIVIDUAL_FIGURE_SIZE', 'COMPOSITE_PLOT_SIZE',
            # Analysis parameters
            'BASE_TARGET_TOLERANCE',
            'TOLERANCE_MULTIPLIER', 'COPY_NUMBER_MULTIPLIER', 'EXPECTED_CENTROIDS', 'EXPECTED_COPY_NUMBERS', 
            'EXPECTED_STANDARD_DEVIATION', 'CHROMOSOME_COUNT', 'ENABLE_COPY_NUMBER_ANALYSIS', 'CLASSIFY_CNV_DEVIATIONS',
            'LOWER_DEVIATION_TARGET', 'UPPER_DEVIATION_TARGET', 'CNV_LOSS_RATIO', 'CNV_GAIN_RATIO', 'ANEUPLOIDY_TARGETS', 'TARGET_NAMES',
            # Additional processing parameters
            'MIN_USABLE_DROPLETS', 'COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD',
            'TARGET_COLORS'
        }
        
        # For parameter attributes, use context-aware access
        if name in PARAMETER_ATTRS:
            try:
                # Get the context-aware method
                context_method = object.__getattribute__(self, '_get_parameter_with_context')
                class_default = getattr(self.__class__, name, None)
                value = context_method(name, class_default)
                logger.debug(f"DEBUG __getattribute__: {name} = {value} (context-aware)")
                return value
            except AttributeError:
                # Fall back to class attribute if something goes wrong
                value = getattr(self.__class__, name)
                logger.debug(f"DEBUG __getattribute__: {name} = {value} (fallback)")
                return value
        
        # For all other attributes, use normal access
        return object.__getattribute__(self, name)
    
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
        Get all chromosome keys from configuration, prioritizing actual configured data over CHROMOSOME_COUNT.
        """
        # First, try to get chromosome keys from actual configured data
        chromosome_keys = set()
        
        # Check expected copy numbers
        try:
            cn_map = cls.get_expected_copy_numbers()
            if isinstance(cn_map, dict) and cn_map:
                chromosome_keys.update([k for k in cn_map.keys() if str(k).startswith('Chrom')])
        except Exception:
            pass
        
        # Check expected centroids
        try:
            centroids = cls.get_expected_centroids()
            if isinstance(centroids, dict) and centroids:
                chromosome_keys.update([k for k in centroids.keys() if str(k).startswith('Chrom')])
        except Exception:
            pass
        
        # Check expected standard deviations
        try:
            std_devs = cls.get_expected_std_dev()
            if isinstance(std_devs, dict) and std_devs:
                chromosome_keys.update([k for k in std_devs.keys() if str(k).startswith('Chrom')])
        except Exception:
            pass
        
        # If we found actual chromosome data, use it (sorted by number)
        if chromosome_keys:
            return sorted(chromosome_keys, key=lambda x: int(str(x).replace('Chrom', '')))
        
        # Fallback: use CHROMOSOME_COUNT parameter
        try:
            instance = cls.get_instance()
            chrom_count = getattr(instance, 'CHROMOSOME_COUNT', 5)  # Default to 5 if not set
            return [f'Chrom{i}' for i in range(1, chrom_count + 1)]
        except Exception:
            # Final fallback
            return ['Chrom1', 'Chrom2', 'Chrom3', 'Chrom4', 'Chrom5']
    
    @classmethod
    def get_ordered_labels(cls) -> List[str]:
        """
        Get ordered labels including all chromosomes.
        
        Returns:
            List of labels in processing order
        """
        return ['Negative'] + cls.get_chromosome_keys() + ['Unknown']
    
    @classmethod
    def get_target_labels(cls) -> List[str]:
        """
        Get target labels for display (Target1, Target2, etc.) instead of Chrom names.
        
        Returns:
            List of target labels for plotting
        """
        chrom_keys = cls.get_chromosome_keys()
        target_keys = []
        for chrom in chrom_keys:
            if chrom.startswith('Chrom'):
                target_num = chrom.replace('Chrom', '')
                target_keys.append(f'Target{target_num}')
            else:
                target_keys.append(chrom)  # Keep non-Chrom names as-is
        return target_keys
    
    @classmethod
    def get_ordered_target_labels(cls) -> List[str]:
        """
        Get ordered target labels for display purposes.
        
        Returns:
            List of target labels in processing order
        """
        return ['Negative'] + cls.get_target_labels() + ['Unknown']
    
    @classmethod
    def get_tolerance_for_chromosome(cls, chrom_name: str) -> float:
        """
        Get the tolerance value for a specific chromosome based on its standard deviation.
        """
        std_map = cls.get_expected_std_dev()
        if chrom_name not in std_map:
            error_msg = f"Unknown chromosome for standard deviation: {chrom_name}"
            logger.error(error_msg)
            raise ConfigError(error_msg, config_key="EXPECTED_STANDARD_DEVIATION")
        std_dev = std_map[chrom_name]
        # TOLERANCE_MULTIPLIER may be overridden on the instance via __getattribute__
        multiplier = getattr(cls.get_instance(), 'TOLERANCE_MULTIPLIER', cls.TOLERANCE_MULTIPLIER)
        tolerance = std_dev * multiplier
        logger.debug(f"{chrom_name}: std_dev={std_dev:.4f}, tol_mult={multiplier:.3f}, tolerance={tolerance:.4f}")
        return tolerance
    
    @classmethod
    def classify_copy_number_state(cls, chrom_name: str, copy_number: float) -> str:
        """
        Classify a copy number value using standard deviation-based tolerances.
        """
        exp_map = cls.get_expected_copy_numbers()
        if chrom_name not in exp_map:
            error_msg = f"Unknown chromosome: {chrom_name}"
            logger.error(error_msg)
            raise ConfigError(error_msg, config_key="EXPECTED_COPY_NUMBERS")
        expected = exp_map[chrom_name]
        tolerance = cls.get_tolerance_for_chromosome(chrom_name)
        targets = cls.get_aneuploidy_targets()
        deletion_target = expected * targets.get("low", 0.75)
        duplication_target = expected * targets.get("high", 1.25)

        # Define euploid range using chromosome-specific tolerance
        euploid_min = expected - tolerance
        euploid_max = expected + tolerance

        # Define aneuploidy target ranges using the same tolerance
        deletion_min = deletion_target - tolerance
        deletion_max = deletion_target + tolerance
        duplication_min = duplication_target - tolerance
        duplication_max = duplication_target + tolerance

        logger.debug(f"{chrom_name} classification ranges:")
        logger.debug(f"  Euploid: [{euploid_min:.4f}, {euploid_max:.4f}]")
        logger.debug(f"  Deletion: [{deletion_min:.4f}, {deletion_max:.4f}]")
        logger.debug(f"  Duplication: [{duplication_min:.4f}, {duplication_max:.4f}]")
        logger.debug(f"  Copy number: {copy_number:.4f}")

        # Check if in euploid range
        if euploid_min <= copy_number <= euploid_max:
            logger.debug(f"  -> euploid")
            return 'euploid'

        # Check if in aneuploidy ranges
        if (deletion_min <= copy_number <= deletion_max or 
            duplication_min <= copy_number <= duplication_max):
            logger.debug(f"  -> aneuploidy")
            return 'aneuploidy'

        # Otherwise, it's in the buffer zone
        logger.debug(f"  -> buffer_zone")
        return 'buffer_zone'
    
    @classmethod
    def get_copy_number_ranges(cls, chrom_name: str) -> Dict[str, tuple]:
        """
        Get copy number ranges for a specific chromosome using standard deviation-based tolerances.
        """
        exp_map = cls.get_expected_copy_numbers()
        if chrom_name not in exp_map:
            error_msg = f"Unknown chromosome: {chrom_name}"
            logger.error(error_msg)
            raise ConfigError(error_msg, config_key="EXPECTED_COPY_NUMBERS")
        expected = exp_map[chrom_name]
        tolerance = cls.get_tolerance_for_chromosome(chrom_name)
        targets = cls.get_aneuploidy_targets()
        deletion_target = expected * targets.get("low", 0.75)
        duplication_target = expected * targets.get("high", 1.25)

        # Calculate ranges using chromosome-specific tolerance
        euploid_range = (
            expected - tolerance,
            expected + tolerance
        )
        deletion_range = (
            deletion_target - tolerance,
            deletion_target + tolerance
        )
        duplication_range = (
            duplication_target - tolerance,
            duplication_target + tolerance
        )
        return {
            'euploid': euploid_range,
            'deletion': deletion_range,
            'duplication': duplication_range
        }
    
    @classmethod
    def get_plot_dpi(cls, plot_type: str = 'individual') -> int:
        """
        Get DPI setting for different plot types.
        
        Args:
            plot_type: Type of plot ('individual', 'composite', or 'placeholder')
            
        Returns:
            DPI value for the specified plot type
            
        Raises:
            ConfigError: If unknown plot type is specified
            
        Example:
            >>> config = Config.get_instance()
            >>> dpi = config.get_plot_dpi('composite')
            >>> dpi
            200
        """
        instance = cls.get_instance()
        dpi_mapping = {
            'individual': getattr(instance, 'INDIVIDUAL_PLOT_DPI', cls.INDIVIDUAL_PLOT_DPI),
            'placeholder': getattr(instance, 'PLACEHOLDER_PLOT_DPI', cls.PLACEHOLDER_PLOT_DPI)
        }
        
        if plot_type not in dpi_mapping:
            error_msg = f"Unknown plot type: {plot_type}. Valid types: {list(dpi_mapping.keys())}"
            logger.error(error_msg)
            raise ConfigError(error_msg, config_key="plot_type")
        
        return dpi_mapping[plot_type]
    
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
        Get HDBSCAN clustering parameters with well context support.
        
        Returns:
            Dictionary of HDBSCAN parameters ready for clustering
        """
        instance = cls.get_instance()
        logger.info(f"DEBUG get_hdbscan_params: instance id = {id(instance)}, well context = {instance._well_context}")
        
        result = {
            'min_cluster_size': instance._get_parameter_with_context('HDBSCAN_MIN_CLUSTER_SIZE', cls.HDBSCAN_MIN_CLUSTER_SIZE),
            'min_samples': instance._get_parameter_with_context('HDBSCAN_MIN_SAMPLES', cls.HDBSCAN_MIN_SAMPLES),
            'cluster_selection_epsilon': instance._get_parameter_with_context('HDBSCAN_EPSILON', cls.HDBSCAN_EPSILON),
            'metric': instance._get_parameter_with_context('HDBSCAN_METRIC', cls.HDBSCAN_METRIC),
            'cluster_selection_method': instance._get_parameter_with_context('HDBSCAN_CLUSTER_SELECTION_METHOD', cls.HDBSCAN_CLUSTER_SELECTION_METHOD),
            'core_dist_n_jobs': 1  # Use single core for reproducibility
        }
        logger.info(f"DEBUG get_hdbscan_params: returning {result}")
        return result
    
    @classmethod
    def get_expected_centroids(cls) -> Dict[str, List[float]]:
        """
        Get expected centroids with well context support.
        """
        instance = cls.get_instance()
        logger.debug(f"DEBUG get_expected_centroids: instance id = {id(instance)}, well context = {instance._well_context}")
        
        # Use context-aware parameter access
        expected_centroids = instance._get_parameter_with_context('EXPECTED_CENTROIDS', cls.EXPECTED_CENTROIDS)
        logger.debug(f"DEBUG get_expected_centroids: returning {expected_centroids}")
        return expected_centroids

    @classmethod
    def get_expected_copy_numbers(cls) -> Dict[str, float]:
        """Get expected copy numbers with well context support."""
        instance = cls.get_instance()
        return instance._get_parameter_with_context('EXPECTED_COPY_NUMBERS', cls.EXPECTED_COPY_NUMBERS)

    @classmethod
    def get_expected_std_dev(cls) -> Dict[str, float]:
        """Get expected standard deviation with well context support."""
        instance = cls.get_instance()
        return instance._get_parameter_with_context('EXPECTED_STANDARD_DEVIATION', cls.EXPECTED_STANDARD_DEVIATION)

    @classmethod
    def get_lower_deviation_target(cls) -> float:
        """Get lower deviation target with well context support."""
        instance = cls.get_instance()
        return instance._get_parameter_with_context('LOWER_DEVIATION_TARGET', cls.LOWER_DEVIATION_TARGET)
    
    @classmethod
    def get_upper_deviation_target(cls) -> float:
        """Get upper deviation target with well context support."""
        instance = cls.get_instance()
        return instance._get_parameter_with_context('UPPER_DEVIATION_TARGET', cls.UPPER_DEVIATION_TARGET)
    
    @classmethod
    def get_enable_copy_number_analysis(cls) -> bool:
        """Get copy number analysis enable flag with well context support."""
        instance = cls.get_instance()
        return instance._get_parameter_with_context('ENABLE_COPY_NUMBER_ANALYSIS', cls.ENABLE_COPY_NUMBER_ANALYSIS)
    
    @classmethod
    def get_classify_cnv_deviations(cls) -> bool:
        """Get CNV deviation classification flag with well context support."""
        instance = cls.get_instance()
        return instance._get_parameter_with_context('CLASSIFY_CNV_DEVIATIONS', cls.CLASSIFY_CNV_DEVIATIONS)
    
    @classmethod
    def get_cnv_loss_ratio(cls) -> float:
        """Get CNV loss ratio with well context support (legacy method)."""
        instance = cls.get_instance()
        # Use new deviation target for consistency
        return instance._get_parameter_with_context('LOWER_DEVIATION_TARGET', cls.LOWER_DEVIATION_TARGET)
    
    @classmethod
    def get_cnv_gain_ratio(cls) -> float:
        """Get CNV gain ratio with well context support (legacy method)."""
        instance = cls.get_instance()
        # Use new deviation target for consistency
        return instance._get_parameter_with_context('UPPER_DEVIATION_TARGET', cls.UPPER_DEVIATION_TARGET)
    
    
    @classmethod
    def get_copy_number_multiplier(cls) -> float:
        """Get copy number multiplier with well context support."""
        instance = cls.get_instance()
        return instance._get_parameter_with_context('COPY_NUMBER_MULTIPLIER', cls.COPY_NUMBER_MULTIPLIER)
    
    @classmethod
    def get_target_names(cls) -> Dict[str, str]:
        """Get target names mapping with well context support."""
        instance = cls.get_instance()
        result = instance._get_parameter_with_context('TARGET_NAMES', {})
        print(f"DEBUG: Config.get_target_names() returning: {result}")
        return result
    
    @classmethod
    def get_aneuploidy_targets(cls) -> Dict[str, float]:
        """Get aneuploidy targets with well context support (legacy method)."""
        instance = cls.get_instance()
        # Build from individual deviation targets for consistency
        return {
            'low': instance._get_parameter_with_context('LOWER_DEVIATION_TARGET', cls.LOWER_DEVIATION_TARGET),
            'high': instance._get_parameter_with_context('UPPER_DEVIATION_TARGET', cls.UPPER_DEVIATION_TARGET)
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
        # Apply scale factor directly (no limits)
        
        # Apply scale factor to base tolerance for all targets
        return {target: cls.BASE_TARGET_TOLERANCE * scale_factor 
                for target in cls.get_expected_centroids().keys()}
    
    @classmethod
    def get_plot_dimensions(cls, for_composite: bool = False) -> tuple:
        """
        Get plot dimension settings.
        
        Args:
            for_composite: Whether to get dimensions for composite plot
            
        Returns:
            Figure size as (width, height) tuple
        """
        instance = cls.get_instance()
        if for_composite:
            return getattr(instance, 'COMPOSITE_PLOT_SIZE', cls.COMPOSITE_PLOT_SIZE)
        else:
            return getattr(instance, 'INDIVIDUAL_FIGURE_SIZE', cls.INDIVIDUAL_FIGURE_SIZE)
    
    @classmethod
    def get_axis_limits(cls) -> Dict[str, tuple]:
        """
        Get axis limit settings.
        
        Returns:
            Dictionary of axis limits for x and y axes
        """
        instance = cls.get_instance()
        result = {
            'x': (getattr(instance, 'X_AXIS_MIN', cls.X_AXIS_MIN), 
                  getattr(instance, 'X_AXIS_MAX', cls.X_AXIS_MAX)),
            'y': (getattr(instance, 'Y_AXIS_MIN', cls.Y_AXIS_MIN), 
                  getattr(instance, 'Y_AXIS_MAX', cls.Y_AXIS_MAX))
        }
        logger.info(f"DEBUG get_axis_limits: instance X_AXIS_MAX = {getattr(instance, 'X_AXIS_MAX', 'NOT_SET')}, class X_AXIS_MAX = {cls.X_AXIS_MAX}")
        logger.info(f"DEBUG get_axis_limits: returning {result}")
        return result
    
    @classmethod
    def get_grid_intervals(cls) -> Dict[str, int]:
        """
        Get grid interval settings.
        
        Returns:
            Dictionary of grid intervals for x and y axes
        """
        instance = cls.get_instance()
        return {
            'x': getattr(instance, 'X_GRID_INTERVAL', cls.X_GRID_INTERVAL),
            'y': getattr(instance, 'Y_GRID_INTERVAL', cls.Y_GRID_INTERVAL)
        }

    @classmethod
    def load_user_parameters(cls):
        """
        Load user parameters from the parameter editor if they exist.
        
        This method is called automatically during configuration setup
        to apply any user-customized parameters.
        """
        try:
            from ..utils.parameter_editor import load_parameters_if_exist
            return load_parameters_if_exist(cls)
        except ImportError:
            logger.debug("Parameter editor module not available")
            return False
        except Exception as e:
            logger.debug(f"Could not load user parameters: {e}")
            return False

    # Target colors
    TARGET_COLORS: dict = {}

    @classmethod
    def _get_target_names(cls):
        """
        Return the current list of target names.
        Tries instance-aware EXPECTED_COPY_NUMBERS first, then EXPECTED_CENTROIDS.
        Always includes special names present in cls.SPECIAL_COLOR_DEFAULTS.
        """
        names = []
        try:
            # Use instance-aware accessors to get well-specific parameters
            copy_numbers = cls.get_expected_copy_numbers()
            if isinstance(copy_numbers, dict):
                names = list(copy_numbers.keys())
        except Exception:
            pass
        
        if not names:
            try:
                centroids = cls.get_expected_centroids()
                if isinstance(centroids, dict):
                    names = list(centroids.keys())
            except Exception:
                pass

        # ensure specials are present
        for s in getattr(cls, "SPECIAL_COLOR_DEFAULTS", {}).keys():
            if s not in names:
                names.append(s)

        return names

    @classmethod
    def _reconcile_target_colors(cls):
        """
        Assign colors consistently by order: Negative first, then Chrom1, Chrom2, etc.
        Colors are assigned from DEFAULT_COLOR_PALETTE in order.
        """
        names = cls._get_target_names()
        new = {}
        
        # Sort names to ensure consistent order: Negative first, then Chrom1, Chrom2, etc.
        def sort_key(name):
            if name == "Negative":
                return (0, name)
            elif name.startswith("Chrom") and name[5:].isdigit():
                return (1, int(name[5:]))
            elif name == "Unknown":
                return (999, name)  # Unknown always last
            else:
                return (500, name)  # Other names in the middle
        
        sorted_names = sorted(names, key=sort_key)
        
        # Assign colors with special cases for 'Negative' and 'Unknown'
        base_palette = list(getattr(cls, "DEFAULT_COLOR_PALETTE", []))
        logger.info(f"  Base palette: {base_palette}")
        
        # Start palette index at 0 for Chrom labels; we do NOT consume palette entries for specials
        palette_idx = 0
        
        # First, assign chrom colors in order
        for name in sorted_names:
            if name.startswith("Chrom") and name[5:].isdigit():
                color = base_palette[palette_idx % len(base_palette)] if base_palette else "#000000"
                new[name] = color
                logger.info(f"  {name} = {color} (palette index {palette_idx})")
                palette_idx += 1
        
        # Assign any other non-special names (excluding Negative/Unknown) using remaining palette
        for name in sorted_names:
            if name not in new and name not in ("Negative", "Unknown"):
                color = base_palette[palette_idx % len(base_palette)] if base_palette else "#000000"
                new[name] = color
                logger.info(f"  {name} = {color} (other, palette index {palette_idx})")
                palette_idx += 1
        
        # Finally, assign specials using configured defaults (do not consume palette)
        specials = getattr(cls, "SPECIAL_COLOR_DEFAULTS", {})
        if "Negative" in sorted_names:
            neg_color = specials.get("Negative", base_palette[0] if base_palette else "#000000")
            new["Negative"] = neg_color
            logger.info(f"  Negative = {neg_color} (special)")
        if "Unknown" in sorted_names:
            unk_color = specials.get("Unknown", "#c7c7c7")
            new["Unknown"] = unk_color
            logger.info(f"  Unknown = {unk_color} (special)")

        logger.info(f"  Final TARGET_COLORS: {new}")
        cls.TARGET_COLORS = new

    @classmethod
    def finalize_colors(cls):
        """
        Public method: call after editing targets (e.g., via parameter editor).
        """
        logger.info("DEBUG: finalize_colors() called")
        cls._reconcile_target_colors()
    
    # MARK: - Well Parameter Context Management
    
    def set_well_context(self, well_id: str, parameters: Dict[str, Any] = None):
        """
        Set the current well context with optional parameter overrides.
        
        Args:
            well_id: Well identifier (e.g., 'A01')
            parameters: Dictionary of parameter overrides for this well
        """
        self._well_context = well_id
        if parameters:
            self._well_parameters[well_id] = parameters.copy()
        logger.debug(f"Set well context: {well_id} with {len(parameters or {})} parameter overrides")
        
        # Regenerate TARGET_COLORS to include any new chromosomes from the well context
        self.finalize_colors()
    
    def clear_well_context(self):
        """Clear the current well context, reverting to global parameters."""
        old_context = self._well_context
        self._well_context = None
        logger.debug(f"Cleared well context (was: {old_context})")
    
    def get_current_well_context(self) -> str:
        """Get the current well context identifier."""
        return self._well_context
    
    def _get_parameter_with_context(self, param_name: str, default_value=None):
        """
        Get a parameter value considering the current well context.
        
        Args:
            param_name: Name of the parameter
            default_value: Default value if parameter not found
            
        Returns:
            Parameter value with well context considered
        """
        # If we have a well context and well-specific parameters for this well
        if (self._well_context and 
            self._well_context in self._well_parameters and 
            param_name in self._well_parameters[self._well_context]):
            
            value = self._well_parameters[self._well_context][param_name]
            logger.debug(f"Using well-specific {param_name} = {value} for {self._well_context}")
            return value
        
        # Debug: show what parameters ARE available for this well
        if self._well_context and self._well_context in self._well_parameters:
            available_params = list(self._well_parameters[self._well_context].keys())
            logger.debug(f"Well {self._well_context} has parameters: {available_params}, looking for {param_name}")
        elif self._well_context:
            logger.debug(f"Well {self._well_context} has no parameters in context")
        
        # Fall back to class default
        if hasattr(self.__class__, param_name):
            value = getattr(self.__class__, param_name)
            logger.debug(f"Using default {param_name} = {value}")
            return value
            
        return default_value
