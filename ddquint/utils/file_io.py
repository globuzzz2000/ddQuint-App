"""
File I/O utilities for ddQuint with debug logging
"""

import os
import shutil
import pandas as pd
import csv
import logging

def ensure_directory(directory):
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory (str): Directory path
        
    Returns:
        str: Path to the directory
    """
    logger = logging.getLogger("ddQuint")
    logger.debug(f"Ensuring directory exists: {directory}")
    
    if not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"Created directory: {directory}")
        except Exception as e:
            logger.error(f"Error creating directory {directory}: {str(e)}")
            logger.debug("Error details:", exc_info=True)
            raise
    else:
        logger.debug(f"Directory already exists: {directory}")
    
    return directory

def list_csv_files(directory):
    """
    List all CSV files in a directory.
    
    Args:
        directory (str): Directory path
        
    Returns:
        list: List of CSV file paths
    """
    logger = logging.getLogger("ddQuint")
    logger.debug(f"Listing CSV files in directory: {directory}")
    
    try:
        files = [
            os.path.join(directory, f) 
            for f in os.listdir(directory) 
            if f.lower().endswith('.csv')
        ]
        logger.debug(f"Found {len(files)} CSV files in {directory}")
        for file in files:
            logger.debug(f"  - {file}")
        return files
    except Exception as e:
        logger.error(f"Error listing CSV files in {directory}: {str(e)}")
        logger.debug("Error details:", exc_info=True)
        return []

def move_files(files, destination):
    """
    Move files to a destination directory.
    
    Args:
        files (list): List of file paths
        destination (str): Destination directory
        
    Returns:
        list: List of successfully moved files
    """
    logger = logging.getLogger("ddQuint")
    logger.debug(f"Moving {len(files)} files to {destination}")
    
    moved_files = []
    
    # Ensure destination directory exists
    ensure_directory(destination)
    
    for file_path in files:
        try:
            if os.path.exists(file_path):
                file_name = os.path.basename(file_path)
                dest_path = os.path.join(destination, file_name)
                
                logger.debug(f"Moving {file_path} to {dest_path}")
                shutil.move(file_path, dest_path)
                moved_files.append(dest_path)
                logger.debug(f"Successfully moved {file_name}")
            else:
                logger.debug(f"File does not exist: {file_path}")
        except Exception as e:
            logger.error(f"Error moving {file_path}: {str(e)}")
            logger.debug("Error details:", exc_info=True)
    
    logger.debug(f"Successfully moved {len(moved_files)} files")
    return moved_files

def copy_files(files, destination):
    """
    Copy files to a destination directory.
    
    Args:
        files (list): List of file paths
        destination (str): Destination directory
        
    Returns:
        list: List of successfully copied files
    """
    logger = logging.getLogger("ddQuint")
    logger.debug(f"Copying {len(files)} files to {destination}")
    
    copied_files = []
    
    # Ensure destination directory exists
    ensure_directory(destination)
    
    for file_path in files:
        try:
            if os.path.exists(file_path):
                file_name = os.path.basename(file_path)
                dest_path = os.path.join(destination, file_name)
                
                logger.debug(f"Copying {file_path} to {dest_path}")
                shutil.copy2(file_path, dest_path)
                copied_files.append(dest_path)
                logger.debug(f"Successfully copied {file_name}")
            else:
                logger.debug(f"File does not exist: {file_path}")
        except Exception as e:
            logger.error(f"Error copying {file_path}: {str(e)}")
            logger.debug("Error details:", exc_info=True)
    
    logger.debug(f"Successfully copied {len(copied_files)} files")
    return copied_files

def find_header_row(file_path, header_keywords=None):
    """
    Find the header row in a CSV file based on keywords.
    
    Args:
        file_path (str): Path to CSV file
        header_keywords (list): List of keywords to look for in headers
        
    Returns:
        int: Header row index or None if not found
    """
    logger = logging.getLogger("ddQuint")
    
    if header_keywords is None:
        header_keywords = ['Ch1Amplitude', 'Ch2Amplitude']
    
    logger.debug(f"Finding header row in {file_path}")
    logger.debug(f"Looking for keywords: {header_keywords}")
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if all(keyword.lower() in line.lower() for keyword in header_keywords):
                    logger.debug(f"Found header row at index {i}")
                    logger.debug(f"Header row content: {line.strip()}")
                    return i
        
        logger.debug("Header row not found")
        return None
    except Exception as e:
        logger.error(f"Error finding header row in {file_path}: {str(e)}")
        logger.debug("Error details:", exc_info=True)
        return None

def read_csv_with_header_detection(file_path):
    """
    Read a CSV file with automatic header row detection.
    
    Args:
        file_path (str): Path to CSV file
        
    Returns:
        pandas.DataFrame: DataFrame with CSV data or None if error
    """
    logger = logging.getLogger("ddQuint")
    logger.debug(f"Reading CSV file: {file_path}")
    
    try:
        # Find the header row
        header_row = find_header_row(file_path)
        
        if header_row is not None:
            logger.debug(f"Reading CSV with header row {header_row}")
            # Read the CSV file with the detected header row
            df = pd.read_csv(file_path, skiprows=header_row)
            logger.debug(f"Successfully read CSV, shape: {df.shape}")
            logger.debug(f"Columns: {list(df.columns)}")
            return df
        else:
            logger.debug("No header row found, trying to read without skipping rows")
            # Try to read the file without skipping rows
            df = pd.read_csv(file_path)
            logger.debug(f"Read CSV without skipping rows, shape: {df.shape}")
            logger.debug(f"Columns: {list(df.columns)}")
            
            # Check if required columns exist
            if 'Ch1Amplitude' in df.columns and 'Ch2Amplitude' in df.columns:
                logger.debug("Required columns found")
                return df
            
            logger.error(f"Could not find header row in {file_path}")
            return None
    except Exception as e:
        logger.error(f"Error reading CSV file {file_path}: {str(e)}")
        logger.debug("Error details:", exc_info=True)
        return None