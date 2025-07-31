#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plate plot visualization module for ddQuint with config integration and buffer zone support.

Creates composite plate images showing all 96 wells with individual scatter plots
and appropriate highlighting for aneuploidies and buffer zones. Integrates with
existing clustering results to avoid recomputation.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import pandas as pd
import logging
from matplotlib.ticker import MultipleLocator
from tqdm import tqdm

from ..config import Config, VisualizationError
from ..visualization.well_plots import create_well_plot

logger = logging.getLogger(__name__)


def create_composite_image(results, output_path):
    """
    Create a composite image using existing clustering results without re-running analysis.
    
    Args:
        results (list): List of result dictionaries with clustering data
        output_path (str): Path to save the composite image
        
    Returns:
        str: Path to the saved composite image
        
    Raises:
        VisualizationError: If composite image creation fails
        ValueError: If results data is invalid
    """
    config = Config.get_instance()
    
    if not results:
        error_msg = "No results provided for composite image creation"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.debug(f"Creating composite image for {len(results)} wells")
    logger.debug(f"Output path: {output_path}")
    
    # Keep track of temporary files
    temp_files = []
    
    try:
        # Get plate layout from config
        row_labels = config.PLATE_ROWS
        col_labels = config.PLATE_COLS
        
        # Create single template for empty wells (optimization)
        empty_template_path = _create_empty_well_template(output_path, config, temp_files)
        
        # Generate optimized images for each well (including error wells)
        _generate_well_images(results, output_path, temp_files)
        
        # Create the composite figure
        logger.info("Generating composite figure...") 
        _create_composite_figure(results, output_path, row_labels, col_labels, config, empty_template_path)
        
        logger.debug(f"Composite image saved to: {output_path}")
        return output_path
        
    except Exception as e:
        error_msg = f"Error creating composite image: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        raise VisualizationError(error_msg) from e
        
    finally:
        # Clean up temporary files
        _cleanup_temp_files(temp_files, results)


def _create_empty_well_template(output_path, config, temp_files):
    """
    Create a single template image for all empty wells (optimization).
    
    Args:
        output_path: Main output path 
        config: Configuration instance
        temp_files: List to track temp files for cleanup
        
    Returns:
        str: Path to the empty well template image
    """
    try:
        # Import the placeholder function from well_plots
        from ..visualization.well_plots import create_placeholder_plot
        
        output_dir = os.path.dirname(output_path)
        graphs_dir = os.path.join(output_dir, config.GRAPHS_DIR_NAME)
        os.makedirs(graphs_dir, exist_ok=True)
        
        # Create single template for all empty wells
        template_path = os.path.join(graphs_dir, "_empty_template.png")
        create_placeholder_plot("", template_path, for_composite=True)
        
        # Track the template file for cleanup
        temp_files.append(template_path)
        
        logger.debug("Created empty well template for reuse")
        return template_path
        
    except Exception as e:
        logger.debug(f"Error creating empty well template: {e}")
        return None


def _generate_well_images(results, output_path, temp_files):
    """Generate optimized images for each well with progress bar (including error wells)."""
    config = Config.get_instance()
    
    for result in tqdm(results, desc="Creating Graphs", unit="well"):
        if not result.get('well'):
            continue
            
        # Create optimized plot for ALL wells (including errors)
        temp_path = _create_temp_well_plot(result, output_path, config, temp_files)
        if temp_path:
            result['temp_graph_path'] = temp_path


def _create_temp_well_plot(result, output_path, config, temp_files):
    """Create temporary well plot for composite image (handles all well types including errors with raw data)."""
    try:
        output_dir = os.path.dirname(output_path)
        graphs_dir = os.path.join(output_dir, config.GRAPHS_DIR_NAME)
        os.makedirs(graphs_dir, exist_ok=True)
        
        # Create temp file in the Graphs directory
        temp_path = os.path.join(graphs_dir, f"{result['well']}_temp.png")
        
        # Get the raw data if available
        df_raw = _get_raw_data_for_result(result, output_path)
        
        # Use existing clustering results
        clustering_results = _extract_clustering_results(result)
        
        # Create the plot using unified system (handles all types consistently)
        create_well_plot(df_raw, clustering_results, result['well'], 
                         temp_path, for_composite=True, add_copy_numbers=True)
        
        # Track the temporary file
        temp_files.append(temp_path)
        return temp_path
        
    except Exception as e:
        logger.debug(f"Error creating temp plot for well {result.get('well')}: {e}")
        return None


def _get_raw_data_for_result(result, output_path):
    """
    Get raw data for a result, attempting to reload from CSV if not available.
    
    Args:
        result: Result dictionary
        output_path: Output path to help locate source files
        
    Returns:
        DataFrame with raw data or None if not available
    """
    # Always try to reload the ORIGINAL raw data from the CSV file for composite plots
    # This ensures we get ALL droplets (clustered + unclustered) for visualization
    filename = result.get('filename')
    well_id = result.get('well')
    
    if filename and well_id:
        try:
            # Try to find the source CSV file
            # Look in the parent directory of the output path
            output_dir = os.path.dirname(output_path)
            possible_paths = [
                os.path.join(output_dir, filename),  # Same directory as output
                os.path.join(os.path.dirname(output_dir), filename),  # Parent directory
            ]
            
            for csv_path in possible_paths:
                if os.path.exists(csv_path):
                    logger.debug(f"Attempting to reload raw data from {csv_path}")
                    df_raw = _load_csv_data(csv_path)
                    if df_raw is not None and not df_raw.empty:
                        logger.debug(f"Successfully loaded {len(df_raw)} raw droplets for {well_id}")
                        return df_raw
                    break
            
        except Exception as e:
            logger.debug(f"Error reloading raw data for well {well_id}: {e}")
    
    # Fallback: If we can't reload from CSV, use filtered data (better than nothing)
    df_filtered = result.get('df_filtered')
    if df_filtered is not None and not df_filtered.empty:
        logger.debug(f"Using filtered data as fallback for {well_id}")
        return df_filtered
    
    return None


def _load_csv_data(csv_path):
    """
    Load CSV data with header detection.
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        DataFrame with droplet data or None if failed
    """
    try:
        # Find header row (same logic as in file_processor)
        header_row = None
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as fh:
            for i, line in enumerate(fh):
                if ('Ch1Amplitude' in line or 'Ch1 Amplitude' in line) and \
                   ('Ch2Amplitude' in line or 'Ch2 Amplitude' in line):
                    header_row = i
                    break
        
        if header_row is None:
            return None
        
        # Load the CSV data
        df = pd.read_csv(csv_path, skiprows=header_row)
        
        # Check for required columns
        required_cols = ['Ch1Amplitude', 'Ch2Amplitude']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            return None
        
        # Filter rows with NaN values
        df_clean = df[required_cols].dropna()
        return df_clean
        
    except Exception as e:
        logger.debug(f"Error loading CSV data from {csv_path}: {e}")
        return None


def _extract_clustering_results(result):
    """Extract clustering results from result dictionary."""
    return {
        'df_filtered': result.get('df_filtered'),
        'target_mapping': result.get('target_mapping'),
        'counts': result.get('counts', {}),
        'copy_numbers': result.get('copy_numbers', {}),
        'copy_number_states': result.get('copy_number_states', {}),
        'has_aneuploidy': result.get('has_aneuploidy', False),
        'has_buffer_zone': result.get('has_buffer_zone', False),
        'chrom3_reclustered': result.get('chrom3_reclustered', False),
        'error': result.get('error')  # Include error for unified handling
    }


def _create_composite_figure(results, output_path, row_labels, col_labels, config, empty_template_path):
    """Create the main composite figure."""
    # Create figure with configured size
    fig_size = config.COMPOSITE_FIGURE_SIZE
    fig = plt.figure(figsize=fig_size)
    logger.debug(f"Creating composite figure with size: {fig_size}")
    
    # Create GridSpec with spacing
    gs = gridspec.GridSpec(8, 12, figure=fig, wspace=0.02, hspace=0.02)
    
    # Create well results mapping
    well_results = {r['well']: r for r in results if r.get('well') is not None}
    
    # Ensure proper margins
    plt.subplots_adjust(left=0.04, right=0.96, top=0.96, bottom=0.04)
    
    # Create subplot for each well position
    _create_well_subplots(fig, gs, row_labels, col_labels, well_results, config, empty_template_path)
    
    # Add row and column labels
    _add_plate_labels(fig, row_labels, col_labels)
    
    # Save the composite image
    fig.savefig(output_path, dpi=400, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)


def _create_well_subplots(fig, gs, row_labels, col_labels, well_results, config, empty_template_path):
    """Create individual subplots for each well position."""
    for i, row in enumerate(row_labels):
        for j, col_num in enumerate(range(1, int(col_labels[-1]) + 1)):
            col = str(col_num)
            well = config.WELL_FORMAT.format(row=row, col=int(col))
            
            # Add subplot at this position
            ax = fig.add_subplot(gs[i, j])
            ax.set_facecolor('#f5f5f5')  # Light gray background
            
            if well in well_results:
                _populate_data_well(ax, well, well_results[well], config)
            else:
                _populate_empty_well_optimized(ax, well, empty_template_path)
            
            # Keep axis visibility for all plots
            ax.set_xticks([])
            ax.set_yticks([])


def _populate_empty_well_optimized(ax, well, empty_template_path):
    """
    Populate empty well using pre-generated template (optimization).
    
    Args:
        ax: Matplotlib axes object
        well: Well identifier
        empty_template_path: Path to pre-generated empty well template
    """
    if empty_template_path and os.path.exists(empty_template_path):
        try:
            # Use the pre-generated template
            img = plt.imread(empty_template_path)
            ax.imshow(img)
            return
        except Exception as e:
            logger.debug(f"Error using empty template for well {well}: {e}")


def _populate_data_well(ax, well, result, config):
    """Populate subplot for a well with data."""
    # Use temp graph path if available, otherwise fall back to original
    graph_path = result.get('temp_graph_path', result.get('graph_path'))
    
    if graph_path and os.path.exists(graph_path):
        try:
            # Read and display the individual well image
            img = plt.imread(graph_path)
            ax.imshow(img)
            
            # Add title
            sample_name = result.get('sample_name')
            title = sample_name if sample_name else well
            ax.set_title(title, fontsize=6, pad=2)
            
            # Apply colored borders based on copy number state
            _apply_well_border(ax, result, well)
            
        except Exception as e:
            logger.debug(f"Error displaying image for well {well}: {e}")
            ax.text(0.5, 0.5, "Image Error", 
                    horizontalalignment='center', verticalalignment='center', 
                    transform=ax.transAxes, fontsize=8, color='red')
    else:
        ax.text(0.5, 0.5, "No Image", 
                horizontalalignment='center', verticalalignment='center', 
                transform=ax.transAxes, fontsize=8)


def _add_plate_buffer_zone_overlay(ax):
    """
    Add buffer zone overlay for plate plots only (center overlay for composite view).
    
    Args:
        ax: Matplotlib axes object
    """
    ax.text(0.5, 0.5, "Buffer Zone", 
            horizontalalignment='center', verticalalignment='center',
            transform=ax.transAxes, fontsize=5, color='black',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgrey', alpha=0.8))
    
    logger.debug("Added buffer zone overlay to plate plot")


def _apply_well_border(ax, result, well):
    """Apply colored border based on well status."""

    if result.get('has_aneuploidy', False) and not result.get('has_buffer_zone', False):
        # Only apply special border for aneuploidy if it's NOT a buffer zone
        border_color = '#E6B8E6'  # Pink border for aneuploidy
        border_width = 2
        logger.debug(f"Applied aneuploidy border (pink) to well {well}")
    else:
        # Standard grey border for all other cases (including buffer zones)
        border_color = '#B0B0B0'  # Light grey border for normal wells
        border_width = 1
        logger.debug(f"Applied standard border (light grey) to well {well}")
    
    # Apply the border
    for spine in ax.spines.values():
        spine.set_edgecolor(border_color)
        spine.set_color(border_color)
        spine.set_linewidth(border_width)
        spine.set_visible(True)


def _add_plate_labels(fig, row_labels, col_labels):
    """Add row and column labels to the plate."""
    # Add row labels (A-H) with proper alignment
    for i, row in enumerate(row_labels):
        ax = fig.axes[i * 12]  # Get the first plot in this row
        y_center = (ax.get_position().y0 + ax.get_position().y1) / 2
        fig.text(0.02, y_center, row, ha='center', va='center', fontsize=12, weight='bold')
    
    # Add column labels (1-12) with proper alignment
    for j, col in enumerate(col_labels):
        ax = fig.axes[j]  # Get the plot in the first row for this column
        x_center = (ax.get_position().x0 + ax.get_position().x1) / 2
        fig.text(x_center, 0.98, col, ha='center', va='center', fontsize=12, weight='bold')


def _cleanup_temp_files(temp_files, results):
    """Clean up temporary files and references."""
    for temp_file in temp_files:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logger.debug(f"Removed temporary file: {os.path.basename(temp_file)}")
        except Exception as e:
            logger.debug(f"Error deleting temporary file {os.path.basename(temp_file)}: {e}")
    
    # Clear any references to temporary files in results
    for result in results:
        if 'temp_graph_path' in result:
            del result['temp_graph_path']