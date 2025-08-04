#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Well coordinate utilities for ddQuint with comprehensive validation and formatting.

Provides utilities for extracting well coordinates from filenames, validating
well identifiers, and formatting well IDs to standard format. Supports 96-well
plate layout (A-H rows, 01-12 columns).
"""

import re
import logging

logger = logging.getLogger(__name__)


def extract_well_coordinate(filename):
    """
    Extract well coordinate (like A01, E05) from a filename.
    Only accepts coordinates in format like "_A05_Amplitude".
    
    Args:
        filename (str): Filename to extract well coordinate from
        
    Returns:
        str: Well coordinate (e.g., 'A05') or None if not found
        
    Example:
        >>> extract_well_coordinate("JaW_E9_B2_LCO_20250709_160810_006_A05_Amplitude.csv")
        'A05'
        >>> extract_well_coordinate("JaW_E10_B2_LCO_20250709_160810_006_H12_Amplitude.csv")
        'H12'
    """
    if not filename:
        logger.debug("Empty filename provided")
        return None
        
    logger.debug(f"Extracting well coordinate from filename: {filename}")
    
    # Only look for pattern like _A05_Amplitude
    pattern = r'_([A-H][0-9]{1,2})_Amplitude'
    matches = re.findall(pattern, filename)
    
    if matches:
        well_id = matches[0]  # Take the first (should only be one)
        formatted_well = format_well_id(well_id)
        if formatted_well and is_valid_well(formatted_well):
            logger.debug(f"Found well coordinate: {well_id} -> formatted as {formatted_well}")
            return formatted_well
        else:
            logger.debug(f"Found match {well_id} but it's not a valid well coordinate")
    
    logger.debug(f"No well coordinate found in filename: {filename}")
    return None

def is_valid_well(well_id):
    """
    Check if a well identifier is valid (e.g., 'A01', 'H12').
    
    Args:
        well_id (str): Well identifier to check
        
    Returns:
        bool: True if valid, False otherwise
        
    Example:
        >>> is_valid_well('A01')
        True
        >>> is_valid_well('A1')
        False
        >>> is_valid_well('I01')
        False
    """
    if not well_id or not isinstance(well_id, str):
        logger.debug(f"Invalid well format - not a string or empty: {well_id}")
        return False
    
    # Check format: letter A-H followed by number 01-12
    pattern = r'^[A-H](0[1-9]|1[0-2])$'
    is_valid = bool(re.match(pattern, well_id))
    
    if is_valid:
        logger.debug(f"Well {well_id} is valid")
    else:
        logger.debug(f"Well {well_id} is invalid (doesn't match pattern {pattern})")
    
    return is_valid


def format_well_id(well_id):
    """
    Format a well identifier to standard format (e.g., 'A1' -> 'A01').
    
    Args:
        well_id (str): Well identifier to format
        
    Returns:
        str: Formatted well identifier or None if invalid
        
    Example:
        >>> format_well_id('A1')
        'A01'
        >>> format_well_id('H12')
        'H12'
        >>> format_well_id('I01')
        None
    """
    if not well_id or not isinstance(well_id, str):
        logger.debug(f"Cannot format - invalid input: {well_id}")
        return None
        
    logger.debug(f"Formatting well ID: {well_id}")
    
    # Check if it's already in correct format
    if is_valid_well(well_id):
        logger.debug(f"Well ID {well_id} already in correct format")
        return well_id
    
    # Try to extract row and column
    match = re.match(r'^([A-H])(\d{1,2})$', well_id.upper())
    if match:
        row, col = match.groups()
        col_int = int(col)
        
        # Check if column is in range 1-12
        if 1 <= col_int <= 12:
            formatted = f"{row}{col_int:02d}"
            logger.debug(f"Formatted well ID from {well_id} to {formatted}")
            return formatted
        else:
            logger.debug(f"Column number {col_int} out of range (1-12)")
    
    logger.debug(f"Could not format well ID: {well_id}")
    return None


def get_all_wells():
    """
    Get a list of all valid wells in a 96-well plate.
    
    Returns:
        list: List of well identifiers (e.g., 'A01', 'A02', ..., 'H12')
        
    Example:
        >>> wells = get_all_wells()
        >>> len(wells)
        96
        >>> wells[0]
        'A01'
        >>> wells[-1]
        'H12'
    """
    logger.debug("Generating all well identifiers for 96-well plate")
    
    rows = list('ABCDEFGH')
    cols = [f"{i:02d}" for i in range(1, 13)]
    wells = [f"{row}{col}" for row in rows for col in cols]
    
    logger.debug(f"Generated {len(wells)} well identifiers")
    return wells


def parse_well_position(well_id):
    """
    Parse a well ID into row and column components.
    
    Args:
        well_id (str): Well identifier (e.g., 'A01', 'H12')
        
    Returns:
        tuple: (row_letter, column_number) or (None, None) if invalid
        
    Example:
        >>> parse_well_position('A01')
        ('A', 1)
        >>> parse_well_position('H12')
        ('H', 12)
        >>> parse_well_position('invalid')
        (None, None)
    """
    if not is_valid_well(well_id):
        logger.debug(f"Cannot parse invalid well ID: {well_id}")
        return (None, None)
    
    row_letter = well_id[0]
    column_number = int(well_id[1:])
    
    logger.debug(f"Parsed well {well_id} -> row: {row_letter}, column: {column_number}")
    return (row_letter, column_number)


def get_well_neighbors(well_id, include_diagonal=False):
    """
    Get neighboring wells for a given well ID.
    
    Args:
        well_id (str): Well identifier
        include_diagonal (bool): If True, include diagonal neighbors
        
    Returns:
        list: List of neighboring well IDs
        
    Example:
        >>> get_well_neighbors('B02')
        ['A02', 'B01', 'B03', 'C02']
        >>> get_well_neighbors('A01')
        ['A02', 'B01']
    """
    if not is_valid_well(well_id):
        logger.debug(f"Cannot get neighbors for invalid well: {well_id}")
        return []
    
    row_letter, column_number = parse_well_position(well_id)
    neighbors = []
    
    # Define relative positions for neighbors
    if include_diagonal:
        # Include all 8 surrounding positions
        deltas = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    else:
        # Only include orthogonal neighbors (up, down, left, right)
        deltas = [(-1, 0), (0, -1), (0, 1), (1, 0)]
    
    row_num = ord(row_letter) - ord('A')  # Convert A-H to 0-7
    
    for delta_row, delta_col in deltas:
        new_row_num = row_num + delta_row
        new_col_num = column_number + delta_col
        
        # Check bounds
        if 0 <= new_row_num <= 7 and 1 <= new_col_num <= 12:
            new_row_letter = chr(ord('A') + new_row_num)
            neighbor_well = f"{new_row_letter}{new_col_num:02d}"
            neighbors.append(neighbor_well)
    
    logger.debug(f"Found {len(neighbors)} neighbors for well {well_id}: {neighbors}")
    return neighbors