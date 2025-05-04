#!/usr/bin/env python
"""
ddQuint: Digital Droplet PCR Multiplex Analysis
Enhanced main entry point for the application
"""

import argparse
import os
import sys
import datetime
import traceback
import warnings
import concurrent.futures
from pathlib import Path

# Filter warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*force_all_finite.*")
warnings.filterwarnings("ignore", message=".*SettingWithCopyWarning.*")

# Suppress wxPython warning message
if sys.platform == 'darwin':
    import contextlib
    import os
    
    @contextlib.contextmanager
    def silence_stderr():
        """Silence stderr output to prevent NSOpenPanel warning."""
        old_fd = os.dup(2)
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, 2)
            os.close(devnull)
            yield
        finally:
            os.dup2(old_fd, 2)
            os.close(old_fd)
else:
    @contextlib.contextmanager
    def silence_stderr():
        """No-op context manager for non-macOS platforms."""
        yield

from ddquint.utils.gui import select_directory
from ddquint.core.file_processor import process_directory
from ddquint.visualization.plate_plots import create_composite_image
from ddquint.reporting.excel_report import create_excel_report

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="ddQuint: Digital Droplet PCR Multiplex Analysis"
    )
    parser.add_argument(
        "--dir", 
        help="Directory containing CSV files to process"
    )
    parser.add_argument(
        "--output", 
        help="Output directory for results (defaults to input directory)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable verbose output"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Enable parallel processing of files"
    )
    
    return parser.parse_args()

def main():
    """Main function to run the application."""
    print("=== ddPCR Quintuplex Analysis ===")
    
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Get input directory
        input_dir = args.dir
        if not input_dir:
            # Silence stderr to avoid NSOpenPanel warning
            with silence_stderr():
                input_dir = select_directory()
            if not input_dir:
                print("No directory selected. Exiting.")
                return
        
        # Get output directory
        output_dir = args.output if args.output else input_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Get sample names from template file
        from ddquint.utils.template_parser import get_sample_names
        sample_names = get_sample_names(input_dir)
        
        # Process the directory with sample names
        results = process_directory(input_dir, output_dir, sample_names, verbose=args.verbose)
        
        # Create output files if we have results
        if results:
            # Add sample names to results
            for result in results:
                well_id = result.get('well')
                if well_id and well_id in sample_names:
                    result['sample_name'] = sample_names[well_id]
            
            # Create output subdirectories
            graphs_dir = os.path.join(output_dir, "Graphs")
            os.makedirs(graphs_dir, exist_ok=True)
            
            # Create composite image with sample names
            composite_path = os.path.join(output_dir, "Graph_Overview.png")
            create_composite_image(results, composite_path)
            
            # Create Excel report with sample names
            excel_path = os.path.join(output_dir, "Plate_Results.xlsx")
            create_excel_report(results, excel_path)
            
            # Count aneuploid samples
            aneuploid_count = sum(1 for r in results if r.get('has_aneuploidy', False))
            

            print(f"\nProcessed {len(results)} files ({aneuploid_count} potential aneuploidies)")
            print(f"Results saved to: {os.path.abspath(output_dir)}")
            print("=== Analysis complete ===")
            print("")
            
        else:
            print("No valid results were generated.")
        
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
    except Exception as e:
        print(f"\nError: {str(e)}")
        if args and args.verbose:
            traceback.print_exc()

if __name__ == "__main__":
    main()