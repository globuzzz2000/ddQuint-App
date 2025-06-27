# ddQuint: Digital Droplet PCR Quintuplex Analysis

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)

A comprehensive pipeline for analyzing digital droplet PCR (ddPCR) data with support for up to 10 chromosome targets, aneuploidy detection, and buffer zone identification.

## Key Features

- **Multi-chromosome Analysis**: Support for up to 10 chromosome targets with dynamic configuration
- **Advanced Clustering**: HDBSCAN-based clustering for robust droplet classification
- **Copy Number Analysis**: Relative and absolute copy number calculations with normalization
- **Aneuploidy Detection**: Automated detection of chromosomal gains and losses
- **Buffer Zone Detection**: Identification of samples with uncertain copy number states
- **Comprehensive Reporting**: Excel reports in list format with color-coded highlighting
- **Visualization**: Individual well plots and composite plate overview images
- **Flexible Configuration**: JSON-based configuration system for all parameters

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
│   │   ├── config_display.py      # Configuration display utilities
│   │   └── template_generator.py  # Configuration template generation
│   ├── core/                      # Core processing modules
│   │   ├── __init__.py
│   │   ├── clustering.py          # HDBSCAN clustering and analysis
│   │   ├── copy_number.py         # Copy number calculations
│   │   ├── file_processor.py      # CSV file processing
│   │   └── list_report.py         # List format Excel reports
│   ├── utils/                     # Utility functions
│   │   ├── __init__.py
│   │   ├── file_io.py             # File input/output utilities
│   │   ├── gui.py                 # GUI file selection
│   │   ├── template_parser.py     # Template CSV parsing
│   │   └── well_utils.py          # Well coordinate utilities
│   └── visualization/             # Visualization modules
│       ├── __init__.py
│       ├── plate_plots.py         # Composite plate images
│       └── well_plots.py          # Individual well plots
├── docs/                          # Documentation
│   └── coding_standards.md       # Coding standards guide
├── pyproject.toml                 # Package configuration and dependencies
└── README.md                      # This file
```

## Installation

### Using pip (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/ddQuint
cd ddQuint

# Install the package with all dependencies
pip install -e .
```

### Dependencies

#### Required Python Packages
- **pandas/numpy**: For data manipulation and analysis
- **scikit-learn**: For data preprocessing
- **hdbscan**: For density-based clustering
- **matplotlib**: For visualization
- **openpyxl**: For Excel report generation
- **wxpython**: For GUI file selection dialogs
- **colorama**: For colored terminal output
- **tqdm**: For progress bars

#### Optional Dependencies
- **pyobjc-core** and **pyobjc-framework-Cocoa** (macOS only): For enhanced GUI support

## Quick Start

### Command Line Usage

```bash
# Basic analysis - select directory interactively
ddquint

# Specify input directory
ddquint --dir /path/to/csv/files

# Enable debug mode for detailed logging
ddquint --debug --dir /path/to/csv/files

# Test mode (preserves input files)
ddquint --test --dir /path/to/csv/files
```

### Configuration Management

```bash
# View current configuration
ddquint --config

# Generate a configuration template
ddquint --config template

# Use custom configuration
ddquint --config my_config.json --dir /path/to/csv/files
```

### Interactive Mode

Simply run `ddquint` without arguments to launch the interactive mode with GUI file selection.

## Configuration

Customize the analysis behavior with a JSON configuration file:

```json
{
    "HDBSCAN_MIN_CLUSTER_SIZE": 4,
    "HDBSCAN_MIN_SAMPLES": 70,
    "HDBSCAN_EPSILON": 0.06,
    "EXPECTED_CENTROIDS": {
        "Negative": [800, 700],
        "Chrom1": [800, 2300],
        "Chrom2": [1700, 2100],
        "Chrom3": [2500, 1750],
        "Chrom4": [3000, 1250],
        "Chrom5": [3500, 700]
    },
    "BASE_TARGET_TOLERANCE": 500,
    "ANEUPLOIDY_DEVIATION_THRESHOLD": 0.15,
    "EUPLOID_TOLERANCE": 0.08,
    "ANEUPLOIDY_TOLERANCE": 0.08
}
```

### Key Configuration Parameters

- **Clustering Parameters**: Control HDBSCAN clustering behavior
- **Expected Centroids**: Define target positions for each chromosome
- **Copy Number Thresholds**: Set sensitivity for aneuploidy detection
- **Buffer Zone Settings**: Configure uncertain classification ranges
- **Visualization Settings**: Customize colors, axis limits, and plot appearance

## Workflow Overview

1. **File Selection**: Choose directory containing CSV files (GUI or command line)
2. **Template Processing**: Parse sample names from template files (if available)
3. **Data Loading**: Read CSV files with automatic header detection
4. **Quality Filtering**: Remove invalid data points and check minimum requirements
5. **Clustering Analysis**: Apply HDBSCAN clustering to identify droplet populations
6. **Target Assignment**: Match clusters to expected chromosome centroids
7. **Copy Number Calculation**: Calculate relative and absolute copy numbers
8. **State Classification**: Classify as euploid, aneuploidy, or buffer zone
9. **Visualization**: Generate individual well plots and composite plate image
10. **Report Generation**: Create Excel report in list format

## Copy Number Classification and Buffer Zones

The pipeline uses a sophisticated three-state classification system for copy number analysis:

### Classification States

1. **Euploid**: Normal copy number (around expected value ± euploid tolerance)
2. **Aneuploidy**: Clear chromosomal gain or loss (around 0.75× or 1.25× expected ± aneuploidy tolerance)
3. **Buffer Zone**: Uncertain intermediate values that don't clearly fit euploid or aneuploidy categories

### Buffer Zone Implementation

Buffer zones identify samples with copy numbers that fall between clearly defined euploid and aneuploidy ranges. These samples require manual review as they may represent:
- Technical artifacts or measurement uncertainty
- Mosaic samples with mixed cell populations
- Borderline cases requiring additional validation

#### Classification Logic

For each chromosome, the system defines:

**Euploid Range**: `expected_value ± EUPLOID_TOLERANCE`
- Default tolerance: ±0.08 (8% deviation from expected)

**Aneuploidy Ranges**:
- **Deletion**: `(expected + (0.75 - 1.0)) ± ANEUPLOIDY_TOLERANCE`
- **Duplication**: `(expected + (1.25 - 1.0)) ± ANEUPLOIDY_TOLERANCE`
- Default tolerance: ±0.08 around aneuploidy targets

**Buffer Zone**: Any copy number that falls outside euploid and aneuploidy ranges

#### Expected Copy Numbers by Chromosome

The system uses chromosome-specific expected values for accurate classification:

```json
{
    "Chrom1": 0.9688,
    "Chrom2": 1.0066, 
    "Chrom3": 1.0300,
    "Chrom4": 0.9890,
    "Chrom5": 1.0056,
    "Chrom6": 1.00,
    "Chrom7": 1.00,
    "Chrom8": 1.00,
    "Chrom9": 1.00,
    "Chrom10": 1.00
}
```

#### Example Classification (Chrom1)

- **Expected value**: 0.9688
- **Euploid range**: 0.8888 - 1.0488 (0.9688 ± 0.08)
- **Deletion target**: 0.7188 (0.9688 + (0.75 - 1.0))
- **Deletion range**: 0.6388 - 0.7988 (0.7188 ± 0.08)
- **Duplication target**: 1.2188 (0.9688 + (1.25 - 1.0))
- **Duplication range**: 1.1388 - 1.2988 (1.2188 ± 0.08)
- **Buffer zones**: 0.7988 - 0.8888 and 1.0488 - 1.1388

### Configurable Parameters

- `EUPLOID_TOLERANCE`: Tolerance around expected values for euploid classification (default: 0.08)
- `ANEUPLOIDY_TOLERANCE`: Tolerance around aneuploidy targets (default: 0.08)
- `ANEUPLOIDY_TARGETS`: Target copy numbers for deletion (0.75) and duplication (1.25)
- `EXPECTED_COPY_NUMBERS`: Chromosome-specific expected copy number values

## Output Formats

### Excel Report

#### List Format (`List_Results.xlsx`)
- Tabular layout with wells as rows
- Separate columns for each chromosome's relative and absolute copy numbers
- Color-coded highlighting for aneuploidies and buffer zones
- Wells sorted in column-first order (A01, B01, ..., A02, B02, ...)

### Visualization

#### Individual Well Plots
- Scatter plot of droplet amplitudes (FAM vs HEX)
- Color-coded by target assignment
- Copy number annotations on each cluster
- Saved in `Graphs/` directory

#### Composite Plate Image (`Graph_Overview.png`)
- Overview of all 96 wells in plate format
- Color-coded borders indicating sample status:
  - **Light grey**: Euploid samples
  - **Light purple**: Aneuploidy samples  
  - **Black**: Buffer zone samples
- Sample names as titles (when available)

## Sample Template Integration

ddQuint automatically searches for sample template files to map well positions to sample names:

- Template file format: `{directory_name}.csv` 
- Searches in parent directories (configurable depth)
- Extracts sample names from "Sample description" columns
- Combines multiple description fields with " - " separator

## Advanced Features

### Dynamic Chromosome Support

The system supports 1-10 chromosome targets with automatic detection based on configuration. Add or remove chromosomes by modifying the `EXPECTED_CENTROIDS` configuration.

### Copy Number Normalization

Sophisticated normalization algorithm:
1. Calculate median of all chromosome copy numbers
2. Identify chromosomes close to median (within deviation threshold)
3. Use mean of close values as baseline for normalization
4. Apply baseline to calculate relative copy numbers

## Troubleshooting

Common issues and solutions:

- **No CSV files found**: Ensure files have `.csv` extension and contain amplitude data
- **Clustering failures**: Adjust `MIN_POINTS_FOR_CLUSTERING` or HDBSCAN parameters
- **Missing sample names**: Check template file format and location
- **GUI errors on macOS**: Ensure pyobjc packages are installed
- **Memory issues**: Reduce `NUM_PROCESSES` in configuration
- **Incorrect target assignment**: Adjust `EXPECTED_CENTROIDS` and `BASE_TARGET_TOLERANCE`

### Debug Mode

Enable debug mode for detailed logging:

```bash
ddquint --debug --dir /path/to/csv/files
```

Debug logs are saved to `~/.ddquint/logs/` with timestamps.

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests with coverage
pytest --cov=ddquint tests/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Citation

If you use ddQuint in your research, please cite:

```
ddQuint: Digital Droplet PCR Analysis Pipeline
```