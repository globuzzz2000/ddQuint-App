"""
Copy number calculation module for ddQuint with dynamic chromosome support
"""

import numpy as np
import logging
from ..config.config import Config

def calculate_copy_numbers(target_counts):
    """
    Calculate relative copy numbers for chromosome targets.
    
    Args:
        target_counts (dict): Counts for each target
        
    Returns:
        dict: Relative copy numbers
    """
    logger = logging.getLogger("ddQuint")
    config = Config.get_instance()
    
    # Extract all chromosome keys dynamically
    chromosome_keys = config.get_chromosome_keys()
    logger.debug(f"Found {len(chromosome_keys)} chromosomes: {chromosome_keys}")
    
    # Extract counts for all chromosomes
    raw_vals = np.array([target_counts.get(key, 0) for key in chromosome_keys])
    logger.debug(f"Raw chromosome counts: {raw_vals}")
    
    # If all chromosomes have zero count, return empty dict
    if np.all(raw_vals == 0):
        logger.debug("All chromosome counts are zero")
        return {}
    
    # Calculate median of non-zero values
    non_zero_vals = raw_vals[raw_vals > 0]
    if len(non_zero_vals) == 0:
        logger.debug("No non-zero chromosome counts")
        return {}
    
    median_val = np.median(non_zero_vals)
    logger.debug(f"Median of non-zero values: {median_val}")
    
    # Calculate deviations from median
    with np.errstate(divide='ignore', invalid='ignore'):
        deviations = np.abs(raw_vals - median_val) / median_val
        deviations = np.nan_to_num(deviations, nan=float('inf'))
    
    logger.debug(f"Deviations from median: {deviations}")
    
    # Identify values close to the median (within config threshold)
    deviation_threshold = config.COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD
    close_to_median = deviations < deviation_threshold
    logger.debug(f"Close to median (< {deviation_threshold}): {close_to_median}")
    
    # Calculate baseline for normalization
    if np.sum(close_to_median) >= config.COPY_NUMBER_BASELINE_MIN_CHROMS:
        # Use mean of values close to median as baseline
        baseline = np.mean(raw_vals[close_to_median])
        logger.debug(f"Using mean of close values as baseline: {baseline}")
    else:
        # Use median as baseline
        baseline = median_val
        logger.debug(f"Using median as baseline: {baseline}")
    
    # Calculate relative copy numbers
    copy_numbers = {}
    for i, chrom in enumerate(chromosome_keys):
        if baseline > 0 and raw_vals[i] > 0:
            copy_num = raw_vals[i] / baseline
            copy_numbers[chrom] = copy_num
            logger.debug(f"{chrom} copy number: {copy_num:.3f} (raw: {raw_vals[i]}, baseline: {baseline})")
    
    return copy_numbers

def detect_aneuploidies(copy_numbers):
    """
    Detect aneuploidies based on copy numbers with chromosome-specific thresholds.
    
    Args:
        copy_numbers (dict): Copy numbers for each chromosome
        
    Returns:
        tuple: (has_abnormality, abnormal_chromosomes)
    """
    logger = logging.getLogger("ddQuint")
    config = Config.get_instance()
    
    abnormal_chromosomes = {}
    
    for chrom, copy_num in copy_numbers.items():
        # Check for deviation from normal copy number (1.0)
        deviation = abs(copy_num - 1.0)
        
        if deviation > config.ANEUPLOIDY_DEVIATION_THRESHOLD:
            abnormal_type = 'gain' if copy_num > 1.0 else 'loss'
            abnormal_chromosomes[chrom] = {
                'copy_number': copy_num,
                'deviation': deviation,
                'type': abnormal_type
            }
            logger.debug(f"{chrom} detected as {abnormal_type}: copy number {copy_num:.3f}, deviation {deviation:.3f}")
        else:
            logger.debug(f"{chrom} is normal: copy number {copy_num:.3f}, deviation {deviation:.3f}")
    
    has_abnormality = len(abnormal_chromosomes) > 0
    logger.debug(f"Overall aneuploidy status: {has_abnormality}")
    
    return has_abnormality, abnormal_chromosomes

def calculate_statistics(results):
    """
    Calculate statistics across multiple samples with dynamic chromosome support.
    
    Args:
        results (list): List of result dictionaries
        
    Returns:
        dict: Statistics
    """
    logger = logging.getLogger("ddQuint")
    config = Config.get_instance()
    
    # Get all chromosome keys dynamically
    chromosome_keys = config.get_chromosome_keys()
    
    # Initialize data collection for all chromosomes
    chrom_data = {key: [] for key in chromosome_keys}
    
    abnormal_count = 0
    total_samples = len(results)
    
    logger.debug(f"Calculating statistics for {total_samples} samples")
    
    for result in results:
        if result.get('has_aneuploidy', False):
            abnormal_count += 1
            
        copy_numbers = result.get('copy_numbers', {})
        for chrom in chromosome_keys:
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
            logger.debug(f"{chrom} statistics: {stats['chromosomes'][chrom]}")
    
    logger.debug(f"Overall statistics: {stats}")
    
    return stats