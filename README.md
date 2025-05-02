# ddQuint: Digital Droplet PCR Multiplex Analysis

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)

A streamlined tool for analyzing droplet digital PCR (ddPCR) multiplex data, optimized for chromosome copy number analysis.

## Key Features

- **Automated Analysis Pipeline**: Process ddPCR data files with minimal user interaction
- **Intelligent Cluster Detection**: Identify droplet populations using density-based clustering
- **Chromosomal Copy Number Analysis**: Calculate relative copy numbers with statistical confidence
- **Comprehensive Visualization**: Generate individual well plots and plate overview composites
- **Detailed Reporting**: Export results to Excel with highlighted abnormalities

## Project Structure

```
ddQuint/
├── ddquint/                       # Main package directory
│   ├── __init__.py
│   ├── main.py                    # Entry point for the application
│   ├── core/                      # Core processing modules
│   │   ├── __init__.py
│   │   ├── clustering.py          # Cluster detection algorithms
│   │   ├── copy_number.py         # Copy number calculation logic
│   │   └── file_processor.py      # CSV file processing functions
│   ├── visualization/             # Visualization modules
│   │   ├── __init__.py
│   │   ├── well_plots.py          # Individual well plotting
│   │   └── plate_plots.py         # Plate composite visualization
│   ├── reporting/                 # Reporting modules
│   │   ├── __init__.py
│   │   └── excel_report.py        # Excel report generation
│   └── utils/                     # Utility functions
│       ├── __init__.py
│       ├── file_io.py             # File input/output operations
│       ├── gui.py                 # GUI dialog functions
│       └── well_utils.py          # Well coordinate utilities
├── pyproject.toml                 # Package configuration and dependencies
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

## Quick Start

### Command Line Usage

```bash
# Process a directory of ddPCR CSV files
ddquint --dir /path/to/csv/files

# Process with specific output directory
ddquint --dir /path/to/csv/files --output /path/to/output
```

### Interactive Mode

Simply run `ddquint` without arguments to launch the interactive mode, which will guide you through directory selection with a graphical interface.

## Workflow Overview

1. **File Selection**: Choose directory containing ddPCR CSV files
2. **Data Processing**: Process each CSV file to extract droplet data
3. **Cluster Detection**: Apply density-based clustering to identify droplet populations
4. **Target Assignment**: Map clusters to expected chromosome targets
5. **Copy Number Calculation**: Calculate relative copy numbers for each chromosome
6. **Visualization**: Generate plots for each well and a composite plate image
7. **Report Generation**: Create Excel report with comprehensive results

## Output Files

The pipeline generates several output files:

- **Individual Well Images**: Plots for each analyzed well in the Graphs directory
- **Composite Plate Image**: Overview of all wells in a single image (All_Samples_Composite.png)
- **Excel Report**: Detailed results with copy numbers and status for each well (Plate_Results.xlsx)
- **Raw Data Archive**: Original CSV files preserved in the Raw Data directory

## Troubleshooting

Common issues and solutions:

- **File Loading Errors**: Check CSV format and ensure it contains Ch1Amplitude and Ch2Amplitude columns
- **Clustering Issues**: Adjust cluster parameters in configuration if needed
- **GUI Problems**: Use command line arguments if GUI selection fails
- **Empty Results**: Verify CSV files contain valid ddPCR data
- **Image Generation Errors**: Check permissions on output directory

## License

This project is licensed under the MIT License - see the LICENSE file for details.