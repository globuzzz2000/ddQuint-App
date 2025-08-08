# ddQuint: Digital Droplet PCR Quintuplex Analysis

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)

A comprehensive pipeline for analyzing digital droplet PCR (ddPCR) data for aneuploidy detection.


## Key Features

- **QX Manager**: Uses QX Manager Amplitude export files (folder selection)
- **Clustering**: HDBSCAN-based clustering for droplet classification (adjust expected centroids)
- **Copy Number Analysis**: Relative and absolute copy number calculations with normalization
- **Aneuploidy Detection**: Automated detection of chromosomal gains and losses
- **Buffer Zone Detection**: Identification of samples with uncertain copy number states
- **Visualization**: Individual well plots and composite plate overview images
- **Output format**: Results saved as Excel file with sample description, copy numbers and classification
- **Sample Naming**: Automatically detects QX Manager template files and names samples accordingly
- **Plate Template Generation**: Create QX Manager-compatible plate layout files from a sample list


## Installation

### Using pip

```bash
# Clone the repository
git clone https://github.com/globuzzz2000/ddQuint
cd ddQuint

# Install the package with all dependencies
pip install -e .
```


## Quick Start

### Command Line Usage

```bash
# Basic analysis
ddquint --dir /path/to/csv/files
```

### Interactive Mode

Simply run `ddquint` without arguments to launch the interactive mode with GUI file selection.


## Project Structure

```
ddQuint/
├── ddquint/                       # Main package directory
│   ├── __init__.py
│   ├── main.py                    # Main entry point
│   ├── config/                    # Configuration and settings
│   │   ├── __init__.py
│   │   ├── config.py              # Core configuration settings
│   │   ├── exceptions.py          # Error handling
│   │   ├── config_display.py      # Configuration display
│   │   └── template_generator.py  # Configuration template generation
│   ├── core/                      # Core processing modules
│   │   ├── __init__.py
│   │   ├── clustering.py          # HDBSCAN clustering and analysis
│   │   ├── copy_number.py         # Copy number calculations
│   │   ├── file_processor.py      # CSV file processing
│   │   └── list_report.py         # Excel report formatting
│   ├── utils/                     # Utility functions
│   │   ├── __init__.py
│   │   ├── file_io.py             # File input/output utilities
│   │   ├── gui.py                 # GUI file selection
│   │   ├── template_parser.py     # Template CSV parsing
│   │   ├── template_creator.py    # QX template generation
│   │   └── well_utils.py          # Well coordinate utilities
│   └── visualization/             # Visualization modules
│       ├── __init__.py
│       ├── plate_plots.py         # Plate overview plots
│       └── well_plots.py          # Individual well plots
├── pyproject.toml                 # Package configuration and dependencies
└── README.md             
```


## Workflow Overview

1. **File Selection**: Choose directory containing CSV files (GUI or command line)
2. **Template Processing**: Parse sample names from template files (if available)
3. **Clustering Analysis**: Apply HDBSCAN clustering to identify droplet populations
4. **Target Assignment**: Match clusters to expected chromosome centroids
5. **Copy Number Calculation**: Calculate relative and absolute copy numbers
6. **State Classification**: Classify as euploid, aneuploidy, or buffer zone
7. **Visualization**: Generate individual well plots and composite plate image
8. **Report Generation**: Create Excel report


## Configuration

Customize the pipeline behavior with a JSON configuration file:

```bash
ddquint --config config.json
```

Example configuration:

```json
{
"HDBSCAN_MIN_CLUSTER_SIZE": 4,
"HDBSCAN_MIN_SAMPLES": 70,
"HDBSCAN_EPSILON": 0.06,
"HDBSCAN_METRIC": "euclidean",
"HDBSCAN_CLUSTER_SELECTION_METHOD": "eom",
"MIN_POINTS_FOR_CLUSTERING": 50,
"EXPECTED_CENTROIDS": "{'Negative': [1000, 800], 'Chrom1': [1000, 2500], 'Chrom2': [1900, 2300], 'Chrom3': [2700, 1850], 'Chrom4': [3300, 1400], 'Chrom5': [3600, 900]"
}
```

### Parameter Editor

Use the parameter editor for configuring frequently modified settings (HDBSCAN Settings, Expected Centroids, ...):

```bash
# Launch parameter editor GUI
ddquint --parameterss
```

**Parameter Priority Order:**
1. User parameters file (highest priority)
2. Config file specified with `--config`
3. Default config.py values (lowest priority)

The parameter editor automatically loads on startup and provides tooltips with detailed explanations and optimization tips for each setting.


### Configuration Management

```bash
# View current configuration
ddquint --config

# Generate a configuration template
ddquint --config template

# Use custom configuration
ddquint --config my_config.json --dir /path/to/csv/files
```


## Poisson Correction

### The Mixed-Target Problem

In multiplex ddPCR assays, each droplet can contain DNA from multiple targets (e.g., 5 chromosomes). The detection system has a critical limitation:

- **Can detect**: Droplets positive for only one target type (even if multiple copies)
- **Can detect**: Empty droplets (no targets)
- **Cannot detect**: Droplets containing multiple different target types

This means droplets with mixed targets are **undetectable and uncountable**. Without proper Poisson correction, this leads to systematic underestimation of true concentrations and incorrect target ratios.

For targets, each with true concentration **λᵢ** copies per droplet, target copy numbers follow **Poisson distributions**.

## Key Probabilities

### Empty Droplets
$P(\text{empty}) = e^{-(\lambda_1 + \lambda_2 + \lambda_3 + \lambda_4 + \lambda_5)}$

### Single-Target Droplets  
Droplets containing only target *i* (but possibly multiple copies of *i*):

$P(\text{only } i) = \left(1 - e^{-\lambda_i}\right) \cdot \prod_{j \neq i} e^{-\lambda_j}$

Where:
- $\left(1 - e^{-\lambda_i}\right)$ = probability of ≥1 copy of target *i*
- $\prod_{j \neq i} e^{-\lambda_j}$ = probability of 0 copies of all other targets

## The Solution

### Taking the Ratio
$\frac{P(\text{only } i)}{P(\text{empty})} = \frac{\left(1 - e^{-\lambda_i}\right) \cdot \prod_{j \neq i} e^{-\lambda_j}}{\prod_{j=1}^5 e^{-\lambda_j}}$

### Simplification
$\frac{P(\text{only } i)}{P(\text{empty})} = \frac{1 - e^{-\lambda_i}}{e^{-\lambda_i}} = e^{\lambda_i} - 1$

$\lambda_i = \ln\left(1 + \frac{P(\text{only } i)}{P(\text{empty})}\right)$

This allows direct calculation of true target concentrations from observed exclusive counts and empty droplets, accounting for all undetectable mixed-target droplets.


## Copy Number Classification and Buffer Zones

The pipeline uses a three-state classification system for copy number analysis:

### Classification States

1. **Euploid**: Normal copy number

    `expected_value ± EUPLOID_TOLERANCE`

2. **Aneuploidy**: Clear chromosomal gain or loss

    `(expected_value + (ANEUPLOIDY_TARGETS - 1.0)) ± ANEUPLOIDY_TOLERANCE`

3. **Buffer Zone**: Uncertain intermediate values that don't clearly fit euploid or aneuploidy categories, likely technical artifact


### Copy Number Normalization

Normalization algorithm:
1. Calculate median of all chromosome copy numbers
2. Identify chromosomes close to median (within deviation threshold)
3. Use mean of close values as baseline for normalization
4. Apply baseline to calculate relative copy numbers


## Additional Utilities

### QX Manager Template
Generate QX Manager compatible template file from sample list:

**CSV/Excel format**: 1 to 4-column table with Sample Descriptions

```bash
# Generate Template file
ddprimer --QXtemplate
```

### Automatic Sample Naming
Automatically searches for QX template files to map well positions to sample names:

- Requires matching name between input folder and template file
- Searches in parent directories (configurable depth)
- Extracts sample names from "Sample description" columns

Alternatively provide QX template file location for sample naming:

```bash
ddprimer --template /path/to/csv
```

## Troubleshooting

Common issues and solutions:

- **Incorrect target assignment**: Adjust `EXPECTED_CENTROIDS` and `BASE_TARGET_TOLERANCE`
- **Clustering failures**: Adjust `MIN_POINTS_FOR_CLUSTERING` or HDBSCAN parameters
- **No CSV files found**: Ensure files have `.csv` extension and contain amplitude data
- **Missing sample names**: Check template file format and location

For more detailed output, run `ddprimer --debug` or check the logs in `~/.ddQuint/logs/`.

## License

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License - see the LICENSE file for details.
