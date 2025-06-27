#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ddQuint: Digital Droplet PCR Quintuplex Analysis

Enhanced main entry point with comprehensive configuration support, 
template selection capabilities, and robust error handling.

This module provides the primary command-line interface for the ddQuint
pipeline, handling argument parsing, configuration management, file
selection, and orchestrating the complete analysis workflow.
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
from .config import Config, display_config, generate_config_template, ddQuintError, ConfigError, FileProcessingError

logger = logging.getLogger(__name__)

# Suppress wxPython warning message on macOS
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

from .utils import select_directory, select_file, mark_selection_complete, get_sample_names
from .core import process_directory, create_list_report
from .visualization import create_composite_image

def setup_logging(debug=False):
    """
    Configure logging for the application.
    
    Sets up both file and console logging with appropriate formatting
    and log levels based on debug mode settings.
    
    Args:
        debug: Enable debug mode with detailed logging
        
    Returns:
        Path to the log file for reference
        
    Raises:
        ConfigError: If logging setup fails
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
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception as e:
        raise ConfigError(f"Failed to create log directory: {log_dir}") from e
        
    log_file = os.path.join(log_dir, f"ddquint_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    # Create file handler
    try:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        ))
    except Exception as e:
        raise ConfigError(f"Failed to create log file handler: {log_file}") from e
    
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
    logger = logging.getLogger(__name__)
    
    if debug:
        logger.debug(f"Debug mode enabled")
        logger.debug(f"Log file: {log_file}")
        logger.debug(f"Python version: {sys.version}")
        logger.debug(f"Platform: {sys.platform}")
    
    return log_file

def parse_arguments():
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="ddQuint: Digital Droplet PCR Multiplex Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ddquint                           # Interactive mode with GUI
  ddquint --dir /path/to/csv        # Process specific directory
  ddquint --config                  # Display configuration
  ddquint --config template         # Generate config template
  ddquint --test --dir /path        # Test mode (preserves input files)
        """
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
        True if configuration command was handled and should exit
        
    Raises:
        ConfigError: If configuration file loading fails
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
        try:
            success = Config.load_from_file(config_arg)
            if success:
                logger.info(f"Configuration loaded from {config_arg}")
            else:
                error_msg = f"Failed to load configuration from {config_arg}"
                logger.error(error_msg)
                raise ConfigError(error_msg)
        except Exception as e:
            error_msg = f"Error loading configuration from {config_arg}: {str(e)}"
            logger.error(error_msg)
            raise ConfigError(error_msg) from e
        return False  # Continue with main execution after loading config
    elif config_arg:
        # Invalid config argument
        error_msg = f"Configuration file not found: {config_arg}"
        logger.error(error_msg)
        raise ConfigError(error_msg)
    return False

def get_template_file(template_arg, input_dir):
    """
    Get the template file path based on the template argument.
    
    Args:
        template_arg: Template argument from command line
        input_dir: Input directory path for context
        
    Returns:
        Path to template file or None if not found/selected
        
    Raises:
        FileProcessingError: If template file cannot be processed
    """
    logger.debug(f"Template argument received: {repr(template_arg)}")
    
    if template_arg is None:
        # No template flag specified, use automatic discovery
        logger.debug("No template flag specified, using automatic discovery")
        return None
    elif template_arg == "prompt":
        # Prompt user to select template file
        logger.debug("Template flag set to 'prompt', showing file selection dialog")
        logger.info(">>> Please select template file for well names <<<\n")
        
        # Use GUI file selector with CSV filter
        with silence_stderr():
            template_path = select_file(
                title="Select Template File for Well Names",
                wildcard="CSV files (*.csv)|*.csv|All files (*.*)|*.*",
                file_type="template"
            )
        
        if template_path:
            logger.debug(f"Template file selected: {template_path}")
            return template_path
        else:
            logger.debug("No template file selected, proceeding without template")
            return None
    elif os.path.isfile(template_arg):
        # Template file path provided directly
        logger.debug(f"Template file path provided: {template_arg}")
        if template_arg.lower().endswith('.csv'):
            logger.debug(f"Using template file: {template_arg}")
            return template_arg
        else:
            logger.warning(f"Template file is not a CSV file: {template_arg}")
            logger.info(f"Warning: Template file '{template_arg}' is not a CSV file. Proceeding without template.")
            return None
    else:
        # Invalid template file path
        error_msg = f"Template file not found: {template_arg}"
        logger.error(error_msg)
        raise FileProcessingError(error_msg, filename=template_arg)

def parse_manual_template(template_path):
    """
    Parse a manually specified template file to extract sample names.
    
    Args:
        template_path: Path to the template file
        
    Returns:
        Dictionary mapping well IDs to sample names
        
    Raises:
        FileProcessingError: If template parsing fails
    """
    try:
        # Import the template parsing function
        from .utils.template_parser import parse_template_file
        
        logger.debug(f"Parsing manual template file: {template_path}")
        sample_names = parse_template_file(template_path)
        
        if sample_names:
            logger.debug(f"Successfully loaded {len(sample_names)} sample names from template file")
            if logger.isEnabledFor(logging.DEBUG):
                for well, name in list(sample_names.items())[:5]:  # Show first 5 entries
                    logger.debug(f"  {well}: {name}")
                if len(sample_names) > 5:
                    logger.debug(f"  ... and {len(sample_names) - 5} more entries")
        else:
            logger.warning("No sample names found in template file")
            
        return sample_names
        
    except Exception as e:
        error_msg = f"Error parsing template file {template_path}: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        logger.info(f"Error parsing template file '{template_path}': {str(e)}")
        logger.info("Proceeding without template...")
        raise FileProcessingError(error_msg, filename=template_path) from e

def create_test_output_directory(input_dir):
    """
    Create a test output directory based on the input directory name.
    
    Args:
        input_dir: Input directory path
        
    Returns:
        Path to the created test output directory
        
    Raises:
        FileProcessingError: If directory creation fails
    """
    # Get the parent directory and input directory name
    parent_dir = os.path.dirname(input_dir)
    input_name = os.path.basename(input_dir)
    
    # Create test output directory name with timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    test_output_name = f"{input_name}_test_{timestamp}"
    test_output_dir = os.path.join(parent_dir, test_output_name)
    
    # Create the directory
    try:
        os.makedirs(test_output_dir, exist_ok=True)
        logger.debug(f"Test mode: Output will be saved to {test_output_dir}")
        logger.debug(f"Test mode: Input files in {input_dir} will remain untouched")
        return test_output_dir
    except Exception as e:
        error_msg = f"Failed to create test output directory: {test_output_dir}"
        logger.error(error_msg)
        raise FileProcessingError(error_msg) from e

def main():
    """
    Main function to run the ddQuint application.
    
    Orchestrates the complete analysis pipeline including argument parsing,
    configuration handling, file processing, and report generation.
    
    Raises:
        ddQuintError: For any application-specific errors
    """
    try:
        # Parse command line arguments first to check for test mode
        args = parse_arguments()
        
        # Setup logging
        log_file = setup_logging(debug=args.debug)
        
        # Print header with test mode indication
        if args.test:
            logger.info("=== ddPCR Quintuplex Analysis - Test Mode ===")
        else:
            logger.info("=== ddPCR Quintuplex Analysis ===")
        
        # Handle configuration commands
        if args.config:
            if handle_config_command(args.config):
                return  # Exit if configuration command was handled
        
        # Get input directory
        input_dir = args.dir
        if not input_dir:
            logger.info("\n>>> Please select folder with amplitude CSV files <<<\n")
            # Silence stderr to avoid NSOpenPanel warning
            with silence_stderr():
                input_dir = select_directory()
            if not input_dir:
                logger.info("No directory selected. Exiting.")
                return
        
        if not os.path.exists(input_dir):
            error_msg = f"Input directory not found: {input_dir}"
            logger.error(error_msg)
            raise FileProcessingError(error_msg)
        
        logger.debug(f"Input directory: {input_dir}")
        
        # Handle template file selection
        template_path = get_template_file(args.template, input_dir)
        
        # Mark file selection as complete (important for GUI cleanup)
        try:
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
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            error_msg = f"Failed to create output directory: {output_dir}"
            logger.error(error_msg)
            raise FileProcessingError(error_msg) from e
        
        # Create directory name pattern for graphs and raw data
        config = Config.get_instance()
        graphs_dir = os.path.join(output_dir, config.GRAPHS_DIR_NAME)
        raw_data_dir = os.path.join(output_dir, config.RAW_DATA_DIR_NAME)
        
        try:
            os.makedirs(graphs_dir, exist_ok=True)
            os.makedirs(raw_data_dir, exist_ok=True)
        except Exception as e:
            error_msg = f"Failed to create output subdirectories"
            logger.error(error_msg)
            raise FileProcessingError(error_msg) from e
        
        # Process the directory with sample names (test_mode parameter)
        results = process_directory(input_dir, output_dir, sample_names, 
                                  verbose=args.verbose, test_mode=args.test)
        
        # Create output files if we have results
        if results:
            _create_output_files(results, output_dir, sample_names, config)
            _log_summary_statistics(results, output_dir, template_path, sample_names, args)
        else:
            logger.info("No valid results were generated.")
        
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user.")
    except ddQuintError as e:
        logger.error(f"ddQuint error: {str(e)}")
        if args and args.verbose:
            traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        if args and args.verbose:
            traceback.print_exc()
        sys.exit(1)

def _create_output_files(results, output_dir, sample_names, config):
    """Create all output files from processing results."""
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

def _log_summary_statistics(results, output_dir, template_path, sample_names, args):
    """Log summary statistics and completion messages."""
    # Count aneuploid and buffer zone samples
    aneuploid_count = sum(1 for r in results if r.get('has_aneuploidy', False))
    buffer_zone_count = sum(1 for r in results if r.get('has_buffer_zone', False))
    
    logger.info(f"\nProcessed {len(results)} files ({aneuploid_count} potential aneuploidies, {buffer_zone_count} buffer zone samples)")
    logger.info(f"Results saved to: {os.path.abspath(output_dir)}")
    
    if template_path:
        logger.debug(f"Sample names loaded from: {os.path.basename(template_path)}")
    elif sample_names:
        logger.debug(f"Sample names auto-discovered from template")
    
    logger.info("\n=== Analysis complete ===")

if __name__ == "__main__":
    main()