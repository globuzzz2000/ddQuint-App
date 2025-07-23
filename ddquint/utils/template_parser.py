#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Template CSV parser module for ddQuint with comprehensive error handling.

Provides functionality to find and parse CSV template files that contain
sample name mappings for well positions. Searches parent directories and
extracts sample descriptions with proper error handling.
"""

import os
import csv
import time
import logging

from ..config import Config, FileProcessingError, TemplateError

logger = logging.getLogger(__name__)


def find_template_file(input_dir):
    """
    Find the CSV template file based on the input directory name.
    Searches in folders from the configured parent directory levels.
    
    Args:
        input_dir (str): Input directory path
        
    Returns:
        str: Path to the template file or None if not found
        
    Raises:
        FileProcessingError: If input directory is invalid
    """
    config = Config.get_instance()

    if not os.path.exists(input_dir):
        error_msg = f"Input directory does not exist: {input_dir}"
        logger.error(error_msg)
        raise FileProcessingError(error_msg)
    
    # Get the base name of the input directory
    dir_name = os.path.basename(input_dir)
    template_name = f"{dir_name}.csv"
    
    logger.debug(f"Looking for template file: {template_name}")
    logger.debug(f"Input directory: {input_dir}")
    
    # Go up configured number of parent directories
    try:
        current_dir = input_dir
        for _ in range(config.TEMPLATE_SEARCH_PARENT_LEVELS):
            current_dir = os.path.dirname(current_dir)
        
        parent_dir = current_dir
        logger.debug(f"Searching in parent directory ({config.TEMPLATE_SEARCH_PARENT_LEVELS} levels up): {parent_dir}")
        
        # Search in all subdirectories
        for root, dirs, files in os.walk(parent_dir):
            for file in files:
                if file == template_name:
                    template_path = os.path.join(root, file)
                    logger.debug(f"Template file found: {template_path}")
                    return template_path
        
        logger.debug(f"Template file {template_name} not found")
        return None
        
    except Exception as e:
        logger.warning(f"Error searching for template file: {str(e)}")
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        return None


def find_header_row(file_path):
    """
    Find the row containing 'Well' column header with robust file access handling.
    
    Args:
        file_path (str): Path to CSV file
        
    Returns:
        int: Row number (0-indexed) containing headers, or -1 if not found
        
    Raises:
        FileProcessingError: If file cannot be read after retries
    """
    if not os.path.exists(file_path):
        error_msg = f"Template file does not exist: {file_path}"
        logger.error(error_msg)
        raise FileProcessingError(error_msg)
    
    max_retries = 3
    retry_delay = 0.5
    
    for attempt in range(max_retries):
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                lines = csvfile.readlines()
                
                for row_num, line in enumerate(lines):
                    # Check if this line contains 'Well' column
                    if 'Well,' in line:
                        logger.debug(f"Found 'Well' header in row {row_num}")
                        return row_num
                        
            logger.debug("'Well' header not found in template file")
            return -1
            
        except (PermissionError, OSError) as e:
            if attempt < max_retries - 1:
                logger.debug(f"Template file access failed on attempt {attempt + 1}, retrying in {retry_delay}s: {str(e)}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                error_msg = f"Template file access failed after {max_retries} attempts: {os.path.basename(file_path)}"
                logger.error(error_msg)
                logger.debug(f"Final error: {str(e)}", exc_info=True)
                raise FileProcessingError(error_msg) from e
        except Exception as e:
            error_msg = f"Error reading template file {os.path.basename(file_path)}: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Error details: {str(e)}", exc_info=True)
            raise FileProcessingError(error_msg) from e


def parse_template_file(template_path):
    """
    Parse the CSV template file to extract sample names from Well and Sample description columns.
    
    Args:
        template_path (str): Path to the template CSV file
        
    Returns:
        dict: Mapping of well IDs to sample names
        
    Raises:
        TemplateError: If template parsing fails
        FileProcessingError: If template file cannot be read
    """
    logger.debug(f"Parsing template file: {os.path.basename(template_path)}")
    
    well_to_name = {}
    max_retries = 3
    retry_delay = 0.5
    
    for attempt in range(max_retries):
        try:
            # First, find which row contains the headers
            header_row = find_header_row(template_path)
            
            if header_row == -1:
                error_msg = f"Could not find header row in template file: {os.path.basename(template_path)}"
                logger.error(error_msg)
                raise TemplateError(error_msg)
            
            logger.debug(f"Header row found at index: {header_row}")
            
            # Read the file, skipping to the header row
            with open(template_path, 'r', newline='', encoding='utf-8') as csvfile:
                # Skip rows before the header
                for _ in range(header_row):
                    next(csvfile)
                
                # Create reader starting from header row
                reader = csv.DictReader(csvfile)
                
                # Check for required columns
                required_columns = ['Well', 'Sample description 1', 'Sample description 2', 
                                  'Sample description 3', 'Sample description 4']
                
                if not reader.fieldnames:
                    error_msg = f"No fieldnames found in template file: {os.path.basename(template_path)}"
                    logger.error(error_msg)
                    raise TemplateError(error_msg)
                
                missing_columns = []
                for col in required_columns:
                    if col not in reader.fieldnames:
                        missing_columns.append(col)
                        logger.warning(f"Column '{col}' not found in template")
                
                if missing_columns:
                    logger.warning(f"Missing columns: {missing_columns}")
                    logger.debug(f"Available columns: {reader.fieldnames}")
                
                # Process each row
                for row_num, row in enumerate(reader, start=header_row + 2):
                    well_id = row.get('Well', '').strip()
                    
                    # Skip empty wells
                    if not well_id:
                        continue
                    
                    # Combine Sample description columns with " - " separator
                    sample_description_parts = []
                    for i in range(1, 5):
                        part = row.get(f'Sample description {i}', '').strip()
                        if part:  # Only add non-empty parts
                            sample_description_parts.append(part)
                    
                    if sample_description_parts:
                        sample_name = ' - '.join(sample_description_parts)
                        
                        # Check for duplicate well IDs with different names
                        if well_id in well_to_name and well_to_name[well_id] != sample_name:
                            logger.warning(f"Multiple descriptions for well {well_id}: "
                                           f"'{well_to_name[well_id]}' vs '{sample_name}'")
                        else:
                            well_to_name[well_id] = sample_name
                    else:
                        continue
            
            logger.debug(f"Finished parsing template. Found {len(well_to_name)} unique well-sample mappings")
            return well_to_name
            
        except (TemplateError, FileProcessingError):
            # Re-raise template and file processing errors as-is
            raise
        except (PermissionError, OSError) as e:
            if attempt < max_retries - 1:
                logger.debug(f"Template file access failed on attempt {attempt + 1}, retrying in {retry_delay}s: {str(e)}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                error_msg = f"Template file access failed after {max_retries} attempts: {os.path.basename(template_path)}"
                logger.error(error_msg)
                logger.debug(f"Final error: {str(e)}", exc_info=True)
                raise FileProcessingError(error_msg) from e
        except Exception as e:
            error_msg = f"Error parsing template file {os.path.basename(template_path)}: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Error details: {str(e)}", exc_info=True)
            raise TemplateError(error_msg) from e


def get_sample_names(input_dir):
    """
    Get sample names for all wells based on the template file.
    
    Args:
        input_dir (str): Input directory path
        
    Returns:
        dict: Mapping of well IDs to sample names (empty dict if no template)
        
    Raises:
        FileProcessingError: If input directory is invalid
    """
    logger.debug(f"Getting sample names for directory: {os.path.basename(input_dir)}")
    
    if not os.path.exists(input_dir):
        error_msg = f"Input directory does not exist: {input_dir}"
        logger.error(error_msg)
        raise FileProcessingError(error_msg)
    
    try:
        template_path = find_template_file(input_dir)
        
        if template_path:
            logger.debug(f"Template file found: {os.path.basename(template_path)}")
            sample_names = parse_template_file(template_path)
            logger.debug(f"Successfully parsed {len(sample_names)} sample names from template")
            return sample_names
        else:
            logger.info(f"No template file found for {os.path.basename(input_dir)}")
            return {}
            
    except (TemplateError, FileProcessingError):
        # Re-raise specific errors
        raise
    except Exception as e:
        error_msg = f"Unexpected error getting sample names for {os.path.basename(input_dir)}: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        raise FileProcessingError(error_msg) from e