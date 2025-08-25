# ddQuint Parameter Tooltips Documentation

This document provides a comprehensive overview of all implemented hover-help tooltips in the ddQuint application's parameter selection screens.

## Overview

The ddQuint application includes comprehensive tooltip help system for all parameter configuration screens. Tooltips provide detailed explanations, usage tips, and best practices for each parameter setting.

## Tooltip Categories

### 1. Expected Centroids Settings

#### EXPECTED_CENTROIDS (General)
**Expected Centroid Positions**

Define the expected fluorescence positions for each target chromosome.
These positions are used to assign detected clusters to specific targets.

💡 Tips:
• Measure actual centroids from control samples
• Each chromosome should have distinct positions

#### Target-Specific Centroids
**Expected Centroid Position for Target X**

Define the expected fluorescence position (FAM, HEX coordinates) for Target X.
These positions are used to assign detected clusters to this specific target.

💡 Tips:
• Measure actual centroids from control samples
• Each target should have distinct positions
• Format: FAM_value, HEX_value (e.g., 1500, 2200)

#### Negative Control Centroids
**Expected Centroid Position for Negative Control**

Define the expected fluorescence position for the negative control droplets.
These are typically droplets with low fluorescence in both channels.

💡 Tips:
• Usually positioned at low FAM and HEX values
• Serves as baseline reference for other targets
• Format: FAM_value, HEX_value (e.g., 1000, 900)

### 2. Tolerance and Matching Settings

#### BASE_TARGET_TOLERANCE
**Base Target Tolerance**

Base tolerance distance for matching detected clusters to expected centroids.
Clusters within this distance are assigned to the nearest target.

💡 Tips:
• Higher values = more lenient matching
• Lower values = stricter, more precise matching
• Adjust based on your assay's cluster tightness

#### SCALE_FACTOR_MIN
**Scale Factor Minimum**

Minimum scale factor for adaptive tolerance adjustment.
Controls how tolerance scales at different fluorescence intensities.

💡 Tips:
• Range: 0.1-1.0
• Lower values = tighter matching requirements
• 0.5 = tolerance can shrink to 50% of base value
• Use lower values for well-separated targets

#### SCALE_FACTOR_MAX
**Scale Factor Maximum**

Maximum scale factor for adaptive tolerance adjustment.
Controls maximum tolerance expansion at high fluorescence.

💡 Tips:
• Range: 1.0-2.0
• Higher values = more flexible matching
• 1.0 = no expansion (constant tolerance)
• Use higher values if clusters spread at high intensity

### 3. HDBSCAN Clustering Settings

#### HDBSCAN_MIN_CLUSTER_SIZE
**HDBSCAN Min Cluster Size**

Minimum number of droplets required to form a cluster.
Smaller clusters are treated as noise and ignored.

💡 Tips:
• Lower values (2-4): More sensitive, detects small clusters
• Higher values (8-15): More conservative, ignores noise
• Increase if too many noise clusters detected

#### HDBSCAN_MIN_SAMPLES
**HDBSCAN Min Samples**

Minimum points in neighborhood for core point classification.
Controls how conservative the clustering algorithm is.

💡 Tips:
• Higher values = denser, more conservative clusters
• Lower values = more loose, inclusive clusters
• Increase if clusters are too fragmented

#### HDBSCAN_EPSILON
**HDBSCAN Epsilon**

Distance threshold for cluster selection from hierarchy.
Controls how clusters are extracted from the cluster tree.

💡 Tips:
• Lower values (0.01-0.05): Tighter, more separated clusters
• Higher values (0.1+): Merges nearby clusters
• Increase if legitimate clusters are split

#### HDBSCAN_METRIC
**Distance Metric**

Distance metric used for clustering calculations.
Determines how distances between points are measured.

💡 Options:
• Euclidean: Standard straight-line distance (recommended)
• Manhattan: Sum of absolute differences
• Chebyshev: Maximum difference in any dimension
• Minkowski: Generalized distance metric

#### HDBSCAN_CLUSTER_SELECTION_METHOD
**Cluster Selection Method**

Method for selecting clusters from the hierarchy tree.
Determines which clusters are chosen as final results.

💡 Options:
• EOM (Excess of Mass): More stable, recommended
• Leaf: Selects leaf clusters, can be less stable

#### MIN_POINTS_FOR_CLUSTERING
**Min Points for Clustering**

Minimum total data points required before attempting clustering.
Prevents clustering on insufficient data.

💡 Tips:
• Higher values = more reliable clustering
• Lower values = clustering on sparse data

### 4. Copy Number Analysis Settings

#### MIN_USABLE_DROPLETS
**Min Usable Droplets**

Minimum total droplets required for reliable copy number analysis.
Wells with fewer droplets are excluded from analysis.

💡 Tips:
• Higher values = better statistical confidence
• Lower values = include more wells but less reliable

#### COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD
**Median Deviation Threshold**

Maximum deviation from median for selecting baseline (euploid) chromosomes.
Only chromosomes close to median are used for normalization.

💡 Tips:
• Lower values (0.10): Stricter baseline selection
• Higher values (0.20): More inclusive baseline

#### COPY_NUMBER_BASELINE_MIN_CHROMS
**Baseline Min Chromosomes**

Minimum number of chromosomes needed to establish diploid baseline.
Ensures robust normalization with sufficient reference chromosomes.

💡 Tips:
• Higher values = more robust normalization
• Lower values = less stringent requirements

### 5. Expected Copy Numbers Settings

#### EXPECTED_COPY_NUMBERS (General)
**Expected Copy Numbers**

Baseline copy number values for each target.
Used for normalization and classification thresholds.

💡 Tips:
• Values should be close to 1.0
• Slight variations account for assay differences
• Measure from known control samples
• Update based on your specific assay performance

#### Target-Specific Copy Numbers
**Expected Copy Number for Target X**

Baseline copy number value for Target X.
Used for normalization and classification thresholds.

💡 Tips:
• Measure from known diploid control samples
• Typically around 1.0 for balanced targets
• Values significantly different from 1.0 may indicate aneuploidy

### 6. Expected Standard Deviation Settings

#### EXPECTED_STANDARD_DEVIATION (General)
**Expected Standard Deviation**

Standard deviation for each chromosome's copy number.
Used with tolerance multiplier to set classification ranges.

💡 Tips:
• Lower values = tighter classification ranges
• Higher values = more permissive classification
• Measure from known control samples

#### Target-Specific Standard Deviations
**Expected Standard Deviation for Target X**

Standard deviation for Target X's copy number.
Used with tolerance multiplier to set classification ranges.

💡 Tips:
• Lower values = tighter classification ranges
• Higher values = more permissive classification
• Measure from known control samples

### 7. Classification and Tolerance Settings

#### TOLERANCE_MULTIPLIER
**Tolerance Multiplier**

Multiplier applied to chromosome-specific standard deviation.
Controls width of classification ranges (euploid/aneuploidy).

💡 Tips:
• Higher values = wider tolerance ranges
• Lower values = stricter classification
• 3 = 99.7% confidence interval

#### ANEUPLOIDY_TARGETS_LOW
**Aneuploidy Deletion Target**

Target copy number ratio for chromosome deletions.
Relative to expected copy number.

💡 Tips:
• 0.75 = 75% of expected (3 copies instead of 4)
• Adjust based on your assay design

#### ANEUPLOIDY_TARGETS_HIGH
**Aneuploidy Duplication Target**

Target copy number ratio for duplications.
Relative to expected copy number.

💡 Tips:
• 1.25 = 125% of expected (5 copies instead of 4)
• Adjust based on your assay design

### 8. Target Configuration

#### CHROMOSOME_COUNT
**Chromosome Count**

Number of target chromosomes to analyze in this assay.
Determines how many chromosomes are expected and displayed.

💡 Tips:
• Set based on your specific assay design
• Must match your expected centroids configuration
• Common values: 3-8 targets per assay

### 9. Visualization Settings

#### X_AXIS_MIN
**X-Axis Minimum**

Minimum value for X-axis (HEX fluorescence) in plots.
Sets the left boundary of the plot area.

#### X_AXIS_MAX
**X-Axis Maximum**

Maximum value for X-axis (HEX fluorescence) in plots.
Sets the right boundary of the plot area.

#### Y_AXIS_MIN
**Y-Axis Minimum**

Minimum value for Y-axis (FAM fluorescence) in plots.
Sets the bottom boundary of the plot area.

#### Y_AXIS_MAX
**Y-Axis Maximum**

Maximum value for Y-axis (FAM fluorescence) in plots.
Sets the top boundary of the plot area.

## Special Features

### Target-Specific Tooltips
- **Centroid Fields**: Automatically replace "Chrom X" references with "Target X" format
- **Copy Number Fields**: Provide target-specific guidance for each chromosome
- **Standard Deviation Fields**: Include target-specific measurement recommendations

### Dynamic Content
- Tooltips adapt based on the specific target being configured
- Contextual tips are provided based on parameter relationships
- Format examples are included where applicable

### Implementation Details

The tooltip system is implemented through:
1. **parameterTooltips dictionary**: Contains base tooltip text for all parameters
2. **addParameterTooltip() function**: Handles special cases and target-specific customization
3. **Automatic application**: All parameter controls (text fields, popups, labels) receive appropriate tooltips

### Coverage
All parameter configuration screens include comprehensive tooltips:
- Main parameter selection menu
- HDBSCAN clustering settings
- Expected centroids configuration
- Copy number and standard deviation settings
- Aneuploidy target configuration
- Visualization settings

This tooltip system ensures users have immediate access to contextual help while configuring ddQuint analysis parameters.