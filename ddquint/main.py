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
    print("=" * 50)
    print("ddQuint: Digital Droplet PCR Multiplex Analysis")
    print("=" * 50)
    print(f"Started at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
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
        print(f"\nProcessing directory: {input_dir}")
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
            
            print("\nProcessing complete!")
            print(f"- Individual graphs: {graphs_dir}")
            print(f"- Composite image: {composite_path}")
            print(f"- Excel report: {excel_path}")
        else:
            print("No valid results were generated.")
        
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
    except Exception as e:
        print(f"\nCritical error: {str(e)}")
        traceback.print_exc()
    finally:
        print("\n" + "=" * 50)
        print(f"Finished at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)

if __name__ == "__main__":
    main()