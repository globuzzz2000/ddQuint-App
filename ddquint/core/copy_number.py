#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copy number calculation module for ddQuint with dynamic chromosome support.

Contains functionality for:
1. Relative copy number calculations with normalization
2. Aneuploidy detection based on deviation thresholds
3. Statistical analysis across multiple samples
4. Baseline calculation using median-based approach

This module provides robust copy number analysis capabilities for
digital droplet PCR data with support for up to 10 chromosome targets.
"""

import numpy as np
import logging
from ..config import Config, CopyNumberError

logger = logging.getLogger(__name__)

def calculate_copy_numbers(target_counts):
    """
    Calculate relative copy numbers for chromosome targets.
    
    Uses a sophisticated normalization algorithm that calculates the median
    of non-zero values, identifies chromosomes close to the median, and
    uses their mean as the baseline for normalization.
    
    Args:
        target_counts: Dictionary of target names to droplet counts
        
    Returns:
        Dictionary of relative copy numbers for each chromosome
        
    Raises:
        CopyNumberError: If all chromosome counts are zero or invalid
        
    Example:
        >>> counts = {'Chrom1': 1000, 'Chrom2': 950, 'Chrom3': 1100}
        >>> copy_numbers = calculate_copy_numbers(counts)
        >>> copy_numbers['Chrom1']
        0.952
    """
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
    
    # Calculate baseline for normalization
    baseline = _calculate_baseline(raw_vals, median_val, config)
    
    # Calculate relative copy numbers
    copy_numbers = {}
    for i, chrom in enumerate(chromosome_keys):
        if baseline > 0 and raw_vals[i] > 0:
            copy_num = raw_vals[i] / baseline
            copy_numbers[chrom] = copy_num
            logger.debug(f"{chrom} copy number: {copy_num:.3f} (raw: {raw_vals[i]}, baseline: {baseline})")
    
    return copy_numbers

def _calculate_baseline(raw_vals, median_val, config):
    """
    Calculate baseline for copy number normalization.
    
    Args:
        raw_vals: Array of raw chromosome counts
        median_val: Median of non-zero values
        config: Configuration instance
        
    Returns:
        Baseline value for normalization
    """
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
    
    return baseline

def detect_aneuploidies(copy_numbers):
    """
    Detect aneuploidies based on copy numbers with chromosome-specific thresholds.
    
    Identifies chromosomes with copy numbers that deviate significantly
    from the expected value of 1.0, classifying them as gains or losses.
    
    Args:
        copy_numbers: Dictionary of chromosome names to copy number values
        
    Returns:
        Tuple of (has_abnormality, abnormal_chromosomes_dict)
        
    Raises:
        CopyNumberError: If copy number values are invalid
        
    Example:
        >>> copy_nums = {'Chrom1': 1.3, 'Chrom2': 0.7, 'Chrom3': 1.0}
        >>> has_abn, abnormal = detect_aneuploidies(copy_nums)
        >>> has_abn
        True
    """
    config = Config.get_instance()
    abnormal_chromosomes = {}
    
    for chrom, copy_num in copy_numbers.items():
        if not isinstance(copy_num, (int, float)) or np.isnan(copy_num):
            error_msg = f"Invalid copy number value for {chrom}: {copy_num}"
            logger.error(error_msg)
            raise CopyNumberError(error_msg, chromosome=chrom, copy_number=copy_num)
        
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
    
    Computes mean, median, standard deviation, and range statistics
    for copy numbers across all processed samples.
    
    Args:
        results: List of result dictionaries from sample processing
        
    Returns:
        Dictionary containing comprehensive statistics
        
    Raises:
        CopyNumberError: If results contain invalid data
        
    Example:
        >>> results = [{'copy_numbers': {'Chrom1': 1.0}}, {'copy_numbers': {'Chrom1': 1.1}}]
        >>> stats = calculate_statistics(results)
        >>> stats['chromosomes']['Chrom1']['mean']
        1.05
    """
    config = Config.get_instance()
    
    if not results or not isinstance(results, list):
        error_msg = "Invalid results data for statistics calculation"
        logger.error(error_msg)
        raise CopyNumberError(error_msg)
    
    # Get all chromosome keys dynamically
    chromosome_keys = config.get_chromosome_keys()
    
    # Initialize data collection for all chromosomes
    chrom_data = {key: [] for key in chromosome_keys}
    
    abnormal_count = 0
    buffer_zone_count = 0
    total_samples = len(results)
    
    logger.debug(f"Calculating statistics for {total_samples} samples")
    
    for result in results:
        if result.get('has_aneuploidy', False):
            abnormal_count += 1
        if result.get('has_buffer_zone', False):
            buffer_zone_count += 1
            
        copy_numbers = result.get('copy_numbers', {})
        for chrom in chromosome_keys:
            if chrom in copy_numbers:
                chrom_data[chrom].append(copy_numbers[chrom])
    
    # Calculate statistics
    stats = {
        'sample_count': total_samples,
        'abnormal_count': abnormal_count,
        'buffer_zone_count': buffer_zone_count,
        'abnormal_percent': (abnormal_count / total_samples * 100) if total_samples > 0 else 0,
        'buffer_zone_percent': (buffer_zone_count / total_samples * 100) if total_samples > 0 else 0,
        'chromosomes': {}
    }
    
    for chrom, values in chrom_data.items():
        if values:
            try:
                stats['chromosomes'][chrom] = {
                    'count': len(values),
                    'mean': np.mean(values),
                    'median': np.median(values),
                    'std': np.std(values),
                    'min': np.min(values),
                    'max': np.max(values)
                }
                logger.debug(f"{chrom} statistics: {stats['chromosomes'][chrom]}")
            except Exception as e:
                error_msg = f"Error calculating statistics for {chrom}: {str(e)}"
                logger.error(error_msg)
                logger.debug(f"Error details: {str(e)}", exc_info=True)
                raise CopyNumberError(error_msg, chromosome=chrom) from e
    
    logger.debug(f"Overall statistics: abnormal={abnormal_count}/{total_samples}, buffer_zone={buffer_zone_count}/{total_samples}")
    
    return stats