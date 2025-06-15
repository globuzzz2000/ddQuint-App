#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom exceptions for the ddQuint pipeline.
"""

class ddQuintError(Exception):
    """Base exception class for all ddQuint-related errors."""
    pass

class ConfigError(ddQuintError):
    """Exception raised for configuration-related errors."""
    
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
    """Exception raised for clustering analysis failures."""
    
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
    """Exception raised for file processing errors."""
    
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
    """Exception raised for well-specific processing errors."""
    
    def __init__(self, message, well_id=None):
        super().__init__(message)
        self.well_id = well_id
    
    def __str__(self):
        base_msg = super().__str__()
        if self.well_id:
            return f"{base_msg} (well: {self.well_id})"
        return base_msg

class CopyNumberError(ddQuintError):
    """Exception raised for copy number calculation errors."""
    
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
    """Exception raised for visualization and plotting errors."""
    
    def __init__(self, message, plot_type=None, output_path=None):
        super().__init__(message)
        self.plot_type = plot_type
        self.output_path = output_path

class ReportGenerationError(ddQuintError):
    """Exception raised for report generation errors."""
    
    def __init__(self, message, report_type=None, output_path=None):
        super().__init__(message)
        self.report_type = report_type
        self.output_path = output_path

class TemplateError(ddQuintError):
    """Exception raised for template file processing errors."""
    
    def __init__(self, message, template_path=None):
        super().__init__(message)
        self.template_path = template_path
    
    def __str__(self):
        base_msg = super().__str__()
        if self.template_path:
            return f"{base_msg} (template: {self.template_path})"
        return base_msg

# Convenience functions for raising common exceptions
def raise_config_error(message, config_key=None, config_value=None):
    """Convenience function to raise ConfigError."""
    raise ConfigError(message, config_key=config_key, config_value=config_value)

def raise_clustering_error(message, well_id=None, data_points=None):
    """Convenience function to raise ClusteringError."""
    raise ClusteringError(message, well_id=well_id, data_points=data_points)

def raise_file_error(message, filename=None, line_number=None):
    """Convenience function to raise FileProcessingError."""
    raise FileProcessingError(message, filename=filename, line_number=line_number)

def raise_well_error(message, well_id=None):
    """Convenience function to raise WellProcessingError."""
    raise WellProcessingError(message, well_id=well_id)