#!/usr/bin/env python
"""
ddQuint: Digital Droplet PCR Quintuplex Analysis
Enhanced main entry point with configuration support
"""

import argparse
import os
import sys
import datetime
import traceback
import warnings
import concurrent.futures
import logging
from pathlib import Path

# Filter warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*force_all_finite.*")
warnings.filterwarnings("ignore", message=".*SettingWithCopyWarning.*")

# Import configuration modules
from ddquint.config.config import Config
from ddquint.config.config_display import display_config
from ddquint.config.template_generator import generate_config_template

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
from ddquint.utils.template_parser import get_sample_names

def setup_logging(debug=False):
    """
    Configure logging for the application.
    
    Args:
        debug: Enable debug mode
        
    Returns:
        str: Path to the log file
    """
    # Update Config debug mode
    Config.DEBUG_MODE = debug
    
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Different log formats based on debug mode
    if debug:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    else:
        log_format = '%(message)s'
    
    # Set up logging to file
    log_dir = os.path.join(os.path.expanduser("~"), ".ddquint", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"ddquint_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    ))
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Clear existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add the handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Configure our specific logger
    logger = logging.getLogger("ddQuint")
    
    if debug:
        logger.debug(f"Debug mode enabled: {debug}")
        logger.debug(f"Log file: {log_file}")
        logger.debug(f"Python version: {sys.version}")
        logger.debug(f"Platform: {sys.platform}")
    else:
        logger.debug(f"Log file: {log_file}")
    
    return log_file

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
        "--debug",
        action="store_true",
        help="Enable debug mode with detailed logging"
    )
    parser.add_argument(
        "--config",
        nargs="?",  
        const=True,
        help="Configuration file or command (display, template, or path to config file)"
    )
    
    return parser.parse_args()

def handle_config_command(config_arg):
    """
    Handle configuration-related commands.
    
    Args:
        config_arg: Configuration argument from command line
        
    Returns:
        bool: True if configuration command was handled, False otherwise
    """
    if config_arg is True or config_arg == "display": 
        # Display current configuration
        display_config(Config)
        return True
    elif config_arg == "template":
        # Generate configuration template
        generate_config_template(Config)
        return True
    elif config_arg and os.path.isfile(config_arg):
        # Load configuration from file
        success = Config.load_from_file(config_arg)
        if success:
            print(f"Configuration loaded from {config_arg}")
        else:
            print(f"Error loading configuration from {config_arg}")
        return False  # Continue with main execution after loading config
    return False

def main():
    """Main function to run the application."""
    
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Setup logging
        setup_logging(debug=args.debug)
        logger = logging.getLogger("ddQuint")
        logger.info("=== ddPCR Quintuplex Analysis ===")
        
        # Handle configuration commands
        if args.config:
            if handle_config_command(args.config):
                return  # Exit if configuration command was handled
        
        # Get input directory
        input_dir = args.dir
        if not input_dir:
            # Silence stderr to avoid NSOpenPanel warning
            with silence_stderr():
                input_dir = select_directory()
            if not input_dir:
                logger.info("No directory selected. Exiting.")
                return
        
        logger.debug(f"Input directory: {input_dir}")
        
        # Get output directory
        output_dir = args.output if args.output else input_dir
        logger.debug(f"Output directory: {output_dir}")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create directory name pattern for graphs and raw data
        config = Config.get_instance()
        graphs_dir = os.path.join(output_dir, config.GRAPHS_DIR_NAME)
        raw_data_dir = os.path.join(output_dir, config.RAW_DATA_DIR_NAME)
        os.makedirs(graphs_dir, exist_ok=True)
        os.makedirs(raw_data_dir, exist_ok=True)
        
        # Get sample names from template file
        sample_names = get_sample_names(input_dir)
        logger.debug(f"Found {len(sample_names)} sample names")
        
        # Process the directory with sample names
        results = process_directory(input_dir, output_dir, sample_names, verbose=args.verbose)
        
        # Create output files if we have results
        if results:
            # Add sample names to results
            for result in results:
                well_id = result.get('well')
                if well_id and well_id in sample_names:
                    result['sample_name'] = sample_names[well_id]
            
            # Create composite image with sample names
            composite_path = os.path.join(output_dir, config.COMPOSITE_IMAGE_FILENAME)
            create_composite_image(results, composite_path)
            
            # Create Excel report with sample names
            excel_path = os.path.join(output_dir, config.EXCEL_OUTPUT_FILENAME)
            create_excel_report(results, excel_path)
            
            # Count aneuploid samples
            aneuploid_count = sum(1 for r in results if r.get('has_aneuploidy', False))
            
            logger.info(f"\nProcessed {len(results)} files ({aneuploid_count} potential aneuploidies)")
            logger.info(f"Results saved to: {os.path.abspath(output_dir)}")
            logger.info("=== Analysis complete ===")
            logger.info("")
            
        else:
            logger.info("No valid results were generated.")
        
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user.")
    except Exception as e:
        logger.info(f"\nError: {str(e)}")
        if args and args.verbose:
            traceback.print_exc()

if __name__ == "__main__":
    main()