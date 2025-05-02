"""
Core file processing module for ddQuint
Handles loading, processing, and organizing CSV files
"""

import os
import shutil
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from ddquint.utils.well_utils import extract_well_coordinate
from ddquint.core.clustering import analyze_droplets
from ddquint.visualization.well_plots import create_well_plot

def process_csv_file(file_path, graphs_dir, verbose=False):
    """
    Process a single CSV file and return the results.
    
    Args:
        file_path (str): Path to the CSV file
        graphs_dir (str): Directory to save graphs
        verbose (bool): Enable verbose output
        
    Returns:
        dict: Results dictionary or None if processing failed
    """
    if verbose:
        print(f"  Processing file: {os.path.basename(file_path)}")
    
    basename = os.path.basename(file_path)
    sample_name = os.path.splitext(basename)[0]
    well_coord = extract_well_coordinate(sample_name)
    
    if not well_coord:
        if verbose:
            print(f"  Warning: Could not extract well coordinate from {basename}")
        return None
    
    # Try to load the CSV file
    try:
        # Find the header row containing Ch1Amplitude
        header_row = find_header_row(file_path)
        if header_row is None:
            if verbose:
                print(f"  Error: Could not find header row in {basename}")
            return create_error_result(well_coord, basename, 
                                      "Could not find header row",
                                      graphs_dir)
        
        # Load the CSV data
        df = pd.read_csv(file_path, skiprows=header_row)
        
        # Check for required columns
        required_cols = ['Ch1Amplitude', 'Ch2Amplitude']
        if not all(col in df.columns for col in required_cols):
            if verbose:
                print(f"  Error: Required columns not found in {basename}")
            return create_error_result(well_coord, basename, 
                                      "Required columns not found",
                                      graphs_dir)
        
        # Filter rows with NaN values
        df_clean = df[required_cols].dropna()
        
        # Check if we have enough data points
        if len(df_clean) < 10:
            if verbose:
                print(f"  Error: Not enough data points in {basename}")
            return create_error_result(well_coord, basename, 
                                      f"Not enough data points: {len(df_clean)}",
                                      graphs_dir)
        
        # Analyze the droplets
        if verbose:
            print(f"  Analyzing droplets in {basename}")
        
        clustering_results = analyze_droplets(df_clean)
        
        # Create plot and save it
        plot_path = os.path.join(graphs_dir, f"{well_coord}.png")
        if verbose:
            print(f"  Creating plot for {basename}")
        
        create_well_plot(df_clean, clustering_results, well_coord, plot_path)
        
        # Return the results
        result = {
            'well': well_coord,
            'filename': basename,
            'has_outlier': clustering_results.get('has_outlier', False),
            'copy_numbers': clustering_results.get('copy_numbers', {}),
            'counts': clustering_results.get('counts', {}),
            'graph_path': plot_path
        }
        
        if verbose:
            print(f"  Successfully processed {basename}")
        
        return result
        
    except Exception as e:
        if verbose:
            print(f"  Error processing {basename}: {str(e)}")
        return create_error_result(well_coord, basename, str(e), graphs_dir)

def find_header_row(file_path):
    """Find the row containing column headers in a CSV file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as fh:
            for i, line in enumerate(fh):
                if ('Ch1Amplitude' in line or 'Ch1 Amplitude' in line) and \
                   ('Ch2Amplitude' in line or 'Ch2 Amplitude' in line):
                    return i
    except Exception:
        pass
    return None

def create_error_result(well_coord, filename, error_message, graphs_dir):
    """Create an error result dictionary with a simple error plot."""
    # Create a simple error plot
    fig = plt.figure(figsize=(6, 5))
    plt.text(0.5, 0.5, f"Error: {error_message}", 
             horizontalalignment='center', verticalalignment='center')
    plt.axis('off')
    
    # Save the plot
    if well_coord:
        save_path = os.path.join(graphs_dir, f"{well_coord}.png")
    else:
        save_path = os.path.join(graphs_dir, f"{os.path.splitext(filename)[0]}_error.png")
    
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    # Return an error result dictionary
    return {
        'well': well_coord,
        'filename': filename,
        'has_outlier': False,
        'copy_numbers': {},
        'counts': {},
        'graph_path': save_path,
        'error': error_message
    }

def process_directory(input_dir, output_dir=None, verbose=False):
    """
    Process all CSV files in the input directory.
    
    Args:
        input_dir (str): Directory containing CSV files
        output_dir (str): Directory to save output files (defaults to input_dir)
        verbose (bool): Enable verbose output
        
    Returns:
        list: List of result dictionaries
    """
    if output_dir is None:
        output_dir = input_dir
    
    print(f"\nStarting batch processing in directory: {input_dir}")
    
    # Create output directories
    graphs_dir = os.path.join(output_dir, "Graphs")
    raw_data_dir = os.path.join(output_dir, "Raw Data")
    
    print(f"Creating output directories:")
    print(f"  - Graphs directory: {graphs_dir}")
    os.makedirs(graphs_dir, exist_ok=True)
    print(f"  - Raw Data directory: {raw_data_dir}")
    os.makedirs(raw_data_dir, exist_ok=True)
    
    # Find all CSV files in the input directory
    print("Searching for CSV files...")
    try:
        csv_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.csv')]
    except Exception as e:
        print(f"Error listing directory contents: {str(e)}")
        return []
    
    if not csv_files:
        print(f"No CSV files found in {input_dir}")
        return []
    
    print(f"Found {len(csv_files)} CSV files to process.")
    
    # Process each CSV file
    results = []
    for i, csv_file in enumerate(csv_files, 1):
        print(f"Processing file {i}/{len(csv_files)}: {csv_file}")
        file_path = os.path.join(input_dir, csv_file)
        
        try:
            # Process the file
            result = process_csv_file(file_path, graphs_dir, verbose)
            if result:
                results.append(result)
            
            # Copy the processed file to Raw Data directory
            try:
                shutil.copy2(file_path, os.path.join(raw_data_dir, csv_file))
            except Exception as e:
                if verbose:
                    print(f"  Error copying file to Raw Data directory: {str(e)}")
        except Exception as e:
            print(f"  Error processing {csv_file}: {str(e)}")
            
            # Try to extract well coordinate for error reporting
            basename = os.path.basename(file_path)
            sample_name = os.path.splitext(basename)[0]
            well_coord = extract_well_coordinate(sample_name)
            
            # Add error result
            if well_coord:
                results.append({
                    'well': well_coord,
                    'filename': basename,
                    'has_outlier': False,
                    'copy_numbers': {},
                    'counts': {},
                    'graph_path': None,
                    'error': str(e)
                })
    
    print(f"\nFile processing complete. Processed {len(results)} files successfully.")
    
    # Move original files to Raw Data folder
    print("\nMoving original CSV files to Raw Data folder...")
    for csv_file in csv_files:
        file_path = os.path.join(input_dir, csv_file)
        if os.path.exists(file_path):  # Make sure it still exists
            try:
                shutil.move(file_path, os.path.join(raw_data_dir, csv_file))
            except Exception as e:
                if verbose:
                    print(f"  Error moving {csv_file}: {str(e)}")
    
    return results