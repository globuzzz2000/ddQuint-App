"""
Enhanced clustering module for ddQuint with dynamic chromosome support
"""

import numpy as np
import logging
from sklearn.preprocessing import StandardScaler
from hdbscan import HDBSCAN
import warnings

# Import functions from their proper modules
from ..core.copy_number import calculate_copy_numbers, detect_aneuploidies
from ..config.config import Config

def analyze_droplets(df):
    """
    Analyze droplet data using enhanced density-based clustering.
    
    Args:
        df (pandas.DataFrame): DataFrame containing Ch1Amplitude and Ch2Amplitude columns
        
    Returns:
        dict: Clustering results including counts, copy numbers, and aneuploidy status
    """
    logger = logging.getLogger("ddQuint")
    config = Config.get_instance()
    
    # Suppress specific sklearn warnings that don't affect results
    warnings.filterwarnings("ignore", category=UserWarning, message=".*force_all_finite.*")
    warnings.filterwarnings("ignore", category=FutureWarning)
    
    # Make a full copy of input dataframe to avoid warnings
    df_copy = df.copy()
    
    # Check if we have enough data points for clustering
    if len(df_copy) < config.MIN_POINTS_FOR_CLUSTERING:
        logger.debug(f"Not enough data points for clustering: {len(df_copy)} < {config.MIN_POINTS_FOR_CLUSTERING}")
        return {
            'clusters': np.array([-1] * len(df_copy)),
            'counts': {},
            'copy_numbers': {},
            'has_aneuploidy': False,
            'target_mapping': {}
        }
    
    # Standardize the data for clustering
    X = df_copy[['Ch1Amplitude', 'Ch2Amplitude']].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    logger.debug(f"Data scaled. Shape: {X_scaled.shape}")
    
    # Get HDBSCAN parameters from config
    hdbscan_params = config.get_hdbscan_params()
    logger.debug(f"HDBSCAN parameters: {hdbscan_params}")
    
    # Enhanced HDBSCAN clustering with configured parameters
    clusterer = HDBSCAN(**hdbscan_params)
    
    clusters = clusterer.fit_predict(X_scaled)
    logger.debug(f"Clustering completed. Unique clusters: {np.unique(clusters)}")
    
    # Add cluster assignments to the dataframe
    df_copy['cluster'] = clusters
    
    # Filter out noise points (cluster -1)
    df_filtered = df_copy[df_copy['cluster'] != -1].copy()
    logger.debug(f"Filtered data shape: {df_filtered.shape}")
    
    # Get expected centroids from config
    expected_centroids = config.EXPECTED_CENTROIDS
    logger.debug(f"Expected centroids: {expected_centroids}")
    
    # Calculate overall scale factor based on data range
    x_range = np.ptp(df_copy['Ch2Amplitude'])
    y_range = np.ptp(df_copy['Ch1Amplitude'])
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
    if "Negative" in expected_centroids:
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
    
    # Assign the rest of the targets
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
    
    # Check for aneuploidies in copy numbers
    has_aneuploidy, abnormal_chroms = detect_aneuploidies(copy_numbers)
    logger.debug(f"Has aneuploidy: {has_aneuploidy}, Abnormal chromosomes: {abnormal_chroms}")
    
    return {
        'clusters': df_copy['cluster'].values,
        'df_filtered': df_filtered, 
        'counts': label_counts,
        'copy_numbers': copy_numbers,
        'has_aneuploidy': has_aneuploidy,
        'abnormal_chromosomes': abnormal_chroms,
        'target_mapping': target_mapping
    }