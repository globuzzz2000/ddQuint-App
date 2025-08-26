# ddQuint for macOS: Digital Droplet PCR Quintuplex Analysis (App)

![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-orange.svg)
![macOS 13+](https://img.shields.io/badge/macOS-13%2B-lightgrey.svg)
![Apple Silicon Optimized](https://img.shields.io/badge/Apple%20Silicon-Optimized-success.svg)

A native **macOS application** for analyzing multiplex digital droplet PCR (ddPCR) data with a focus on **copy number deviation detection**. The app works with QX MAnager exports and allows for parameter tuning, result visualization, and report exporting.

> There is also a CLI tool of this app that provides the same core analysis workflow.


## Key Features

- **HDBSCAN clustering:** Identifies clusters of droplets; expected clusters should be adjusted in‑app.
- **Poisson correction for multiplex ddPCR:** Corrects for undetectable mixed‑target droplets in multiplex assays.
- **Copy number analysis:** Relative/absolute copy numbers with robust normalization.
- **Aneuploidy detection:** Automatic detection of copy number deviations with customizable thresholds.
- **Visualization:** Individual well plots and a composite plate overview.
- **Fast iteration:** Change parameters and re‑analyze single wells or full sets.
- **Export:** Save an **Excel** report and high‑resolution plots from within the app.


## System Requirements

- **macOS 13 Ventura or newer**
- **Apple Silicon (M1/M2/M3…)** recommended; Intel may work but has not been tested
- ~1–2 GB free disk space for temporary files and plots (varies with dataset size)


## Installation

1. **Download** the latest release (`.dmg`) from the [GitHub Releases page](https://github.com/globuzzz2000/ddQuint-App/releases).  
2. Open the downloaded `.dmg` and drag **ddQuint.app** to `/Applications` (or your preferred location).  
3. On first launch, macOS Gatekeeper may show a warning. Open **System Settings → Privacy & Security** and choose **Open Anyway** if needed.


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
7. **Visualization** → Per‑well plots, composite plate overview.
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
- **Plot images** for each well and a composite **plate overview**.
- **Parameter Files**


## QX Manager Template Creation

The app includes a **template creator** for generating Bio-Rad QX Manager-compatible template files (`.csv`). These templates serve two purposes:
Simply select a header-less excel table with the sample names. Each row will be read as a unique sample and assigned to the plate. Up to four columns can be used to add further descriptions for samples.
The selected assay and experiment type will be applied uniformly to all samples on the plate.
The generated template file can also be used in ddQuint during analysis. It maps well IDs (e.g., A01, B02) to the sample names you defined, ensuring that exported reports and plots are labeled consistently.


## Troubleshooting

- **No CSVs found:** Ensure files are QX Manager **Amplitude** exports (`.csv`), not summaries.
- **Incorrect target assignment:** Adjust **Expected Centroids** and `BASE_TARGET_TOLERANCE` in Parameters.
- **Clustering fails or under‑clusters:** Increase `MIN_POINTS_FOR_CLUSTERING`; tune HDBSCAN parameters.
- **Sample names missing:** Manually provide the QX template file (menu band) or place it near the input folder with matching naming.
- **First‑launch warnings:** Use **Open Anyway** in Privacy & Security if Gatekeeper blocks the app.


## License

**Creative Commons Attribution–NonCommercial 4.0 International (CC BY‑NC 4.0).**  
You are free to **share** and **adapt** the material for **non‑commercial** purposes, provided you give appropriate credit and indicate changes. For details, see the [Creative Commons summary](https://creativecommons.org/licenses/by-nc/4.0/) and the full [legal code](https://creativecommons.org/licenses/by-nc/4.0/legalcode).

© The ddQuint authors. All rights reserved where not granted by the license above.
