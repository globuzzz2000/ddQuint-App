#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File I/O utilities for ddQuint with comprehensive error handling and debug logging.

Provides utilities for directory management, file operations, and CSV processing
with automatic header detection and robust error handling.
"""

import os
import shutil
import pandas as pd
import logging

from ..config.exceptions import FileProcessingError

logger = logging.getLogger(__name__)


def ensure_directory(directory):
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory (str): Directory path to create
        
    Returns:
        str: Path to the directory
        
    Raises:
        FileProcessingError: If directory creation fails
    """
    logger.debug(f"Ensuring directory exists: {directory}")
    
    if not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"Created directory: {directory}")
        except Exception as e:
            error_msg = f"Error creating directory {directory}: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Error details: {str(e)}", exc_info=True)
            raise FileProcessingError(error_msg) from e
    else:
        logger.debug(f"Directory already exists: {directory}")
    
    return directory


def list_csv_files(directory):
    """
    List all CSV files in a directory.
    
    Args:
        directory (str): Directory path to search
        
    Returns:
        list: List of CSV file paths
        
    Raises:
        FileProcessingError: If directory cannot be accessed
    """
    logger.debug(f"Listing CSV files in directory: {directory}")
    
    if not os.path.exists(directory):
        error_msg = f"Directory does not exist: {directory}"
        logger.error(error_msg)
        raise FileProcessingError(error_msg)
    
    try:
        files = [
            os.path.join(directory, f) 
            for f in os.listdir(directory) 
            if f.lower().endswith('.csv')
        ]
        logger.debug(f"Found {len(files)} CSV files in {directory}")
        
        if logger.isEnabledFor(logging.DEBUG):
            for file in files:
                logger.debug(f"  - {os.path.basename(file)}")
                
        return files
        
    except Exception as e:
        error_msg = f"Error listing CSV files in {directory}: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        raise FileProcessingError(error_msg) from e


def move_files(files, destination):
    """
    Move files to a destination directory.
    
    Args:
        files (list): List of file paths to move
        destination (str): Destination directory path
        
    Returns:
        list: List of successfully moved file paths
        
    Raises:
        FileProcessingError: If destination cannot be created
    """
    logger.debug(f"Moving {len(files)} files to {destination}")
    
    moved_files = []
    
    # Ensure destination directory exists
    ensure_directory(destination)
    
    for file_path in files:
        try:
            if os.path.exists(file_path):
                file_name = os.path.basename(file_path)
                dest_path = os.path.join(destination, file_name)
                
                logger.debug(f"Moving {file_name} to {dest_path}")
                shutil.move(file_path, dest_path)
                moved_files.append(dest_path)
                logger.debug(f"Successfully moved {file_name}")
            else:
                logger.warning(f"File does not exist, skipping: {file_path}")
                
        except Exception as e:
            logger.error(f"Error moving {os.path.basename(file_path)}: {str(e)}")
            logger.debug(f"Error details: {str(e)}", exc_info=True)
    
    logger.debug(f"Successfully moved {len(moved_files)} out of {len(files)} files")
    return moved_files


def copy_files(files, destination):
    """
    Copy files to a destination directory.
    
    Args:
        files (list): List of file paths to copy
        destination (str): Destination directory path
        
    Returns:
        list: List of successfully copied file paths
        
    Raises:
        FileProcessingError: If destination cannot be created
    """
    logger.debug(f"Copying {len(files)} files to {destination}")
    
    copied_files = []
    
    # Ensure destination directory exists
    ensure_directory(destination)
    
    for file_path in files:
        try:
            if os.path.exists(file_path):
                file_name = os.path.basename(file_path)
                dest_path = os.path.join(destination, file_name)
                
                logger.debug(f"Copying {file_name} to {dest_path}")
                shutil.copy2(file_path, dest_path)
                copied_files.append(dest_path)
                logger.debug(f"Successfully copied {file_name}")
            else:
                logger.warning(f"File does not exist, skipping: {file_path}")
                
        except Exception as e:
            logger.error(f"Error copying {os.path.basename(file_path)}: {str(e)}")
            logger.debug(f"Error details: {str(e)}", exc_info=True)
    
    logger.debug(f"Successfully copied {len(copied_files)} out of {len(files)} files")
    return copied_files


def find_header_row(file_path, header_keywords=None):
    """
    Find the header row in a CSV file based on keywords.
    
    Args:
        file_path (str): Path to CSV file
        header_keywords (list, optional): Keywords to look for in headers
        
    Returns:
        int: Header row index (0-based) or None if not found
        
    Raises:
        FileProcessingError: If file cannot be read
    """
    if header_keywords is None:
        header_keywords = ['Ch1Amplitude', 'Ch2Amplitude']
    
    logger.debug(f"Finding header row in {os.path.basename(file_path)}")
    logger.debug(f"Looking for keywords: {header_keywords}")
    
    if not os.path.exists(file_path):
        error_msg = f"File does not exist: {file_path}"
        logger.error(error_msg)
        raise FileProcessingError(error_msg)
    
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
        error_msg = f"Error reading file {os.path.basename(file_path)}: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        raise FileProcessingError(error_msg) from e


def read_csv_with_header_detection(file_path):
    """
    Read a CSV file with automatic header row detection.
    
    Args:
        file_path (str): Path to CSV file
        
    Returns:
        pandas.DataFrame: DataFrame with CSV data
        
    Raises:
        FileProcessingError: If CSV cannot be read or processed
        ValueError: If required columns are missing
    """
    logger.debug(f"Reading CSV file: {os.path.basename(file_path)}")
    
    if not os.path.exists(file_path):
        error_msg = f"CSV file does not exist: {file_path}"
        logger.error(error_msg)
        raise FileProcessingError(error_msg)
    
    try:
        # Find the header row
        header_row = find_header_row(file_path)
        
        if header_row is not None:
            logger.debug(f"Reading CSV with header row {header_row}")
            df = pd.read_csv(file_path, skiprows=header_row)
            logger.debug(f"Successfully read CSV, shape: {df.shape}")
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Columns: {list(df.columns)}")
            
            return df
        else:
            logger.debug("No header row found, trying to read without skipping rows")
            df = pd.read_csv(file_path)
            logger.debug(f"Read CSV without skipping rows, shape: {df.shape}")
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Columns: {list(df.columns)}")
            
            # Check if required columns exist
            required_cols = ['Ch1Amplitude', 'Ch2Amplitude']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                error_msg = f"Missing required columns in {os.path.basename(file_path)}: {missing_cols}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            logger.debug("Required columns found")
            return df
            
    except pd.errors.EmptyDataError:
        error_msg = f"CSV file is empty: {os.path.basename(file_path)}"
        logger.error(error_msg)
        raise FileProcessingError(error_msg)
        
    except pd.errors.ParserError as e:
        error_msg = f"CSV parsing failed for {os.path.basename(file_path)}: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Parser error details: {str(e)}", exc_info=True)
        raise FileProcessingError(error_msg) from e
        
    except Exception as e:
        error_msg = f"Error reading CSV file {os.path.basename(file_path)}: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        raise FileProcessingError(error_msg) from e