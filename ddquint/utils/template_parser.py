"""
Template CSV parser module for ddQuint with debug logging
"""

import os
import csv
import logging
from pathlib import Path

def find_template_file(input_dir):
    """
    Find the CSV template file based on the input directory name.
    Searches in folders from the -2 parent directory.
    
    Args:
        input_dir (str): Input directory path
        
    Returns:
        str: Path to the template file or None if not found
    """
    logger = logging.getLogger("ddQuint")
    
    # Get the base name of the input directory (without path)
    dir_name = os.path.basename(input_dir)
    template_name = f"{dir_name}.csv"
    
    logger.debug(f"Looking for template file: {template_name}")
    logger.debug(f"Input directory: {input_dir}")
    
    # Go up 2 parent directories
    parent_dir = os.path.dirname(os.path.dirname(input_dir))
    logger.debug(f"Searching in parent directory: {parent_dir}")
    
    # Search in all subdirectories
    for root, dirs, files in os.walk(parent_dir):
        logger.debug(f"Searching in: {root}")
        for file in files:
            logger.debug(f"Found file: {file}")
            if file == template_name:
                template_path = os.path.join(root, file)
                logger.debug(f"Template file found: {template_path}")
                return template_path
    
    logger.debug(f"Template file {template_name} not found")
    return None

def find_header_row(file_path):
    """
    Find the row containing 'Well' column header.
    
    Args:
        file_path (str): Path to CSV file
        
    Returns:
        int: Row number (0-indexed) containing headers, or -1 if not found
    """
    logger = logging.getLogger("ddQuint")
    
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            lines = csvfile.readlines()
            
            for row_num, line in enumerate(lines):
                # Check if this line contains 'Well' column
                if 'Well,' in line:
                    logger.debug(f"Found 'Well' header in row {row_num}")
                    return row_num
    except Exception as e:
        logger.error(f"Error finding header row: {str(e)}")
    
    return -1

def parse_template_file(template_path):
    """
    Parse the CSV template file to extract sample names from Well column and Sample description columns.
    
    Args:
        template_path (str): Path to the template CSV file
        
    Returns:
        dict: Mapping of well IDs to sample names
    """
    logger = logging.getLogger("ddQuint")
    logger.debug(f"Parsing template file: {template_path}")
    
    well_to_name = {}
    
    try:
        # First, find which row contains the headers
        header_row = find_header_row(template_path)
        
        if header_row == -1:
            logger.error("Could not find header row in template file")
            return {}
        
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
            
            header_found = True
            for col in required_columns:
                if col not in reader.fieldnames:
                    logger.warning(f"Column '{col}' not found. Available columns: {reader.fieldnames}")
                    header_found = False
            
            if not header_found:
                # Try to find similar column names
                logger.debug("Trying to find similar column names...")
                available_cols = reader.fieldnames if reader.fieldnames else []
                logger.debug(f"Available columns: {available_cols}")
            
            # Process each row
            for row_num, row in enumerate(reader, start=header_row+2):  # +2 because header row is 0-indexed and data starts at next row
                well_id = row.get('Well', '').strip()
                
                # Skip empty wells
                if not well_id:
                    logger.debug(f"Row {row_num}: Empty well identifier")
                    continue
                
                # Combine Sample description columns with " - " separator
                sample_description_parts = []
                for i in range(1, 5):
                    part = row.get(f'Sample description {i}', '').strip()
                    if part:  # Only add non-empty parts
                        sample_description_parts.append(part)
                
                if sample_description_parts:
                    sample_name = ' - '.join(sample_description_parts)
                    
                    # If well already exists, all instances should have the same name
                    # so we just log if they differ
                    if well_id in well_to_name and well_to_name[well_id] != sample_name:
                        logger.warning(f"Multiple descriptions for well {well_id}: "
                                       f"'{well_to_name[well_id]}' vs '{sample_name}'")
                    else:
                        well_to_name[well_id] = sample_name
                        logger.debug(f"Row {row_num}: Well {well_id} -> sample '{sample_name}'")
                else:
                    logger.debug(f"Row {row_num}: Well {well_id} has no sample description")
        
        logger.debug(f"Finished parsing template. Found {len(well_to_name)} unique well-sample mappings")
        
    except Exception as e:
        logger.error(f"Error parsing template file: {str(e)}")
        logger.debug("Error details:", exc_info=True)
    
    return well_to_name

def get_sample_names(input_dir):
    """
    Get sample names for all wells based on the template file.
    
    Args:
        input_dir (str): Input directory path
        
    Returns:
        dict: Mapping of well IDs to sample names
    """
    logger = logging.getLogger("ddQuint")
    logger.debug(f"Getting sample names for directory: {input_dir}")
    
    template_path = find_template_file(input_dir)
    
    if template_path:
        logger.debug(f"Template file found: {template_path}")
        sample_names = parse_template_file(template_path)
        logger.debug(f"Successfully parsed {len(sample_names)} sample names from template")
        return sample_names
    else:
        logger.info(f"No template file found for {os.path.basename(input_dir)}")
        return {}