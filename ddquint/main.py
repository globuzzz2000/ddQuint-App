#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ddQuint: Digital Droplet PCR Quintuplex Analysis

Main entry point with comprehensive configuration support, 
template selection capabilities, and robust error handling.

This module provides the primary command-line interface for the ddQuint
pipeline, handling argument parsing, configuration management, file
selection, and orchestrating the complete analysis workflow.
"""

import argparse
import os
import sys
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
from .utils.parameter_editor import open_parameter_editor, load_parameters_if_exist

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

from .utils import select_directory, select_file, mark_selection_complete, get_sample_names, create_template_from_file, select_multiple_directories
from .core import process_directory, create_list_report
from .visualization import create_composite_image

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
  ddquint                           # Interactive analysis mode with GUI
  ddquint --dir /path/to/csv        # Process specific directory
  ddquint --batch                   # Process multiple directories with GUI selection
  ddquint --parameters              # Open parameter editor GUI
  ddquint --QXtemplate              # Interactively create a plate template
  ddquint --QXtemplate list.xlsx    # Create template from a specific file
  ddquint --config                  # Display configuration
  ddquint --config template         # Generate config template
        """
    )
    parser.add_argument(
        "--dir", 
        help="Directory containing CSV files to process"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process multiple directories (allows selection of multiple folders)"
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
        "--QXtemplate",
        nargs="?",
        const="prompt",
        default=None,
        help="Create a plate template from a sample list (CSV/Excel). "
             "Optionally provide a path or use 'prompt' for a GUI selector."
    )
    parser.add_argument(
        "--parameters",
        action="store_true",
        help="Open parameter editor GUI for EXPECTED_CENTROIDS and HDBSCAN settings"
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

def get_input_directories(args):
    """
    Get input directories based on command line arguments.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        List of input directory paths
        
    Raises:
        FileProcessingError: If directories cannot be accessed
    """
    if args.dir:
        # Single directory specified
        if not os.path.exists(args.dir):
            error_msg = f"Input directory not found: {args.dir}"
            logger.error(error_msg)
            raise FileProcessingError(error_msg)
        return [args.dir]
    
    elif args.batch:
        # Multiple directories selection
        logger.info("\n>>> Please select multiple folders with amplitude CSV files <<<\n")
        with silence_stderr():
            input_dirs = select_multiple_directories()
        
        if not input_dirs:
            logger.info("No directories selected. Exiting.")
            return []
        
        # Validate all directories exist
        invalid_dirs = [d for d in input_dirs if not os.path.exists(d)]
        if invalid_dirs:
            error_msg = f"Input directories not found: {invalid_dirs}"
            logger.error(error_msg)
            raise FileProcessingError(error_msg)
        
        return input_dirs
    
    else:
        # Interactive single directory selection
        logger.info("\n>>> Please select folder with amplitude CSV files <<<\n")
        with silence_stderr():
            input_dir = select_directory()
        
        if not input_dir:
            logger.info("No directory selected. Exiting.")
            return []
        
        if not os.path.exists(input_dir):
            error_msg = f"Input directory not found: {input_dir}"
            logger.error(error_msg)
            raise FileProcessingError(error_msg)
        
        return [input_dir]

def process_single_directory(input_dir, output_dir, template_path, sample_names, args):
    """
    Process a single directory and return results.
    
    Args:
        input_dir: Input directory path
        output_dir: Output directory path
        template_path: Template file path (may be None)
        sample_names: Sample names mapping (may be None)
        args: Command line arguments
        
    Returns:
        List of processing results
    """
    logger.debug(f"Processing directory: {input_dir}")
    
    # Get sample names for this directory
    if template_path:
        dir_sample_names = parse_manual_template(template_path)
    else:
        dir_sample_names = get_sample_names(input_dir)
    
    # Determine output directory for this input
    if output_dir:
        # Use specified output directory, create subdirectory for this input
        dir_output = os.path.join(output_dir, os.path.basename(input_dir))
    else:
        # Use input directory as output
        dir_output = input_dir
    
    logger.debug(f"Output directory: {dir_output}")
    
    # Create output directory if it doesn't exist
    try:
        os.makedirs(dir_output, exist_ok=True)
    except Exception as e:
        error_msg = f"Failed to create output directory: {dir_output}"
        logger.error(error_msg)
        raise FileProcessingError(error_msg) from e
    
    # Create graphs directory
    config = Config.get_instance()
    graphs_dir = os.path.join(dir_output, config.GRAPHS_DIR_NAME)
    
    try:
        os.makedirs(graphs_dir, exist_ok=True)
    except Exception as e:
        error_msg = f"Failed to create graphs directory"
        logger.error(error_msg)
        raise FileProcessingError(error_msg) from e
    
    # Process the directory
    results = process_directory(input_dir, dir_output, dir_sample_names, verbose=args.verbose)
    
    # Create output files if we have results
    if results:
        _create_output_files(results, dir_output, dir_sample_names, config)
        
        # Log summary for this directory
        aneuploid_count = sum(1 for r in results if r.get('has_aneuploidy', False))
        buffer_zone_count = sum(1 for r in results if r.get('has_buffer_zone', False))
        
        logger.info(f"  {os.path.basename(input_dir)}: {len(results)} files ({aneuploid_count} aneuploidies, {buffer_zone_count} buffer zones)\n")
    else:
        logger.info(f"  {os.path.basename(input_dir)}: No valid results")
    
    return results

def main():
    """
    Main function to run the ddQuint application.
    
    Orchestrates the complete analysis pipeline including argument parsing,
    configuration handling, file processing, and report generation.
    
    Raises:
        ddQuintError: For any application-specific errors
    """
    args = None  # Define args here to be available in except blocks
    try:
        # Parse command line arguments first
        args = parse_arguments()
        
        # Setup logging
        from .config import setup_logging
        log_file = setup_logging(debug=args.debug)

        # Load user parameters if they exist (before other config operations)
        from .config import Config
        load_parameters_if_exist(Config)

        # Handle Parameters Editor Flag
        if args.parameters:
            logger.info("=== ddPCR Quintuplex - Parameter Editor ===")
            try:
                if open_parameter_editor(Config):
                    logger.info("Parameters updated successfully")
                else:
                    logger.info("Parameter editing cancelled")
            except Exception as e:
                logger.error(f"Parameter editor failed: {e}")
                if args.verbose or args.debug:
                    traceback.print_exc()
                sys.exit(1)
            return

        # Handle Template Creator Flag
        if args.QXtemplate:
            logger.info("=== ddPCR Quintuplex - Template Creator ===")
            input_file = args.QXtemplate
            
            if input_file == "prompt":
                logger.info("\n>>> Please select the input file (CSV/Excel) containing sample names <<<\n")
                with silence_stderr():
                    input_file = select_file(
                        title="Select Sample List File (CSV or Excel)",
                        wildcard="Supported Files (*.csv;*.xlsx;*.xls)|*.csv;*.xlsx;*.xls|All files (*.*)|*.*",
                        file_type="template"
                    )
            
            if not input_file or not os.path.isfile(input_file):
                logger.info("No valid input file selected. Exiting.")
                return

            try:
                create_template_from_file(input_file)
                logger.info("\n=== Template creation complete ===")
            except (FileProcessingError, ValueError) as e:
                logger.error(f"Template creation failed: {e}")
                sys.exit(1)
            except Exception as e:
                logger.error(f"An unexpected error occurred during template creation: {e}")
                if args.verbose or args.debug:
                    traceback.print_exc()
                sys.exit(1)
            return

        # Print header
        if args.batch:
            logger.info("=== ddPCR Quintuplex Analysis - Batch Mode ===")
        else:
            logger.info("=== ddPCR Quintuplex Analysis ===")
        
        # Handle configuration commands
        if args.config:
            if handle_config_command(args.config):
                return  # Exit if configuration command was handled
        
        # Get input directories
        input_dirs = get_input_directories(args)
        if not input_dirs:
            return
        
        # Handle template file selection (applies to all directories in batch mode)
        template_path = get_template_file(args.template, input_dirs[0])
        
        # Mark file selection as complete
        try:
            mark_selection_complete()
        except Exception as e:
            logger.debug(f"Could not mark selection complete: {e}")
        
        # Process directories
        all_results = []
        
        if len(input_dirs) > 1:
            logger.info(f"\nProcessing {len(input_dirs)} directories:")
        
        for input_dir in input_dirs:
            try:
                results = process_single_directory(input_dir, args.output, template_path, None, args)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Error processing directory {input_dir}: {str(e)}")
                if args.verbose or args.debug:
                    traceback.print_exc()
                continue
        
        logger.info("=== Analysis complete ===")
        
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user.")
    except ddQuintError as e:
        logger.error(f"ddQuint error: {str(e)}")
        if args and (args.verbose or args.debug):
            traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        if args and (args.verbose or args.debug):
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
    list_path = os.path.join(output_dir, "Analysis_Results.xlsx")
    create_list_report(results, list_path)

if __name__ == "__main__":
    main()