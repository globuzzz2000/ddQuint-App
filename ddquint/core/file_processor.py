"""
Core file processing module for ddQuint
Handles loading, processing, and organizing CSV files
"""

import os
import shutil
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from ..utils.well_utils import extract_well_coordinate
from ..core.clustering import analyze_droplets
from ..visualization.well_plots import create_well_plot

def process_csv_file(file_path, graphs_dir, sample_names=None, verbose=False):
    """
    Process a single CSV file and return the results.
    
    Args:
        file_path (str): Path to the CSV file
        graphs_dir (str): Directory to save graphs
        sample_names (dict): Optional mapping of well IDs to sample names
        verbose (bool): Enable verbose output
        
    Returns:
        dict: Results dictionary or None if processing failed
    """
    basename = os.path.basename(file_path)
    sample_name = os.path.splitext(basename)[0]
    well_coord = extract_well_coordinate(sample_name)
    
    if not well_coord:
        return None
    
    # Try to load the CSV file
    try:
        # Find the header row containing Ch1Amplitude
        header_row = find_header_row(file_path)
        if header_row is None:
            return create_error_result(well_coord, basename, 
                                      "Could not find header row",
                                      graphs_dir)
        
        # Load the CSV data
        df = pd.read_csv(file_path, skiprows=header_row)
        
        # Check for required columns
        required_cols = ['Ch1Amplitude', 'Ch2Amplitude']
        if not all(col in df.columns for col in required_cols):
            return create_error_result(well_coord, basename, 
                                      "Required columns not found",
                                      graphs_dir)
        
        # Filter rows with NaN values
        df_clean = df[required_cols].dropna()
        
        # Check if we have enough data points
        if len(df_clean) < 10:
            return create_error_result(well_coord, basename, 
                                      f"Not enough data points: {len(df_clean)}",
                                      graphs_dir)
        
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

        
        # Return the results
        result = {
            'well': well_coord,
            'filename': basename,
            'has_aneuploidy': clustering_results.get('has_aneuploidy', False),
            'copy_numbers': clustering_results.get('copy_numbers', {}),
            'counts': clustering_results.get('counts', {}),
            'graph_path': standard_plot_path,
            'df_filtered': clustering_results.get('df_filtered'), 
            'target_mapping': clustering_results.get('target_mapping'), 
            'chrom3_reclustered': clustering_results.get('chrom3_reclustered', False)
        }
        
        # Add sample name if available
        if template_name:
            result['sample_name'] = template_name
            
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
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    else:
        save_path = os.path.join(graphs_dir, f"{os.path.splitext(filename)[0]}_error.png")
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    
    plt.close(fig)
    
    # Return an error result dictionary
    return {
        'well': well_coord,
        'filename': filename,
        'has_aneuploidy': False,
        'copy_numbers': {},
        'counts': {},
        'graph_path': save_path,
        'error': error_message
    }

def process_directory(input_dir, output_dir=None, sample_names=None, verbose=False):
    """
    Process all CSV files in the input directory.
    
    Args:
        input_dir (str): Directory containing CSV files
        output_dir (str): Directory to save output files (defaults to input_dir)
        sample_names (dict): Optional mapping of well IDs to sample names
        verbose (bool): Enable verbose output
        
    Returns:
        list: List of result dictionaries
    """
    from tqdm import tqdm  # Import tqdm for progress bar
    
    if output_dir is None:
        output_dir = input_dir
    
    # Create output directories
    graphs_dir = os.path.join(output_dir, "Graphs")
    raw_data_dir = os.path.join(output_dir, "Raw Data")
    
    os.makedirs(graphs_dir, exist_ok=True)
    os.makedirs(raw_data_dir, exist_ok=True)
    
    # Find all CSV files in the input directory
    try:
        csv_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.csv')]
    except Exception as e:
        if verbose:
            print(f"Error listing directory contents: {str(e)}")
        return []
    
    if not csv_files:
        print(f"No CSV files found in {input_dir}")
        return []
    
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
            try:
                shutil.copy2(file_path, os.path.join(raw_data_dir, csv_file))
            except Exception:
                pass
        except Exception as e:
            if verbose:
                print(f"  Error processing {csv_file}: {str(e)}")
    
    if verbose:
        print(f"Processed {processed_count} of {len(csv_files)} files successfully")
    
    # Move original files to Raw Data folder
    for csv_file in csv_files:
        file_path = os.path.join(input_dir, csv_file)
        if os.path.exists(file_path):  # Make sure it still exists
            try:
                shutil.move(file_path, os.path.join(raw_data_dir, csv_file))
            except Exception:
                pass
    
    return results