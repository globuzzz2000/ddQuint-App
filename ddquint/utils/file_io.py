"""
File I/O utilities for ddQuint
"""

import os
import shutil
import pandas as pd
import csv

def ensure_directory(directory):
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory (str): Directory path
        
    Returns:
        str: Path to the directory
    """
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    return directory

def list_csv_files(directory):
    """
    List all CSV files in a directory.
    
    Args:
        directory (str): Directory path
        
    Returns:
        list: List of CSV file paths
    """
    try:
        files = [
            os.path.join(directory, f) 
            for f in os.listdir(directory) 
            if f.lower().endswith('.csv')
        ]
        return files
    except Exception as e:
        print(f"Error listing CSV files in {directory}: {str(e)}")
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
    moved_files = []
    
    # Ensure destination directory exists
    ensure_directory(destination)
    
    for file_path in files:
        try:
            if os.path.exists(file_path):
                file_name = os.path.basename(file_path)
                dest_path = os.path.join(destination, file_name)
                shutil.move(file_path, dest_path)
                moved_files.append(dest_path)
        except Exception as e:
            print(f"Error moving {file_path}: {str(e)}")
    
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
    copied_files = []
    
    # Ensure destination directory exists
    ensure_directory(destination)
    
    for file_path in files:
        try:
            if os.path.exists(file_path):
                file_name = os.path.basename(file_path)
                dest_path = os.path.join(destination, file_name)
                shutil.copy2(file_path, dest_path)
                copied_files.append(dest_path)
        except Exception as e:
            print(f"Error copying {file_path}: {str(e)}")
    
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
    if header_keywords is None:
        header_keywords = ['Ch1Amplitude', 'Ch2Amplitude']
        
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if all(keyword.lower() in line.lower() for keyword in header_keywords):
                    return i
    except Exception as e:
        print(f"Error finding header row in {file_path}: {str(e)}")
    
    return None

def read_csv_with_header_detection(file_path):
    """
    Read a CSV file with automatic header row detection.
    
    Args:
        file_path (str): Path to CSV file
        
    Returns:
        pandas.DataFrame: DataFrame with CSV data or None if error
    """
    try:
        # Find the header row
        header_row = find_header_row(file_path)
        
        if header_row is not None:
            # Read the CSV file with the detected header row
            df = pd.read_csv(file_path, skiprows=header_row)
            return df
        else:
            # Try to read the file without skipping rows
            df = pd.read_csv(file_path)
            
            # Check if required columns exist
            if 'Ch1Amplitude' in df.columns and 'Ch2Amplitude' in df.columns:
                return df
            
            print(f"Error: Could not find header row in {file_path}")
            return None
    except Exception as e:
        print(f"Error reading CSV file {file_path}: {str(e)}")
        return None