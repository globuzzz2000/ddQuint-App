import Cocoa

// MARK: - Parameter Tooltips

/// Comprehensive tooltip definitions for parameters (from parameter_editor.py)
let parameterTooltips: [String: String] = [
    // Expected Centroids
    "EXPECTED_CENTROIDS": """
Expected Centroid Positions

Define the expected fluorescence positions for each target chromosome.
These positions are used to assign detected clusters to specific targets.

💡 Tips:
• Measure actual centroids from control samples
• Each chromosome should have distinct positions
""",
    
    "BASE_TARGET_TOLERANCE": """
Target Tolerance

Tolerance distance for matching detected clusters to expected centroids.
Clusters within this distance are assigned to the nearest target.

💡 Tips:
• Higher values = more lenient matching
• Lower values = stricter, more precise matching
""",
    
    
    // Clustering Settings
    "HDBSCAN_MIN_CLUSTER_SIZE": """
HDBSCAN Min Cluster Size

Minimum number of droplets required to form a cluster.
Smaller clusters are treated as noise and ignored.

💡 Tips:
• Lower values (2-4): More sensitive, detects small clusters
• Higher values (8-15): More conservative, ignores noise
• Increase if too many noise clusters detected
""",
    
    "HDBSCAN_MIN_SAMPLES": """
HDBSCAN Min Samples

Minimum points in neighborhood for core point classification.
Controls how conservative the clustering algorithm is.

💡 Tips:
• Higher values = denser, more conservative clusters
• Lower values = more loose, inclusive clusters
• Increase if clusters are too fragmented
""",
    
    "HDBSCAN_EPSILON": """
HDBSCAN Epsilon

Distance threshold for cluster selection from hierarchy.
Controls how clusters are extracted from the cluster tree.

💡 Tips:
• Lower values (0.01-0.05): Tighter, more separated clusters
• Higher values (0.1+): Merges nearby clusters
• Increase if legitimate clusters are split
""",
    
    "HDBSCAN_METRIC": """
Distance Metric

Distance metric used for clustering calculations.
Determines how distances between points are measured.

💡 Options:
• Euclidean: Standard straight-line distance (recommended)
• Manhattan: Sum of absolute differences
• Chebyshev: Maximum difference in any dimension
• Minkowski: Generalized distance metric
""",
    
    "HDBSCAN_CLUSTER_SELECTION_METHOD": """
Cluster Selection Method

Method for selecting clusters from the hierarchy tree.
Determines which clusters are chosen as final results.

💡 Options:
• EOM (Excess of Mass): More stable, recommended
• Leaf: Selects leaf clusters, can be less stable
""",
    
    "MIN_POINTS_FOR_CLUSTERING": """
Min Points for Clustering

Minimum total data points required before attempting clustering.
Prevents clustering on insufficient data.

💡 Tips:
• Higher values = more reliable clustering
• Lower values = clustering on sparse data
""",
    
    // Copy Number Settings
    "MIN_USABLE_DROPLETS": """
Min Usable Droplets

Minimum total droplets required to perform copy number analysis.
Wells with fewer droplets are excluded from analysis.
""",
    
    "COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD": """
Median Deviation Threshold

Maximum deviation from median for dynamically selecting baseline references.
Only targets this close to median are used for normalization.
""",
    
    
    "TOLERANCE_MULTIPLIER": """
Tolerance Multiplier

Multiplier applied to target-specific standard deviation.
Controls width of classification ranges.

💡 Tips:
• Higher values = wider tolerance ranges
• Lower values = stricter classification
• 3 = 99.7% confidence interval
""",
    
    "COPY_NUMBER_MULTIPLIER": """
Copy Number Multiplier

Multiplier applied for displaying relative copy number results.
Use to adjust the scale of copy number values relative to the default of 1.
""",
    
    "ENABLE_COPY_NUMBER_ANALYSIS": """
Do Copy Number Analysis?

Enable or disable copy number buffer zone detection.
When disabled, relative copy numbers are not classified.
""",
    
    "CLASSIFY_CNV_DEVIATIONS": """
Classify Copy Number Deviations?

Enable or disable copy number deviation classification.
When disabled, removes aneuploidy identification and associated formatting.
""",

    "ENABLE_FLUOROPHORE_MIXING": """
Enable Fluorophore/Probe Mixing

Enable or disable modeling for fluorophore/probe mixing in 4-plex assays.
When disabled, dye channels are treated as independent.
""",
    
    "AMPLITUDE_NON_LINEARITY": """
Amplitude Non-linearity

Scaling factor for combination centroid distances in non-mixing mode.
Applied progressively to double/triple/quad combinations.

💡 Tips:
• 1.0 = Perfect linear amplitude addition (default)
• < 1.0 = Combinations closer to negative (sublinear)
• > 1.0 = Combinations further from negative (superlinear)
""",
    
    "LOWER_DEVIATION_TARGET": """
Lower Deviation Target

Expected ratio for lower copy number deviation.
Relative to detected reference.
""",
    
    "UPPER_DEVIATION_TARGET": """
Upper Deviation Target

Expected ratio for upper copy number deviation.
Relative to detected reference.
""",
    
    
    // Legacy CNV/aneuploidy target tooltips removed
    
    "COPY_NUMBER_SPEC": """
Copy Number Expectations

Per-target baseline copy number and standard deviation values.
Used for normalization and standard deviation based classification.

💡 Tips:
• Measure from known control samples
• Keep std dev representative for your assay
""",
    
    "CHROMOSOME_COUNT": """
Chromosome Count

Number of targets to analyze in this assay.
Determines how many targets are expected and displayed.
""",
    
    // Visualization (if needed)
    "X_AXIS_MIN": """
X-Axis Minimum

Minimum value for X-axis (HEX fluorescence) in plots.
Sets the left boundary of the plot area.
""",
    
    "X_AXIS_MAX": """
X-Axis Maximum

Maximum value for X-axis (HEX fluorescence) in plots.
Sets the right boundary of the plot area.
""",
    
    "Y_AXIS_MIN": """
Y-Axis Minimum

Minimum value for Y-axis (FAM fluorescence) in plots.
Sets the bottom boundary of the plot area.
""",
    
    "Y_AXIS_MAX": """
Y-Axis Maximum

Maximum value for Y-axis (FAM fluorescence) in plots.
Sets the top boundary of the plot area.
"""
]

/// Add tooltip to a control based on its parameter identifier
func addParameterTooltip(to control: NSView, identifier: String) {
    // Handle special cases where identifier might be different from tooltip key
    let tooltipKey: String
    var customTooltipText: String? = nil
    
    if identifier.hasPrefix("EXPECTED_CENTROIDS_") {
        tooltipKey = "EXPECTED_CENTROIDS"
        // Extract the target name and customize the tooltip
        let target = String(identifier.dropFirst("EXPECTED_CENTROIDS_".count))
        if target.hasPrefix("Chrom") {
            let chromNumber = target.replacingOccurrences(of: "Chrom", with: "")
            customTooltipText = """
Expected Centroid Position for Target \(chromNumber)

Define the expected fluorescence position (FAM, HEX coordinates) for Target \(chromNumber).
These positions are used to assign detected clusters to this specific target.

💡 Tips:
• Measure actual centroids from control samples
• Format: FAM_value, HEX_value (e.g., 1500, 2200)
"""
        } else if target == "Negative" {
            customTooltipText = """
Expected Centroid Position for Negative Control

Define the expected fluorescence position (FAM, HEX coordinates) for the target-negative droplets.
These are typically droplets with low fluorescence in both channels.
💡 Tips:
• Measure actual centroids from control samples
• Format: FAM_value, HEX_value (e.g., 1500, 2200)
"""
        }
    } else if identifier.hasPrefix("COPY_NUMBER_SPEC_") && identifier.hasSuffix("_expected") {
        tooltipKey = "COPY_NUMBER_SPEC"
        // Extract the target name and customize the tooltip
        let fullTarget = String(identifier.dropFirst("COPY_NUMBER_SPEC_".count))
        let target = String(fullTarget.dropLast("_expected".count))
        if target.hasPrefix("Chrom") {
            let chromNumber = target.replacingOccurrences(of: "Chrom", with: "")
            customTooltipText = """
Expected Copy Number for Target \(chromNumber)

Baseline copy number value for Target \(chromNumber).
Used for normalization and classification thresholds.

💡 Tips:
• Measure from known control samples
• Update in case of systematic target specific deviation
"""
        }
    } else if identifier.hasPrefix("COPY_NUMBER_SPEC_") && identifier.hasSuffix("_std_dev") {
        tooltipKey = "COPY_NUMBER_SPEC"
        // Extract the target name and customize the tooltip
        let fullTarget = String(identifier.dropFirst("COPY_NUMBER_SPEC_".count))
        let target = String(fullTarget.dropLast("_std_dev".count))
        if target.hasPrefix("Chrom") {
            let chromNumber = target.replacingOccurrences(of: "Chrom", with: "")
            customTooltipText = """
Expected Standard Deviation for Target \(chromNumber)

Standard deviation for Target \(chromNumber)'s copy number.
Used with tolerance multiplier to set classification ranges.

💡 Tips:
• Measure from known control samples
"""
        }
    } else {
        tooltipKey = identifier
    }
    
    // Use custom tooltip text if available, otherwise use the standard one
    let tooltipText = customTooltipText ?? parameterTooltips[tooltipKey]
    if let tooltip = tooltipText {
        control.toolTip = tooltip
    }
}
