#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Well plot visualization module for ddQuint with config integration and buffer zone support.

Creates individual well scatter plots with droplet classification, copy number annotations,
and appropriate highlighting for different chromosome states. Supports both standalone
and composite image formats with unified plot creation logic.
"""

import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.ticker as ticker
import logging

from ..config import Config, VisualizationError

logger = logging.getLogger(__name__)


def create_well_plot(df, clustering_results, well_id, save_path, for_composite=False, 
                    add_copy_numbers=True, sample_name=None):
    """
    Create an enhanced visualization plot for a single well with unified plot creation logic.
    
    Args:
        df (pandas.DataFrame): DataFrame with droplet data
        clustering_results (dict): Results from clustering analysis
        well_id (str): Well identifier (e.g., 'A01')
        save_path (str): Path to save the plot
        for_composite (bool): If True, creates a version optimized for composite image
        add_copy_numbers (bool): If True, adds copy number annotations to clusters
        sample_name (str, optional): Sample name to include in title
        
    Returns:
        str: Path to the saved plot
        
    Raises:
        VisualizationError: If plot creation fails
        ValueError: If required data is missing
    """
    config = Config.get_instance()
    
    logger.debug(f"Creating well plot for {well_id}, composite: {for_composite}")
    
    try:
        # Create the plot using unified logic
        fig, ax = _create_base_plot(config, for_composite)
        
        # ALWAYS apply consistent axis formatting first (unified base)
        _apply_axis_formatting(ax, config)
        
        # Determine plot type and add content overlay
        if _is_error_result(clustering_results):
            if df is not None and not df.empty:
                # Show raw data points with error overlay
                _add_raw_data_with_error(ax, df, clustering_results, well_id, for_composite)
            else:
                # No data available - just show error message
                _add_error_overlay(ax, clustering_results, well_id, for_composite)
        elif _has_insufficient_data(df, clustering_results, config):
            if df is not None and not df.empty:
                # Show whatever data we have
                _add_raw_data_content(ax, df, for_composite)
            # Skip "no data" overlay - just show empty plot with axes
        else:
            _add_data_content(ax, df, clustering_results, well_id, for_composite, 
                            add_copy_numbers, sample_name, config)
        
        # Set labels and title
        _set_plot_labels_and_title(ax, well_id, sample_name, for_composite)
        
        # Save figure with config-based DPI
        plot_type = 'composite' if for_composite else 'individual'
        dpi = config.get_plot_dpi(plot_type)
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        
        logger.debug(f"Well plot saved to: {save_path} (DPI: {dpi})")
        return save_path
        
    except Exception as e:
        error_msg = f"Error creating well plot for {well_id}: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        return None


def _create_base_plot(config, for_composite):
    """
    Create the base figure and axes with consistent dimensions and setup.
    
    Args:
        config: Configuration instance
        for_composite (bool): Whether this is for composite image
        
    Returns:
        tuple: (figure, axes) objects
    """
    # Get configuration settings
    fig_size = config.get_plot_dimensions(for_composite)
    
    # Create figure with configured dimensions
    fig = plt.figure(figsize=fig_size)
    
    # Set up axes with appropriate positioning
    if for_composite:
        ax = fig.add_axes([0.1, 0.1, 0.85, 0.85])  # Margins for axes
    else:
        ax = fig.add_axes([0.1, 0.1, 0.7, 0.8])  # Space for legend
    
    return fig, ax


def _apply_axis_formatting(ax, config, border_color='#B0B0B0'):
    """
    Apply consistent axis formatting to ALL plots (unified base formatting).
    
    This ensures every plot has identical axis limits, grid, borders, and appearance
    regardless of whether it contains data, errors, or is empty.
    
    Args:
        ax: Matplotlib axes object
        config: Configuration instance
        border_color: Color for plot borders (default grey)
    """
    # Set axis limits from config
    axis_limits = config.get_axis_limits()
    ax.set_xlim(axis_limits['x'])
    ax.set_ylim(axis_limits['y'])
    
    # Add grid with configured intervals
    ax.grid(True, alpha=0.4, linewidth=0.8)
    grid_intervals = config.get_grid_intervals()
    ax.xaxis.set_major_locator(ticker.MultipleLocator(grid_intervals['x']))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(grid_intervals['y']))
    
    # Set consistent aspect ratio
    ax.set_aspect('auto')
    
    # Make sure spines are visible and prominent
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1.0)
        spine.set_color(border_color)


def _is_error_result(clustering_results):
    """Check if this is an error result."""
    return clustering_results.get('error') is not None


def _has_insufficient_data(df, clustering_results, config):
    """Check if there's insufficient data for plotting."""
    if df is None or df.empty:
        return True
    
    if len(df) < config.MIN_POINTS_FOR_CLUSTERING:
        return True
        
    # Check if clustering was successful
    return not _validate_clustering_data(clustering_results)


def _validate_clustering_data(clustering_results):
    """Validate that clustering results contain necessary data."""
    return ('df_filtered' in clustering_results and 
            clustering_results['df_filtered'] is not None and 
            not clustering_results['df_filtered'].empty and
            'target_mapping' in clustering_results and 
            clustering_results['target_mapping'] is not None)


def _add_raw_data_with_error(ax, df, clustering_results, well_id, for_composite):
    """
    Add raw data visualization with error overlay on top of pre-formatted axes.
    Shows both raw data points and any available clustering results.
    
    Args:
        ax: Matplotlib axes object (already formatted)
        df: DataFrame with raw droplet data
        clustering_results (dict): Clustering results containing error info
        well_id (str): Well identifier
        for_composite (bool): Whether this is for composite image
    """
    # Check if we have any clustering data available
    df_filtered = clustering_results.get('df_filtered')
    target_mapping = clustering_results.get('target_mapping')
    config = Config.get_instance()
    label_color_map = config.TARGET_COLORS
    
    if df_filtered is not None and not df_filtered.empty and target_mapping:
        # We have partial clustering results - show colored clusters
        logger.debug(f"Plotting {len(df_filtered)} clustered droplets for well {well_id} with error overlay")
        
        # Assign colors based on target labels
        df_filtered_copy = df_filtered.copy()
        df_filtered_copy['color'] = df_filtered_copy['TargetLabel'].map(label_color_map)
        
        # Plot clustered droplets with colors
        scatter_size = 3 if for_composite else 6
        colors = df_filtered_copy['color'].fillna(label_color_map.get('Unknown', '#c7c7c7')).astype(str).tolist()
        ax.scatter(df_filtered_copy['Ch2Amplitude'], df_filtered_copy['Ch1Amplitude'],
                  c=colors, s=scatter_size, alpha=0.6)
        
        # Add legend for standalone plots if we have clusters
        if not for_composite:
            counts = clustering_results.get('counts', {})
            _add_legend(ax, label_color_map, counts)
    else:
        # No clustering data - plot raw data in grey
        scatter_size = 3 if for_composite else 6
        ax.scatter(df['Ch2Amplitude'], df['Ch1Amplitude'],
                  c='grey', s=scatter_size, alpha=0.5, label='Raw Droplets')
        
        logger.debug(f"Plotted {len(df)} raw droplets for well {well_id} with error overlay")
    
    # Add error message overlay in upper portion
    error_msg = clustering_results.get('error', 'Unknown Error')
    display_msg = _get_error_message(error_msg)
    
    font_size = 12 if for_composite else 16
    ax.text(0.5, 0.85, display_msg, 
            horizontalalignment='center', verticalalignment='top',
            transform=ax.transAxes, fontsize=font_size, color='red',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9))


def _add_raw_data_content(ax, df, for_composite):
    """
    Add raw data visualization without clustering information.
    
    Args:
        ax: Matplotlib axes object (already formatted)
        df: DataFrame with raw droplet data
        for_composite (bool): Whether this is for composite image
    """
    # Plot raw data points in grey
    scatter_size = 3 if for_composite else 6
    ax.scatter(df['Ch2Amplitude'], df['Ch1Amplitude'],
              c='grey', s=scatter_size, alpha=0.5, label='Raw Droplets')
    
    logger.debug(f"Plotted {len(df)} raw droplets without clustering")


def _add_error_overlay(ax, clustering_results, well_id, for_composite):
    """
    Add error message overlay on top of pre-formatted axes.
    
    Args:
        ax: Matplotlib axes object (already formatted)
        clustering_results (dict): Clustering results containing error info
        well_id (str): Well identifier
        for_composite (bool): Whether this is for composite image
    """
    # Get error message and convert to user-friendly format
    error_msg = clustering_results.get('error', 'Unknown Error')
    display_msg = _get_error_message(error_msg)
    
    # Add error message overlay with appropriate styling
    font_size = 12 if for_composite else 20
    ax.text(0.5, 0.5, display_msg, 
            horizontalalignment='center', verticalalignment='center',
            transform=ax.transAxes, fontsize=font_size, color='red',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))


def _add_data_content(ax, df, clustering_results, well_id, for_composite, 
                     add_copy_numbers, sample_name, config):
    """
    Add scatter plot data content on top of pre-formatted axes.
    
    Args:
        ax: Matplotlib axes object (already formatted)
        df: DataFrame with droplet data (original unfiltered data)
        clustering_results (dict): Results from clustering analysis
        well_id (str): Well identifier
        for_composite (bool): Whether this is for composite image
        add_copy_numbers (bool): Whether to add copy number annotations
        sample_name (str): Sample name for display
        config: Configuration instance
    """
    # Extract data from clustering results
    df_filtered = clustering_results['df_filtered']
    counts = clustering_results['counts']
    copy_numbers = clustering_results['copy_numbers']
    label_color_map = config.TARGET_COLORS
    
    logger.debug(f"Plotting {len(df_filtered)} filtered droplets for well {well_id}")
    
    # Get unclustered points (noise points with cluster = -1)
    # We need to get the original clustering data to identify unclustered points
    scatter_size = 5 if for_composite else 8
    
    # Find unclustered points by comparing original df with df_filtered
    # Create a set of indices that are in df_filtered
    clustered_indices = set(df_filtered.index)
    unclustered_mask = ~df.index.isin(clustered_indices)
    df_unclustered = df[unclustered_mask]
    
    # Plot unclustered points using "Unknown" color (same as unassigned clusters)
    unknown_color = label_color_map.get('Unknown', '#c7c7c7')
    if not df_unclustered.empty:
        ax.scatter(df_unclustered['Ch2Amplitude'], df_unclustered['Ch1Amplitude'],
                  c=unknown_color, s=scatter_size, alpha=0.6, label='Unclustered')
    
    # Plot clustered droplets with target colors
    df_filtered_copy = df_filtered.copy()
    df_filtered_copy['color'] = df_filtered_copy['TargetLabel'].map(label_color_map)
    
    colors = df_filtered_copy['color'].fillna(label_color_map.get('Unknown', '#c7c7c7')).astype(str).tolist()
    ax.scatter(df_filtered_copy['Ch2Amplitude'], df_filtered_copy['Ch1Amplitude'],
              c=colors, s=scatter_size, alpha=0.6)
    
    logger.debug(f"Plotted {len(df_filtered)} clustered droplets and {len(df_unclustered)} unclustered droplets for well {well_id}")
    
    # Add copy number annotations if requested
    if add_copy_numbers and copy_numbers:
        _add_copy_number_annotations(ax, df_filtered_copy, copy_numbers, 
                                   clustering_results.get('copy_number_states', {}), 
                                   label_color_map, for_composite)
    
    # Add buffer zone overlay for well plots (bottom right corner)
    if clustering_results.get('has_buffer_zone', False):
        _add_well_buffer_zone_overlay(ax, for_composite)
    
    # Add legend for standalone plots
    if not for_composite:
        _add_legend(ax, label_color_map, counts, has_unclustered=(not df_unclustered.empty))


def _add_well_buffer_zone_overlay(ax, for_composite):
    """
    Add buffer zone overlay for well plots (same position as error messages).
    
    Args:
        ax: Matplotlib axes object
        for_composite (bool): Whether this is for composite image
    """
    font_size = 12 if for_composite else 16
    ax.text(0.5, 0.85, "Buffer Zone", 
            horizontalalignment='center', verticalalignment='top',
            transform=ax.transAxes, fontsize=font_size, color='black',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgrey', alpha=0.8))
    
    logger.debug("Added buffer zone overlay to well plot")


def _add_copy_number_annotations(ax, df_filtered, copy_numbers, copy_number_states, 
                               label_color_map, for_composite):
    """Add copy number annotations to cluster centroids."""
    logger.debug("Adding copy number annotations")
    
    for target, color in label_color_map.items():
        if target not in ['Negative', 'Unknown'] and target in copy_numbers:
            # Get all points for this target
            target_points = df_filtered[df_filtered['TargetLabel'] == target]
            if not target_points.empty:
                # Calculate centroid
                cx = target_points['Ch2Amplitude'].mean()
                cy = target_points['Ch1Amplitude'].mean()
                
                # Format copy number text
                cn_value = copy_numbers[target]
                cn_text = f"{cn_value:.2f}"
                
                # Determine formatting based on state
                state = copy_number_states.get(target, 'euploid')
                font_size = 7 if for_composite else 12
                font_weight = 'bold' if state in ['aneuploidy', 'buffer_zone'] else 'normal'
                
                # Choose text color based on state
                if state == 'aneuploidy':
                    text_color = 'darkred'
                elif state == 'buffer_zone':
                    text_color = 'darkslategray'
                else:
                    text_color = 'black'
                
                logger.debug(f"Adding {target} copy number annotation: {cn_text} "
                           f"at ({cx:.1f}, {cy:.1f}), state: {state}")
                
                ax.text(cx, cy, cn_text, 
                        color=text_color, fontsize=font_size, fontweight=font_weight,
                        ha='center', va='center',
                        bbox=dict(facecolor='white', alpha=0.7, pad=1, edgecolor='none'))



def _add_legend(ax, label_color_map, counts, has_unclustered=False):
    """Add legend for standalone plots."""
    # Define ordered labels for legend
    ordered_labels = ['Negative', 'Chrom1', 'Chrom2', 'Chrom3', 'Chrom4', 'Chrom5']
    legend_handles = []
    
    for tgt in ordered_labels:
        # Skip targets with no droplets
        if tgt not in counts or counts[tgt] == 0:
            continue
            
        # Get color for this target
        color = label_color_map[tgt]
        
        # Create legend handle
        handle = mpl.lines.Line2D([], [], marker='o', linestyle='', markersize=10,
                               markerfacecolor=color, markeredgecolor='none', label=tgt)
        legend_handles.append(handle)
    
    # Add unclustered points to legend if they exist
    if has_unclustered:
        unknown_color = label_color_map.get('Unknown', '#c7c7c7')
        unclustered_handle = mpl.lines.Line2D([], [], marker='o', linestyle='', markersize=10,
                                            markerfacecolor=unknown_color, markeredgecolor='none', 
                                            label='Unclustered')
        legend_handles.append(unclustered_handle)
    
    # Add legend to right side of plot
    ax.legend(handles=legend_handles, title="Target",
             bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)


def _set_plot_labels_and_title(ax, well_id, sample_name, for_composite):
    """Set plot labels and title."""
    if for_composite:
        ax.set_xlabel("HEX Amplitude", fontsize=10)
        ax.set_ylabel("FAM Amplitude", fontsize=10)
        ax.tick_params(axis='both', which='both', labelsize=8)
    else:
        ax.set_xlabel("HEX Amplitude")
        ax.set_ylabel("FAM Amplitude")
        
        # Set title with sample name if available
        if sample_name:
            ax.set_title(f"Well {well_id} - {sample_name}")
        else:
            ax.set_title(f"Well {well_id}")


def create_placeholder_plot(well_id, save_path, for_composite=False):
    """
    Create a placeholder plot for empty well positions (no CSV file).
    
    Args:
        well_id (str): Well identifier (e.g., 'A01')
        save_path (str): Path to save the plot
        for_composite (bool): If True, creates a version optimized for composite image
        
    Returns:
        str: Path to the saved plot
    """
    config = Config.get_instance()
    
    logger.debug(f"Creating placeholder plot for {well_id}, composite: {for_composite}")
    
    try:
        # Create the plot using unified logic
        fig, ax = _create_base_plot(config, for_composite)
        
        # Apply consistent axis formatting with grey borders for placeholders
        _apply_axis_formatting(ax, config, border_color='#B0B0B0')  # Same grey as populated plots
        
        # Set labels and title (minimal for placeholders)
        _set_plot_labels_and_title(ax, well_id, None, for_composite)
        
        # Save figure with config-based DPI
        dpi = config.get_plot_dpi('placeholder')
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        
        logger.debug(f"Placeholder plot saved to: {save_path} (DPI: {dpi})")
        return save_path
        
    except Exception as e:
        error_msg = f"Error creating placeholder plot for {well_id}: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        return None


def _get_error_message(error_message):
    """
    Convert technical error messages to user-friendly messages.
    
    Args:
        error_message (str): Original technical error message
        
    Returns:
        str: Clean, user-friendly error message
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