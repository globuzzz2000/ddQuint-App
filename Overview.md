# ddQuint-App Project Overview

## Project Architecture

The ddQuint-App is a hybrid macOS application that combines a Swift-based native GUI with a Python backend for ddPCR (Digital Droplet PCR) data analysis. The application provides an interactive interface for analyzing well plate data, visualizing results, and managing analysis parameters.

## Project Structure

```
ddQuint-App/
├── Sources/                          # Swift source files
│   ├── main.swift                   # Application entry point
│   ├── AppDelegate.swift            # macOS app lifecycle management
│   ├── InteractiveApp.swift         # Main interactive GUI interface
│   └── SimpleApp.swift              # Simple batch processing interface
├── ddquint/                         # Python analysis backend
│   ├── __init__.py                  # Package initialization
│   ├── config/                      # Configuration management
│   │   ├── __init__.py
│   │   ├── config.py                # Main configuration singleton
│   │   ├── exceptions.py            # Custom exception classes
│   │   └── logging_config.py        # Logging system setup
│   ├── core/                        # Core analysis algorithms
│   │   ├── __init__.py
│   │   ├── clustering.py            # HDBSCAN clustering implementation
│   │   ├── copy_number.py           # Copy number analysis
│   │   ├── file_processor.py        # Data file processing
│   │   └── list_report.py           # Analysis report generation
│   ├── gui/                         # GUI integration utilities
│   │   ├── __init__.py
│   │   └── macos_native.py          # macOS-specific GUI helpers
│   ├── utils/                       # Utility modules
│   │   ├── __init__.py
│   │   ├── file_io.py               # File I/O operations
│   │   ├── parameter_editor.py      # Parameter editing interface
│   │   ├── template_creator.py      # Template creation utilities
│   │   ├── template_parser.py       # Template parsing logic
│   │   └── well_utils.py            # Well plate utilities
│   └── visualization/               # Plotting and visualization
│       ├── __init__.py
│       ├── plate_plots.py           # Composite plate visualizations
│       └── well_plots.py            # Individual well plots
├── Assets.xcassets/                 # macOS app resources
│   └── AppIcon.appiconset/
├── dist/                            # Built application bundle
├── build/                           # Build artifacts
├── .build/                          # Swift Package Manager artifacts
├── Package.swift                    # Swift package configuration
├── pyproject.toml                   # Python project configuration
├── build.sh                         # Build script
├── README.md                        # Project documentation
├── analysis_architecture.md         # Technical architecture documentation
└── debug.log                        # Application debug log
```

## Core Components

### Swift GUI Layer (Sources/)

#### main.swift
**Purpose**: Application entry point that determines interface mode
- `main()`: Entry point that launches either interactive or simple interface based on command line arguments

#### AppDelegate.swift
**Purpose**: macOS application lifecycle management
- **Class**: `AppDelegate`
  - `applicationDidFinishLaunching(_:)`: Initializes application and determines interface mode
  - `applicationShouldTerminateAfterLastWindowClosed(_:)`: Configures app termination behavior

#### InteractiveApp.swift
**Purpose**: Main interactive GUI with real-time analysis and parameter editing
- **Class**: `InteractiveApp: NSObject`
  - **Core UI Management**:
    - `setupUI()`: Initializes main interface layout and controls
    - `setupConstraints()`: Configures Auto Layout constraints
    - `updateDisplayedData()`: Refreshes table view with analysis results
  
  - **Analysis Pipeline**:
    - `selectFolder(_:)`: Handles folder selection for analysis
    - `startAnalysis()`: Initiates progressive analysis with real-time updates
    - `processWellOutput(_:)`: Parses Python script output and updates GUI
    - `finalizeProgressiveAnalysis()`: Completes analysis and enables UI controls
  
  - **Parameter Management**:
    - `openParameterWindow(isGlobal:title:)`: Opens parameter editing windows
    - `editWellParameters()`: Opens well-specific parameter editor
    - `editGlobalParameters()`: Opens global parameter editor
    - `applyWellParameters(_:)`: Applies edited parameters to specific wells
    - `applyGlobalParameters(_:)`: Applies global parameter changes
  
  - **Plot Regeneration**:
    - `regeneratePlotForWell()`: Regenerates individual well plots with new parameters
    - `applyParametersAndRegeneratePlot()`: Applies parameters and triggers regeneration
    - `handleWellRegenerationResult(_:exitCode:errorOutput:)`: Processes regeneration results
  
  - **Parameter Window Creation**:
    - `createHDBSCANParametersView(isGlobal:parameters:)`: Creates clustering parameter interface
    - `createCentroidsParametersView(isGlobal:parameters:)`: Creates expected centroids interface
    - `createCopyNumberParametersView(parameters:)`: Creates copy number analysis interface
    - `createVisualizationParametersView(parameters:)`: Creates visualization settings interface
  
  - **Export Functions**:
    - `exportExcel()`: Exports analysis results to Excel format
    - `exportPlots()`: Exports all generated plots
  
  - **Utility Functions**:
    - `parseWellIdColumnFirst(_:)`: Parses well IDs for column-first sorting
    - `getDefaultParameters()`: Retrieves default analysis parameters
    - `writeDebugLog(_:)`: Writes debug information to log file

#### SimpleApp.swift
**Purpose**: Simple batch processing interface for automated analysis
- **Class**: `SimpleApp: NSObject`
  - `setupSimpleUI()`: Creates minimal interface for folder selection
  - `selectFolder(_:)`: Handles folder selection and automatic analysis
  - `startSimpleAnalysis()`: Runs complete analysis without real-time updates

### Python Backend (ddquint/)

#### config/config.py
**Purpose**: Centralized configuration management with singleton pattern
- **Class**: `Config`
  - **Singleton Management**:
    - `get_instance()`: Returns singleton instance with thread-safe creation
    - `__init__()`: Initializes configuration and sets up color mapping
  
  - **Parameter Access**:
    - `__getattribute__(name)`: Custom attribute access with instance-first fallback for per-well parameters
    - **Supported Parameters**: HDBSCAN settings, visualization parameters, copy number thresholds
  
  - **Color Management**:
    - `finalize_colors()`: Public method to update color assignments
    - `_reconcile_target_colors()`: Assigns colors consistently by target order
    - `_get_target_names()`: Retrieves current target names from configuration
  
  - **Chromosome Utilities**:
    - `get_chromosome_keys()`: Returns sorted list of chromosome identifiers
    - `get_ordered_labels()`: Returns processing order for all labels
    - `get_tolerance_for_chromosome(chrom_name)`: Calculates tolerance values
  
  - **Well Management**:
    - `get_well_format()`: Returns standardized well ID format
    - **Plate Layout**: PLATE_ROWS (A-H), PLATE_COLS (1-12), WELL_FORMAT

#### config/exceptions.py
**Purpose**: Custom exception hierarchy for error handling
- **Classes**:
  - `DDQuintError`: Base exception class
  - `ConfigError`: Configuration-related errors
  - `FileProcessingError`: File I/O and processing errors
  - `AnalysisError`: Analysis algorithm errors
  - `ValidationError`: Data validation errors

#### config/logging_config.py
**Purpose**: Centralized logging configuration
- `setup_logging(debug=False)`: Configures logging with file and console handlers
- `get_logger(name)`: Returns configured logger instance for modules

#### core/clustering.py
**Purpose**: HDBSCAN-based clustering for droplet classification
- **Functions**:
  - `perform_clustering(data, config)`: Executes HDBSCAN clustering on droplet data
  - `validate_clustering_results(labels, data)`: Validates clustering output
  - `calculate_cluster_metrics(data, labels)`: Computes clustering quality metrics
  - `assign_cluster_targets(clusters, expected_centroids)`: Maps clusters to biological targets

#### core/copy_number.py
**Purpose**: Copy number variation analysis
- **Functions**:
  - `calculate_copy_numbers(well_data, config)`: Computes copy number ratios
  - `classify_copy_number_status(ratio, thresholds)`: Classifies as euploid/aneuploid
  - `normalize_copy_numbers(data, baseline_wells)`: Normalizes against baseline
  - `generate_copy_number_report(results)`: Creates analysis summary

#### core/file_processor.py
**Purpose**: CSV data file processing and validation
- **Class**: `FileProcessor`
  - `process_well_file(file_path)`: Processes individual well CSV files
  - `validate_file_format(file_path)`: Validates CSV format and required columns
  - `extract_well_id(file_path)`: Extracts well identifier from filename
  - `load_droplet_data(file_path)`: Loads and validates droplet fluorescence data

#### core/list_report.py
**Purpose**: Analysis report generation and formatting
- **Functions**:
  - `generate_analysis_report(well_results)`: Creates comprehensive analysis report
  - `format_results_for_export(results)`: Formats data for Excel export
  - `create_summary_statistics(results)`: Generates summary metrics
  - `validate_report_data(data)`: Validates report data integrity

#### visualization/well_plots.py
**Purpose**: Individual well plot generation
- **Functions**:
  - `create_well_plot(well_data, config, output_path)`: Generates individual well scatter plots
  - `_apply_axis_formatting(ax, config)`: Applies consistent axis formatting
  - `_add_cluster_annotations(ax, clusters)`: Adds cluster labels and annotations
  - `_save_plot_with_dpi(fig, output_path, dpi)`: Saves plots with specified resolution

#### visualization/plate_plots.py
**Purpose**: Composite plate overview generation
- **Functions**:
  - `create_composite_overview(well_results, output_path)`: Creates plate overview visualization
  - `_arrange_wells_in_grid(results)`: Arranges wells in 96-well plate layout
  - `_apply_well_borders(well_image, status)`: Applies color-coded borders based on analysis results
  - `_generate_plate_legend()`: Creates legend for plate overview

#### utils/file_io.py
**Purpose**: File I/O operations and path management
- **Functions**:
  - `read_csv_file(file_path)`: Safely reads CSV files with error handling
  - `write_excel_report(data, output_path)`: Writes Excel reports with formatting
  - `create_output_directory(base_path, subdirectory)`: Creates organized output directories
  - `validate_file_permissions(file_path)`: Checks file access permissions

#### utils/parameter_editor.py
**Purpose**: Parameter validation and editing interface
- **Functions**:
  - `validate_parameters(parameters)`: Validates parameter values and ranges
  - `update_well_parameters(well_id, parameters)`: Updates well-specific parameters
  - `reset_to_defaults(parameter_type)`: Resets parameters to default values
  - `export_parameter_template(output_path)`: Creates parameter template files

#### utils/template_creator.py
**Purpose**: Analysis template creation
- **Functions**:
  - `create_analysis_template(plate_layout)`: Creates template for plate analysis
  - `save_template_file(template, output_path)`: Saves template to file
  - `validate_template_structure(template)`: Validates template format

#### utils/template_parser.py
**Purpose**: Template file parsing and validation
- **Functions**:
  - `parse_template_file(file_path)`: Parses template files into usable format
  - `validate_template_syntax(template_content)`: Validates template syntax
  - `extract_well_mapping(template)`: Extracts well-to-target mappings

#### utils/well_utils.py
**Purpose**: Well plate utilities and coordinate management
- **Functions**:
  - `parse_well_id(well_id)`: Parses well identifiers into row/column coordinates
  - `format_well_id(row, column)`: Formats coordinates into standard well IDs
  - `get_adjacent_wells(well_id)`: Returns neighboring wells for validation
  - `validate_well_coordinates(row, col)`: Validates well coordinates are within plate bounds

## Key Features

### Progressive Analysis System
- Real-time GUI updates during analysis
- Individual well processing with immediate feedback
- Progress tracking and status updates
- Error handling with graceful recovery

### Parameter Management
- Global parameter settings affecting all wells
- Well-specific parameter overrides
- Parameter validation and range checking
- Template-based parameter management

### Dual Interface Support
- Interactive GUI with real-time feedback
- Simple batch processing for automated workflows
- Command-line interface detection
- Flexible deployment options

### Visualization System
- Individual well scatter plots with cluster annotations
- Composite plate overview with status color coding
- Configurable plot resolution and formatting
- Export capabilities for multiple formats

### Data Export
- Excel reports with formatted results
- Plot export in multiple resolutions
- Comprehensive analysis summaries
- Template creation for repeated analyses

## Build System

### build.sh
**Purpose**: Automated build script for creating macOS application bundle
- Cleans previous builds and resets debug logs
- Compiles Swift code using Swift Package Manager
- Creates .app bundle with proper macOS structure
- Bundles Python ddquint module into app resources
- Installs application to /Applications folder
- Provides build status and error reporting

### Package.swift
**Purpose**: Swift Package Manager configuration
- Defines Swift package dependencies
- Configures build targets and platforms
- Specifies minimum macOS version requirements
- Sets up executable targets for the application

### pyproject.toml
**Purpose**: Python project configuration
- Defines Python package dependencies
- Specifies development and testing dependencies
- Configures package metadata and entry points
- Sets up development environment requirements

## Error Handling Strategy

### Custom Exception Hierarchy
- `DDQuintError`: Base exception for all application errors
- Specific exception types for different error categories
- Detailed error messages with context information
- Graceful error recovery where possible

### Logging System
- Centralized logging configuration
- Debug logging for development and troubleshooting
- Structured log messages with module identification
- File-based logging with rotation capabilities

### Validation Framework
- Input validation at multiple levels
- File format validation before processing
- Parameter range checking and constraints
- Data integrity verification throughout pipeline

## Integration Points

### Swift-Python Communication
- Process-based execution with stdout/stderr parsing
- Message-based communication protocol
- Structured output parsing for real-time updates
- Error propagation between language layers

### File System Integration
- Temporary file management for plot generation
- Output directory organization and cleanup
- Path resolution between Swift and Python layers
- Resource bundling for standalone app distribution

### macOS Native Integration
- Native file dialogs and user interface elements
- Application lifecycle management
- Menu integration and keyboard shortcuts
- System notification support

This overview provides a comprehensive understanding of the ddQuint-App architecture, from the Swift GUI layer through the Python analysis pipeline, including all major components, their relationships, and key functionality.