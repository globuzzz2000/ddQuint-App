# ddQuint for Windows: Digital Droplet PCR Quintuplex Analysis (App)

![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-orange.svg)
![Windows 10+](https://img.shields.io/badge/Windows-10%2B-blue.svg)
![ARM64 Support](https://img.shields.io/badge/ARM64-Supported-success.svg)

A **windows application** for analyzing multiplex digital droplet PCR (ddPCR) data with a focus on **copy number deviation detection**. The app works with QX Manager exports and allows for parameter tuning, result visualization, and report exporting.

> There is also a CLI tool and a MacOS version of this app that provide the same core analysis workflow.


## Key Features

- **HDBSCAN clustering:** Identifies clusters of droplets; expected clusters should be adjusted in‑app.
- **Poisson correction for multiplex ddPCR:** Corrects for undetectable mixed‑target droplets in multiplex assays.
- **Copy number analysis:** Relative/absolute copy numbers with robust normalization.
- **Aneuploidy detection:** Automatic detection of copy number deviations with customizable thresholds.
- **Visualization:** Individual well plots.
- **Fast iteration:** Change parameters and re‑analyze single wells or full sets.
- **Export:** Save an **Excel** report and high‑resolution plots from within the app.


## Installation

1. **Download** the setup file for your architecture:
   - `ddQuint-win-x64-Setup.exe` (for Intel/AMD processors)
   - `ddQuint-win-arm64-Setup.exe` (for ARM processors)
2. **Run the installer** - it will automatically install ddQuint with all dependencies
3. **Launch** from the desktop shortcut or Start Menu


## Quick Start (App)

1. **Launch the app.**
2. Click **Select Input Folder** and choose the directory containing your **QX Manager Amplitude** CSV files.
3. Optional: Provide a **QX template** file to auto‑assign sample names.
4. Open **Global Parameters** to review/tune:
   - HDBSCAN (min cluster size, min samples, , metric, selection method)
   - Expected centroids for multiplex targets
   - Tolerances for copy number classification and "buffer zones"
6. Use **Export** to generate a report file (relative and absolute copy numbers, classifications), to export the generated plots and to save the utilized parameters.


## Indicators

Each well in the results pane is annotated with an indicator to quickly convey classification status:

- **White circle**: Normal copy number
- **Grey circle**: Buffer Zone (intermediate/uncertain result detected)
- **Purple circle**: Copy number deviation detected
- **Red circle**: Warning (analysis issue such as low droplets)
- **Square shape**: Edited well (well-specific parameters applied)

You can use the filter icon above the results pane to hide buffer zone or warning samples.


## App Layout

- **Toolbar / Controls**: Folder selection, Global Parameters, Analyze, Export.
- **Status & Logs**: Minimal progress messages for ongoing steps.
- **Results Pane**:
  - **Plate Overview** image at the top after processing finishes.
  - **Per‑Well Plots** with names derived from the template (if available).
- **Parameter Editor**: Opens as a sheet or window with grouped settings and inline help tooltips.


## Workflow Overview

1. **File Selection** → Choose the folder with CSV files (and optional QX template).
2. **Template Processing** → Parse sample names and map wells.
3. **Clustering** → HDBSCAN to identify droplet populations.
4. **Target Assignment** → Map clusters to expected centroids (5 targets + negative).
5. **Poisson‑Aware Copy Number** → Compute λ per target from exclusive positives and empties.
6. **Classification** → Euploid / Aneuploid / Buffer Zone.
7. **Visualization** → Per‑well plots.
8. **Reporting** → Export Excel + plots.


## Copy Number Classification & Buffer Zones

The app uses a three‑state model:

1. **Reference** – values near expected copy number (within a configurable tolerance).
2. **Deviation** – clear gain or loss (thresholds configurable; e.g., expected ± tolerance).
3. **Buffer Zone** – intermediate or uncertain values that are likely technical artifacts or need additional data.

**Normalization strategy:**  
Computes the median of target copy numbers, select values within a deviation threshold, average them as baseline, and normalize each target relative to that baseline.


## Configuration in the App

Open **Global Parameters** to adjust general anbalysis parameters:

- **HDBSCAN:** `min_cluster_size`, `min_samples`, `epsilon`, `metric`, `cluster_selection_method`
- **Expected Centroids:** Positions for Negative + 5 targets
- **Clustering Preconditions:** `MIN_POINTS_FOR_CLUSTERING` (skip under‑populated wells)
- **Copy Number & Classification:** Tolerances for euploid, aneuploid, and buffer zones

Use **Edit This Well** to adjust clustering and analysis parameters for a single sample:

- Select a well from the results pane and select **Edit This Well**.  
- A parameter window opens, showing the same options as the Global Parameters, but applied only to this well.  
- After adjusting and confirming, the app will **re-cluster and re-analyze only the selected well**, updating its cached results and plots.


## Export Outputs

- **Excel report** (`.xlsx`) containing:
  - Sample metadata (from template, if provided)
  - Copy numbers per chromosome
  - Deviation classifications
- **Plot images** for each well.
- **Parameter Files**


## QX Manager Template Creation

The app includes a **template creator** for generating Bio-Rad QX Manager-compatible template files (`.csv`). These templates serve two purposes:
Simply select a header-less excel table with the sample names. Each row will be read as a unique sample and assigned to the plate. Up to four columns can be used to add further descriptions for samples.
The selected assay and experiment type will be applied uniformly to all samples on the plate.
The generated template file can also be used in ddQuint during analysis. It maps well IDs (e.g., A01, B02) to the sample names you defined, ensuring that exported reports and plots are labeled consistently.


## Troubleshooting

### Application Issues
- **No CSVs found:** Ensure files are QX Manager **Amplitude** exports (`.csv`), not summaries.
- **Incorrect target assignment:** Adjust **Expected Centroids** and `BASE_TARGET_TOLERANCE` in Parameters.
- **Clustering fails or under‑clusters:** Increase `MIN_POINTS_FOR_CLUSTERING`; tune HDBSCAN parameters.
- **Sample names missing:** Manually provide the QX template file or place it near the input folder.

### Installation Issues
- **Installer blocked:** Windows may show security warnings for downloaded executables. Choose "More info" → "Run anyway" or download from trusted source.
- **Permission errors:** Run the installer as Administrator if installation to Program Files fails.
- **Python setup fails:** Ensure internet connection for downloading Python packages during first run.


## Development: Building from Source

This section is for developers who want to build ddQuint from source code.

### Prerequisites
- **.NET 8 SDK** for building the WPF application
- **PowerShell** for Python bundling scripts  
- **7z** (p7zip) for creating self-extracting installers

### Build Process

#### 1. Build the Application
```bash
./build.sh      # On macOS/Linux (cross-platform build)
# OR
build.bat       # On Windows
```

This creates platform-specific builds in `dist/win-arm64-standalone/` and `dist/win-x64-standalone/`.

#### 2. Bundle Python Environments
The builds include bundling scripts that must be run on Windows to create portable Python environments:

- Copy the build output to a Windows machine
- For each architecture, run `bundle_python.bat` in the build directory
- This downloads embedded Python and installs all required packages
- Copy the resulting `Python/` directories back to the development machine

#### 3. Store Python Environments
Store the bundled Python environments for packaging:
```bash
# Copy Python directories to the project's python store
cp -r /path/to/bundled/Python/ ./python_store/win-arm64/
cp -r /path/to/bundled/Python/ ./python_store/win-x64/
```

#### 4. Create Distribution Packages

**On Windows:**
```cmd
.\scripts\package.bat
```

**On macOS/Linux:**
```bash
./scripts/package.sh
```

This creates:
- ZIP packages: `ddQuint-win-x64.zip`, `ddQuint-win-arm64.zip`
- Self-extracting installers: `ddQuint-win-x64-Setup.exe`, `ddQuint-win-arm64-Setup.exe`

The packages include the application, pre-bundled Python environment, and installation scripts.

## License

**Creative Commons Attribution–NonCommercial 4.0 International (CC BY‑NC 4.0).**  
You are free to **share** and **adapt** the material for **non‑commercial** purposes, provided you give appropriate credit and indicate changes. For details, see the [Creative Commons summary](https://creativecommons.org/licenses/by-nc/4.0/) and the full [legal code](https://creativecommons.org/licenses/by-nc/4.0/legalcode).

© The ddQuint authors. All rights reserved where not granted by the license above.
