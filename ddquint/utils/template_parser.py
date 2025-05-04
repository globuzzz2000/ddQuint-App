"""
Template Excel parser module for ddQuint
Finds and parses Excel template files to extract sample names for wells
"""

import os
import re
import openpyxl
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
    # Get the base name of the input directory (without path)
    dir_name = os.path.basename(input_dir)
    template_name = f"{dir_name}.xlsx"
    
    # Go up 2 parent directories
    parent_dir = os.path.dirname(os.path.dirname(input_dir))
    
    # Search in all subdirectories
    for root, dirs, files in os.walk(parent_dir):
        for file in files:
            if file == template_name:
                return os.path.join(root, file)
    
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
    if row < 1 or row > 8 or col < 1 or col > 12:
        return None
    
    # Convert Excel column to well row (A-L)
    well_row_letter = chr(ord('A') + col - 1)
    
    # Convert Excel row to well column (01-08)
    well_col_number = f"{row:02d}"
    
    return f"{well_row_letter}{well_col_number}"

def parse_template_file(template_path):
    """
    Parse the Excel template file to extract sample names.
    
    Args:
        template_path (str): Path to the template Excel file
        
    Returns:
        dict: Mapping of well IDs to sample names
    """
    well_to_name = {}
    
    try:
        workbook = openpyxl.load_workbook(template_path)
        sheet = workbook.active
        
        # Parse the first 8 rows and 12 columns
        for row in range(1, 9):  # 1-8 (rows in Excel)
            for col in range(1, 13):  # 1-12 (columns in Excel)
                cell_value = sheet.cell(row=row, column=col).value
                
                if cell_value:
                    well_id = excel_coords_to_well_id(row, col)
                    if well_id:
                        well_to_name[well_id] = str(cell_value)
        
        workbook.close()
        
    except Exception as e:
        print(f"Error parsing template file: {str(e)}")
    
    return well_to_name

def get_sample_names(input_dir):
    """
    Get sample names for all wells based on the template file.
    
    Args:
        input_dir (str): Input directory path
        
    Returns:
        dict: Mapping of well IDs to sample names
    """
    template_path = find_template_file(input_dir)
    
    if template_path:
        print(f"Found template file: {template_path}")
        return parse_template_file(template_path)
    else:
        print(f"No template file found for {os.path.basename(input_dir)}")
        return {}