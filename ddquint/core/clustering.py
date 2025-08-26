#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clustering module for ddQuint with standard deviation-based classification system.

Contains functionality for:
1. HDBSCAN-based droplet clustering
2. Copy number calculation and normalization
3. Standard deviation-based aneuploidy and buffer zone detection
4. Target assignment based on expected centroids

This module integrates with the broader ddQuint pipeline to provide
robust clustering capabilities for digital droplet PCR analysis.
"""

import numpy as np
import logging
from sklearn.preprocessing import StandardScaler
from hdbscan import HDBSCAN
import warnings

# Import functions from their proper modules
from ..core.copy_number import calculate_copy_numbers, detect_aneuploidies
from ..config import Config, ClusteringError, ConfigError

logger = logging.getLogger(__name__)

def analyze_droplets(df):
    """
    Analyze droplet data using enhanced density-based clustering.
    
    Performs HDBSCAN clustering on droplet amplitude data and calculates
    copy numbers for each chromosome target. Includes buffer zone and
    aneuploidy detection using standard deviation-based tolerances.
    
    Args:
        df: DataFrame containing Ch1Amplitude and Ch2Amplitude columns
        
    Returns:
        Dictionary containing clustering results, copy numbers, and aneuploidy status
        
    Raises:
        ClusteringError: If clustering fails or insufficient data points
        ConfigError: If configuration parameters are invalid
        
    Example:
        >>> df = pd.DataFrame({'Ch1Amplitude': [800, 900], 'Ch2Amplitude': [700, 800]})
        >>> results = analyze_droplets(df)
        >>> results['has_aneuploidy']
        False
    """
    config = Config.get_instance()
    
    # Debug: Log key parameters that might be well-specific
    logger.info(f"🔧 CLUSTERING DEBUG - Config instance: {id(config)}")
    logger.info(f"🔧 CLUSTERING DEBUG - MIN_POINTS_FOR_CLUSTERING: {getattr(config, 'MIN_POINTS_FOR_CLUSTERING', 'NOT_SET')}")
    logger.info(f"🔧 CLUSTERING DEBUG - HDBSCAN_MIN_CLUSTER_SIZE: {getattr(config, 'HDBSCAN_MIN_CLUSTER_SIZE', 'NOT_SET')}")
    logger.info(f"🔧 CLUSTERING DEBUG - TOLERANCE_MULTIPLIER: {getattr(config, 'TOLERANCE_MULTIPLIER', 'NOT_SET')}")
    logger.info(f"🔧 CLUSTERING DEBUG - CHROMOSOME_COUNT: {getattr(config, 'CHROMOSOME_COUNT', 'NOT_SET')}")
    
    # Suppress specific sklearn warnings that don't affect results
    warnings.filterwarnings("ignore", category=UserWarning, message=".*force_all_finite.*")
    warnings.filterwarnings("ignore", category=FutureWarning)
    
    # Make a full copy of input dataframe to avoid warnings
    df_copy = df.copy()
    
    # Store total droplets for reporting
    total_droplets = len(df_copy)
    
    # Check if we have enough data points for clustering
    min_points = getattr(config, 'MIN_POINTS_FOR_CLUSTERING', 50)  # Use instance-aware access
    if len(df_copy) < min_points:
        logger.debug(f"Insufficient data points for clustering: {len(df_copy)} < {min_points}")
        return _create_empty_result(df_copy, total_droplets)
    
    # Standardize the data for clustering
    X = df_copy[['Ch1Amplitude', 'Ch2Amplitude']].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    logger.debug(f"Data scaled. Shape: {X_scaled.shape}")
    
    # Get HDBSCAN parameters from config
    hdbscan_params = config.get_hdbscan_params()
    logger.debug(f"HDBSCAN parameters: {hdbscan_params}")
    
    # Enhanced HDBSCAN clustering with configured parameters
    try:
        clusterer = HDBSCAN(**hdbscan_params)
        clusters = clusterer.fit_predict(X_scaled)
        logger.debug(f"Clustering completed. Unique clusters: {np.unique(clusters)}")
    except Exception as e:
        error_msg = f"HDBSCAN clustering failed: {str(e)}"
        logger.error(error_msg)
        raise ClusteringError(error_msg) from e
    
    # Add cluster assignments to the dataframe
    df_copy['cluster'] = clusters
    
    # Filter out noise points (cluster -1)
    df_filtered = df_copy[df_copy['cluster'] != -1].copy()
    logger.debug(f"Filtered data shape: {df_filtered.shape}")
    
    # Assign targets to clusters
    target_mapping = _assign_targets_to_clusters(df_filtered, config)
    
    # Add target labels to the dataframe
    df_filtered.loc[:, 'TargetLabel'] = df_filtered['cluster'].map(target_mapping)
    
    # Get ordered labels dynamically from config
    ordered_labels = config.get_ordered_labels()
    logger.debug(f"Ordered labels: {ordered_labels}")
    
    # Count droplets for each target
    label_counts = {label: len(df_filtered[df_filtered['TargetLabel'] == label]) 
                   for label in ordered_labels}
    
    logger.debug(f"Label counts: {label_counts}")
    
    # Calculate droplet metrics
    negative_droplets = label_counts.get('Negative', 0)
    usable_droplets = sum(count for label, count in label_counts.items() 
                         if label != 'Negative' and label != 'Unknown')
    
    # Always calculate relative copy numbers with total droplets for ML estimation
    copy_numbers = calculate_copy_numbers(label_counts, total_droplets)
    logger.debug(f"ML-corrected copy numbers: {copy_numbers}")
    
    # Check if copy number analysis (buffer zones) is enabled
    enable_copy_number = config.get_enable_copy_number_analysis()
    logger.debug(f"Copy number analysis (buffer zones) enabled: {enable_copy_number}")
    
    # Check if deviation classification (aneuploidy) is enabled
    classify_deviations = config.get_classify_cnv_deviations()
    logger.debug(f"CNV deviation classification (aneuploidy) enabled: {classify_deviations}")
    
    if enable_copy_number:
        # Classify copy number states using standard deviation-based tolerances
        copy_number_states, has_aneuploidy, has_buffer_zone = _classify_copy_number_states_std_dev(copy_numbers, config, classify_deviations)
        
        # Detect abnormal chromosomes for detailed reporting
        _, abnormal_chroms = detect_aneuploidies(copy_numbers)
    else:
        # Copy number analysis disabled - no buffer zones or aneuploidy detection
        copy_number_states = {chrom: 'euploid' for chrom in copy_numbers.keys()}
        has_aneuploidy = False
        has_buffer_zone = False
        abnormal_chroms = []
        logger.debug("Copy number analysis disabled - no buffer zones or aneuploidy detection")
    
    logger.debug(f"Final analysis - Aneuploidy: {has_aneuploidy}, Buffer zone: {has_buffer_zone}")
    logger.debug(f"Droplet metrics - Total: {total_droplets}, Usable: {usable_droplets}, Negative: {negative_droplets}")
    
    return {
        'clusters': df_copy['cluster'].values,
        'df_filtered': df_filtered, 
        'counts': label_counts,
        'copy_numbers': copy_numbers,
        'copy_number_states': copy_number_states,
        'has_aneuploidy': has_aneuploidy,
        'has_buffer_zone': has_buffer_zone,
        'abnormal_chromosomes': abnormal_chroms,
        'target_mapping': target_mapping,
        'total_droplets': total_droplets,
        'usable_droplets': usable_droplets,
        'negative_droplets': negative_droplets
    }

def _create_empty_result(df_copy, total_droplets):
    """Create empty result when clustering cannot be performed."""
    return {
        'clusters': np.array([-1] * len(df_copy)),
        'df_filtered': df_copy,
        'counts': {},
        'copy_numbers': {},
        'copy_number_states': {},
        'has_aneuploidy': False,
        'has_buffer_zone': False,
        'target_mapping': {},
        'total_droplets': total_droplets,
        'usable_droplets': 0,
        'negative_droplets': 0
    }

def _assign_targets_to_clusters(df_filtered, config):
    """
    Assign targets to clusters based on distance to expected centroids.
    
    Args:
        df_filtered: DataFrame with filtered cluster data
        config: Configuration instance
        
    Returns:
        Dictionary mapping cluster IDs to target names
        
    Raises:
        ConfigError: If expected centroids are not configured
    """
    # Get expected centroids from config (with per-instance support)
    expected_centroids = config.get_expected_centroids()
    if not expected_centroids:
        error_msg = "No expected centroids configured"
        logger.error(error_msg)
        raise ConfigError(error_msg)
    
    logger.debug(f"Expected centroids: {expected_centroids}")
    
    # Calculate overall scale factor based on data range
    x_range = np.ptp(df_filtered['Ch2Amplitude'])
    y_range = np.ptp(df_filtered['Ch1Amplitude'])
    scale_factor = min(1.0, max(0.5, np.sqrt((x_range * y_range) / 2000000)))
    
    # Use scale factor directly (no limits)
    logger.debug(f"Calculated scale factor: {scale_factor}")
    
    # Get target tolerance with scale factor
    target_tol = config.get_target_tolerance(scale_factor)
    logger.debug(f"Target tolerance: {target_tol}")
    
    # Calculate centroids for each cluster
    cluster_centroids = {}
    for cluster_id in df_filtered['cluster'].unique():
        cluster_data = df_filtered[df_filtered['cluster'] == cluster_id]
        centroid = np.array([
            cluster_data['Ch1Amplitude'].mean(),
            cluster_data['Ch2Amplitude'].mean()
        ])
        cluster_centroids[cluster_id] = centroid
        logger.debug(f"Cluster {cluster_id} centroid: {centroid}")
    
    # Assign targets to clusters based on distance to expected centroids
    target_mapping = {cl: "Unknown" for cl in df_filtered['cluster'].unique()}
    remaining_cls = set(cluster_centroids.keys())
    
    # First try assigning "Negative" since it's usually well defined
    if "Negative" in expected_centroids and remaining_cls:
        _assign_negative_cluster(expected_centroids, cluster_centroids, target_tol, 
                               target_mapping, remaining_cls)
    
    # Assign the rest of the targets
    _assign_remaining_targets(expected_centroids, cluster_centroids, target_tol,
                            target_mapping, remaining_cls)
    
    return target_mapping

def _assign_negative_cluster(expected_centroids, cluster_centroids, target_tol, 
                           target_mapping, remaining_cls):
    """Assign the Negative cluster first since it's usually well-defined."""
    neg_ref = expected_centroids["Negative"]
    neg_dists = {
        cl: np.linalg.norm(centroid - neg_ref)
        for cl, centroid in cluster_centroids.items()
        if cl in remaining_cls
    }
    
    if neg_dists:
        cl_best, d_best = min(neg_dists.items(), key=lambda t: t[1])
        if d_best < target_tol["Negative"]:
            target_mapping[cl_best] = "Negative"
            remaining_cls.remove(cl_best)
            logger.debug(f"Assigned cluster {cl_best} to Negative (distance: {d_best:.2f})")

def _assign_remaining_targets(expected_centroids, cluster_centroids, target_tol,
                            target_mapping, remaining_cls):
    """Assign remaining targets to clusters."""
    for target, ref in expected_centroids.items():
        if target == "Negative" or not remaining_cls:
            continue
        
        # Calculate distances from each remaining cluster to this target
        dists = {
            cl: np.linalg.norm(centroid - ref)
            for cl, centroid in cluster_centroids.items()
            if cl in remaining_cls
        }
        
        if not dists:
            continue
        
        # Find the closest cluster
        cl_best, d_best = min(dists.items(), key=lambda t: t[1])
        
        # Assign target if within tolerance
        if d_best < target_tol[target]:
            target_mapping[cl_best] = target
            remaining_cls.remove(cl_best)
            logger.debug(f"Assigned cluster {cl_best} to {target} (distance: {d_best:.2f})")
        else:
            logger.debug(f"Cluster {cl_best} too far from {target} (distance: {d_best:.2f} > tolerance: {target_tol[target]})")

def _classify_copy_number_states_std_dev(copy_numbers, config, classify_deviations=True):
    """
    Classify copy number states using standard deviation-based tolerances.
    
    Args:
        copy_numbers: Dictionary of chromosome copy numbers
        config: Configuration instance
        classify_deviations: Whether to classify aneuploidy (if False, only buffer zones)
        
    Returns:
        Tuple of (copy_number_states, has_aneuploidy, has_buffer_zone)
    """
    copy_number_states = {}
    has_aneuploidy = False
    has_buffer_zone = False
    
    logger.debug("Classifying copy number states using standard deviation-based tolerances")
    
    for chrom_name, copy_number in copy_numbers.items():
        if chrom_name.startswith('Chrom'):
            # Use the new standard deviation-based classification
            state = config.classify_copy_number_state(chrom_name, copy_number)
            
            # If deviation classification is disabled, reclassify aneuploidy based on buffer zone tolerance
            if not classify_deviations and state == 'aneuploidy':
                # Get expected value and tolerance
                expected_copy_numbers = config.get_expected_copy_numbers()
                expected = expected_copy_numbers.get(chrom_name, 1.0)
                tolerance = config.get_tolerance_for_chromosome(chrom_name)
                
                # Check if it falls within buffer zone tolerance (±X SDs from expected)
                deviation = abs(copy_number - expected)
                if deviation <= tolerance:
                    state = 'euploid'  # Within tolerance, so normal
                else:
                    state = 'buffer_zone'  # Outside tolerance but not classified as aneuploidy
                
            copy_number_states[chrom_name] = state
            
            # Get tolerance for logging
            tolerance = config.get_tolerance_for_chromosome(chrom_name)
            expected_copy_numbers = config.get_expected_copy_numbers()  # Use instance-aware method
            expected = expected_copy_numbers.get(chrom_name, 1.0)
            
            if state == 'buffer_zone':
                has_buffer_zone = True
                logger.debug(f"{chrom_name} classified as buffer zone: {copy_number:.3f} "
                           f"(expected: {expected:.3f}, tolerance: ±{tolerance:.3f})")
            elif state == 'aneuploidy':
                has_aneuploidy = True
                logger.debug(f"{chrom_name} classified as aneuploidy: {copy_number:.3f} "
                           f"(expected: {expected:.3f}, tolerance: ±{tolerance:.3f})")
            else:
                logger.debug(f"{chrom_name} classified as euploid: {copy_number:.3f} "
                           f"(expected: {expected:.3f}, tolerance: ±{tolerance:.3f})")
    
    # Buffer zone trumps aneuploidy - if any chromosome is in buffer zone, mark as buffer zone sample
    if has_buffer_zone:
        has_aneuploidy = False  # Reset aneuploidy flag when buffer zone is present
        logger.debug("Sample marked as buffer zone (overrides aneuploidy classification)")
    
    # Additional logging for classification settings
    if not classify_deviations:
        logger.debug("Aneuploidy classification disabled - only buffer zones detected")
    
    return copy_number_states, has_aneuploidy, has_buffer_zone