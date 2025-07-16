#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration modules for ddQuint.

This package provides comprehensive configuration management including:
- Core configuration settings and singleton pattern
- Configuration display and formatting utilities  
- Template generation for custom configurations
- Custom exception classes for error handling

The configuration system supports JSON-based configuration files and
provides intelligent defaults for all pipeline parameters.
"""

from .config import Config
from .config_display import display_config
from .logging_config import setup_logging, cleanup_old_log_files
from .template_generator import generate_config_template
from .exceptions import (
    ddQuintError,
    ConfigError, 
    ClusteringError,
    FileProcessingError,
    WellProcessingError,
    CopyNumberError,
    VisualizationError,
    ReportGenerationError,
    TemplateError,
    raise_config_error,
    raise_clustering_error,
    raise_file_error,
    raise_well_error
)

__all__ = [
    # Core configuration
    "Config",
    "display_config", 
    "generate_config_template",
    "setup_logging",
    "cleanup_old_log_files",
    
    # Exception classes
    "ddQuintError",
    "ConfigError",
    "ClusteringError", 
    "FileProcessingError",
    "WellProcessingError",
    "CopyNumberError",
    "VisualizationError",
    "ReportGenerationError",
    "TemplateError",
    
    # Exception convenience functions
    "raise_config_error",
    "raise_clustering_error", 
    "raise_file_error",
    "raise_well_error"
]