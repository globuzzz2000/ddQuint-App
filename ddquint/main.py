#!/usr/bin/env python
"""
ddQuint: Digital Droplet PCR Quintuplex Analysis
Enhanced main entry point with configuration support and manual template selection
"""

import argparse
import os
import sys
import datetime
import traceback
import warnings
import logging

# Filter warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*force_all_finite.*")
warnings.filterwarnings("ignore", message=".*SettingWithCopyWarning.*")

# Import configuration modules
from .config import Config, display_config, generate_config_template

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

from .utils.gui import select_directory, select_file, mark_selection_complete
from .utils.template_parser import get_sample_names
from .core.file_processor import process_directory
from .visualization import create_composite_image
from .reporting import create_plate_report, create_list_report

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
    parser.add_argument(
        "--template",
        nargs="?",
        const="prompt",
        help="Template file path for well names, or 'prompt' to select via GUI"
    )
    parser.add_argument(
        "--plate",
        nargs="?",
        const="default",
        help="Generate plate format Excel report. Use 'rotated' to also generate rotated layout without absolute counts"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: creates output in separate folder without moving input files"
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

def get_template_file(template_arg, input_dir):
    """
    Get the template file path based on the template argument.
    
    Args:
        template_arg: Template argument from command line
        input_dir: Input directory path
        
    Returns:
        str: Path to template file or None if not found/selected
    """
    logger = logging.getLogger("ddQuint")
    
    # Debug: Show what template_arg we received
    logger.debug(f"Template argument received: {repr(template_arg)}")
    
    if template_arg is None:
        # No template flag specified, use automatic discovery
        logger.debug("No template flag specified, using automatic discovery")
        return None
    elif template_arg == "prompt":
        # Prompt user to select template file
        logger.debug("Template flag set to 'prompt', showing file selection dialog")
        print("\n>>> Please select template file for well names <<<")
        
        # Use GUI file selector with CSV filter
        with silence_stderr():
            template_path = select_file(
                title="Select Template File for Well Names",
                wildcard="CSV files (*.csv)|*.csv|All files (*.*)|*.*",
                file_type="template"
            )
        
        if template_path:
            logger.info(f"Template file selected: {template_path}")
            return template_path
        else:
            logger.info("No template file selected, proceeding without template")
            return None
    elif os.path.isfile(template_arg):
        # Template file path provided directly
        logger.debug(f"Template file path provided: {template_arg}")
        if template_arg.lower().endswith('.csv'):
            logger.debug(f"Using template file: {template_arg}")
            return template_arg
        else:
            logger.warning(f"Template file is not a CSV file: {template_arg}")
            print(f"Warning: Template file '{template_arg}' is not a CSV file. Proceeding without template.")
            return None
    else:
        # Invalid template file path
        logger.warning(f"Template file not found: {template_arg}")
        print(f"Warning: Template file '{template_arg}' not found. Proceeding without template.")
        return None

def parse_manual_template(template_path):
    """
    Parse a manually specified template file to extract sample names.
    
    Args:
        template_path: Path to the template file
        
    Returns:
        dict: Mapping of well IDs to sample names
    """
    logger = logging.getLogger("ddQuint")
    
    try:
        # Import the template parsing function
        from .utils.template_parser import parse_template_file
        
        logger.debug(f"Parsing manual template file: {template_path}")
        sample_names = parse_template_file(template_path)
        
        if sample_names:
            logger.info(f"Successfully loaded {len(sample_names)} sample names from template file")
            if logger.isEnabledFor(logging.DEBUG):
                for well, name in list(sample_names.items())[:5]:  # Show first 5 entries
                    logger.debug(f"  {well}: {name}")
                if len(sample_names) > 5:
                    logger.debug(f"  ... and {len(sample_names) - 5} more entries")
        else:
            logger.warning("No sample names found in template file")
            
        return sample_names
        
    except Exception as e:
        logger.error(f"Error parsing template file: {str(e)}")
        logger.debug("Error details:", exc_info=True)
        print(f"Error parsing template file '{template_path}': {str(e)}")
        print("Proceeding without template...")
        return {}

def create_test_output_directory(input_dir):
    """
    Create a test output directory based on the input directory name.
    
    Args:
        input_dir (str): Input directory path
        
    Returns:
        str: Path to the test output directory
    """
    logger = logging.getLogger("ddQuint")
    
    # Get the parent directory and input directory name
    parent_dir = os.path.dirname(input_dir)
    input_name = os.path.basename(input_dir)
    
    # Create test output directory name with timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    test_output_name = f"{input_name}_test_{timestamp}"
    test_output_dir = os.path.join(parent_dir, test_output_name)
    
    # Create the directory
    os.makedirs(test_output_dir, exist_ok=True)
    
    logger.debug(f"Test mode: Output will be saved to {test_output_dir}")
    logger.debug(f"Test mode: Input files in {input_dir} will remain untouched")
    
    return test_output_dir

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
            logger.info(">>> Please select folder with amplitude CSV files <<<")
            # Silence stderr to avoid NSOpenPanel warning
            with silence_stderr():
                input_dir = select_directory()
            if not input_dir:
                logger.info("No directory selected. Exiting.")
                return
        
        logger.debug(f"Input directory: {input_dir}")
        
        # Handle template file selection
        template_path = get_template_file(args.template, input_dir)
        
        # Mark file selection as complete (important for GUI cleanup)
        try:
            from .utils.gui import mark_selection_complete
            mark_selection_complete()
        except Exception as e:
            logger.debug(f"Could not mark selection complete: {e}")
        
        # Get sample names
        if template_path:
            # Use manually specified template file
            logger.debug(f"Using manual template file: {template_path}")
            sample_names = parse_manual_template(template_path)
        else:
            # Use automatic template discovery
            logger.debug("Using automatic template discovery")
            sample_names = get_sample_names(input_dir)
        
        logger.debug(f"Found {len(sample_names)} sample names")
        
        # Determine output directory based on test mode
        if args.test:
            output_dir = create_test_output_directory(input_dir)
        else:
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
        
        # Process the directory with sample names (test_mode parameter)
        results = process_directory(input_dir, output_dir, sample_names, verbose=args.verbose, test_mode=args.test)
        
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
            
            # Create list format report
            list_path = os.path.join(output_dir, "List_Results.xlsx")
            create_list_report(results, list_path)
            
            # Create plate format report if requested
            if args.plate is not None:
                # Always create the default plate report
                excel_path = os.path.join(output_dir, config.EXCEL_OUTPUT_FILENAME)
                create_plate_report(results, excel_path, rotated=False)
                
                # If "rotated" was specified, also create the rotated version
                if args.plate == "rotated":
                    rotated_path = os.path.join(output_dir, "Plate_Results_Rotated.xlsx")
                    create_plate_report(results, rotated_path, rotated=True)
            
            # Count aneuploid and buffer zone samples
            aneuploid_count = sum(1 for r in results if r.get('has_aneuploidy', False))
            buffer_zone_count = sum(1 for r in results if r.get('has_buffer_zone', False))
            
            logger.info(f"\nProcessed {len(results)} files ({aneuploid_count} potential aneuploidies, {buffer_zone_count} buffer zone samples)")
            logger.info(f"\nResults saved to: {os.path.abspath(output_dir)}")
            
            if template_path:
                logger.debug(f"Sample names loaded from: {os.path.basename(template_path)}")
            elif sample_names:
                logger.debug(f"Sample names auto-discovered from template")
            
            if args.test:
                logger.debug(f"Test mode: Input files remain in: {os.path.abspath(input_dir)}")
            
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