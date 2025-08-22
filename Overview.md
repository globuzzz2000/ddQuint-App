# ddQuint-App Project Overview

## Project Description

ddQuint-App is a macOS application that provides a graphical user interface for the ddQuint Python pipeline, which analyzes Digital Droplet PCR (ddPCR) data for aneuploidy detection. The project combines a native Swift macOS frontend with a comprehensive Python backend for data processing and visualization.

**Version:** 0.1.0  
**Author:** Jakob Wimmer  
**License:** MIT  
**Python Requirements:** ≥3.10  

## Project Architecture

The project follows a hybrid architecture with:
- **Swift Frontend**: Native macOS GUI using Cocoa/AppKit
- **Python Backend**: Complete ddPCR analysis pipeline
- **Progressive Analysis**: Real-time processing and GUI updates
- **Bundled Distribution**: Self-contained .app package

## Complete Project Tree

```
ddQuint-App/
├── README.md                           # Project documentation and goals
├── Package.swift                       # Swift Package Manager configuration
├── pyproject.toml                     # Python package configuration
├── build.sh                           # Build script for macOS app bundle
├── icon.png                           # Application icon
├── analysis_architecture.md           # Technical architecture documentation
├── debug.log                          # Runtime debug log
│
├── Sources/                           # Swift source files
│   ├── main.swift                     # Application entry point
│   ├── AppDelegate.swift              # Main app delegate and menu setup
│   ├── InteractiveApp.swift           # Primary interactive GUI controller
│   └── SimpleApp.swift                # Simple batch processing GUI
│
├── Assets.xcassets/                   # Application icon assets
│   └── AppIcon.appiconset/
│       ├── Contents.json
│       └── [Various sized PNG icons]
│
├── build/                             # Build artifacts
│   ├── ddQuint.xcodeproj/            # Generated Xcode project
│   └── ddQuint/                      # Build output
│
├── dist/                             # Distribution package
│   └── ddQuint.app/                  # Complete macOS app bundle
│       ├── Contents/
│       │   ├── Info.plist           # App metadata
│       │   ├── MacOS/ddQuint        # Swift executable
│       │   └── Resources/
│       │       ├── Python/ddquint/  # Bundled Python modules
│       │       └── Assets.xcassets/ # App assets
│
└── ddquint/                          # Python analysis pipeline
    ├── __init__.py                   # Package initialization
    │
    ├── config/                       # Configuration management
    │   ├── __init__.py
    │   ├── config.py                 # Main configuration class (singleton)
    │   ├── exceptions.py             # Custom exception classes
    │   └── logging_config.py         # Logging setup utilities
    │
    ├── core/                         # Core analysis modules
    │   ├── __init__.py
    │   ├── clustering.py             # HDBSCAN-based droplet clustering
    │   ├── copy_number.py            # Copy number calculation and analytics
    │   ├── file_processor.py         # CSV file processing and validation
    │   └── list_report.py            # Excel report generation
    │
    ├── gui/                          # GUI components
    │   ├── __init__.py
    │   └── macos_native.py           # Native macOS Tkinter interface
    │
    ├── utils/                        # Utility modules
    │   ├── __init__.py
    │   ├── file_io.py                # File I/O and directory management
    │   ├── parameter_editor.py       # Parameter editing GUI
    │   ├── template_creator.py       # Template file generation
    │   ├── template_parser.py        # Sample name template parsing
    │   └── well_utils.py            # 96-well plate utilities
    │
    └── visualization/                # Plotting and visualization
        ├── __init__.py
        ├── plate_plots.py            # Composite plate overview plots
        └── well_plots.py             # Individual well scatter plots
```

## Key Files Analysis

### Configuration Files

#### Package.swift
- **Purpose**: Swift Package Manager configuration for macOS app
- **Key Components**:
  - Target platform: macOS 11.0+
  - Single executable target: "ddQuint"
  - No external Swift dependencies

#### pyproject.toml
- **Purpose**: Python package configuration and dependencies
- **Key Components**:
  - `build-system`: Uses setuptools for Python packaging
  - `dependencies`: Core scientific packages (pandas, numpy, matplotlib, scikit-learn, hdbscan)
  - `project.scripts`: Command line entry points
  - Platform-specific dependencies for macOS (pyobjc frameworks)

#### build.sh
- **Purpose**: Automated build script for creating macOS app bundle
- **Key Functions**:
  - `swift build -c release`: Compiles Swift executable
  - Creates proper app bundle structure
  - Bundles Python ddquint module into Resources/
  - Generates Info.plist with app metadata
  - Automatically installs to /Applications/

### Swift Source Files

#### main.swift
- **Purpose**: Application entry point
- **Functions**:
  - Creates NSApplication instance
  - Sets up AppDelegate
  - Starts main run loop

#### AppDelegate.swift
- **Purpose**: Main application delegate and menu management
- **Class**: `AppDelegate: NSObject, NSApplicationDelegate`
- **Key Methods**:
  - `applicationDidFinishLaunching()`: Initial setup, creates main window
  - `setupMenuBar()`: Creates native macOS menu structure
  - `selectTemplateFile()`: File dialog for template selection
  - `exportPlateOverview()`: Triggers overview export
- **Menu Structure**: App menu, File menu (template selection), Export menu, Edit menu

#### InteractiveApp.swift (Primary GUI Controller)
- **Purpose**: Main interactive interface for progressive analysis
- **Class**: `InteractiveMainWindowController: NSWindowController, NSWindowDelegate`
- **Key Properties**:
  - UI Elements: `wellListView`, `plotImageView`, `progressIndicator`, control buttons
  - Data: `analysisResults`, `wellData`, `selectedWellIndex`
  - State: `isAnalysisComplete`, parameter storage, cache management
- **Key Methods**:
  - `setupWindow()`: UI initialization and drag-drop setup
  - `runAnalysis()`: Python subprocess management for batch analysis
  - `parseAnalysisOutput()`: Progressive output parsing from Python
  - `regeneratePlotForWell()`: Individual well re-analysis with custom parameters
  - `exportExcelReport()`: Excel generation from cached results
  - Cache management methods for persistent result storage

#### SimpleApp.swift
- **Purpose**: Simple batch processing interface
- **Class**: `SimpleMainWindowController: NSWindowController`
- **Key Methods**:
  - `browseClicked()`: Folder selection dialog
  - `startClicked()`: Batch analysis execution
  - `runAnalysis()`: Python subprocess for simple processing
  - `findPython()`, `findDDQuint()`: Environment detection

### Python Core Modules

#### ddquint/__init__.py
- **Purpose**: Package initialization
- **Contents**: Version info and author metadata

#### ddquint/config/config.py
- **Purpose**: Central configuration management with singleton pattern
- **Class**: `Config` (Singleton)
- **Key Features**:
  - **Expected Centroids**: Target positions for up to 10 chromosomes
  - **Clustering Parameters**: HDBSCAN configuration (min_cluster_size, min_samples, epsilon)
  - **Copy Number Settings**: Standard deviation-based classification with tolerance multipliers
  - **Visualization Settings**: Plot dimensions, DPI, color schemes, axis limits
  - **File Management**: Directory patterns, template parsing options
- **Key Methods**:
  - `get_instance()`: Singleton pattern implementation
  - `get_hdbscan_params()`: Clustering parameter retrieval
  - `classify_copy_number_state()`: Standard deviation-based classification
  - `get_tolerance_for_chromosome()`: Chromosome-specific tolerance calculation
  - `load_from_file()`, `save_to_file()`: Configuration persistence
- **Configuration Categories**:
  - Expected centroids for 5 chromosomes plus negative control
  - HDBSCAN clustering parameters
  - Copy number thresholds and aneuploidy detection
  - Plot styling and color management
  - File I/O patterns

#### ddquint/config/exceptions.py
- **Purpose**: Custom exception hierarchy for error handling
- **Exception Classes**:
  - `ddQuintError`: Base exception
  - `ConfigError`: Configuration-related errors
  - `ClusteringError`: Clustering analysis failures
  - `FileProcessingError`: File I/O errors
  - `WellProcessingError`: Well-specific processing errors
  - `CopyNumberError`: Copy number calculation errors
  - `VisualizationError`: Plotting errors
  - `ReportGenerationError`: Report creation errors
  - `TemplateError`: Template file processing errors

#### ddquint/config/logging_config.py
- **Purpose**: Logging system configuration
- **Key Functions**:
  - `setup_logging()`: Configures file and console logging
  - `cleanup_old_log_files()`: Maintains log file rotation
- **Features**:
  - Dual output: file (always DEBUG) and console (configurable)
  - Log rotation with maximum file count
  - Suppression of matplotlib debug spam
  - Debug mode with enhanced formatting

### Core Analysis Modules

#### ddquint/core/clustering.py
- **Purpose**: HDBSCAN-based droplet clustering and copy number calculation
- **Key Functions**:
  - `analyze_droplets(df)`: Main clustering analysis pipeline
    - Parameters: DataFrame with Ch1Amplitude, Ch2Amplitude columns
    - Returns: Dictionary with clustering results, copy numbers, aneuploidy status
    - Process: Data standardization → HDBSCAN clustering → target assignment → copy number calculation
  - `_assign_targets_to_clusters()`: Matches detected clusters to expected centroids
  - `_create_empty_result()`: Handles insufficient data cases
- **Integration**: Uses Config singleton for parameters, imports copy number functions

#### ddquint/core/copy_number.py
- **Purpose**: Copy number calculation using analytical estimation
- **Key Functions**:
  - `calculate_copy_numbers(target_counts, total_droplets)`: Main copy number calculation
    - Process: Analytical estimation for mixed droplets → baseline calculation → relative normalization
    - Returns: Dictionary of relative copy numbers per chromosome
  - `_estimate_concentrations_analytical()`: Handles mixed-positive droplet correction
  - `detect_aneuploidies()`: Standard deviation-based aneuploidy detection
  - `calculate_statistics()`: Statistical analysis across multiple samples
- **Algorithm**: Uses analytical solution for Poisson-corrected concentrations

#### ddquint/core/file_processor.py
- **Purpose**: CSV file processing and analysis coordination
- **Key Functions**:
  - `process_csv_file(file_path, graphs_dir, sample_names, verbose)`: Single file processing
    - Process: Header detection → data loading → validation → clustering → plotting
    - Returns: Complete analysis results dictionary or error result
  - `process_directory()`: Batch processing for entire directories
  - `find_header_row()`: Automatic CSV header detection
  - `create_error_result()`: Standardized error result formatting
- **Error Handling**: Comprehensive error recovery with partial result preservation

#### ddquint/core/list_report.py
- **Purpose**: Excel report generation
- **Key Functions**:
  - `create_list_report()`: Generates comprehensive Excel reports
  - Cell formatting and conditional highlighting
  - Multiple worksheet organization
  - Integration with cached analysis results

### Utility Modules

#### ddquint/utils/file_io.py
- **Purpose**: File I/O utilities with error handling
- **Key Functions**:
  - `ensure_directory()`: Directory creation with error handling
  - `list_csv_files()`: CSV file discovery in directories
  - `load_csv_with_fallback()`: Robust CSV loading with encoding detection
- **Features**: Automatic header detection, encoding fallback, comprehensive error handling

#### ddquint/utils/parameter_editor.py
- **Purpose**: GUI parameter editing interface
- **Key Features**:
  - User-friendly parameter modification interface
  - Comprehensive tooltips for all parameters
  - Parameter persistence in ~/.ddquint/parameters.json
  - Priority system: User parameters > Config file > Defaults
- **Key Functions**:
  - `open_parameter_editor()`: Main GUI interface
  - `load_parameters_if_exist()`: Automatic parameter loading
  - `save_parameters()`: Parameter persistence
- **Parameters Categories**: Centroids, clustering settings, visualization options, copy number thresholds

#### ddquint/utils/template_parser.py
- **Purpose**: Sample name template processing
- **Key Functions**:
  - `parse_template_file()`: Template file parsing
  - `get_sample_names()`: Sample name extraction for wells
  - Template search across parent directories
- **Features**: Flexible template matching, automatic template discovery

#### ddquint/utils/well_utils.py
- **Purpose**: 96-well plate management utilities
- **Key Functions**:
  - `extract_well_coordinate()`: Well ID extraction from filenames
  - `is_valid_well()`: Well coordinate validation
  - `get_well_row_col()`: Well position parsing
- **Features**: Supports standard 96-well plate format (A01-H12)

### Visualization Modules

#### ddquint/visualization/well_plots.py
- **Purpose**: Individual well scatter plot generation
- **Key Functions**:
  - `create_well_plot()`: Main plot creation function
    - Parameters: DataFrame, clustering results, well ID, save path
    - Options: Composite optimization, copy number annotations
    - Returns: Path to saved plot
  - `_create_base_plot()`: Unified plot setup
  - `_plot_droplets()`: Scatter plot rendering with cluster colors
  - `_add_copy_number_annotations()`: Copy number value overlays
- **Features**: Consistent styling, color management, axis formatting, aneuploidy highlighting

#### ddquint/visualization/plate_plots.py
- **Purpose**: Composite plate overview visualization
- **Key Functions**:
  - `create_composite_image()`: Multi-well composite plot generation
  - Grid layout management for 96-well plates
  - Unified scaling and formatting across wells
- **Features**: Automatic layout optimization, consistent scaling, sample name integration

#### ddquint/gui/macos_native.py
- **Purpose**: Native macOS Tkinter GUI application
- **Class**: `ddQuintMacOSNativeApp`
- **Features**:
  - Native macOS styling and behaviors
  - Integrated matplotlib plotting
  - Progressive analysis with real-time updates
  - Parameter editing interface
  - Export functionality
- **Integration**: Complete integration with ddQuint analysis pipeline

## Key Relationships and Data Flow

### Analysis Pipeline Flow
1. **File Selection**: User selects input directory via Swift GUI
2. **Python Subprocess**: Swift launches Python analysis script
3. **Progressive Processing**: Python processes CSV files individually
4. **Real-time Updates**: Python outputs structured messages to Swift
5. **GUI Updates**: Swift updates interface progressively
6. **Cache Management**: Results cached for Excel export
7. **Plot Generation**: Individual plots generated on demand

### Message-Based Communication
The Swift frontend and Python backend communicate via structured JSON messages:

- **WELL_COMPLETED**: Basic well information for GUI updates
- **UPDATED_RESULT**: Complete analysis results for caching
- **COMPOSITE_READY**: Overview plot completion notification
- **PLOT_CREATED**: Individual plot generation completion
- **DEBUG**: Development and troubleshooting messages

### Parameter Management
Three-tier parameter system:
1. **User Parameters**: Highest priority, stored in ~/.ddquint/parameters.json
2. **Config File**: Medium priority, specified via --config flag
3. **Default Values**: Lowest priority, hardcoded in config.py

### Cache System
Dual-layer caching for performance:
- **In-Memory Cache**: Real-time analysis results in Swift
- **Persistent Cache**: JSON files for session persistence
- **Validation**: Cache key and timestamp validation

## Build and Distribution

### Build Process
1. `swift build -c release`: Compiles Swift executable
2. App bundle creation with proper macOS structure
3. Python module bundling into Resources/
4. Info.plist generation with metadata
5. Automatic installation to /Applications/

### Dependencies
**Python Dependencies**:
- Scientific: pandas, numpy, matplotlib, scikit-learn
- Clustering: hdbscan
- File I/O: openpyxl, Send2Trash
- GUI: wxpython, tkinter
- macOS: pyobjc-core, pyobjc-framework-Cocoa

**Swift Dependencies**: None (uses system frameworks)

### Distribution
Self-contained .app bundle including:
- Compiled Swift executable
- Complete Python ddquint module
- All required assets and metadata
- No external dependencies required

## Development and Architecture Notes

### Progressive Analysis Architecture
Unlike traditional batch processing, ddQuint-App uses progressive analysis:
- Real-time processing feedback
- Immediate result availability
- Interactive parameter editing
- Partial result preservation
- Responsive user experience

### Error Handling Strategy
Comprehensive error handling at multiple levels:
- Python: Custom exception hierarchy with context
- Swift: Graceful degradation and user feedback
- File I/O: Encoding fallback and validation
- Analysis: Partial result preservation

### Configuration Management
Singleton pattern with parameter override system:
- Thread-safe configuration access
- Dynamic parameter modification
- Persistent settings storage
- Validation and type checking

### Platform Integration
Native macOS integration features:
- Cocoa/AppKit UI components
- Native file dialogs and menus
- Drag-and-drop support
- System styling and behaviors
- Proper app bundle structure

This architecture provides a robust, user-friendly analysis platform that combines the power of scientific Python libraries with native macOS user experience, enabling efficient ddPCR data analysis for aneuploidy detection.