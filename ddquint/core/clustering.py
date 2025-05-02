"""
Clustering module for ddQuint
Handles density-based clustering of droplet data and target assignment
"""

import numpy as np
from sklearn.preprocessing import StandardScaler
from hdbscan import HDBSCAN

def analyze_droplets(df):
    """
    Analyze droplet data using density-based clustering.
    
    Args:
        df (pandas.DataFrame): DataFrame containing Ch1Amplitude and Ch2Amplitude columns
        
    Returns:
        dict: Clustering results including counts, copy numbers, and outlier status
    """
    # Make a full copy of input dataframe to avoid warnings
    df_copy = df.copy()
    
    # Standardize the data for clustering
    X = df_copy[['Ch1Amplitude', 'Ch2Amplitude']].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Apply HDBSCAN clustering
    clusterer = HDBSCAN(
        min_cluster_size=8,
        min_samples=5,
        cluster_selection_method='eom',
        cluster_selection_epsilon=0.03,
        metric='euclidean',
        core_dist_n_jobs=1
    )
    
    clusters = clusterer.fit_predict(X_scaled)
    
    # Add cluster assignments to the dataframe
    df_copy['cluster'] = clusters
    
    # Filter out noise points (cluster -1)
    df_filtered = df_copy[df_copy['cluster'] != -1].copy()  # Create a proper copy here
    
    # If no valid clusters were found, return empty results
    if df_filtered.empty or len(df_filtered['cluster'].unique()) == 0:
        return {
            'clusters': clusters,
            'counts': {},
            'copy_numbers': {},
            'has_outlier': False,
            'target_mapping': {}
        }
    
    # Define expected centroids for targets
    # These are in [FAM, HEX] order (Ch1Amplitude, Ch2Amplitude)
    expected_centroids = {
        "Negative": np.array([800, 700]),
        "Chrom1":   np.array([800, 2300]),
        "Chrom2":   np.array([1700, 2100]),
        "Chrom3":   np.array([3050, 1850]),
        "Chrom4":   np.array([3300, 1250]),
        "Chrom5":   np.array([3900, 700])
    }
    
    # Define tolerance for each target
    target_tol = {
        "Negative": 350,
        "Chrom1":   350,
        "Chrom2":   350,
        "Chrom3":   400,
        "Chrom4":   350,
        "Chrom5":   350
    }
    
    # Calculate centroids for each cluster
    cluster_centroids = {}
    for cluster_id in df_filtered['cluster'].unique():
        cluster_data = df_filtered[df_filtered['cluster'] == cluster_id]
        centroid = np.array([
            cluster_data['Ch1Amplitude'].mean(),
            cluster_data['Ch2Amplitude'].mean()
        ])
        cluster_centroids[cluster_id] = centroid
    
    # Assign targets to clusters based on distance to expected centroids
    target_mapping = {cl: "Unknown" for cl in df_filtered['cluster'].unique()}
    remaining_cls = set(cluster_centroids.keys())
    
    for target, ref in expected_centroids.items():
        if not remaining_cls:
            break
        
        # Calculate distances from each remaining cluster to this target
        dists = {
            cl: np.linalg.norm(centroid - ref)
            for cl, centroid in cluster_centroids.items()
            if cl in remaining_cls
        }
        
        if not dists:
            break
        
        # Find the closest cluster
        cl_best, d_best = min(dists.items(), key=lambda t: t[1])
        
        # Assign target if within tolerance
        if d_best < target_tol[target]:
            target_mapping[cl_best] = target
            remaining_cls.remove(cl_best)
    
    # Add target labels to the dataframe - FIX: use loc to avoid SettingWithCopyWarning
    df_filtered.loc[:, 'TargetLabel'] = df_filtered['cluster'].map(target_mapping)
    
    # Count droplets for each target
    ordered_labels = ['Negative', 'Chrom1', 'Chrom2', 'Chrom3', 'Chrom4', 'Chrom5', 'Unknown']
    label_counts = {label: len(df_filtered[df_filtered['TargetLabel'] == label]) 
                   for label in ordered_labels}
    
    # Calculate relative copy numbers
    copy_numbers = calculate_copy_numbers(label_counts)
    
    # Check for outliers in copy numbers
    has_outlier = check_for_outliers(copy_numbers)
    
    return {
        'clusters': clusters,
        'df_filtered': df_filtered,
        'counts': label_counts,
        'copy_numbers': copy_numbers,
        'has_outlier': has_outlier,
        'target_mapping': target_mapping
    }

def calculate_copy_numbers(label_counts):
    """
    Calculate relative copy numbers based on droplet counts.
    
    Args:
        label_counts (dict): Counts for each target
        
    Returns:
        dict: Relative copy numbers
    """
    # Extract raw counts for chromosomes
    raw_vals = np.array([
        label_counts.get('Chrom1', 0),
        label_counts.get('Chrom2', 0),
        label_counts.get('Chrom3', 0),
        label_counts.get('Chrom4', 0),
        label_counts.get('Chrom5', 0)
    ])
    
    # Handle case with no droplets
    if np.all(raw_vals == 0) or np.median(raw_vals) == 0:
        return {}
    
    # Calculate median of non-zero values
    median_val = np.median(raw_vals[raw_vals > 0]) if np.any(raw_vals > 0) else 1
    
    # Calculate deviations from median
    with np.errstate(divide='ignore', invalid='ignore'):
        dev = np.abs(raw_vals - median_val) / median_val
        dev = np.nan_to_num(dev, nan=float('inf'))
    
    # Identify values close to the median (within 15%)
    mask_good = dev < 0.15
    
    # Calculate baseline for normalization
    if mask_good.sum() >= 3:
        baseline = np.mean(raw_vals[mask_good])
    else:
        baseline = median_val
    
    # Calculate relative copy numbers
    rel_vals = np.zeros_like(raw_vals, dtype=float)
    for i in range(len(raw_vals)):
        if baseline != 0 and raw_vals[i] != 0:
            rel_vals[i] = raw_vals[i] / baseline
        else:
            rel_vals[i] = np.nan
    
    # Create dictionary of copy numbers
    copy_numbers = {}
    for i, chrom in enumerate(['Chrom1', 'Chrom2', 'Chrom3', 'Chrom4', 'Chrom5']):
        if not np.isnan(rel_vals[i]):
            copy_numbers[chrom] = rel_vals[i]
    
    return copy_numbers

def check_for_outliers(copy_numbers):
    """
    Check for outliers in copy numbers.
    
    Args:
        copy_numbers (dict): Copy numbers for each chromosome
        
    Returns:
        bool: True if outliers are detected, False otherwise
    """
    # Check if any chromosome has a copy number more than 15% different from 1.0
    for val in copy_numbers.values():
        if abs(val - 1.0) > 0.15:
            return True
    
    return False