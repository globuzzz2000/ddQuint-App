#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom exceptions for the ddQuint pipeline.

This module defines ddQuint-specific exception classes to provide
clear error reporting and enable granular error handling throughout
the pipeline.
"""


class ddQuintError(Exception):
    """
    Base exception class for all ddQuint-related errors.
    
    This serves as the parent class for all ddQuint-specific exceptions,
    allowing users to catch all ddQuint errors with a single except clause.
    """
    pass


class ConfigError(ddQuintError):
    """
    Exception raised for configuration-related errors.
    
    This includes invalid configuration parameters, missing required
    settings, or configuration file parsing errors.
    
    Attributes:
        config_key: The configuration key that caused the error (optional)
        config_value: The invalid configuration value (optional)
    """
    
    def __init__(self, message, config_key=None, config_value=None):
        super().__init__(message)
        self.config_key = config_key
        self.config_value = config_value
    
    def __str__(self):
        base_msg = super().__str__()
        if self.config_key:
            return f"{base_msg} (config key: {self.config_key})"
        return base_msg


class ClusteringError(ddQuintError):
    """
    Exception raised for clustering analysis failures.
    
    This includes insufficient data points, HDBSCAN failures, or
    target assignment problems.
    
    Attributes:
        well_id: The well identifier where clustering failed (optional)
        data_points: Number of data points available (optional)
    """
    
    def __init__(self, message, well_id=None, data_points=None):
        super().__init__(message)
        self.well_id = well_id
        self.data_points = data_points
    
    def __str__(self):
        base_msg = super().__str__()
        if self.well_id:
            return f"{base_msg} (well: {self.well_id})"
        return base_msg


class FileProcessingError(ddQuintError):
    """
    Exception raised for file processing errors.
    
    This includes CSV file reading errors, header detection failures,
    or invalid file formats.
    
    Attributes:
        filename: The file that caused the error (optional)
        line_number: The line number where the error occurred (optional)
    """
    
    def __init__(self, message, filename=None, line_number=None):
        super().__init__(message)
        self.filename = filename
        self.line_number = line_number
    
    def __str__(self):
        base_msg = super().__str__()
        details = []
        if self.filename:
            details.append(f"file: {self.filename}")
        if self.line_number:
            details.append(f"line: {self.line_number}")
        
        if details:
            return f"{base_msg} ({', '.join(details)})"
        return base_msg


class WellProcessingError(ddQuintError):
    """
    Exception raised for well-specific processing errors.
    
    This includes invalid well coordinates, missing well data,
    or well-specific analysis failures.
    
    Attributes:
        well_id: The well identifier that caused the error
    """
    
    def __init__(self, message, well_id=None):
        super().__init__(message)
        self.well_id = well_id
    
    def __str__(self):
        base_msg = super().__str__()
        if self.well_id:
            return f"{base_msg} (well: {self.well_id})"
        return base_msg


class CopyNumberError(ddQuintError):
    """
    Exception raised for copy number calculation errors.
    
    This includes normalization failures, invalid copy number values,
    or chromosome classification errors.
    
    Attributes:
        chromosome: The chromosome that caused the error (optional)
        copy_number: The problematic copy number value (optional)
    """
    
    def __init__(self, message, chromosome=None, copy_number=None):
        super().__init__(message)
        self.chromosome = chromosome
        self.copy_number = copy_number
    
    def __str__(self):
        base_msg = super().__str__()
        details = []
        if self.chromosome:
            details.append(f"chromosome: {self.chromosome}")
        if self.copy_number is not None:
            details.append(f"copy_number: {self.copy_number:.3f}")
        
        if details:
            return f"{base_msg} ({', '.join(details)})"
        return base_msg


class VisualizationError(ddQuintError):
    """
    Exception raised for visualization and plotting errors.
    
    This includes plot generation failures, image saving errors,
    or visualization configuration problems.
    
    Attributes:
        plot_type: The type of plot that failed (optional)
        output_path: The intended output path (optional)
    """
    
    def __init__(self, message, plot_type=None, output_path=None):
        super().__init__(message)
        self.plot_type = plot_type
        self.output_path = output_path
    
    def __str__(self):
        base_msg = super().__str__()
        details = []
        if self.plot_type:
            details.append(f"plot_type: {self.plot_type}")
        if self.output_path:
            details.append(f"output_path: {self.output_path}")
        
        if details:
            return f"{base_msg} ({', '.join(details)})"
        return base_msg


class ReportGenerationError(ddQuintError):
    """
    Exception raised for report generation errors.
    
    This includes Excel file creation failures, template processing errors,
    or report formatting problems.
    
    Attributes:
        report_type: The type of report that failed (optional)
        output_path: The intended output path (optional)
    """
    
    def __init__(self, message, report_type=None, output_path=None):
        super().__init__(message)
        self.report_type = report_type
        self.output_path = output_path
    
    def __str__(self):
        base_msg = super().__str__()
        details = []
        if self.report_type:
            details.append(f"report_type: {self.report_type}")
        if self.output_path:
            details.append(f"output_path: {self.output_path}")
        
        if details:
            return f"{base_msg} ({', '.join(details)})"
        return base_msg


class TemplateError(ddQuintError):
    """
    Exception raised for template file processing errors.
    
    This includes template file not found, parsing errors,
    or invalid template format.
    
    Attributes:
        template_path: The template file that caused the error (optional)
    """
    
    def __init__(self, message, template_path=None):
        super().__init__(message)
        self.template_path = template_path
    
    def __str__(self):
        base_msg = super().__str__()
        if self.template_path:
            return f"{base_msg} (template: {self.template_path})"
        return base_msg


# Convenience functions for common error scenarios
def raise_config_error(message, config_key=None, config_value=None):
    """
    Convenience function to raise a ConfigError with consistent formatting.
    
    Args:
        message: Error message
        config_key: Configuration key that caused the error
        config_value: Invalid configuration value
        
    Raises:
        ConfigError: Always raises this exception
    """
    raise ConfigError(message, config_key=config_key, config_value=config_value)


def raise_clustering_error(message, well_id=None, data_points=None):
    """
    Convenience function to raise a ClusteringError with consistent formatting.
    
    Args:
        message: Error message
        well_id: Well identifier where clustering failed
        data_points: Number of data points available
        
    Raises:
        ClusteringError: Always raises this exception
    """
    raise ClusteringError(message, well_id=well_id, data_points=data_points)


def raise_file_error(message, filename=None, line_number=None):
    """
    Convenience function to raise a FileProcessingError with consistent formatting.
    
    Args:
        message: Error message
        filename: File that caused the error
        line_number: Line number where error occurred
        
    Raises:
        FileProcessingError: Always raises this exception
    """
    raise FileProcessingError(message, filename=filename, line_number=line_number)


def raise_well_error(message, well_id=None):
    """
    Convenience function to raise a WellProcessingError with consistent formatting.
    
    Args:
        message: Error message
        well_id: Well identifier that caused the error
        
    Raises:
        WellProcessingError: Always raises this exception
    """
    raise WellProcessingError(message, well_id=well_id)