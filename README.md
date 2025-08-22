# ddQuint-App (macOS): GUI Layer for the ddQuint Python Pipeline

This repository provides a macOS graphical user interface (GUI) for the **ddQuint** Python pipeline that analyzes ddPCR data for aneuploidy detection. **Current status:** the app calls into a separately installed ddQuint/CLI-style environment. We are refactoring toward a fully bundled, stand-alone app.

---

## Goals

- **Stand-alone app:** Bundle Python and all required dependencies inside the `.app`, so no separate installation is needed.
- **No direct exports in modules:** Python modules should compute and render for the UI; file exports are initiated and owned by the app.
- **Exports use app-side cache:** Export actions must read already computed, cached results instead of re-running analysis.
- **Light Python migration:** Incrementally refactor to cleaner boundaries (pure compute functions, plotting returns figures/bytes, Excel writer as a formatter only).


---

## Approach (rough plan)

- **Embed Python + wheels** inside the app bundle and set `PYTHONHOME`/`PYTHONPATH` at launch.
- **Separate compute from save:** Core functions return serializable data; plotting functions return `matplotlib` figures or image bytes; the app decides where/when to save.
- **Introduce an app cache:** Keep the latest results in memory and persist a compact `results.json` next to outputs; exports read only from this cache.
- **Excel as a formatter:** Keep the Excel writer focused on formatting an already-finished results object and writing to a chosen path—no analysis calls.
- **Parameters handling (brief):** The GUI applies user overrides on top of sensible defaults to produce a single “resolved parameters” dict that all compute calls receive.

---

## What Works Well

- Input folder selection functions as intended.
- CSV files are analyzed progressively and displayed immediately after processing.
- At the end of processing, a composite image is generated and shown at the top of the list.
- The list is properly sorted, and names are assigned based on the provided template file.
- The **Global Parameters** menu and settings work exactly as intended.
- Plot exports correctly use pre-generated images (though these should no longer be stored in the input folder, which is a legacy behavior).
- Progress indicators
- Excel export from cached results

---

## What Does Not Work


- The **Edit this Well** functionality does not work as intended; it should allow editing parameters for a single well and then re-run analysis only for that well, updating its cached data and plots accordingly.

---
