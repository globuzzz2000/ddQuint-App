"""
Well coordinate utilities for ddQuint
"""

import re

def extract_well_coordinate(filename):
    """
    Extract well coordinate (like A01, E05) from a filename.
    
    Args:
        filename (str): Filename to extract well coordinate from
        
    Returns:
        str: Well coordinate (e.g., 'A01') or None if not found
    """
    # Look for explicitly marked well coordinates (like _A01_ or similar patterns)
    explicit_pattern = r'_([A-H][0-9]{2})_'
    explicit_matches = re.findall(explicit_pattern, filename)
    if explicit_matches:
        return explicit_matches[0]
    
    # Try finding patterns with a letter followed by numbers
    patterns = [
        r'_([A-H][0-9]{2})',     # _A01
        r'([A-H][0-9]{2})_',     # A01_
        r'_([A-H][0-9]{1,2})[_\.]',  # _A1_ or _A1.
        r'([A-H][0-9]{1,2})[_\.]'    # A1_ or A1.
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, filename)
        if matches:
            match = matches[-1]  # Use the last match as it's more likely to be the actual well
            
            # Format to ensure we have A01 format (not A1)
            if len(match) == 2:  # Like "A1"
                return match[0] + "0" + match[1]
            return match
    
    # Final fallback - look for any well-like coordinate
    general_pattern = r'([A-H][0-9]{1,2})'
    general_matches = re.findall(general_pattern, filename)
    
    if general_matches:
        match = general_matches[-1]
        if len(match) == 2:  # Like "A1"
            return match[0] + "0" + match[1]
        return match
    
    return None

def is_valid_well(well_id):
    """
    Check if a well identifier is valid (e.g., 'A01', 'H12').
    
    Args:
        well_id (str): Well identifier to check
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not well_id or not isinstance(well_id, str):
        return False
    
    # Check format: letter A-H followed by number 01-12
    pattern = r'^[A-H](0[1-9]|1[0-2])$'
    return bool(re.match(pattern, well_id))

def format_well_id(well_id):
    """
    Format a well identifier to standard format (e.g., 'A1' -> 'A01').
    
    Args:
        well_id (str): Well identifier to format
        
    Returns:
        str: Formatted well identifier or None if invalid
    """
    if not well_id or not isinstance(well_id, str):
        return None
    
    # Check if it's already in correct format
    if is_valid_well(well_id):
        return well_id
    
    # Try to extract row and column
    match = re.match(r'^([A-H])(\d{1,2})$', well_id)
    if match:
        row, col = match.groups()
        col_int = int(col)
        
        # Check if column is in range 1-12
        if 1 <= col_int <= 12:
            return f"{row}{col_int:02d}"
    
    return None

def get_all_wells():
    """
    Get a list of all valid wells in a 96-well plate.
    
    Returns:
        list: List of well identifiers (e.g., 'A01', 'A02', ..., 'H12')
    """
    rows = list('ABCDEFGH')
    cols = [f"{i:02d}" for i in range(1, 13)]
    return [f"{row}{col}" for row in rows for col in cols]