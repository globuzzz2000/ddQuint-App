#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clustering module for ddQuint with dynamic chromosome support and buffer zone detection.

Contains functionality for:
1. HDBSCAN-based droplet clustering
2. Copy number calculation and normalization
3. Aneuploidy and buffer zone detection
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
    aneuploidy detection.
    
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
    
    # Suppress specific sklearn warnings that don't affect results
    warnings.filterwarnings("ignore", category=UserWarning, message=".*force_all_finite.*")
    warnings.filterwarnings("ignore", category=FutureWarning)
    
    # Make a full copy of input dataframe to avoid warnings
    df_copy = df.copy()
    
    # Check if we have enough data points for clustering
    if len(df_copy) < config.MIN_POINTS_FOR_CLUSTERING:
        logger.debug(f"Insufficient data points for clustering: {len(df_copy)} < {config.MIN_POINTS_FOR_CLUSTERING}")
        return _create_empty_result(df_copy)
    
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
    
    # Calculate relative copy numbers
    copy_numbers = calculate_copy_numbers(label_counts)
    logger.debug(f"Copy numbers: {copy_numbers}")
    
    # Classify copy number states and detect aneuploidies/buffer zones
    copy_number_states, has_aneuploidy, has_buffer_zone = _classify_copy_number_states(copy_numbers, config)
    
    # Check for aneuploidies in copy numbers (legacy compatibility)
    legacy_has_aneuploidy, abnormal_chroms = detect_aneuploidies(copy_numbers)
    
    # Use the more sophisticated classification if available
    final_has_aneuploidy = has_aneuploidy if copy_number_states else legacy_has_aneuploidy
    
    logger.debug(f"Final analysis - Aneuploidy: {final_has_aneuploidy}, Buffer zone: {has_buffer_zone}")
    
    return {
        'clusters': df_copy['cluster'].values,
        'df_filtered': df_filtered, 
        'counts': label_counts,
        'copy_numbers': copy_numbers,
        'copy_number_states': copy_number_states,
        'has_aneuploidy': final_has_aneuploidy,
        'has_buffer_zone': has_buffer_zone,
        'abnormal_chromosomes': abnormal_chroms,
        'target_mapping': target_mapping,
        'chrom3_reclustered': False  # Legacy field for compatibility
    }

def _create_empty_result(df_copy):
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
        'chrom3_reclustered': False
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
    # Get expected centroids from config
    expected_centroids = config.EXPECTED_CENTROIDS
    if not expected_centroids:
        error_msg = "No expected centroids configured"
        logger.error(error_msg)
        raise ConfigError(error_msg)
    
    logger.debug(f"Expected centroids: {expected_centroids}")
    
    # Calculate overall scale factor based on data range
    x_range = np.ptp(df_filtered['Ch2Amplitude'])
    y_range = np.ptp(df_filtered['Ch1Amplitude'])
    scale_factor = min(1.0, max(0.5, np.sqrt((x_range * y_range) / 2000000)))
    
    # Ensure scale factor is within config limits
    scale_factor = max(config.SCALE_FACTOR_MIN, min(config.SCALE_FACTOR_MAX, scale_factor))
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

def _classify_copy_number_states(copy_numbers, config):
    """
    Classify copy number states and detect aneuploidies/buffer zones.
    
    Args:
        copy_numbers: Dictionary of chromosome copy numbers
        config: Configuration instance
        
    Returns:
        Tuple of (copy_number_states, has_aneuploidy, has_buffer_zone)
    """
    copy_number_states = {}
    has_aneuploidy = False
    has_buffer_zone = False
    
    for chrom_name, copy_number in copy_numbers.items():
        if chrom_name.startswith('Chrom'):
            state = config.classify_copy_number_state(chrom_name, copy_number)
            copy_number_states[chrom_name] = state
            
            if state == 'buffer_zone':
                has_buffer_zone = True
                logger.debug(f"{chrom_name} classified as buffer zone: {copy_number:.3f}")
            elif state == 'aneuploidy':
                has_aneuploidy = True
                logger.debug(f"{chrom_name} classified as aneuploidy: {copy_number:.3f}")
            else:
                logger.debug(f"{chrom_name} classified as euploid: {copy_number:.3f}")
    
    # Buffer zone trumps aneuploidy - if any chromosome is in buffer zone, mark as buffer zone sample
    if has_buffer_zone:
        has_aneuploidy = False  # Reset aneuploidy flag when buffer zone is present
    
    return copy_number_states, has_aneuploidy, has_buffer_zone