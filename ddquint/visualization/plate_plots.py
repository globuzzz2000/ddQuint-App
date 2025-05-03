"""
Fixed plate plot visualization module for ddQuint
Creates an optimized composite image of all wells in a plate layout
"""

import os
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
from matplotlib.ticker import MultipleLocator
import tempfile
import shutil

# Define plate layout constants
ROW_LABELS = list('ABCDEFGH')
COL_LABELS = [str(i) for i in range(1, 13)]  # Format as "1", "2", etc.

def create_composite_image(results, output_path):
    """
    Create an optimized composite image of all wells arranged in a plate layout.
    
    Args:
        results (list): List of result dictionaries for each well
        output_path (str): Path to save the composite image
        
    Returns:
        str: Path to the saved composite image
    """
    # Import tqdm for progress bar
    from tqdm import tqdm
    
    # Keep track of all temporary files we create
    temp_files = []
    
    try:
        # Generate optimized images for each well - with progress bar
        for result in tqdm(results, desc="Creating Plate image", unit="well"):
            if not result.get('well'):
                continue
                
            # Call the optimized well plot function to create a version without legend
            from ddquint.visualization.well_plots import create_well_plot
            
            # Get the data file
            df_file = os.path.join(os.path.dirname(result['graph_path']), "..", "Raw Data", result['filename'])
            if not os.path.exists(df_file):
                continue
                
            # Load the data and rerun the clustering
            import pandas as pd
            from ddquint.core.clustering import analyze_droplets
            
            try:
                # Find the header row containing Ch1Amplitude
                header_row = None
                with open(df_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f):
                        if ('Ch1Amplitude' in line or 'Ch1 Amplitude' in line) and \
                           ('Ch2Amplitude' in line or 'Ch2 Amplitude' in line):
                            header_row = i
                            break
                
                if header_row is None:
                    continue
                    
                # Load the CSV data
                df = pd.read_csv(df_file, skiprows=header_row)
                
                # Check for required columns
                required_cols = ['Ch1Amplitude', 'Ch2Amplitude']
                if not all(col in df.columns for col in required_cols):
                    continue
                
                # Filter rows with NaN values
                df_clean = df[required_cols].dropna()
                
                # Analyze the droplets
                clustering_results = analyze_droplets(df_clean)
                
                # Create optimized plot for composite image - put it directly in the Graphs folder
                # Extract the output directory from the output_path
                output_dir = os.path.dirname(output_path)
                graphs_dir = os.path.join(output_dir, "Graphs")
                os.makedirs(graphs_dir, exist_ok=True)
                
                # Create a temp file in the Graphs directory with a distinct name pattern
                temp_path = os.path.join(graphs_dir, f"{result['well']}_temp.png")
                create_well_plot(df_clean, clustering_results, result['well'], temp_path, for_composite=True, add_copy_numbers=True)
                
                # Track the temporary file so we can delete it later
                temp_files.append(temp_path)
                
                # Store the temporary path in the result
                result['temp_graph_path'] = temp_path
                
            except Exception as e:
                print(f"Error processing well {result.get('well')}: {e}")
                # On error, just use the original graph
                pass
        
        # Create figure with adjusted size for better proportions and maximum space usage
        fig = plt.figure(figsize=(16, 11))  # Adjusted size for better clarity
        
        # Create GridSpec with spacing that ensures borders are visible
        gs = gridspec.GridSpec(8, 12, figure=fig, wspace=0.02, hspace=0.02)
        
        # Create a mapping of well to result for easy lookup
        well_results = {r['well']: r for r in results if r.get('well') is not None}
        
        # Ensure the figure has proper margins
        plt.subplots_adjust(left=0.04, right=0.96, top=0.96, bottom=0.04)
        
        # Create a subplot for each well position
        for i, row in enumerate(ROW_LABELS):
            for j, col_num in enumerate(range(1, 13)):
                col = str(col_num)  # Simple column format
                well = f"{row}{col.zfill(2)}"  # Ensure zero-padding for well ID
                
                # Add subplot at this position
                ax = fig.add_subplot(gs[i, j])
                
                # Set light gray background for empty wells
                ax.set_facecolor('#f5f5f5')
                
                if well in well_results:
                    # This well has data
                    result = well_results[well]
                    
                    # Use temp graph path if available, otherwise fall back to original
                    graph_path = result.get('temp_graph_path', result.get('graph_path'))
                    
                    # Check if graph_path exists and is valid
                    if graph_path and os.path.exists(graph_path):
                        try:
                            # Read and display the individual well image
                            img = plt.imread(graph_path)
                            ax.imshow(img)
                            
                            # Remove title
                            ax.set_title("")
                            
                            # Add purple border for wells with outliers - ensure this is applied
                            # Simply rely on the has_outlier flag that was set by the analysis modules
                            if result.get('has_outlier', False):
                                # Force purple border with increased visibility
                                for spine in ax.spines.values():
                                    spine.set_edgecolor('#E6B8E6')  # Alternative way to set color 
                                    spine.set_color('#E6B8E6')      # Set both to ensure it works
                                    spine.set_linewidth(1)
                                    spine.set_visible(True)
                        except Exception as e:
                            print(f"Error displaying image for well {well}: {e}")
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
                    # Empty well with no data - create a properly sized placeholder
                    # Set up the exact same dimensions as real plots
                    ax.set_xlim(0, 3000)
                    ax.set_ylim(0, 5000)
                    
                    # Add grid with same spacing as real plots for consistent appearance
                    ax.grid(True, alpha=0.4, linewidth=0.8)
                    ax.xaxis.set_major_locator(MultipleLocator(500))
                    ax.yaxis.set_major_locator(MultipleLocator(1000))
                    
                    # Turn off tick marks but keep the grid
                    ax.tick_params(axis='both', which='both', length=0)
                    
                    # Ensure aspect ratio is consistent with data plots
                    ax.set_aspect('auto')
                    
                    # Add well identifier in gray
                    ax.text(0.5, 0.5, well, fontsize=8, color='gray',
                            horizontalalignment='center', verticalalignment='center',
                            transform=ax.transAxes)
                
                # Keep axis visibility for all plots
                ax.set_xticks([])
                ax.set_yticks([])
                
                # Use consistent border width for all graphs
                for spine_name in ['top', 'right', 'bottom', 'left']:
                    ax.spines[spine_name].set_visible(True)
                    ax.spines[spine_name].set_linewidth(1)
                    ax.spines[spine_name].set_color('black')
                    
                # Check again for outliers to ensure purple border is applied
                # Simply use the has_outlier flag as determined by the analysis modules
                if well in well_results and well_results[well].get('has_outlier', False):
                    for spine in ax.spines.values():
                        spine.set_color('#E6B8E6')
                        spine.set_linewidth(2)
        
        # Add row labels (A-H) with proper alignment to match the actual plots
        for i, row in enumerate(ROW_LABELS):
            # Calculate the exact y-position by using the axes position
            ax = fig.axes[i*12]  # Get the first plot in this row
            # Get the vertical center of this axes
            y_center = (ax.get_position().y0 + ax.get_position().y1) / 2
            fig.text(0.02, y_center, row, ha='center', va='center', fontsize=12, weight='bold')
        
        # Add column labels (1-12) with proper alignment to match the actual plots
        for j, col in enumerate(COL_LABELS):
            # Calculate the exact x-position by using the axes position
            ax = fig.axes[j]  # Get the plot in the first row for this column
            # Get the horizontal center of this axes
            x_center = (ax.get_position().x0 + ax.get_position().x1) / 2
            fig.text(x_center, 0.98, col, ha='center', va='center', fontsize=12, weight='bold')
        
        # Save the composite image with high resolution but ensure quality
        # Use pad_inches=0.1 to ensure borders are visible
        fig.savefig(output_path, dpi=400, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        
        # Now explicitly delete each temporary file
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                print(f"Error deleting temporary file {temp_file}: {e}")
        
        # Clear any references to temporary files in results
        for result in results:
            if 'temp_graph_path' in result:
                del result['temp_graph_path']
                
    except Exception as e:
        print(f"Error creating composite image: {e}")
        
        # Even if there's an error, try to clean up temporary files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass  # Ignore errors during cleanup
    
    return output_path
