"""
Updated plate plot visualization module for ddQuint with config integration and buffer zone support
"""

import os
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
import logging
from matplotlib.ticker import MultipleLocator
from tqdm import tqdm

from ..config.config import Config
from ..visualization.well_plots import create_well_plot

def create_composite_image(results, output_path):
    """
    Create a composite image using the existing clustering results without re-running analysis.
    
    Args:
        results (list): List of result dictionaries
        output_path (str): Path to save the composite image
        
    Returns:
        str: Path to the saved composite image
    """
    logger = logging.getLogger("ddQuint")
    config = Config.get_instance()
    
    # Keep track of all temporary files we create
    temp_files = []
    
    try:
        # Get plate layout from config
        row_labels = config.PLATE_ROWS
        col_labels = config.PLATE_COLS
        
        # Generate optimized images for each well - with progress bar
        for result in tqdm(results, desc="Creating Plate image", unit="well"):
            if not result.get('well'):
                continue
                
            # Get the data file
            df_file = os.path.join(os.path.dirname(result['graph_path']), "..", 
                                   config.RAW_DATA_DIR_NAME, result['filename'])
            if not os.path.exists(df_file):
                logger.debug(f"Raw data file not found: {df_file}")
                continue
                
            # Load the raw data
            try:
                # Find the header row
                header_row = None
                with open(df_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f):
                        if ('Ch1Amplitude' in line or 'Ch1 Amplitude' in line) and \
                           ('Ch2Amplitude' in line or 'Ch2 Amplitude' in line):
                            header_row = i
                            break
                
                if header_row is None:
                    logger.debug(f"Could not find header row in {df_file}")
                    continue
                    
                # Load the CSV data
                df = pd.read_csv(df_file, skiprows=header_row)
                
                # Check for required columns
                required_cols = ['Ch1Amplitude', 'Ch2Amplitude']
                if not all(col in df.columns for col in required_cols):
                    logger.debug(f"Required columns not found in {df_file}")
                    continue
                
                # Filter rows with NaN values
                df_clean = df[required_cols].dropna()
                
                # Use the existing clustering results from the first analysis
                clustering_results = {
                    'df_filtered': result.get('df_filtered'),
                    'target_mapping': result.get('target_mapping'),
                    'counts': result.get('counts', {}),
                    'copy_numbers': result.get('copy_numbers', {}),
                    'copy_number_states': result.get('copy_number_states', {}),
                    'has_aneuploidy': result.get('has_aneuploidy', False),
                    'has_buffer_zone': result.get('has_buffer_zone', False),
                    'chrom3_reclustered': result.get('chrom3_reclustered', False)
                }
                
                # Verify we have the necessary data
                if clustering_results['df_filtered'] is None or clustering_results['target_mapping'] is None:
                    logger.debug(f"Missing clustering data for well {result['well']}")
                    continue
                
                # Create optimized plot for composite image
                output_dir = os.path.dirname(output_path)
                graphs_dir = os.path.join(output_dir, config.GRAPHS_DIR_NAME)
                os.makedirs(graphs_dir, exist_ok=True)
                
                # Create a temp file in the Graphs directory
                temp_path = os.path.join(graphs_dir, f"{result['well']}_temp.png")
                create_well_plot(df_clean, clustering_results, result['well'], 
                                 temp_path, for_composite=True, add_copy_numbers=True)
                
                # Track the temporary file
                temp_files.append(temp_path)
                result['temp_graph_path'] = temp_path
                
            except Exception as e:
                logger.debug(f"Error processing well {result.get('well')}: {e}")
                continue
        
        # Create figure with configured size
        fig_size = config.COMPOSITE_FIGURE_SIZE
        fig = plt.figure(figsize=fig_size)
        logger.debug(f"Creating composite figure with size: {fig_size}")
        
        # Create GridSpec with spacing that ensures borders are visible
        gs = gridspec.GridSpec(8, 12, figure=fig, wspace=0.02, hspace=0.02)
        
        # Create a mapping of well to result for easy lookup
        well_results = {r['well']: r for r in results if r.get('well') is not None}
        
        # Ensure the figure has proper margins
        plt.subplots_adjust(left=0.04, right=0.96, top=0.96, bottom=0.04)
        
        # Create a subplot for each well position
        for i, row in enumerate(row_labels):
            for j, col_num in enumerate(range(1, int(col_labels[-1]) + 1)):
                col = str(col_num)
                well = config.WELL_FORMAT.format(row=row, col=int(col))
                
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
                            
                            # Add title
                            if result.get('sample_name'):
                                # Add sample name title for data wells
                                ax.set_title(result['sample_name'], fontsize=6, pad=2)
                            else:
                                # Add well ID title for data wells without sample names
                                ax.set_title(well, fontsize=6, pad=2)
                            
                            # Apply colored borders based on copy number state
                            # Buffer zone trumps aneuploidy in detection, but has specific border styling
                            if result.get('has_buffer_zone', False):
                                border_color = '#000000'  # Black border for buffer zone
                                border_width = 2  # Thin border like euploid
                                logger.debug(f"Applied buffer zone border (black) to well {well}")
                            elif result.get('has_aneuploidy', False):
                                border_color = '#E6B8E6'  # Light purple border for aneuploidy (matching Excel)
                                border_width = 3  # Thick border
                                logger.debug(f"Applied aneuploidy border (light purple) to well {well}")
                            else:
                                border_color = '#B0B0B0'  # Light grey border for euploid samples
                                border_width = 2  # Thin border
                                logger.debug(f"Applied euploid border (light grey) to well {well}")
                            
                            # Apply the border
                            for spine in ax.spines.values():
                                spine.set_edgecolor(border_color)
                                spine.set_color(border_color)
                                spine.set_linewidth(border_width)
                                spine.set_visible(True)
                                
                        except Exception as e:
                            logger.debug(f"Error displaying image for well {well}: {e}")
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
                    axis_limits = config.get_axis_limits()
                    ax.set_xlim(axis_limits['x'])
                    ax.set_ylim(axis_limits['y'])
                    
                    # Add grid with configured spacing
                    ax.grid(True, alpha=0.4, linewidth=0.8)
                    grid_intervals = config.get_grid_intervals()
                    ax.xaxis.set_major_locator(MultipleLocator(grid_intervals['x']))
                    ax.yaxis.set_major_locator(MultipleLocator(grid_intervals['y']))
                    
                    # Turn off tick marks but keep the grid
                    ax.tick_params(axis='both', which='both', length=0)
                    
                    # Ensure aspect ratio is consistent with data plots
                    ax.set_aspect('auto')
                    
                    # Add well identifier in gray
                    ax.text(0.5, 0.5, well, fontsize=8, color='gray',
                            horizontalalignment='center', verticalalignment='center',
                            transform=ax.transAxes)
                    
                    # Apply default grey border for empty wells
                    for spine in ax.spines.values():
                        spine.set_color('#cccccc')
                        spine.set_linewidth(1)
                        spine.set_visible(True)
                
                # Keep axis visibility for all plots
                ax.set_xticks([])
                ax.set_yticks([])
        
        # Add row labels (A-H) with proper alignment to match the actual plots
        for i, row in enumerate(row_labels):
            # Calculate the exact y-position by using the axes position
            ax = fig.axes[i*12]  # Get the first plot in this row
            # Get the vertical center of this axes
            y_center = (ax.get_position().y0 + ax.get_position().y1) / 2
            fig.text(0.02, y_center, row, ha='center', va='center', fontsize=12, weight='bold')
        
        # Add column labels (1-12) with proper alignment to match the actual plots
        for j, col in enumerate(col_labels):
            # Calculate the exact x-position by using the axes position
            ax = fig.axes[j]  # Get the plot in the first row for this column
            # Get the horizontal center of this axes
            x_center = (ax.get_position().x0 + ax.get_position().x1) / 2
            fig.text(x_center, 0.98, col, ha='center', va='center', fontsize=12, weight='bold')
        
        # Save the composite image with high resolution
        fig.savefig(output_path, dpi=400, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        
        logger.debug(f"Composite image saved to: {output_path}")
        
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.debug(f"Removed temporary file: {temp_file}")
            except Exception as e:
                logger.debug(f"Error deleting temporary file {temp_file}: {e}")
        
        # Clear any references to temporary files in results
        for result in results:
            if 'temp_graph_path' in result:
                del result['temp_graph_path']
                
    except Exception as e:
        logger.error(f"Error creating composite image: {e}")
        logger.debug("Error details:", exc_info=True)
        # Clean up temporary files on error
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
    
    return output_path