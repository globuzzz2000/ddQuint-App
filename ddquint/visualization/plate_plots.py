"""
Plate plot visualization module for ddQuint
Creates a composite image of all wells in a plate layout
"""

import os
import datetime
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# Define plate layout constants
ROW_LABELS = list('ABCDEFGH')
COL_LABELS = [str(i).zfill(2) for i in range(1, 13)]  # Format as "01", "02", etc.

def create_composite_image(results, output_path):
    """
    Create a composite image of all wells arranged in a plate layout.
    
    Args:
        results (list): List of result dictionaries for each well
        output_path (str): Path to save the composite image
        
    Returns:
        str: Path to the saved composite image
    """
    print(f"Creating composite plate image...")
    
    # Create figure with grid for 8 rows (A-H) and 12 columns (1-12)
    fig = plt.figure(figsize=(16, 10))
    gs = gridspec.GridSpec(8, 12, figure=fig)
    
    # Create a mapping of well to result for easy lookup
    well_results = {r['well']: r for r in results if r.get('well') is not None}
    
    # Create a subplot for each well position
    for i, row in enumerate(ROW_LABELS):
        for j, col_num in enumerate(range(1, 13)):
            col = str(col_num).zfill(2)  # Format as "01", "02", etc.
            well = f"{row}{col}"
            
            # Add subplot at this position
            ax = fig.add_subplot(gs[i, j])
            
            # Set light gray background for empty wells
            ax.set_facecolor('#f5f5f5')
            
            if well in well_results:
                # This well has data
                result = well_results[well]
                
                # Check if graph_path exists and is valid
                if 'graph_path' in result and result['graph_path'] and os.path.exists(result['graph_path']):
                    try:
                        # Read and display the individual well image
                        img = plt.imread(result['graph_path'])
                        ax.imshow(img)
                        
                        # Add red border for wells with outliers
                        if result.get('has_outlier', False):
                            for spine in ax.spines.values():
                                spine.set_color('red')
                                spine.set_linewidth(2)
                    except Exception as e:
                        # Show error message if image can't be loaded
                        ax.text(0.5, 0.5, "Image Error", 
                                horizontalalignment='center', verticalalignment='center', 
                                transform=ax.transAxes, fontsize=8, color='red')
                else:
                    # Show message if no image is available
                    ax.text(0.5, 0.5, "No Image", 
                            horizontalalignment='center', verticalalignment='center', 
                            transform=ax.transAxes, fontsize=8)
            else:
                # Empty well with no data
                ax.text(0.5, 0.5, "Empty", 
                        horizontalalignment='center', verticalalignment='center', 
                        transform=ax.transAxes, color='gray', fontsize=8)
            
            # Set well coordinate as title
            ax.set_title(well, fontsize=10)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.grid(False)
    
    # Add overall title and timestamp
    plt.suptitle("ddQuint: Multiplex Analysis - All Wells", fontsize=16)
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    plt.figtext(0.5, 0.01, f"Generated: {timestamp}", ha='center', fontsize=10)
    
    # Adjust layout to make room for title and timestamp
    plt.tight_layout(rect=[0, 0.02, 1, 0.98])
    
    # Save the composite image
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    print(f"Composite image saved to: {output_path}")
    return output_path