#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Non-mixing (Amplitude Multiplex) 4-plex pipeline.

Classifies droplets by nearest expected combination centroid derived from
user-provided single-target centroids and the negative centroid. Produces
per-subset counts, per-target positive rates, and a plotting-compatible
result structure to integrate with existing visualization and exports.
"""

from itertools import combinations
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

from ..config import Config, ConfigError
from sklearn.preprocessing import StandardScaler
from hdbscan import HDBSCAN


def _subset_centroid(neg: np.ndarray, singles: Dict[str, np.ndarray], subset: Tuple[str, ...]) -> np.ndarray:
    # C_S = sum(C_i) - (|S|-1) * C_neg
    s = np.sum([singles[k] for k in subset], axis=0)
    return s - (len(subset) - 1) * neg


def _build_expected_combo_centroids(expected: Dict[str, List[float]], n: int) -> Dict[str, np.ndarray]:
    if 'Negative' not in expected:
        raise ConfigError("Negative centroid required for non-mixing mode", config_key='EXPECTED_CENTROIDS')
    neg = np.array(expected['Negative'], dtype=float)
    # Collect single-target centroids
    singles: Dict[str, np.ndarray] = {}
    chrom_keys = [f'Chrom{i}' for i in range(1, n + 1)]
    for k in chrom_keys:
        if k not in expected:
            raise ConfigError(f"Missing centroid for {k}", config_key='EXPECTED_CENTROIDS')
        singles[k] = np.array(expected[k], dtype=float)

    # Include Negative as a class
    combo: Dict[str, np.ndarray] = {'Negative': neg}
    # All non-empty subsets
    for r in range(1, n + 1):
        for subset in combinations(chrom_keys, r):
            label = '+'.join(subset) if r > 1 else subset[0]
            combo[label] = _subset_centroid(neg, singles, subset)
    return combo


def _compute_scale_and_tol(df: pd.DataFrame) -> float:
    # Approximate scale as in clustering module
    x_range = np.ptp(df['Ch2Amplitude'].values)
    y_range = np.ptp(df['Ch1Amplitude'].values)
    scale_factor = min(1.0, max(0.5, np.sqrt((x_range * y_range) / 2000000)))
    return scale_factor


def analyze_non_mixing_4plex(df: pd.DataFrame) -> Dict:
    """
    Analyze droplets using non-mixing amplitude multiplex model (N<=4).

    Args:
        df: DataFrame with columns 'Ch1Amplitude', 'Ch2Amplitude'

    Returns:
        dict compatible with existing plotting/export paths.
    """
    config = Config.get_instance()
    n = int(getattr(config, 'CHROMOSOME_COUNT', 4))
    if n > 4:
        n = 4  # hard cap in this mode

    expected = Config.get_expected_centroids()
    combos = _build_expected_combo_centroids(expected, n)

    df_copy = df[['Ch1Amplitude', 'Ch2Amplitude']].copy()
    scale = _compute_scale_and_tol(df_copy)
    tol_map = Config.get_target_tolerance(scale)
    base_tol = float(next(iter(tol_map.values()))) if tol_map else 750.0

    # HDBSCAN clustering on scaled amplitudes
    X = df_copy[['Ch1Amplitude', 'Ch2Amplitude']].values.astype(float)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    params = Config.get_hdbscan_params()
    clusterer = HDBSCAN(**params)
    cluster_labels = clusterer.fit_predict(X_scaled)
    df_copy['cluster'] = cluster_labels

    # Compute observed centroids in original amplitude space for non-noise clusters
    observed_centroids: Dict[int, np.ndarray] = {}
    for cl in np.unique(cluster_labels):
        if cl == -1:
            continue
        pts = df_copy[df_copy['cluster'] == cl][['Ch1Amplitude', 'Ch2Amplitude']].values
        if len(pts) == 0:
            continue
        observed_centroids[cl] = pts.mean(axis=0)

    # Map observed clusters to expected combination centroids
    combo_labels = list(combos.keys())
    combo_centroids = np.stack([combos[k] for k in combo_labels], axis=0)

    cluster_to_label: Dict[int, str] = {}
    for cl, cen in observed_centroids.items():
        diffs = cen[None, :] - combo_centroids  # (C,2)
        dists = np.sqrt(np.sum(diffs**2, axis=1))
        idx = int(np.argmin(dists))
        label = combo_labels[idx]
        # Size-aware tolerance
        if label == 'Negative':
            tol = base_tol
        else:
            k = 1 + label.count('+')
            tol = base_tol * (1.0 + 0.10 * (k - 1))
        cluster_to_label[cl] = label if dists[idx] <= tol else 'Unknown'

    # Assign droplet labels from cluster mapping; fallback for noise points
    assigned = []
    for i, cl in enumerate(cluster_labels):
        if cl != -1:
            assigned.append(cluster_to_label.get(cl, 'Unknown'))
        else:
            # Fallback: nearest expected centroid with tolerance
            diffs = X[i][None, :] - combo_centroids
            dists = np.sqrt(np.sum(diffs**2, axis=1))
            idx = int(np.argmin(dists))
            label = combo_labels[idx]
            if label == 'Negative':
                tol = base_tol
            else:
                k = 1 + label.count('+')
                tol = base_tol * (1.0 + 0.10 * (k - 1))
            assigned.append(label if dists[idx] <= tol else 'Unknown')

    df_copy['TargetLabel'] = assigned

    # Per-subset counts
    subset_counts: Dict[str, int] = {lab: 0 for lab in combo_labels}
    subset_counts.update({'Unknown': 0})
    for lab in df_copy['TargetLabel']:
        subset_counts[lab] = subset_counts.get(lab, 0) + 1

    total = len(df_copy)
    neg = subset_counts.get('Negative', 0)

    # Per-target positives (sum of subsets containing that target)
    chrom_keys = [f'Chrom{i}' for i in range(1, n + 1)]
    per_target_positive = {ck: 0 for ck in chrom_keys}
    for lab, cnt in subset_counts.items():
        for ck in chrom_keys:
            if ck != 'Negative' and ck in lab.split('+'):
                per_target_positive[ck] += cnt

    # Construct counts compatible with existing summaries: Negative + each ChromX
    counts = {'Negative': neg}
    counts.update(per_target_positive)

    # Non-Poisson per-target rate (fraction of droplets containing target)
    # Relative copy numbers normalized to each other (median baseline)
    copy_numbers = {}
    if total > 0:
        rates = {ck: (pos / total) for ck, pos in per_target_positive.items()}
        # Use median of non-zero rates as baseline to normalize targets to ~1.0 diploid scale
        non_zero = [v for v in rates.values() if v > 0]
        baseline = float(np.median(non_zero)) if non_zero else 1.0
        if baseline <= 0:
            baseline = 1.0
        for ck, r in rates.items():
            copy_numbers[ck] = r / baseline if baseline > 0 else 0.0

    # Optional classification: buffer zone and aneuploidy
    copy_number_states: Dict[str, str] = {}
    has_aneuploidy = False
    has_buffer_zone = False
    try:
        if Config.get_enable_copy_number_analysis():
            from ..config.config import Config as _C
            do_classify = Config.get_classify_cnv_deviations()
            for chrom, val in copy_numbers.items():
                if do_classify:
                    state = _C.classify_copy_number_state(chrom, float(val))
                else:
                    state = 'euploid'
                copy_number_states[chrom] = state
                if state == 'aneuploidy':
                    has_aneuploidy = True
                if state == 'buffer_zone':
                    has_buffer_zone = True
    except Exception:
        # Fallback silently if classification not available
        copy_number_states = {}
        has_aneuploidy = False
        has_buffer_zone = False

    return {
        'clusters': np.zeros((total,), dtype=int),  # placeholder
        'df_filtered': df_copy,
        'counts': counts,
        'copy_numbers': copy_numbers,
        'copy_number_states': copy_number_states,
        'has_aneuploidy': has_aneuploidy,
        'has_buffer_zone': has_buffer_zone,
        'abnormal_chromosomes': [],
        'target_mapping': {},
        'total_droplets': total,
        'usable_droplets': total - neg,
        'negative_droplets': neg,
        'subset_counts': subset_counts,
    }
