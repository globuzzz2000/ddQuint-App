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
- **Comprehensive Reporting**: Excel reports in both plate and list formats
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
│   │   ├── exceptions.py          # Error haneling
│   │   ├── config_display.py      # Configuration display utilities
│   │   └── template_generator.py  # Configuration template generation
│   ├── core/                      # Core processing modules
│   │   ├── __init__.py
│   │   ├── clustering.py          # HDBSCAN clustering and analysis
│   │   ├── copy_number.py         # Copy number calculations
│   │   └── file_processor.py      # CSV file processing
│   ├── utils/                     # Utility functions
│   │   ├── __init__.py
│   │   ├── file_io.py            # File input/output utilities
│   │   ├── gui.py                # GUI file selection
│   │   ├── template_parser.py    # Template CSV parsing
│   │   └── well_utils.py         # Well coordinate utilities
│   ├── visualization/             # Visualization modules
│   │   ├── __init__.py
│   │   ├── plate_plots.py        # Composite plate images
│   │   └── well_plots.py         # Individual well plots
│   └── reporting/                 # Report generation
│       ├── __init__.py
│       ├── list_report.py        # List format Excel reports
│       └── plate_report.py       # Plate format Excel reports
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

# Generate Excel reports in plate format
ddquint --plate --dir /path/to/csv/files

# Generate both standard and rotated plate reports
ddquint --plate rotated --dir /path/to/csv/files

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
10. **Report Generation**: Create Excel reports in list and/or plate formats

## Output Formats

### Excel Reports

#### List Format (`List_Results.xlsx`)
- Tabular layout with wells as rows
- Separate columns for each chromosome's relative and absolute copy numbers
- Color-coded highlighting for aneuploidies and buffer zones

#### Plate Format (`Plate_Results.xlsx`)
- 96-well plate layout matching physical plate
- Copy number data organized by well position
- Chromosome-specific highlighting for abnormal values

#### Rotated Plate Format (`Plate_Results_Rotated.xlsx`)
- Alternative plate layout (1-12 as rows, A-H as columns)
- Relative copy numbers only (no absolute counts)
- Optimized for certain analysis workflows

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

### Buffer Zone Detection

Buffer zones identify samples with copy numbers that fall between clearly euploid and clearly aneuploid ranges, indicating uncertain classification that may require manual review.

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