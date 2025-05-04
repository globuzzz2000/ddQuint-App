"""
Template Excel parser module for ddQuint with debug logging
"""

import os
import re
import openpyxl
import logging
from pathlib import Path

def find_template_file(input_dir):
    """
    Find the Excel template file based on the input directory name.
    Searches in folders from the -2 parent directory.
    
    Args:
        input_dir (str): Input directory path
        
    Returns:
        str: Path to the template file or None if not found
    """
    logger = logging.getLogger("ddQuint")
    
    # Get the base name of the input directory (without path)
    dir_name = os.path.basename(input_dir)
    template_name = f"{dir_name}.xlsx"
    
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

def excel_coords_to_well_id(row, col):
    """
    Convert Excel row/column coordinates to well ID.
    The mapping is:
    - Excel row (1-8) becomes well column (01-08)
    - Excel column (1-12) becomes well row (A-L)
    
    Examples:
    - Excel A1 (row=1, col=1) → Well A01
    - Excel B1 (row=2, col=1) → Well A02
    - Excel A2 (row=1, col=2) → Well B01
    
    Args:
        row (int): Row number (1-indexed)
        col (int): Column number (1-indexed)
        
    Returns:
        str: Well ID like 'A01'
    """
    logger = logging.getLogger("ddQuint")
    
    logger.debug(f"Converting Excel coordinates (row={row}, col={col}) to well ID")
    
    if row < 1 or row > 8 or col < 1 or col > 12:
        logger.debug(f"Invalid Excel coordinates: row={row}, col={col}")
        return None
    
    # Convert Excel column to well row (A-L)
    well_row_letter = chr(ord('A') + col - 1)
    
    # Convert Excel row to well column (01-08)
    well_col_number = f"{row:02d}"
    
    well_id = f"{well_row_letter}{well_col_number}"
    logger.debug(f"Converted to well ID: {well_id}")
    
    return well_id

def parse_template_file(template_path):
    """
    Parse the Excel template file to extract sample names.
    
    Args:
        template_path (str): Path to the template Excel file
        
    Returns:
        dict: Mapping of well IDs to sample names
    """
    logger = logging.getLogger("ddQuint")
    logger.debug(f"Parsing template file: {template_path}")
    
    well_to_name = {}
    
    try:
        workbook = openpyxl.load_workbook(template_path)
        sheet = workbook.active
        logger.debug(f"Opened workbook, active sheet: {sheet.title}")
        
        # Parse the first 8 rows and 12 columns
        for row in range(1, 9):  # 1-8 (rows in Excel)
            for col in range(1, 13):  # 1-12 (columns in Excel)
                cell_value = sheet.cell(row=row, column=col).value
                
                if cell_value:
                    well_id = excel_coords_to_well_id(row, col)
                    if well_id:
                        well_to_name[well_id] = str(cell_value)
                        logger.debug(f"Parsed cell ({row},{col}): {cell_value} -> well {well_id}")
                else:
                    logger.debug(f"Empty cell at ({row},{col})")
        
        workbook.close()
        logger.debug(f"Finished parsing template. Found {len(well_to_name)} sample names")
        
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