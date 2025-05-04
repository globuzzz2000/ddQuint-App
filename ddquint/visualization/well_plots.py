"""
Updated well plot visualization module for ddQuint with config integration
"""

import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.ticker as ticker
import numpy as np
import logging

from ..config.config import Config

def create_well_plot(df, clustering_results, well_id, save_path, for_composite=False, add_copy_numbers=True, sample_name=None):
    """
    Create an enhanced visualization plot for a single well with square aspect ratio.
    
    Args:
        df (pandas.DataFrame): DataFrame with droplet data
        clustering_results (dict): Results from clustering analysis
        well_id (str): Well identifier (e.g., 'A01')
        save_path (str): Path to save the plot
        for_composite (bool): If True, creates a version optimized for the composite image
        add_copy_numbers (bool): If True, adds copy number annotations to clusters
        sample_name (str): Optional sample name to include in title
        
    Returns:
        str: Path to the saved plot
    """
    logger = logging.getLogger("ddQuint")
    config = Config.get_instance()

    # Get color map from config
    label_color_map = config.TARGET_COLORS
    logger.debug(f"Using target colors: {label_color_map}")

    # Define ordered labels for legend
    ordered_labels = ['Negative', 'Chrom1', 'Chrom2', 'Chrom3', 'Chrom4', 'Chrom5']
    
    # Get figure dimensions from config
    fig_size = config.get_plot_dimensions(for_composite)
    logger.debug(f"Using figure size: {fig_size}")
    
    # Create figure with configured dimensions
    fig = plt.figure(figsize=fig_size)
    
    # Get axes with absolute positioning (left, bottom, width, height)
    if for_composite:
        ax = fig.add_axes([0.1, 0.1, 0.85, 0.85])  # Ensure margins for axes
    else:
        ax = fig.add_axes([0.1, 0.1, 0.7, 0.8])  # Space for legend
    
    # Check if clustering was successful
    if 'df_filtered' not in clustering_results or clustering_results['df_filtered'].empty:
        logger.debug(f"No valid clustering data for well {well_id}")
        # Create a basic plot with raw data
        ax.scatter(df['Ch2Amplitude'], df['Ch1Amplitude'], c='gray', s=4, alpha=0.5)
        ax.set_xlabel("HEX Amplitude")
        ax.set_ylabel("FAM Amplitude")
        if not for_composite:
            ax.set_title(f"Well {well_id}")
        
        # Set axis limits from config
        axis_limits = config.get_axis_limits()
        ax.set_xlim(axis_limits['x'])
        ax.set_ylim(axis_limits['y'])
        
        # Add grid with configured intervals
        ax.grid(True)
        grid_intervals = config.get_grid_intervals()
        ax.xaxis.set_major_locator(ticker.MultipleLocator(grid_intervals['x']))
        ax.yaxis.set_major_locator(ticker.MultipleLocator(grid_intervals['y']))
        
        # Save figure with tight layout
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return save_path
    
    # Get filtered data with clusters
    df_filtered = clustering_results['df_filtered']
    target_mapping = clustering_results['target_mapping']
    counts = clustering_results['counts']
    copy_numbers = clustering_results['copy_numbers']
    
    logger.debug(f"Plotting {len(df_filtered)} filtered droplets for well {well_id}")
    
    # Assign colors based on target labels
    df_filtered['color'] = df_filtered['TargetLabel'].map(label_color_map)
    
    # Plot all droplets, colored by target
    ax.scatter(df_filtered['Ch2Amplitude'], df_filtered['Ch1Amplitude'],
              c=df_filtered['color'], s=5 if for_composite else 8, alpha=0.6)
    
    # Add copy number annotations directly on the plot
    if add_copy_numbers and 'copy_numbers' in clustering_results:
        logger.debug("Adding copy number annotations")
        copy_numbers = clustering_results['copy_numbers']
        
        # For each target, calculate the centroid and add a label
        for target, color in label_color_map.items():
            if target not in ['Negative', 'Unknown'] and target in copy_numbers:
                # Get all points for this target
                target_points = df_filtered[df_filtered['TargetLabel'] == target]
                if not target_points.empty:
                    # Calculate centroid
                    cx = target_points['Ch2Amplitude'].mean()
                    cy = target_points['Ch1Amplitude'].mean()
                    # Add copy number label
                    cn_value = copy_numbers[target]
                    
                    # Check if this is an aneuploidy
                    is_aneuploidy = (clustering_results.get('has_aneuploidy', False) and 
                                     abs(cn_value - 1.0) > config.ANEUPLOIDY_DEVIATION_THRESHOLD)
                    cn_text = f"{cn_value:.2f}"
                    
                    # Adjust size and font weight for individual vs composite plots
                    font_size = 7 if for_composite else 12
                    font_weight = 'bold' if is_aneuploidy else 'normal'
                    
                    logger.debug(f"Adding {target} copy number annotation: {cn_text} at ({cx:.1f}, {cy:.1f})")
                    
                    ax.text(cx, cy, cn_text, 
                            color='black' if not is_aneuploidy else 'darkred',
                            fontsize=font_size, fontweight=font_weight,
                            ha='center', va='center',
                            bbox=dict(facecolor='white', alpha=0.7, pad=1, edgecolor='none'))
    
    # Add noise points (cluster -1) with lower opacity
    noise_points = df[~df.index.isin(df_filtered.index)]
    if not noise_points.empty:
        logger.debug(f"Adding {len(noise_points)} noise points")
        ax.scatter(noise_points['Ch2Amplitude'], noise_points['Ch1Amplitude'],
                  c='lightgray', s=3, alpha=0.3)
    
    # Add legend only for standalone plots (not for composite)
    if not for_composite:
        # Build legend
        legend_handles = []
        
        for tgt in ordered_labels:
            # Skip targets with no droplets
            if tgt not in counts or counts[tgt] == 0:
                continue
                
            # Get color for this target
            color = label_color_map[tgt]
            
            # Create simple label text
            label_text = tgt
                
            # Create legend handle
            handle = mpl.lines.Line2D([], [], marker='o', linestyle='', markersize=10,
                                   markerfacecolor=color, markeredgecolor='none', label=label_text)
            legend_handles.append(handle)
        
        # Add legend to right side of plot
        ax.legend(handles=legend_handles, title="Target",
                 bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
    
    # Set plot labels and title
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
    
    # Set axis limits from config
    axis_limits = config.get_axis_limits()
    ax.set_xlim(axis_limits['x'])
    ax.set_ylim(axis_limits['y'])
    
    # Add grid with configured intervals
    ax.grid(True, alpha=0.4, linewidth=0.8)
    grid_intervals = config.get_grid_intervals()
    ax.xaxis.set_major_locator(ticker.MultipleLocator(grid_intervals['x']))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(grid_intervals['y']))
    
    # Set equal aspect with set limits to ensure proper scaling
    ax.set_aspect('auto')
    
    # Make sure spines are visible and prominent
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1.0)
        spine.set_color('#000000')  # Black borders
    
    # Save the figure with appropriate resolution
    dpi = 200 if for_composite else 150
    plt.savefig(save_path, dpi=dpi, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    
    logger.debug(f"Well plot saved to: {save_path}")
    return save_path