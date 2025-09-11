using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;

namespace ddQuint.Desktop.Views
{
    internal static class ParameterTooltips
    {
        private static readonly Dictionary<string, string> Map = new()
        {
            // Expected Centroids (group tooltip)
            ["EXPECTED_CENTROIDS"] = "Expected Centroid Positions\n\nDefine the expected fluorescence positions for each target chromosome.\nThese positions are used to assign detected clusters to specific targets.\n\nTips:\n• Measure actual centroids from control samples\n• Each chromosome should have distinct positions",

            // Centroid matching tolerance
            ["BASE_TARGET_TOLERANCE"] = "Target Tolerance\n\nTolerance distance for matching detected clusters to expected centroids.\nClusters within this distance are assigned to the nearest target.\n\nTips:\n• Higher values = more lenient matching\n• Lower values = stricter, more precise matching",

            // HDBSCAN
            ["HDBSCAN_MIN_CLUSTER_SIZE"] = "HDBSCAN Min Cluster Size\n\nMinimum number of droplets required to form a cluster.\nSmaller clusters are treated as noise and ignored.\n\nTips:\n• Lower values (2-4): More sensitive, detects small clusters\n• Higher values (8-15): More conservative, ignores noise\n• Increase if too many noise clusters detected",
            ["HDBSCAN_MIN_SAMPLES"] = "HDBSCAN Min Samples\n\nMinimum points in neighborhood for core point classification.\nControls how conservative the clustering algorithm is.\n\nTips:\n• Higher values = denser, more conservative clusters\n• Lower values = more loose, inclusive clusters\n• Increase if clusters are too fragmented",
            ["HDBSCAN_EPSILON"] = "HDBSCAN Epsilon\n\nDistance threshold for cluster selection from hierarchy.\nControls how clusters are extracted from the cluster tree.\n\nTips:\n• Lower values (0.01-0.05): Tighter, more separated clusters\n• Higher values (0.1+): Merges nearby clusters\n• Increase if legitimate clusters are split",
            ["HDBSCAN_METRIC"] = "Distance Metric\n\nDistance metric used for clustering calculations.\nDetermines how distances between points are measured.\n\nOptions:\n• Euclidean: Standard straight-line distance (recommended)\n• Manhattan: Sum of absolute differences\n• Chebyshev: Maximum difference in any dimension\n• Minkowski: Generalized distance metric",
            ["HDBSCAN_CLUSTER_SELECTION_METHOD"] = "Cluster Selection Method\n\nMethod for selecting clusters from the hierarchy tree.\nDetermines which clusters are chosen as final results.\n\nOptions:\n• EOM (Excess of Mass): More stable, recommended\n• Leaf: Selects leaf clusters, can be less stable",
            ["MIN_POINTS_FOR_CLUSTERING"] = "Min Points for Clustering\n\nMinimum total data points required before attempting clustering.\nPrevents clustering on insufficient data.\n\nTips:\n• Higher values = more reliable clustering\n• Lower values = clustering on sparse data",

            // Copy number – general
            ["MIN_USABLE_DROPLETS"] = "Min Usable Droplets\n\nMinimum total droplets required to perform copy number analysis.\nWells with fewer droplets are excluded from analysis.",
            ["COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD"] = "Median Deviation Threshold\n\nMaximum deviation from median for dynamically selecting baseline references.\nOnly targets this close to median are used for normalization.",
            ["TOLERANCE_MULTIPLIER"] = "Tolerance Multiplier\n\nMultiplier applied to target-specific standard deviation.\nControls width of classification ranges.\n\nTips:\n• Higher values = wider tolerance ranges\n• Lower values = stricter classification\n• 3 = 99.7% confidence interval",
            ["LOWER_DEVIATION_TARGET"] = "Lower deviation target\n\nExpected ratio for lower copy number deviation.",
            ["UPPER_DEVIATION_TARGET"] = "Upper deviation target\n\nExpected ratio for upper copy number deviation.",
            ["COPY_NUMBER_MULTIPLIER"] = "Copy Number Multiplier\n\nMultiplier applied for displaying relative copy number results.",
            ["COPY_NUMBER_SPEC"] = "Copy Number Expectations\n\nPer-target baseline copy number and standard deviation values.\nUsed for normalization and standard deviation based classification.\n\nTips:\n• Measure from known control samples\n• Keep std dev representative for your assay",

            // Visualization
            ["X_AXIS_MIN"] = "X-Axis Minimum\n\nMinimum value for X-axis (HEX fluorescence) in plots.\nSets the left boundary of the plot area.",
            ["X_AXIS_MAX"] = "X-Axis Maximum\n\nMaximum value for X-axis (HEX fluorescence) in plots.\nSets the right boundary of the plot area.",
            ["Y_AXIS_MIN"] = "Y-Axis Minimum\n\nMinimum value for Y-axis (FAM fluorescence) in plots.\nSets the bottom boundary of the plot area.",
            ["Y_AXIS_MAX"] = "Y-Axis Maximum\n\nMaximum value for Y-axis (FAM fluorescence) in plots.\nSets the top boundary of the plot area.",
            ["X_GRID_INTERVAL"] = "X-Grid Interval\n\nSpacing between vertical grid lines.",
            ["Y_GRID_INTERVAL"] = "Y-Grid Interval\n\nSpacing between horizontal grid lines.",

            // General toggles
            ["ENABLE_FLUOROPHORE_MIXING"] = "Enable Fluorophore Mixing\n\nEnable or disable modeling for fluorophore/probe mixing in 4-plex assays.",
            ["AMPLITUDE_NON_LINEARITY"] = "Amplitude Non-linearity\n\nScaling factor for combination centroid distances in non-mixing mode.\n\nAdjusts the distance calculations when fluorophore mixing is disabled to account for non-linear amplitude effects between channels.\n\nTips:\n• Only visible when fluorophore mixing is disabled\n• Values > 1.0 increase scaling\n• Values < 1.0 decrease scaling",
            ["ENABLE_COPY_NUMBER_ANALYSIS"] = "Do copy number analysis?\n\nEnable or disable copy number analysis and buffer zone detection.",
            ["CLASSIFY_CNV_DEVIATIONS"] = "Classify copy number deviations?\n\nEnable or disable copy number deviation classification.",

            // Count
            ["CHROMOSOME_COUNT"] = "Chromosome Count\n\nNumber of targets to analyze in this assay.\nDetermines how many targets are expected and displayed."
        };

        internal static string? Get(string key)
        {
            if (string.IsNullOrWhiteSpace(key)) return null;

            // Dynamic: expected centroids
            if (key.StartsWith("EXPECTED_CENTROIDS_", StringComparison.Ordinal))
            {
                var target = key.Substring("EXPECTED_CENTROIDS_".Length);
                if (target.Equals("Negative", StringComparison.Ordinal))
                {
                    return "Expected Centroid Position for Negative Control\n\nDefine the expected fluorescence position (FAM, HEX coordinates) for the target-negative droplets.\nThese are typically droplets with low fluorescence in both channels.\nTips:\n• Measure actual centroids from control samples\n• Format: FAM_value, HEX_value (e.g., 1500, 2200)";
                }
                var m = Regex.Match(target, @"Chrom(\d+)");
                if (m.Success)
                {
                    var n = m.Groups[1].Value;
                    return $"Expected Centroid Position for Target {n}\n\nDefine the expected fluorescence position (FAM, HEX coordinates) for Target {n}.\nThese positions are used to assign detected clusters to this specific target.\n\nTips:\n• Measure actual centroids from control samples\n• Format: FAM_value, HEX_value (e.g., 1500, 2200)";
                }
                return Map.GetValueOrDefault("EXPECTED_CENTROIDS");
            }

            // Dynamic: per-target CN/SD
            if (key.StartsWith("EXPECTED_COPY_NUMBERS_Chrom", StringComparison.Ordinal))
            {
                var n = key.Substring("EXPECTED_COPY_NUMBERS_Chrom".Length);
                return $"Expected Copy Number for Target {n}\n\nBaseline copy number value for Target {n}.\nUsed for normalization and classification thresholds.\n\nTips:\n• Measure from known control samples\n• Update in case of systematic target specific deviation";
            }
            if (key.StartsWith("EXPECTED_STANDARD_DEVIATION_Chrom", StringComparison.Ordinal))
            {
                var n = key.Substring("EXPECTED_STANDARD_DEVIATION_Chrom".Length);
                return $"Expected Standard Deviation for Target {n}\n\nStandard deviation for Target {n}'s copy number.\nUsed with tolerance multiplier to set classification ranges.\n\nTips:\n• Measure from known control samples";
            }

            // Dynamic: target names
            if (key.StartsWith("TARGET_NAME_", StringComparison.Ordinal))
            {
                var n = key.Substring("TARGET_NAME_".Length);
                return $"Custom name for Target {n} (leave empty for default)";
            }

            // Direct lookup
            return Map.GetValueOrDefault(key);
        }
    }
}

