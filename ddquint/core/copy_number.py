"""
Copy number calculation module for ddQuint
"""

import numpy as np

def calculate_copy_numbers(target_counts):
    """
    Calculate relative copy numbers for chromosome targets.
    
    Args:
        target_counts (dict): Counts for each target
        
    Returns:
        dict: Relative copy numbers
    """
    # Extract counts for chromosomes
    raw_vals = np.array([
        target_counts.get('Chrom1', 0),
        target_counts.get('Chrom2', 0),
        target_counts.get('Chrom3', 0),
        target_counts.get('Chrom4', 0),
        target_counts.get('Chrom5', 0)
    ])
    
    # If all chromosomes have zero count, return empty dict
    if np.all(raw_vals == 0):
        return {}
    
    # Calculate median of non-zero values
    non_zero_vals = raw_vals[raw_vals > 0]
    if len(non_zero_vals) == 0:
        return {}
    
    median_val = np.median(non_zero_vals)
    
    # Calculate deviations from median
    with np.errstate(divide='ignore', invalid='ignore'):
        deviations = np.abs(raw_vals - median_val) / median_val
        deviations = np.nan_to_num(deviations, nan=float('inf'))
    
    # Identify values close to the median (within 15%)
    close_to_median = deviations < 0.15  # within ±15%
    
    # Calculate baseline for normalization
    if np.sum(close_to_median) >= 3:
        # Use mean of values close to median as baseline
        baseline = np.mean(raw_vals[close_to_median])
    else:
        # Use median as baseline
        baseline = median_val
    
    # Calculate relative copy numbers
    copy_numbers = {}
    chromosome_names = ['Chrom1', 'Chrom2', 'Chrom3', 'Chrom4', 'Chrom5']
    
    for i, chrom in enumerate(chromosome_names):
        if baseline > 0 and raw_vals[i] > 0:
            copy_numbers[chrom] = raw_vals[i] / baseline
    
    return copy_numbers

def detect_aneuploidies(copy_numbers, threshold=0.15):
    """
    Detect aneuploidies based on copy numbers.
    
    Args:
        copy_numbers (dict): Copy numbers for each chromosome
        threshold (float): Threshold for abnormality detection (default: 0.15)
        
    Returns:
        tuple: (has_abnormality, abnormal_chromosomes)
    """
    abnormal_chromosomes = {}
    
    for chrom, copy_num in copy_numbers.items():
        # Check for deviation from normal copy number (1.0)
        deviation = abs(copy_num - 1.0)
        
        if deviation > threshold:
            abnormal_chromosomes[chrom] = {
                'copy_number': copy_num,
                'deviation': deviation,
                'type': 'gain' if copy_num > 1.0 else 'loss'
            }
    
    has_abnormality = len(abnormal_chromosomes) > 0
    
    return has_abnormality, abnormal_chromosomes

def calculate_statistics(results):
    """
    Calculate statistics across multiple samples.
    
    Args:
        results (list): List of result dictionaries
        
    Returns:
        dict: Statistics
    """
    # Extract copy numbers for each chromosome
    chrom_data = {
        'Chrom1': [],
        'Chrom2': [],
        'Chrom3': [],
        'Chrom4': [],
        'Chrom5': []
    }
    
    abnormal_count = 0
    total_samples = len(results)
    
    for result in results:
        if result.get('has_aneuploidy', False):
            abnormal_count += 1
            
        copy_numbers = result.get('copy_numbers', {})
        for chrom in chrom_data.keys():
            if chrom in copy_numbers:
                chrom_data[chrom].append(copy_numbers[chrom])
    
    # Calculate statistics
    stats = {
        'sample_count': total_samples,
        'abnormal_count': abnormal_count,
        'abnormal_percent': (abnormal_count / total_samples * 100) if total_samples > 0 else 0,
        'chromosomes': {}
    }
    
    for chrom, values in chrom_data.items():
        if values:
            stats['chromosomes'][chrom] = {
                'count': len(values),
                'mean': np.mean(values),
                'median': np.median(values),
                'std': np.std(values),
                'min': np.min(values),
                'max': np.max(values)
            }
    
    return stats