# ddQuint: Digital Droplet PCR Multiplex Analysis

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)

A streamlined tool for analyzing droplet digital PCR (ddPCR) multiplex data, optimized for chromosome copy number analysis with dynamic support for up to 10 chromosome targets.

## Key Features

- **Automated Analysis Pipeline**: Process ddPCR data files with minimal user interaction
- **Intelligent Cluster Detection**: Identify droplet populations using density-based HDBSCAN clustering
- **Dynamic Chromosome Support**: Configurable support for up to 10 chromosomes with adaptive algorithms
- **Chromosomal Copy Number Analysis**: Calculate relative copy numbers with statistical confidence
- **Aneuploidy Detection**: Identify potential aneuploidies with configurable thresholds
- **Comprehensive Visualization**: Generate individual well plots and plate overview composites
- **Detailed Reporting**: Export results to Excel with highlighted abnormalities
- **Template Integration**: Parse Excel templates for sample naming and organization

## Project Structure

```
ddQuint/
├── ddquint/                       # Main package directory
│   ├── __init__.py
│   ├── main.py                    # Entry point with configuration support
│   ├── core/                      # Core processing modules
│   │   ├── __init__.py
│   │   ├── clustering.py          # HDBSCAN clustering algorithms
│   │   ├── copy_number.py         # Copy number calculation logic
│   │   └── file_processor.py      # CSV file processing functions
│   ├── visualization/             # Visualization modules
│   │   ├── __init__.py
│   │   ├── well_plots.py          # Individual well plotting
│   │   └── plate_plots.py         # Plate composite visualization
│   ├── reporting/                 # Reporting modules
│   │   ├── __init__.py
│   │   └── excel_report.py        # Excel report generation
│   ├── config/                    # Configuration management
│   │   ├── __init__.py
│   │   ├── config.py              # Central configuration class
│   │   ├── config_display.py      # Configuration display utilities
│   │   └── template_generator.py  # Config template generation
│   └── utils/                     # Utility functions
│       ├── __init__.py
│       ├── file_io.py             # File input/output operations
│       ├── gui.py                 # GUI dialog functions
│       ├── well_utils.py          # Well coordinate utilities
│       └── template_parser.py     # Excel template parsing
├── pyproject.toml                 # Package configuration
└── README.md                      # Project documentation
```

## Installation

### Using pip

```bash
# Clone the repository
git clone https://github.com/yourusername/ddQuint
cd ddQuint

# Install the package
pip install -e .
```

### Dependencies

- **Python 3.7+**: For core functionality
- **pandas/numpy**: For data manipulation
- **matplotlib**: For visualization
- **scikit-learn**: For machine learning components
- **hdbscan**: For density-based clustering
- **wxpython**: For GUI file selection
- **openpyxl**: For Excel report generation
- **colorama**: For colored console output
- **tqdm**: For progress bars

## Quick Start

### Command Line Usage

```bash
# Process a directory of ddPCR CSV files
ddquint --dir /path/to/csv/files

# Process with specific output directory
ddquint --dir /path/to/csv/files --output /path/to/output

# Enable debug logging
ddquint --dir /path/to/csv/files --debug

# View current configuration
ddquint --config

# Generate a configuration template
ddquint --config template

# Use custom configuration file
ddquint --config your_config.json
```

### Interactive Mode

Simply run `ddquint` without arguments to launch the interactive mode with a graphical interface.

## Configuration Management

ddQuint features a comprehensive configuration system that allows you to customize all aspects of the analysis pipeline.

### Viewing Current Configuration

```bash
ddquint --config
```

### Creating a Configuration Template

```bash
# Create template in current directory
ddquint --config template

# Create template in specific directory
ddquint --config template --output /path/to/dir
```

### Using Custom Configuration

```bash
ddquint --config your_config.json --dir /path/to/csv/files
```

### Key Configuration Sections

1. **Clustering Settings**: Control HDBSCAN parameters for cluster detection
2. **Expected Centroids**: Define chromosome target positions (up to 10 chromosomes)
3. **Copy Number Settings**: Configure aneuploidy detection thresholds
4. **Visualization Settings**: Customize plots, colors, and layout
5. **Performance Settings**: Adjust processing speed and memory usage

Example configuration snippet:
```json
{
    "HDBSCAN_MIN_CLUSTER_SIZE": 4,
    "HDBSCAN_MIN_SAMPLES": 70,
    "EXPECTED_CENTROIDS": {
        "Negative": [800, 700],
        "Chrom1": [800, 2300],
        "Chrom2": [1700, 2100],
        "Chrom3": [2700, 1850],
        "Chrom4": [3200, 1250],
        "Chrom5": [3700, 700]
    },
    "ANEUPLOIDY_DEVIATION_THRESHOLD": 0.15
}
```

## Excel Template Support

ddQuint automatically searches for an Excel template file matching your data directory name. The template:
- Maps well positions to sample names
- Uses standard 96-well plate layout (A01-H12)
- Automatically applies sample names to plots and reports

## Workflow Overview

1. **File Selection**: Choose directory containing ddPCR CSV files
2. **Configuration Loading**: Apply default or custom configuration
3. **Data Processing**: Process each CSV file to extract droplet data
4. **Cluster Detection**: Apply HDBSCAN clustering to identify droplet populations
5. **Target Assignment**: Map clusters to expected chromosome targets
6. **Copy Number Calculation**: Calculate relative copy numbers for each chromosome
7. **Aneuploidy Detection**: Identify potential aneuploidies
8. **Visualization**: Generate plots for each well and a composite plate image
9. **Report Generation**: Create Excel report with comprehensive results

## Output Files

The pipeline generates several output files:

- **Individual Well Images**: Plots for each analyzed well in the Graphs directory
- **Composite Plate Image**: Overview of all wells with aneuploidy highlighting
- **Excel Report**: Detailed results with copy numbers and status for each well
- **Raw Data Archive**: Original CSV files preserved in the Raw Data directory

## Troubleshooting

Common issues and solutions:

- **Configuration Errors**: Use `ddquint --config` to verify settings
- **Clustering Issues**: Adjust HDBSCAN parameters in configuration
- **Template Problems**: Ensure Excel template matches directory name
- **GUI Problems**: Use command line arguments if GUI selection fails
- **Empty Results**: Check CSV files contain Ch1Amplitude and Ch2Amplitude columns

## Debug Mode

Enable detailed logging for troubleshooting:
```bash
ddquint --debug --dir /path/to/csv/files
```

Debug logs are saved to: `~/.ddquint/logs/`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Citation

If you use ddQuint in your research, please cite:
```
ddQuint: A configurable pipeline for digital droplet PCR multiplex analysis
```