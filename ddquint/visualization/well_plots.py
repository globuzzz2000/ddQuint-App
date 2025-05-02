"""
Well plot visualization module for ddQuint
"""

import matplotlib.pyplot as plt
import numpy as np

def create_well_plot(df, clustering_results, well_id, save_path):
    """
    Create a visualization plot for a single well.
    
    Args:
        df (pandas.DataFrame): DataFrame with droplet data
        clustering_results (dict): Results from clustering analysis
        well_id (str): Well identifier (e.g., 'A01')
        save_path (str): Path to save the plot
        
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
    
    # Check if clustering was successful
    if 'df_filtered' not in clustering_results or clustering_results['df_filtered'].empty:
        # Create a basic plot with raw data
        fig = plt.figure(figsize=(6, 5))
        plt.scatter(df['Ch2Amplitude'], df['Ch1Amplitude'], c='gray', s=4, alpha=0.5)
        plt.xlabel("HEX Amplitude")
        plt.ylabel("FAM Amplitude")
        plt.title(f"Well {well_id} - No Valid Clusters Found")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return save_path
    
    # Create figure for the well
    fig = plt.figure(figsize=(6, 5))
    
    # Get filtered data with clusters
    df_filtered = clustering_results['df_filtered']
    target_mapping = clustering_results['target_mapping']
    counts = clustering_results['counts']
    copy_numbers = clustering_results['copy_numbers']
    
    # Assign colors based on target labels
    df_filtered['color'] = df_filtered['TargetLabel'].map(label_color_map)
    
    # If there are identified clusters, focus on them for the plot
    single_pos = df_filtered[df_filtered['TargetLabel'] != "Unknown"]
    
    if not single_pos.empty:
        # Calculate plot limits with padding
        xmin, xmax = single_pos['Ch2Amplitude'].min(), single_pos['Ch2Amplitude'].max()
        ymin, ymax = single_pos['Ch1Amplitude'].min(), single_pos['Ch1Amplitude'].max()
        pad_x = (xmax - xmin) * 0.1
        pad_y = (ymax - ymin) * 0.1
        
        # Plot all droplets, colored by target
        plt.scatter(df_filtered['Ch2Amplitude'], df_filtered['Ch1Amplitude'],
                    c=df_filtered['color'], s=4, alpha=0.5)
        
        # Build legend
        ordered_labels = ['Negative', 'Chrom1', 'Chrom2', 'Chrom3', 'Chrom4', 'Chrom5', 'Unknown']
        legend_handles = []
        
        for tgt in ordered_labels:
            # Skip targets with no droplets
            if tgt not in counts or counts[tgt] == 0:
                continue
                
            # Get color for this target
            color = label_color_map[tgt]
            
            # Create label text
            if tgt == 'Negative':
                label_text = f"{tgt} ({counts[tgt]})"
            elif tgt in copy_numbers:
                label_text = f"{tgt} ({copy_numbers[tgt]:.2f})"
            else:
                label_text = f"{tgt} (N/A)"
                
            # Create legend handle
            handle = plt.Line2D([], [], marker='o', linestyle='', markersize=6,
                              markerfacecolor=color, markeredgecolor='none', label=label_text)
            legend_handles.append(handle)
        
        # Add legend
        plt.legend(handles=legend_handles, title="Target (copy number)",
                   bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Set plot labels and title
        plt.xlabel("HEX Amplitude")
        plt.ylabel("FAM Amplitude")
        plt.title(f"Well {well_id} - HEX vs FAM")
        
        # Set plot limits with padding
        plt.xlim(max(0, xmin - pad_x), xmax + pad_x)
        plt.ylim(max(0, ymin - pad_y), ymax + pad_y)
        
        # Add grid and adjust layout
        plt.grid(True)
        plt.tight_layout()
        
    else:
        # If no clusters were found, create a basic plot
        plt.scatter(df['Ch2Amplitude'], df['Ch1Amplitude'], c='gray', s=3, alpha=0.4)
        plt.xlabel("HEX Amplitude")
        plt.ylabel("FAM Amplitude")
        plt.title(f"Well {well_id} - HEX vs FAM")
        plt.grid(True)
        plt.tight_layout()
    
    # Save the figure
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    return save_path