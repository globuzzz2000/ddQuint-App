#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copy number calculation module for ddQuint with analytical estimation.

Contains functionality for:
1. Analytical estimation for true target concentrations
2. Poisson-corrected copy number calculations accounting for mixed droplets
3. Aneuploidy detection based on corrected concentrations
4. Statistical analysis across multiple samples

This module provides robust copy number analysis capabilities for
digital droplet PCR data with proper handling of mixed-positive droplets.
Uses analytical solution optimized for exclusive target count data.
"""

import numpy as np
import logging
from ..config import Config, CopyNumberError

logger = logging.getLogger(__name__)

def calculate_copy_numbers(target_counts, total_droplets):
    """
    Calculate relative copy numbers using analytical estimation.
    
    Uses direct analytical solution to account for mixed-positive droplets and obtain
    true target concentrations, then normalizes relative to diploid baseline.
    
    Args:
        target_counts: Dictionary of target names to droplet counts
        total_droplets: Total number of droplets analyzed
        
    Returns:
        Dictionary of relative copy numbers for each chromosome
        
    Raises:
        CopyNumberError: If estimation fails or data is invalid
        
    Example:
        >>> counts = {'Chrom1': 1159, 'Chrom2': 1250, 'Chrom3': 1166, 'Negative': 3325}
        >>> copy_numbers = calculate_copy_numbers(counts, 17431)
        >>> copy_numbers['Chrom1']
        0.952
    """
    config = Config.get_instance()
    
    # Check minimum usable droplets threshold
    if total_droplets < config.MIN_USABLE_DROPLETS:
        logger.debug(f"Insufficient droplets for analysis: {total_droplets} < {config.MIN_USABLE_DROPLETS}")
        return {}
    
    # Extract chromosome keys and validate data
    chromosome_keys = config.get_chromosome_keys()
    logger.debug(f"Found {len(chromosome_keys)} chromosomes: {chromosome_keys}")
    
    if total_droplets <= 0:
        logger.debug("No droplets available for analysis")
        return {}
    
    # Extract counts
    negative_count = target_counts.get('Negative', 0)
    chromosome_counts = {key: target_counts.get(key, 0) for key in chromosome_keys}
    
    logger.debug(f"Total droplets: {total_droplets}, Negative: {negative_count}")
    logger.debug(f"Chromosome counts: {chromosome_counts}")
    
    # Estimate true concentrations using analytical solution
    try:
        true_concentrations = _estimate_concentrations_analytical(
            chromosome_counts, negative_count, total_droplets, chromosome_keys
        )
        logger.debug(f"Estimated concentrations: {true_concentrations}")
    except Exception as e:
        # Log the specific error type for debugging without printing to console
        error_msg = f"Analytical estimation failed: {str(e)}"
        logger.debug(error_msg)  # Only debug level - no warning/error level
        raise CopyNumberError(error_msg) from e
    
    # Calculate baseline for normalization
    baseline = _calculate_baseline(true_concentrations, config)
    
    if baseline <= 0:
        logger.debug("No valid baseline for normalization")
        return {}
    
    # Calculate relative copy numbers
    copy_numbers = {}
    for chrom, concentration in true_concentrations.items():
        if concentration > 0:
            copy_num = concentration / baseline
            copy_numbers[chrom] = copy_num
            logger.debug(f"{chrom} relative copy number: {copy_num:.3f} (concentration: {concentration:.3f}, baseline: {baseline:.3f})")
    
    return copy_numbers

def _estimate_concentrations_analytical(chromosome_counts, negative_count, total_droplets, chromosome_keys):
    """
    Estimate true target concentrations using analytical solution.
    
    For independent Poisson processes where we observe exclusive counts:
    - Empty bins (negative droplets): 0 of all targets
    - Only target A bins: ≥1 of A, 0 of all others
    - Only target B bins: ≥1 of B, 0 of all others
    - etc.
    
    Uses the mathematical relationship:
    P(only target i) = (1 - e^(-λᵢ)) × ∏(j≠i) e^(-λⱼ)
    P(empty) = ∏ᵢ e^(-λᵢ)
    
    Therefore: P(only i) / P(empty) = (e^(λᵢ) - 1)
    So: λᵢ = ln(1 + P(only i) / P(empty))
    
    Args:
        chromosome_counts: Dictionary of chromosome counts (exclusive)
        negative_count: Number of negative droplets
        total_droplets: Total number of droplets
        chromosome_keys: List of chromosome identifiers
        
    Returns:
        Dictionary of estimated concentrations for each chromosome
        
    Raises:
        CopyNumberError: If data is inconsistent or invalid
    """
    logger.debug("Starting analytical concentration estimation")
    
    n_targets = len(chromosome_keys)
    if n_targets == 0:
        return {}
    
    # Calculate probabilities
    p_empty = negative_count / total_droplets
    
    if p_empty <= 0:
        raise CopyNumberError("No negative droplets found - cannot estimate concentrations")
    if p_empty >= 1:
        raise CopyNumberError("All droplets are negative - no targets detected")
    
    logger.debug(f"P(empty) = {negative_count}/{total_droplets} = {p_empty:.6f}")
    
    # Calculate λ values using analytical formula
    concentrations = {}
    
    for chrom in chromosome_keys:
        count = chromosome_counts[chrom]
        p_only_chrom = count / total_droplets
        
        logger.debug(f"P(only {chrom}) = {count}/{total_droplets} = {p_only_chrom:.6f}")
        
        if count == 0:
            # No droplets for this target
            concentrations[chrom] = 0.0
            logger.debug(f"{chrom}: No droplets detected, λ = 0.0")
        else:
            # Calculate λᵢ = ln(1 + P(only i) / P(empty))
            ratio = p_only_chrom / p_empty
            lambda_i = np.log(1 + ratio)
            concentrations[chrom] = lambda_i
            
            logger.debug(f"{chrom}: P(only)/P(empty) = {ratio:.6f}, λ = {lambda_i:.6f}")
    
    # Validation: Check consistency with empty droplets
    _validate_concentration_estimates(concentrations, p_empty, chromosome_keys)
    
    return concentrations

def _validate_concentration_estimates(concentrations, p_empty_observed, chromosome_keys):
    """
    Validate that estimated concentrations are consistent with observed data.
    
    Checks that the sum of individual λ values is approximately equal to
    the total λ derived from empty droplets: -ln(P(empty)) = Σλᵢ
    
    Args:
        concentrations: Dictionary of estimated λ values
        p_empty_observed: Observed probability of empty droplets
        chromosome_keys: List of chromosome identifiers
        
    Raises:
        CopyNumberError: If estimates are very inconsistent
    """
    lambda_total_from_individual = sum(concentrations.values())
    lambda_total_from_empty = -np.log(p_empty_observed)
    
    relative_error = abs(lambda_total_from_individual - lambda_total_from_empty) / lambda_total_from_empty
    
    logger.debug(f"Validation check:")
    logger.debug(f"  Sum of individual λ values: {lambda_total_from_individual:.6f}")
    logger.debug(f"  λ_total from empty droplets: {lambda_total_from_empty:.6f}")
    logger.debug(f"  Relative error: {relative_error:.3%}")
    
    # Allow up to 5% relative error (should be much smaller for good data)
    if relative_error > 0.05:
        # Only log to debug level, not warning level
        logger.debug(f"Large inconsistency in concentration estimates: {relative_error:.3%} error")
        logger.debug("This may indicate non-Poisson effects or data quality issues")
    
    # For very large errors, raise an exception
    if relative_error > 0.20:
        raise CopyNumberError(f"Concentration estimates are inconsistent: {relative_error:.1%} error. "
                            "Data may not follow Poisson distribution assumptions.")


def _calculate_baseline(concentrations, config):
    """
    Calculate baseline for copy number normalization using true concentrations.
    
    Args:
        concentrations: Dictionary of true concentrations
        config: Configuration instance
        
    Returns:
        Baseline concentration representing diploid state
    """
    # Get non-zero concentrations
    non_zero_concs = [c for c in concentrations.values() if c > 0]
    
    if len(non_zero_concs) == 0:
        return 0.0
    
    # Calculate median concentration
    median_conc = np.median(non_zero_concs)
    logger.debug(f"Median concentration: {median_conc:.3f}")
    
    # Find concentrations close to median for diploid baseline
    deviation_threshold = config.COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD
    close_to_median = []
    
    for conc in non_zero_concs:
        if median_conc > 0:
            deviation = abs(conc - median_conc) / median_conc
            if deviation < deviation_threshold:
                close_to_median.append(conc)
    
    if len(close_to_median) >= config.COPY_NUMBER_BASELINE_MIN_CHROMS:
        baseline = np.mean(close_to_median)
        logger.debug(f"Using mean of {len(close_to_median)} diploid chromosomes as baseline: {baseline:.3f}")
    else:
        baseline = median_conc
        logger.debug(f"Using median as baseline: {baseline:.3f}")
    
    return baseline

def detect_aneuploidies(copy_numbers):
    """
    Detect aneuploidies based on analytically-corrected copy numbers.
    
    Identifies chromosomes with copy numbers that deviate significantly
    from the expected value of 1.0, using the corrected concentrations
    that account for mixed-positive droplets.
    
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
        
        if deviation > config.COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD:
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
    Calculate statistics across multiple samples using analytically-corrected copy numbers.
    
    Computes mean, median, standard deviation, and range statistics
    for copy numbers across all processed samples, using the corrected
    values that account for mixed-positive droplets.
    
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
    
    logger.debug(f"Calculating statistics for {total_samples} samples using analytically-corrected values")
    
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