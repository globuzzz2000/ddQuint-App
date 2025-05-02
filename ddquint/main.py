#!/usr/bin/env python
"""
ddQuint: Digital Droplet PCR Multiplex Analysis
Main entry point for the application
"""

import argparse
import os
import sys
import datetime
import traceback
import warnings

# Filter warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*force_all_finite.*")
warnings.filterwarnings("ignore", message=".*SettingWithCopyWarning.*")

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
    
    return parser.parse_args()

def main():
    """Main function to run the application."""
    print("ddQuint: Digital Droplet PCR Multiplex Analysis")
    
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Get input directory
        input_dir = args.dir
        if not input_dir:
            input_dir = select_directory()
            if not input_dir:
                print("No directory selected. Exiting.")
                return
        
        # Get output directory
        output_dir = args.output if args.output else input_dir
        
        # Process the directory
        print(f"Processing files in: {os.path.basename(input_dir)}")
        results = process_directory(input_dir, output_dir, verbose=args.verbose)
        
        # Create output files if we have results
        if results:
            # Create composite image
            graphs_dir = os.path.join(output_dir, "Graphs")
            composite_path = os.path.join(output_dir, "All_Samples_Composite.png")
            create_composite_image(results, composite_path)
            
            # Create Excel report
            excel_path = os.path.join(output_dir, "Plate_Results.xlsx")
            create_excel_report(results, excel_path)
            
            # Count abnormal samples
            abnormal_count = sum(1 for r in results if r.get('has_outlier', False))
            
            print("\nAnalysis complete:")
            print(f"- Processed {len(results)} files ({abnormal_count} marked for review)")
            print(f"- Results saved to: {os.path.basename(output_dir)}")
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