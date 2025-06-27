#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core file processing module for ddQuint.

Contains functionality for:
1. CSV file loading with automatic header detection
2. Data validation and quality filtering
3. Single file and batch directory processing
4. Error handling and result organization
5. File management with test mode support

This module handles all file I/O operations and coordinates the
analysis pipeline for digital droplet PCR data files.
"""

import os
import shutil
import pandas as pd
import logging

from ..utils import extract_well_coordinate
from ..core import analyze_droplets
from ..visualization import create_well_plot
from ..config import Config, FileProcessingError, WellProcessingError

logger = logging.getLogger(__name__)

def process_csv_file(file_path, graphs_dir, sample_names=None, verbose=False):
    """
    Process a single CSV file and return the results.
    
    Loads CSV data, validates required columns, performs clustering analysis,
    and generates visualization plots for a single ddPCR data file.
    
    Args:
        file_path: Path to the CSV file to process
        graphs_dir: Directory to save generated graphs
        sample_names: Optional mapping of well IDs to sample names
        verbose: Enable verbose output for debugging
        
    Returns:
        Dictionary with analysis results, or None if processing failed
        
    Raises:
        FileProcessingError: If CSV file cannot be read or parsed
        WellProcessingError: If well coordinate extraction fails
        
    Example:
        >>> result = process_csv_file('/path/to/A01.csv', '/graphs', {'A01': 'Sample1'})
        >>> result['well']
        'A01'
    """
    basename = os.path.basename(file_path)
    sample_name = os.path.splitext(basename)[0]
    
    try:
        well_coord = extract_well_coordinate(sample_name)
        if not well_coord:
            error_msg = f"Could not extract well coordinate from filename: {basename}"
            logger.error(error_msg)
            raise WellProcessingError(error_msg, well_id=sample_name)
        
        logger.debug(f"Processing well {well_coord} from file {basename}")
        
        # Try to load the CSV file
        header_row = find_header_row(file_path)
        if header_row is None:
            error_msg = f"Could not find header row in {basename}"
            logger.error(error_msg)
            return create_error_result(well_coord, basename, error_msg, graphs_dir, sample_names)
        
        # Load the CSV data
        df = pd.read_csv(file_path, skiprows=header_row)
        logger.debug(f"Loaded CSV with {len(df)} rows from {basename}")
        
        # Check for required columns
        required_cols = ['Ch1Amplitude', 'Ch2Amplitude']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            error_msg = f"Missing required columns in {basename}: {missing_cols}"
            logger.error(error_msg)
            return create_error_result(well_coord, basename, error_msg, graphs_dir, sample_names)
        
        # Filter rows with NaN values
        df_clean = df[required_cols].dropna()
        logger.debug(f"Filtered data: {len(df_clean)} droplets from {len(df)} total")
        
        # Check if we have enough data points - be more specific about the threshold
        min_points = Config.MIN_POINTS_FOR_CLUSTERING
        if len(df_clean) < min_points:
            error_msg = f"Insufficient data points in {basename}: {len(df_clean)}"
            logger.debug(error_msg)
            return create_error_result(well_coord, basename, error_msg, graphs_dir, sample_names)
        
        # Analyze the droplets
        clustering_results = analyze_droplets(df_clean)
        
        # Create the plot
        standard_plot_path = os.path.join(graphs_dir, f"{well_coord}.png")
        
        # Get the sample name from the template if available
        template_name = sample_names.get(well_coord) if sample_names else None
        
        # Create standard plot for individual viewing with sample name
        create_well_plot(df_clean, clustering_results, well_coord, 
                        standard_plot_path, for_composite=False, 
                        sample_name=template_name)
        
        # Return the analysis results with droplet metrics
        result = {
            'well': well_coord,
            'filename': basename,
            'has_aneuploidy': clustering_results.get('has_aneuploidy', False),
            'has_buffer_zone': clustering_results.get('has_buffer_zone', False),
            'copy_numbers': clustering_results.get('copy_numbers', {}),
            'copy_number_states': clustering_results.get('copy_number_states', {}),
            'counts': clustering_results.get('counts', {}),
            'graph_path': standard_plot_path,
            'df_filtered': clustering_results.get('df_filtered'), 
            'target_mapping': clustering_results.get('target_mapping'),
            'total_droplets': clustering_results.get('total_droplets', len(df_clean)),
            'usable_droplets': clustering_results.get('usable_droplets', 0),
            'negative_droplets': clustering_results.get('negative_droplets', 0)
        }
        
        # Add sample name if available
        if template_name:
            result['sample_name'] = template_name
            
        logger.debug(f"Successfully processed {well_coord}: aneuploidy={result['has_aneuploidy']}, buffer_zone={result['has_buffer_zone']}")
        logger.debug(f"Droplet metrics - Total: {result['total_droplets']}, Usable: {result['usable_droplets']}, Negative: {result['negative_droplets']}")
        return result
        
    except Exception as e:
        error_msg = f"Processing failed for {basename}: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        
        if verbose:
            print(f"  Error processing {basename}: {_get_error_message(str(e), basename)}")
        
        # Try to extract well coordinate for error result
        try:
            well_coord = extract_well_coordinate(sample_name)
        except:
            well_coord = None
            
        return create_error_result(well_coord, basename, str(e), graphs_dir, sample_names)

def find_header_row(file_path):
    """
    Find the row containing column headers in a CSV file.
    
    Searches for rows containing the required amplitude column headers
    to handle CSV files with metadata or comments before the data.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        Row number containing headers, or None if not found
        
    Raises:
        FileProcessingError: If file cannot be read
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as fh:
            for i, line in enumerate(fh):
                if ('Ch1Amplitude' in line or 'Ch1 Amplitude' in line) and \
                   ('Ch2Amplitude' in line or 'Ch2 Amplitude' in line):
                    logger.debug(f"Found header row at line {i} in {os.path.basename(file_path)}")
                    return i
    except Exception as e:
        error_msg = f"Error reading file to find headers: {file_path}"
        logger.error(error_msg)
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        raise FileProcessingError(error_msg, filename=os.path.basename(file_path)) from e
    return None

def create_error_result(well_coord, filename, error_message, graphs_dir, sample_names=None):
    """
    Create an error result dictionary with unified plot creation.
    
    Uses the same plot creation logic as normal plots but passes error information
    to create appropriate error visualization.
    
    Args:
        well_coord: Well coordinate (may be None if extraction failed)
        filename: Original filename that caused the error
        error_message: Description of the error that occurred
        graphs_dir: Directory to save the error plot
        sample_names: Optional mapping for sample names
        
    Returns:
        Dictionary with error result structure
    """
    try:
        # Create plot path
        if well_coord:
            save_path = os.path.join(graphs_dir, f"{well_coord}.png")
        else:
            save_path = os.path.join(graphs_dir, f"{os.path.splitext(filename)[0]}_error.png")
        
        # Create clustering results with error information
        error_clustering_results = {
            'error': error_message,
            'has_aneuploidy': False,
            'has_buffer_zone': False,
            'copy_numbers': {},
            'copy_number_states': {},
            'counts': {},
            'df_filtered': None,
            'target_mapping': None
        }
        
        # Get sample name if available
        template_name = None
        if sample_names and well_coord:
            template_name = sample_names.get(well_coord)
        
        # Use the unified plot creation system
        create_well_plot(None, error_clustering_results, well_coord or filename, 
                        save_path, for_composite=False, sample_name=template_name)
        
        logger.debug(f"Created error plot: {save_path}")
        
    except Exception as e:
        logger.warning(f"Failed to create error plot: {str(e)}")
        save_path = None
    
    # Return standardized error result
    return {
        'well': well_coord,
        'filename': filename,
        'has_aneuploidy': False,
        'has_buffer_zone': False,
        'copy_numbers': {},
        'copy_number_states': {},
        'counts': {},
        'graph_path': save_path,
        'error': _get_error_message(error_message, filename),
        'total_droplets': 0,
        'usable_droplets': 0,
        'negative_droplets': 0
    }

def process_directory(input_dir, output_dir=None, sample_names=None, verbose=False, test_mode=False):
    """
    Process all CSV files in the input directory.
    
    Performs batch processing of multiple CSV files, handles file organization,
    and manages output directory structure with optional test mode.
    
    Args:
        input_dir: Directory containing CSV files to process
        output_dir: Directory to save output files (defaults to input_dir)
        sample_names: Optional mapping of well IDs to sample names
        verbose: Enable verbose output for debugging
        test_mode: If True, copy files instead of moving them (for testing)
        
    Returns:
        List of result dictionaries from processed files
        
    Raises:
        FileProcessingError: If directory cannot be accessed or processed
        
    Example:
        >>> results = process_directory('/data/csv/', sample_names={'A01': 'Sample1'})
        >>> len(results)
        96
    """
    from tqdm import tqdm  # Import tqdm for progress bar
    
    if output_dir is None:
        output_dir = input_dir
    
    logger.debug(f"Processing directory: {input_dir}")
    logger.debug(f"Output directory: {output_dir}")
    logger.debug(f"Test mode: {test_mode}")
    
    # Create output directories
    graphs_dir = os.path.join(output_dir, "Graphs")
    raw_data_dir = os.path.join(output_dir, "Raw Data")
    
    try:
        os.makedirs(graphs_dir, exist_ok=True)
        os.makedirs(raw_data_dir, exist_ok=True)
        logger.debug(f"Created output directories: {graphs_dir}, {raw_data_dir}")
    except Exception as e:
        error_msg = f"Failed to create output directories in {output_dir}: {str(e)}"
        logger.error(error_msg)
        raise FileProcessingError(error_msg) from e
    
    # Find all CSV files in the input directory
    try:
        csv_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.csv')]
    except Exception as e:
        error_msg = f"Error listing directory contents: {input_dir}"
        logger.error(error_msg)
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        raise FileProcessingError(error_msg, filename=input_dir) from e
    
    if not csv_files:
        logger.warning(f"No CSV files found in {input_dir}")
        return []
    
    logger.debug(f"Found {len(csv_files)} CSV files to process")
    
    # Process each CSV file with progress bar
    results = []
    processed_count = 0
    
    # Use tqdm to create a progress bar
    for csv_file in tqdm(csv_files, desc="Processing files", unit="file"):
        file_path = os.path.join(input_dir, csv_file)
        
        try:
            # Process the file with sample names
            result = process_csv_file(file_path, graphs_dir, sample_names, verbose)
            if result:
                results.append(result)
                processed_count += 1
            
            # Copy the processed file to Raw Data directory
            _copy_file_to_raw_data(file_path, raw_data_dir, csv_file)
                
        except Exception as e:
            error_msg = f"Error processing {csv_file}: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Error details: {str(e)}", exc_info=True)
            if verbose:
                print(f"  {error_msg}")
    
    logger.debug(f"Processed {processed_count} of {len(csv_files)} files successfully")
    if verbose:
        logger.info(f"Processed {processed_count} of {len(csv_files)} files successfully")
    
    # Handle file movement based on test mode
    if test_mode:
        logger.debug(f"Test mode: Original files preserved in {input_dir}")
    else:
        # Move original files to Raw Data folder (normal behavior)
        _move_files_to_raw_data(input_dir, raw_data_dir, csv_files)
    
    return results

def _copy_file_to_raw_data(file_path, raw_data_dir, csv_file):
    """Copy a file to the Raw Data directory."""
    try:
        raw_data_path = os.path.join(raw_data_dir, csv_file)
        shutil.copy2(file_path, raw_data_path)
        logger.debug(f"Copied {csv_file} to Raw Data directory")
    except Exception as e:
        logger.warning(f"Failed to copy {csv_file} to Raw Data: {str(e)}")

def _move_files_to_raw_data(input_dir, raw_data_dir, csv_files):
    """Move original files to Raw Data directory in normal mode."""
    moved_count = 0
    for csv_file in csv_files:
        file_path = os.path.join(input_dir, csv_file)
        if os.path.exists(file_path):  # Make sure it still exists
            try:
                raw_data_path = os.path.join(raw_data_dir, csv_file)
                # Remove the copied file first if it exists to avoid conflicts
                if os.path.exists(raw_data_path):
                    os.remove(raw_data_path)
                # Move the original file
                shutil.move(file_path, raw_data_path)
                moved_count += 1
                logger.debug(f"Moved {csv_file} to Raw Data directory")
            except Exception as e:
                logger.warning(f"Failed to move {csv_file}: {str(e)}")
    
    logger.debug(f"Moved {moved_count} files to Raw Data directory")

def _get_error_message(error_message, filename):
    """
    Convert technical error messages to user-friendly messages.
    
    Args:
        error_message: Original technical error message
        filename: Name of the file that caused the error
        
    Returns:
        Clean, user-friendly error message
    """
    error_lower = error_message.lower()
    
    # Categorize common errors
    if "insufficient data points" in error_lower or "0" in error_message:
        return "No Data\nEmpty or insufficient\ndroplets in file"
    elif "missing required columns" in error_lower:
        return "Invalid Format\nMissing amplitude\ncolumns"
    elif "could not find header" in error_lower:
        return "Invalid Format\nNo valid headers\nfound"
    elif "could not extract well coordinate" in error_lower:
        return "Invalid Filename\nCannot determine\nwell position"
    elif "nan" in error_lower or "empty" in error_lower:
        return "No Data\nFile contains no\nvalid measurements"
    else:
        # Generic error for unexpected issues
        return "Processing Error\nUnable to analyze\nthis file"