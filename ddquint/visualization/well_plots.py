"""
Fixed well plot visualization module for ddQuint
Creates square plots with fixed and equal axes
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MultipleLocator
import matplotlib as mpl


def create_well_plot(df, clustering_results, well_id, save_path, for_composite=False, add_copy_numbers=False, sample_name=None):
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

    # Define color map for targets
    label_color_map = {
        "Negative": "#1f77b4",   # blue
        "Chrom1":   "#ff7f0e",   # orange
        "Chrom2":   "#2ca02c",   # green
        "Chrom3":   "#17becf",   # cyan
        "Chrom4":   "#d62728",   # red
        "Chrom5":   "#9467bd",   # purple
        "Unknown":  "#c7c7c7"    # light gray
    }

    # And when building the legend, keep only the original targets
    ordered_labels = ['Negative', 'Chrom1', 'Chrom2', 'Chrom3', 'Chrom4', 'Chrom5']
    
    # Create figure with square proportions
    # Adjust figure size based on whether it's for the composite image or standalone
    if for_composite:
        fig = plt.figure(figsize=(5, 5))  # Larger square figure for composite
    else:
        fig = plt.figure(figsize=(6, 5))  # Slightly wider for legend space
    
    # Get axes with absolute positioning (left, bottom, width, height)
    if for_composite:
        ax = fig.add_axes([0.1, 0.1, 0.85, 0.85])  # Ensure margins for axes
    else:
        ax = fig.add_axes([0.1, 0.1, 0.7, 0.8])  # Space for legend
    
    # Check if clustering was successful
    if 'df_filtered' not in clustering_results or clustering_results['df_filtered'].empty:
        # Create a basic plot with raw data
        ax.scatter(df['Ch2Amplitude'], df['Ch1Amplitude'], c='gray', s=4, alpha=0.5)
        ax.set_xlabel("HEX Amplitude")
        ax.set_ylabel("FAM Amplitude")
        if not for_composite:
            ax.set_title(f"Well {well_id}")
        
        # Set fixed axis limits
        ax.set_xlim(0, 3000)
        ax.set_ylim(0, 5000)
        
        # Add grid with standard spacing
        ax.grid(True)
        ax.xaxis.set_major_locator(MultipleLocator(500))
        ax.yaxis.set_major_locator(MultipleLocator(1000))
        
        # Save figure with tight layout
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return save_path
    
    # Get filtered data with clusters
    df_filtered = clustering_results['df_filtered']
    target_mapping = clustering_results['target_mapping']
    counts = clustering_results['counts']
    copy_numbers = clustering_results['copy_numbers']
    
    # Assign colors based on target labels
    df_filtered['color'] = df_filtered['TargetLabel'].map(label_color_map)
    
    # Plot all droplets, colored by target
    ax.scatter(df_filtered['Ch2Amplitude'], df_filtered['Ch1Amplitude'],
              c=df_filtered['color'], s=5 if for_composite else 4, alpha=0.6)
    
    # Add copy number annotations directly on the plot for composite images
    if for_composite and add_copy_numbers and 'copy_numbers' in clustering_results:
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
                    # Format copy number - bold and a different color if it's an aneuploidy
                    # Use the has_aneuploidy flag to determine if this is an aneuploidy chromosome
                    is_aneuploidy = clustering_results.get('has_aneuploidy', False) and abs(cn_value - 1.0) > 0.15
                    cn_text = f"{cn_value:.2f}"
                    ax.text(cx, cy, cn_text, 
                            color='black' if not is_aneuploidy else 'darkred',
                            fontsize=7, fontweight='bold' if is_aneuploidy else 'normal',
                            ha='center', va='center',
                            bbox=dict(facecolor='white', alpha=0.7, pad=1, edgecolor='none'))
    
    # Add noise points (cluster -1) with lower opacity
    noise_points = df[~df.index.isin(df_filtered.index)]
    if not noise_points.empty:
        ax.scatter(noise_points['Ch2Amplitude'], noise_points['Ch1Amplitude'],
                  c='lightgray', s=3, alpha=0.3)
    
    # Add legend only for standalone plots (not for composite)
    if not for_composite:
        # Build legend
        ordered_labels = ['Negative', 'Chrom1', 'Chrom2', 'Chrom3', 'Chrom4', 'Chrom5']
        legend_handles = []
        
        for tgt in ordered_labels:
            # Skip targets with no droplets
            if tgt not in counts or counts[tgt] == 0:
                continue
                
            # Get color for this target
            color = label_color_map[tgt]
            
            # Create label text
            if tgt == 'Negative':
                label_text = f"{tgt}"  # No count for negative droplets
            elif tgt in copy_numbers:
                label_text = f"{tgt} ({copy_numbers[tgt]:.2f})"
            else:
                label_text = f"{tgt} (N/A)"
                
            # Create legend handle
            handle = mpl.lines.Line2D([], [], marker='o', linestyle='', markersize=6,
                                   markerfacecolor=color, markeredgecolor='none', label=label_text)
            legend_handles.append(handle)
        
        # Add legend to right side of plot, exclude "Unknown"
        ax.legend(handles=legend_handles, title="Target (copy number)",
                 bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    
    # Set plot labels and title
    if for_composite:
        # Keep axis labels with normal size (same as non-composite plots)
        ax.set_xlabel("HEX Amplitude", fontsize=10)
        ax.set_ylabel("FAM Amplitude", fontsize=10)
        ax.tick_params(axis='both', which='both', labelsize=8)
        # Don't add the well number in the corner for composite plots
    else:
        ax.set_xlabel("HEX Amplitude")
        ax.set_ylabel("FAM Amplitude")
        
        # Set title with sample name if available
        if sample_name:
            ax.set_title(f"Well {well_id} - {sample_name}")
        else:
            ax.set_title(f"Well {well_id}")
    
    # Set fixed axis limits - ensure X and Y scales are visually proportional
    ax.set_xlim(0, 3000)
    ax.set_ylim(0, 5000)
    
    # Add grid with standard spacing
    ax.grid(True, alpha=0.4, linewidth=0.8)
    ax.xaxis.set_major_locator(MultipleLocator(500))
    ax.yaxis.set_major_locator(MultipleLocator(1000))
    
    # Set equal aspect with set limits to ensure proper scaling
    # This will stretch the plot to fill the axis area
    ax.set_aspect('auto')
    
    # Make sure spines are visible and prominent
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1.0)
        spine.set_color('#000000')  # Black borders
    
    # Save the figure with appropriate resolution
    dpi = 200 if for_composite else 150
    
    # Save with proper padding to ensure axes are visible
    plt.savefig(save_path, dpi=dpi, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    
    return save_path