#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core file processing module for ddQuint.

Contains functionality for:
1. CSV file loading with automatic header detection
2. Data validation and quality filtering
3. Single file and batch directory processing
4. Error handling and result organization

This module handles all file I/O operations and coordinates the
analysis pipeline for digital droplet PCR data files.
"""

import os
import pandas as pd
import logging

from ..utils import extract_well_coordinate
from ..core import analyze_droplets
from ..pipelines.non_mixing_4plex import analyze_non_mixing_4plex
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
        
        # Check if we have enough data points
        min_points = Config.MIN_POINTS_FOR_CLUSTERING
        if len(df_clean) < min_points:
            error_msg = f"Insufficient data points in {basename}: {len(df_clean)}"
            logger.debug(error_msg)
            return create_error_result(well_coord, basename, error_msg, graphs_dir, sample_names, 
                                     df_clean=df_clean, total_droplets=len(df_clean))
        
        # Analyze the droplets - this might fail at copy number step
        try:
            # Ensure colors reflect current mode (adds combination labels when non-mixing)
            Config.finalize_colors()
            # Switch pipeline based on fluorophore mixing flag
            if not Config.get_enable_fluorophore_mixing():
                clustering_results = analyze_non_mixing_4plex(df_clean)
            else:
                clustering_results = analyze_droplets(df_clean)
        except Exception as clustering_error:
            # Clustering failed - try to preserve any partial clustering data
            total_droplets = len(df_clean)
            
            # Check if we can extract any partial clustering results
            partial_results = _extract_partial_clustering_results(clustering_error, df_clean)
            
            # Create error result with preserved droplet data and partial clustering
            error_result = create_error_result(
                well_coord, basename, str(clustering_error), graphs_dir, 
                sample_names, df_clean=df_clean, total_droplets=total_droplets,
                partial_clustering=partial_results
            )
            
            # Log the specific error type for debugging
            if "concentration estimates" in str(clustering_error).lower():
                logger.debug(f"Copy number estimation failed for {well_coord}: {str(clustering_error)}")
            elif "no negative droplets" in str(clustering_error).lower():
                logger.debug(f"No negative droplets found in {well_coord}: {str(clustering_error)}")
            else:
                logger.debug(f"Clustering analysis failed for {well_coord}: {str(clustering_error)}")
            
            return error_result
        
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
        
        # Don't print copy number warnings to console unless in verbose/debug mode
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

def _extract_partial_clustering_results(clustering_error, df_clean):
    """
    Try to extract partial clustering results even when full analysis fails.
    
    Args:
        clustering_error: The exception that occurred during clustering
        df_clean: Clean droplet data
        
    Returns:
        Dictionary with any extractable clustering data
    """
    partial_results = {
        'df_filtered': None,
        'target_mapping': None,
        'counts': {},
        'copy_numbers': {},
        'copy_number_states': {}
    }
    
    try:
        # Try basic clustering without copy number calculation
        from ..core import analyze_droplets
        from ..config import Config
        import numpy as np
        from sklearn.preprocessing import StandardScaler
        from hdbscan import HDBSCAN
        
        config = Config.get_instance()
        
        # Attempt basic clustering
        X = df_clean[['Ch1Amplitude', 'Ch2Amplitude']].values
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        hdbscan_params = config.get_hdbscan_params()
        clusterer = HDBSCAN(**hdbscan_params)
        clusters = clusterer.fit_predict(X_scaled)
        
        # If clustering succeeded, create basic results
        df_copy = df_clean.copy()
        df_copy['cluster'] = clusters
        df_filtered = df_copy[df_copy['cluster'] != -1].copy()
        
        if not df_filtered.empty:
            # Try target assignment
            from ..core.clustering import _assign_targets_to_clusters
            target_mapping = _assign_targets_to_clusters(df_filtered, config)
            
            # Add target labels
            df_filtered.loc[:, 'TargetLabel'] = df_filtered['cluster'].map(target_mapping)
            
            # Calculate basic counts
            ordered_labels = config.get_ordered_labels()
            label_counts = {label: len(df_filtered[df_filtered['TargetLabel'] == label]) 
                           for label in ordered_labels}
            
            partial_results['df_filtered'] = df_filtered
            partial_results['target_mapping'] = target_mapping
            partial_results['counts'] = label_counts
            
            logger.debug(f"Extracted partial clustering results: {len(df_filtered)} clustered droplets")
        
    except Exception as e:
        logger.debug(f"Could not extract partial clustering results: {str(e)}")
    
    return partial_results


def create_error_result(well_coord, filename, error_message, graphs_dir, 
                                     sample_names=None, total_droplets=0, usable_droplets=0, 
                                     negative_droplets=0, df_clean=None, partial_clustering=None):
    """
    Create an error result dictionary with preserved droplet counts, raw data, and partial clustering.
    
    Args:
        well_coord: Well coordinate
        filename: Original filename
        error_message: Description of the error
        graphs_dir: Directory to save the error plot
        sample_names: Optional mapping for sample names
        total_droplets: Actual total droplets from data
        usable_droplets: Actual usable droplets (if available)
        negative_droplets: Actual negative droplets (if available)
        df_clean: Raw droplet data for visualization (if available)
        partial_clustering: Partial clustering results (if available)
        
    Returns:
        Dictionary with error result structure including actual droplet counts and partial results
    """
    try:
        # Create plot path
        if well_coord:
            save_path = os.path.join(graphs_dir, f"{well_coord}.png")
        else:
            save_path = os.path.join(graphs_dir, f"{os.path.splitext(filename)[0]}_error.png")
        
        # Create clustering results with error information and partial data
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
        
        # Add partial clustering results if available
        if partial_clustering:
            error_clustering_results.update({
                'df_filtered': partial_clustering.get('df_filtered'),
                'target_mapping': partial_clustering.get('target_mapping'),
                'counts': partial_clustering.get('counts', {}),
                'copy_numbers': partial_clustering.get('copy_numbers', {}),
                'copy_number_states': partial_clustering.get('copy_number_states', {})
            })
        
        # Get sample name if available
        template_name = None
        if sample_names and well_coord:
            template_name = sample_names.get(well_coord)
        
        # Use the unified plot creation system with raw data if available
        create_well_plot(df_clean, error_clustering_results, well_coord or filename, 
                        save_path, for_composite=False, sample_name=template_name)
        
        logger.debug(f"Created error plot: {save_path}")
        
    except Exception as e:
        logger.warning(f"Failed to create error plot: {str(e)}")
        save_path = None
    
    # Calculate positive droplets
    positive_droplets = total_droplets - negative_droplets if total_droplets > 0 else 0
    
    # Create base result
    result = {
        'well': well_coord,
        'filename': filename,
        'has_aneuploidy': False,
        'has_buffer_zone': False,
        'copy_numbers': {},
        'copy_number_states': {},
        'counts': {},
        'graph_path': save_path,
        'error': _get_error_message(error_message, filename),
        'total_droplets': total_droplets,    
        'usable_droplets': usable_droplets,    
        'negative_droplets': negative_droplets      
    }
    
    # Add partial clustering results if available
    if partial_clustering:
        result.update({
            'counts': partial_clustering.get('counts', {}),
            'copy_numbers': partial_clustering.get('copy_numbers', {}),
            'copy_number_states': partial_clustering.get('copy_number_states', {}),
            'df_filtered': partial_clustering.get('df_filtered'),
            'target_mapping': partial_clustering.get('target_mapping')
        })
    
    return result

def process_directory(input_dir, output_dir=None, sample_names=None, verbose=False):
    """
    Process all CSV files in the input directory.
    
    Performs batch processing of multiple CSV files and handles output directory structure.
    Original CSV files remain untouched in their original location.
    
    Args:
        input_dir: Directory containing CSV files to process
        output_dir: Directory to save output files (defaults to input_dir)
        sample_names: Optional mapping of well IDs to sample names
        verbose: Enable verbose output for debugging
        
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
    
    # Create output directories
    graphs_dir = os.path.join(output_dir, "Graphs")
    
    try:
        os.makedirs(graphs_dir, exist_ok=True)
        logger.debug(f"Created graphs directory: {graphs_dir}")
    except Exception as e:
        error_msg = f"Failed to create graphs directory in {output_dir}: {str(e)}"
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
                
        except Exception as e:
            error_msg = f"Error processing {csv_file}: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Error details: {str(e)}", exc_info=True)
            if verbose:
                print(f"  {error_msg}")
    
    logger.debug(f"Processed {processed_count} of {len(csv_files)} files successfully")
    if verbose:
        logger.info(f"Processed {processed_count} of {len(csv_files)} files successfully")
    
    return results

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
