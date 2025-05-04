"""
Parser module for ddPCR .ddplt files
Extracts sample names and other metadata from Bio-Rad's proprietary file format
"""

import os
import re
import struct
import binascii

def extract_sample_names(file_path):
    """
    Extract sample names from a .ddplt file.
    
    Args:
        file_path (str): Path to .ddplt file
        
    Returns:
        dict: Dictionary mapping well IDs to sample names
    """
    try:
        # Check if the file exists
        if not os.path.exists(file_path):
            print(f"Error: File {file_path} does not exist")
            return {}
            
        # Check if it's actually a .ddplt file
        if not file_path.lower().endswith('.ddplt'):
            print(f"Warning: {file_path} does not have .ddplt extension")
        
        # Initialize an empty dictionary to store results
        sample_names = {}
        
        # Read the file in binary mode
        with open(file_path, 'rb') as f:
            # Read the entire file into memory
            data = f.read()
            
            # Look for patterns that might indicate sample names
            # This is a simplified approach - real implementation would need reverse engineering
            
            # First try: look for plain text names with well designations nearby
            text_chunks = extract_text_chunks(data)
            
            # Match patterns like "A01_SampleName" or similar patterns
            well_name_pattern = re.compile(r'([A-H](?:0?[1-9]|1[0-2]))[\s_-]*([\w\s-]+)', re.IGNORECASE)
            
            for chunk in text_chunks:
                matches = well_name_pattern.findall(chunk)
                for match in matches:
                    well_id = standardize_well_id(match[0])
                    name = match[1].strip()
                    if name and not name.isspace():
                        sample_names[well_id] = name
            
            # If we didn't find any samples using the first method, try alternative approaches
            if not sample_names:
                # The format might use fixed offsets or more complex structures
                # Fallback to plate-level metadata
                metadata = extract_metadata(data)
                if 'plate_name' in metadata:
                    # Use plate name as a prefix for all wells
                    for row in 'ABCDEFGH':
                        for col in range(1, 13):
                            well_id = f"{row}{col:02d}"
                            sample_names[well_id] = f"{metadata['plate_name']}_{well_id}"
        
        return sample_names
        
    except Exception as e:
        print(f"Error parsing .ddplt file: {str(e)}")
        return {}

def extract_text_chunks(binary_data, min_length=4):
    """
    Extract text chunks from binary data.
    
    Args:
        binary_data (bytes): Binary data
        min_length (int): Minimum length of text chunks to extract
        
    Returns:
        list: List of text chunks
    """
    chunks = []
    
    # Convert binary data to ASCII representation
    ascii_data = binary_data.decode('ascii', errors='ignore')
    
    # Split by null characters or non-printable characters
    raw_chunks = re.split(r'[\x00-\x1F\x7F-\xFF]+', ascii_data)
    
    # Filter out chunks that are too short or only contain numbers/special chars
    for chunk in raw_chunks:
        # Remove leading/trailing whitespace
        chunk = chunk.strip()
        
        # Check if chunk is long enough and contains at least one letter
        if len(chunk) >= min_length and re.search(r'[a-zA-Z]', chunk):
            chunks.append(chunk)
    
    return chunks

def extract_metadata(binary_data):
    """
    Extract metadata from the binary file.
    
    Args:
        binary_data (bytes): Binary data
        
    Returns:
        dict: Dictionary with metadata
    """
    metadata = {}
    
    # Look for common headers or signatures
    if b'QuantaSoft' in binary_data:
        metadata['software'] = 'QuantaSoft'
    
    # Extract plate name from filename-like patterns
    text_chunks = extract_text_chunks(binary_data)
    for chunk in text_chunks:
        # Look for patterns that might be plate names
        if re.match(r'^[A-Za-z0-9_-]+\d{6,8}$', chunk):  # Common plate naming format with date
            metadata['plate_name'] = chunk
            break
        elif re.match(r'^[A-Za-z0-9_-]+_plate$', chunk, re.IGNORECASE):
            metadata['plate_name'] = chunk
            break
    
    return metadata

def standardize_well_id(well_id):
    """
    Standardize well ID format to 'A01', 'B02', etc.
    
    Args:
        well_id (str): Well ID in various formats
        
    Returns:
        str: Standardized well ID
    """
    # Extract row letter and column number
    match = re.match(r'([A-H])(\d{1,2})', well_id, re.IGNORECASE)
    if match:
        row = match.group(1).upper()
        col = int(match.group(2))
        return f"{row}{col:02d}"
    return well_id

def map_wells_to_samples(ddplt_file, wells_list):
    """
    Map well IDs to sample names for all wells in the list.
    
    Args:
        ddplt_file (str): Path to .ddplt file
        wells_list (list): List of well IDs
        
    Returns:
        dict: Dictionary mapping well IDs to sample names
    """
    # Get all sample names from the file
    all_samples = extract_sample_names(ddplt_file)
    
    # Filter to only the wells we care about
    result = {}
    for well in wells_list:
        std_well = standardize_well_id(well)
        result[well] = all_samples.get(std_well, f"Well_{well}")
    
    return result