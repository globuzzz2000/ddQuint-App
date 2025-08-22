# ddQuint GUI Application

A native macOS GUI wrapper for the ddQuint digital droplet PCR analysis pipeline.

## Features

- **Clean macOS Interface**: Native-looking GUI that follows macOS design principles
- **Folder Selection**: Easy folder selection at startup for CSV file analysis
- **Real-time Progress**: Visual progress tracking during file analysis
- **Interactive Plots**: View and interact with analysis results
- **Parameter Adjustment**: Modify analysis parameters and see results update
- **Export Functionality**: Export results to Excel files and save plots as images

## Installation

1. Install the package with GUI dependencies:
```bash
pip install -e .
```

2. Or install just the GUI dependencies if you already have ddQuint:
```bash
pip install tkinter matplotlib
```

## Usage

### Option 1: Using the command line launcher
```bash
ddquint-gui
```

### Option 2: Using the standalone script
```bash
python ddquint_gui.py
```

### Option 3: Direct import
```python
from ddquint.gui import main
main()
```

## How It Works

1. **Startup**: The application launches with a clean welcome screen
2. **Folder Selection**: Click "Select Folder" to choose a directory containing ddPCR CSV files
3. **Analysis**: Click "Start Analysis" to begin processing the files
4. **Progress**: Watch real-time progress as files are analyzed
5. **Results**: View interactive plots and adjust parameters
6. **Export**: Export results to Excel or save plots as images

## Application Flow

```
Welcome Screen
    ↓
Folder Selection
    ↓
Analysis Progress
    ↓
Results View
    ├── File List (left panel)
    ├── Parameter Controls
    ├── Export Buttons
    └── Interactive Plot (right panel)
```

## Features Detail

### Folder Selection
- Native macOS folder selection dialog
- Remembers last selected directories
- Validates folder contains CSV files

### Analysis Progress
- Real-time progress bar
- Status updates for each processing step
- Cancel option (graceful interruption)

### Interactive Results
- List all processed files
- Click to view individual plots
- Scatter plots of droplet data
- Sample name integration

### Parameter Adjustment
- Modify clustering parameters
- Real-time parameter updates
- Visual feedback of changes

### Export Options
- **Excel Export**: Complete analysis results in Excel format
- **Plot Export**: Save all plots as high-quality images
- **Batch Operations**: Export all results at once

## Technical Details

- Built with `tkinter` for native macOS look and feel
- Uses `matplotlib` for interactive plotting
- Threaded analysis to prevent UI freezing
- Integrates seamlessly with existing ddQuint pipeline
- Memory efficient handling of large datasets

## Replacing the Old GUI

This GUI application replaces the previous wxPython-based file selection dialogs with a complete application interface. The old command-line interface is still available via the `ddquint` command.

## Dependencies

- Python 3.10+
- tkinter (usually included with Python)
- matplotlib
- pandas
- numpy
- All existing ddQuint dependencies

## Troubleshooting

If you encounter issues:

1. Ensure all dependencies are installed
2. Check that CSV files are in the expected format
3. Verify folder permissions
4. Look at the console output for detailed error messages

For more help, see the main ddQuint documentation or file an issue on GitHub.