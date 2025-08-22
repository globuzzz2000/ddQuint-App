ddQuint Progressive Analysis Architecture Summary
================================================

This document explains the progressive analysis and processing architecture discovered and implemented in the ddQuint macOS app.

## Overview
The ddQuint app uses a progressive analysis system that processes CSV files one-by-one and updates the GUI in real-time, rather than batch processing all files at once like the command-line version.

## Architecture Components

### 1. Swift GUI (InteractiveApp.swift)
- **Main Controller**: InteractiveMainWindowController manages the entire UI
- **Real-time Updates**: GUI updates progressively as each well completes analysis
- **Cache Management**: Maintains in-memory cache and persistent file cache
- **Output Processing**: Two parallel systems process Python script output

### 2. Python Backend (ddquint/ modules)
- **Individual Processing**: Each CSV file processed via process_csv_file()
- **Complete Analysis**: Full analysis results include copy_numbers, copy_number_states, etc.
- **Output Streams**: Multiple message types sent to Swift via stdout

### 3. Progressive Output System
The system uses multiple message types for different purposes:

**WELL_COMPLETED:** Basic well info (name, droplet count, has_data)
- Used for: GUI table population, progress tracking
- Format: {"well": "A01", "droplet_count": 1500, "has_data": true, "sample_name": "..."}

**UPDATED_RESULT:** Complete analysis results per well
- Used for: Excel export cache, full analysis data
- Format: {"well": "A01", "copy_numbers": {...}, "copy_number_states": {...}, "counts": {...}, ...}

**COMPOSITE_READY:** Overview plot completion
- Used for: Loading composite plate overview image
- Format: Path to composite image file

**PLOT_CREATED:** Individual well plot completion
- Used for: Loading individual well plots in GUI
- Format: Path to plot image file

**DEBUG:** Python debug messages
- Used for: Troubleshooting and development

## Data Flow

### Analysis Phase:
1. User selects folder → Swift calls Python analysis script
2. Python processes CSV files individually 
3. For each well:
   - Python outputs WELL_COMPLETED → Swift updates GUI table
   - Python outputs UPDATED_RESULT → Swift builds cache for Excel export
4. Python outputs COMPOSITE_READY → Swift loads overview image
5. Swift enables export buttons when sufficient data available

### Plot Generation Phase:
1. User clicks on well → Swift calls Python plot generation script
2. Python outputs PLOT_CREATED → Swift displays individual well plot

## "Edit this Well" Feature Integration

### Overview
The "Edit this Well" feature allows users to modify analysis parameters for individual wells and regenerate their analysis results. This feature is fully integrated into the progressive analysis architecture.

### Contrast with General Analysis Workflow

**General Analysis Workflow:**
- Processes entire folder of CSV files in batch
- Uses hardcoded/global parameters for all wells
- Updates GUI progressively as wells complete
- Results cached for Excel export

**Edit this Well Workflow:**
- Processes single CSV file with custom parameters
- Uses well-specific parameter overrides
- Immediately updates GUI and cache for that well
- Integrates seamlessly with existing cache system

### Implementation Details

**Files Involved:**
1. **InteractiveApp.swift** (lines 3204-3340)
   - `regeneratePlotForWell()`: Main regeneration function
   - `handleWellRegenerationResult()`: Processes regeneration output
   - `openParameterWindow()`: Opens parameter editor
   - `wellParametersMap`: Stores well-specific parameters

2. **regenerate_well.py** (ddquint/regenerate_well.py)
   - Standalone script for single-well regeneration
   - Accepts CSV path, output directory, and parameter file
   - Outputs PLOT_CREATED and UPDATED_RESULT messages

3. **WellParameterEditorWindow.swift** (if exists)
   - Parameter editing interface
   - Saves parameters to wellParametersMap

### Data Flow for Edit this Well:

1. **Parameter Editing:**
   - User clicks "Edit this Well" → Parameter editor opens
   - Editor loads current parameters from wellParametersMap[wellName]
   - User modifies parameters → Swift saves to wellParametersMap
   - Parameters written to temporary JSON file

2. **Regeneration Process:**
   - Swift calls bundled regenerate_well.py script
   - Python loads global + well-specific parameters
   - Python re-processes CSV with custom parameters
   - Python generates new plot and analysis results

3. **Progressive Integration:**
   - Python outputs PLOT_CREATED: [persistent_path]
   - Python outputs UPDATED_RESULT: {complete_analysis_data}
   - Swift processes messages using same handlers as main analysis
   - Cache updated with new results for this well
   - GUI immediately reflects changes

4. **Cache Consistency:**
   - cachedResults[wellName] updated with new analysis
   - Excel export immediately includes regenerated data
   - No cache invalidation needed for other wells

### Key Benefits:

**Seamless Integration:**
- Uses same message-based communication as main analysis
- Reuses existing output processing handlers
- Maintains cache consistency automatically

**Real-time Feedback:**
- Plot updates immediately in GUI
- Well list refreshes to show changes
- Status messages provide user feedback

**Parameter Persistence:**
- Well-specific parameters stored in wellParametersMap
- Parameters persist for duration of session
- Can be applied to Excel export and further operations

### Message Flow Comparison:

**Main Analysis:**
```
WELL_COMPLETED → GUI table update
UPDATED_RESULT → Cache building
COMPOSITE_READY → Overview image
```

**Edit this Well:**
```
PLOT_CREATED → Individual plot display
UPDATED_RESULT → Cache update for specific well
```

The "Edit this Well" feature demonstrates the flexibility and extensibility of the progressive analysis architecture, allowing focused re-analysis while maintaining full integration with the existing cache and GUI systems.

### Plot Generation:
- **Main Analysis**: Plots saved to temp directory (not input folder)
- **Individual Plots**: Generated on-demand when wells are selected
- **Plot Paths**: Temporary files cleaned up automatically

### Excel Export:
1. Check cache for complete results
2. If cache available → Use cached UPDATED_RESULT data
3. Call create_list_report() with cached results
4. Generate Excel file without re-analysis

## Key Issues Resolved

### Cache Population Problem:
**Issue**: Excel export failed because UPDATED_RESULT messages weren't being processed during main analysis.
**Solution**: Added UPDATED_RESULT processing to both progressive output handlers (lines 808-816, 2840-2849).

### JSON Escaping Problem:
**Issue**: Complex cached results with special characters broke Python JSON parsing.
**Solution**: Save cached results to temporary JSON file instead of embedding in Python script string.

### Cache Interference Problem:
**Issue**: Stale cache files caused app to skip analysis and show old results.
**Solution**: Clear cache on app launch and before each new analysis.

### Plot Location Problem:
**Issue**: Plots saved to input folders, violating clean separation.
**Solution**: All plots now saved to temporary directories, no input folder pollution.

## Progressive vs Batch Processing

### Command Line (main.py):
- Batch: results = process_directory() → create_list_report(results)
- Simple, synchronous flow
- All results available at end

### GUI App (InteractiveApp.swift):
- Progressive: Individual process_csv_file() calls → UPDATED_RESULT messages → Cache building
- Complex, asynchronous flow with real-time updates
- Results available incrementally

## Benefits of Progressive Architecture

1. **Responsive GUI**: Users see progress and results immediately
2. **Early Feedback**: Can view individual plots before analysis completes
3. **Partial Results**: Even if some wells fail, others remain available
4. **Interactive Editing**: Can modify parameters for individual wells
5. **Better UX**: Progress indicators and real-time status updates

## Cache System

### In-Memory Cache:
- cachedResults: Array of complete well analysis results
- cacheKey: Unique identifier for current analysis context
- cacheTimestamp: When cache was last updated

### Persistent Cache:
- File: "ddQuint_results_cache.json" in analysis folder
- Contains: Complete results + metadata (timestamp, cache key)
- Validation: Age check (24h max) + cache key matching

### Cache Population:
- Progressive: Each UPDATED_RESULT message updates cache
- Immediate: Cache persisted to disk after each well update
- Validation: Cache key ensures results match current context

## Output Processing System

### Two Parallel Handlers:
1. **parseAnalysisOutput()**: Processes batch output after analysis completes
2. **processPartialOutput()**: Processes streaming output during analysis

Both handlers now process UPDATED_RESULT messages to ensure cache population works regardless of timing.

## File Organization

### Input Folder:
- Contains: CSV files, optional template files
- Clean: No plots or analysis outputs saved here

### Temporary Directories:
- Analysis plots: /tmp/ddquint_analysis_plots/
- Individual plots: /tmp/ddquint_plot_[well].png
- Composite plots: /tmp/ddquint_composite_overview.png
- Cache files: Analysis_folder/ddQuint_results_cache.json

This architecture provides a responsive, user-friendly analysis experience while maintaining clean file organization and robust caching for efficient Excel exports.