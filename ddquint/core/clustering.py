"""
Enhanced clustering module for ddQuint
Improved density-based clustering of droplet data and target assignment
"""

import numpy as np
from sklearn.preprocessing import StandardScaler
from hdbscan import HDBSCAN
import warnings

# Import functions from their proper modules - fixed function name
from ..core.copy_number import calculate_copy_numbers, detect_abnormalities

def analyze_droplets(df):
    """
    Analyze droplet data using enhanced density-based clustering.
    
    Args:
        df (pandas.DataFrame): DataFrame containing Ch1Amplitude and Ch2Amplitude columns
        
    Returns:
        dict: Clustering results including counts, copy numbers, and outlier status
    """
    # Suppress specific sklearn warnings that don't affect results
    warnings.filterwarnings("ignore", category=UserWarning, message=".*force_all_finite.*")
    warnings.filterwarnings("ignore", category=FutureWarning)
    
    # Make a full copy of input dataframe to avoid warnings
    df_copy = df.copy()
    
    # Check if we have enough data points for clustering
    if len(df_copy) < 50:
        return {
            'clusters': np.array([-1] * len(df_copy)),
            'counts': {},
            'copy_numbers': {},
            'has_outlier': False,
            'target_mapping': {}
        }
    
    # Standardize the data for clustering
    X = df_copy[['Ch1Amplitude', 'Ch2Amplitude']].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    
    # Enhanced HDBSCAN clustering with improved parameters
    clusterer = HDBSCAN(
        min_cluster_size=4,
        min_samples=70,
        cluster_selection_method='eom',
        cluster_selection_epsilon=0.06,
        metric='euclidean',
        core_dist_n_jobs=1  # Use all available cores
    )
    
    clusters = clusterer.fit_predict(X_scaled)
    
    # Add cluster assignments to the dataframe
    df_copy['cluster'] = clusters
    
    # Filter out noise points (cluster -1)
    df_filtered = df_copy[df_copy['cluster'] != -1].copy()
    
    # Define expected centroids for targets
    # These are in [FAM, HEX] order (Ch1Amplitude, Ch2Amplitude)
    expected_centroids = {
        "Negative": np.array([800, 700]),
        "Chrom1":   np.array([800, 2300]),
        "Chrom2":   np.array([1700, 2100]),
        "Chrom3":   np.array([2700, 1700]),
        "Chrom4":   np.array([3300, 1250]),
        "Chrom5":   np.array([3700, 700])
    }
    
    # Define tolerance for each target (with adaptive scaling)
    # Calculate overall scale factor based on data range
    x_range = np.ptp(df_copy['Ch2Amplitude'])
    y_range = np.ptp(df_copy['Ch1Amplitude'])
    scale_factor = min(1.0, max(0.5, np.sqrt((x_range * y_range) / 2000000)))
    
    target_tol = {
        "Negative": 350 * scale_factor,
        "Chrom1":   350 * scale_factor,
        "Chrom2":   350 * scale_factor,
        "Chrom3":   350 * scale_factor,
        "Chrom4":   350 * scale_factor,
        "Chrom5":   350 * scale_factor
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
    
    # Add target labels to the dataframe
    df_filtered.loc[:, 'TargetLabel'] = df_filtered['cluster'].map(target_mapping)
    
    # Count droplets for each target
    ordered_labels = ['Negative', 'Chrom1', 'Chrom2', 'Chrom3', 'Chrom4', 'Chrom5', 'Unknown']
    label_counts = {label: len(df_filtered[df_filtered['TargetLabel'] == label]) 
                   for label in ordered_labels}

    # Calculate relative copy numbers
    copy_numbers = calculate_copy_numbers(label_counts)
    
    # Check for outliers in copy numbers
    has_outlier, abnormal_chroms = detect_abnormalities(copy_numbers)
    
    return {
        'clusters': df_copy['cluster'].values,
        'df_filtered': df_filtered, 
        'counts': label_counts,
        'copy_numbers': copy_numbers,
        'has_outlier': has_outlier,
        'abnormal_chromosomes': abnormal_chroms,
        'target_mapping': target_mapping
    }