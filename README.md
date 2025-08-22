# ddQuint‑App (macOS): Standalone ddPCR Quintuplex Analyzer
![Platform: macOS 13+](https://img.shields.io/badge/macOS-13%2B-lightgrey.svg)
![Apple Silicon](https://img.shields.io/badge/Universal2-Apple%20Silicon%20%26%20Intel-blue.svg)

A **native macOS application** for analyzing digital droplet PCR (ddPCR) data for aneuploidy detection. The app ships with an **embedded Python runtime** and all required Python packages. **No external Python installation** or command‑line setup is required.

> This repository focuses on the macOS app. The app **does not call `main.py`**. Instead, it imports and calls the individual modules directly (e.g., `core/clustering.py`, `core/copy_number.py`, …).

---

## Highlights

- **One‑click app**: Drag the `.app` to Applications and run. No Homebrew, Conda, or pip required.
- **Embedded CPython**: Python 3.10+ (universal2) bundled inside the app, with all wheels vendored in `Contents/Resources/site-packages`.
- **Direct module integration**: The GUI orchestrates calls into the Python package internals (clustering, copy number, visualization, report generation) **without** going through `main.py` or the CLI parser.
- **QX Manager support**: Load Amplitude export CSVs (folder selection) and optional template files for sample naming.
- **Aneuploidy pipeline**: HDBSCAN clustering → target assignment → Poisson correction for multiplex → copy‑number normalization → state classification (euploid / aneuploidy / buffer zone).
- **Visualization**: Per‑well plots and plate overview rendered via the embedded Python stack.
- **Excel output**: Results exported to `.xlsx` including metadata, per‑target copy numbers, and classification calls.
- **Fully offline**: All computation happens locally; no internet required.

---

## Getting Started (Users)

1. **Download** the latest `ddQuint‑App.dmg` from Releases.
2. **Drag** `ddQuint‑App.app` into your `/Applications` folder.
3. **Open** the app. On first launch, macOS Gatekeeper may prompt; choose *Open*.
4. **Choose your data folder** containing QX Manager amplitude CSV files.
5. (Optional) **Select a template** to enable automatic sample naming.
6. **Run Analysis** and review plots and the generated Excel report.

> **System requirements:** macOS 13 Ventura or later, Apple Silicon (M‑series) or Intel (universal2 build). No Python installation needed.

---

## What’s Inside

The app bundles a Python environment and imports the following modules directly:

```
ddquint/
├── config/
│   ├── config.py              # default parameters & bounds
│   ├── config_display.py      # descriptions for the parameter editor
│   └── template_generator.py
├── core/
│   ├── clustering.py          # HDBSCAN clustering & QC
│   ├── copy_number.py         # Poisson correction & CN estimates
│   ├── file_processor.py      # QX CSV parsing & validation
│   └── list_report.py         # Excel writer / formatter
├── utils/
│   ├── file_io.py             # IO helpers
│   ├── template_parser.py     # QX template parsing → sample names
│   └── well_utils.py          # plate & well utilities
└── visualization/
    ├── plate_plots.py         # plate overview
    └── well_plots.py          # per‑well plots
```

### No `main.py` in the app path
The GUI calls into these modules via a thin Python bridge (see **Architecture**). CLI argument parsing and `main.py` orchestration are **not** used inside the app.

---

## Architecture

- **SwiftUI / AppKit GUI** (SwiftPM project) handles windowing, file pickers, progress, and error dialogs.
- **Embedded CPython** is loaded at runtime. The app sets `PYTHONHOME`/`PYTHONPATH` to its internal bundle paths and imports `ddquint.*` modules directly.
- **Bridge layer**:
  - For simple calls, we use a minimal Python runner that executes specific functions (e.g., `analyze_directory(dir, params)`), returning structured JSON.
  - Plots and reports are saved to an app‑managed output folder; the GUI previews the generated files.
- **Dependencies** (bundled wheels): `numpy`, `pandas`, `scipy`, `scikit-learn`, `hdbscan`, `matplotlib`, `openpyxl`, and small utilities required by the modules.

> The bridge avoids the CLI completely. The GUI maps user actions → direct function calls in the modules above.

---

## Analysis Flow

1. **File Selection**: choose a folder with QX amplitude CSVs (and optional template file).
2. **Clustering**: run HDBSCAN over droplet amplitudes; adjust expected centroids when needed.
3. **Target Assignment**: map clusters to chromosome targets.
4. **Poisson Correction** (multiplex): recover true λ for each target from exclusive/empty droplet counts.
5. **Copy Numbers**: normalize per sample; compute expected vs observed.
6. **Classification**: euploid / aneuploidy / buffer zone using configurable tolerances.
7. **Visualization**: generate per‑well and plate images.
8. **Report**: write Excel summary with key metrics and calls.

---

## Configuration in the App

- **Parameter Editor** panel exposes frequently tuned settings:
  - HDBSCAN (min cluster size, min samples, metric, selection method)
  - Expected centroids
  - Minimum points for clustering
  - Copy‑number and classification tolerances
- **Priority**: UI overrides → bundled defaults from `config/config.py`.
- **Reset to Defaults**: restores the bundled `config.py` values (not user files).

---

## Building From Source (Developers)

> You do **not** need this to *use* the app. This is for contributors who want to build/sign the app locally.

### Prerequisites

- Xcode 15+
- macOS 14+

### Repository Layout

```
.
├── App/                         # Swift sources (GUI, bridge)
├── PythonEmbedded/              # vendored CPython and wheels (see below)
├── ddquint/                     # Python package sources used by the app
├── pyproject.toml               # for editing/testing the Python package itself
└── Tools/                       # helper scripts
```

### Vendor Python & Wheels

We bundle a universal2 CPython and prebuilt wheels inside the app. Typical layout inside the built app:

```
ddQuint‑App.app/Contents/
├── Frameworks/Python.framework/Versions/3.10/...
└── Resources/
    ├── site‑packages/           # all wheels installed here
    └── ddquint/                 # package modules (mirrors repo’s `ddquint/`)
```

Helper scripts (referenced in `Tools/`) take care of downloading CPython (universal2) and installing wheels into `Resources/site-packages` during the build phase.

### Build

1. Clone the repo.
2. Run the vendor script(s) to populate `PythonEmbedded/` (CPython + wheels).
3. Open the project in Xcode and build the *Release* scheme.
4. The resulting `.app` will already contain Python and required packages.

### Code Signing & Notarization (optional but recommended)

- Sign with a Developer ID Application certificate.
- Notarize via `xcrun notarytool submit`.

---

## Troubleshooting

- **App can’t be opened**: Right‑click → *Open* on first run (Gatekeeper). For unsigned builds, remove the quarantine attribute with `xattr -dr com.apple.quarantine ddQuint‑App.app`.
- **Missing wheels at runtime**: Ensure the vendoring step populated `Resources/site‑packages` and that `PYTHONPATH` includes it before importing.
- **Plots not rendering**: Verify `matplotlib` backend is set to a non‑interactive backend (e.g., `Agg`) inside the embedded environment.
- **HDBSCAN errors**: Confirm the compiled wheel matches the target architecture (universal2 or native arm64/x86_64).

## Acknowledgements

This app bundles an embedded Python runtime and uses the `ddquint` modules directly. Credit to the original module authors and to the scientific Python ecosystem.
