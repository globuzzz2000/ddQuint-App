Welcome to **ddQuint**, an application for analyzing multiplex ddPCR data.

---

## Quick Start
1. **Select Input Folder** → Choose the folder containing QX Manager **Amplitude CSVs**.  
2. *(Optional)* **Load Template** → Use a QX Manager template (`.csv`) to auto-assign sample names.  
3. **Set Parameters** → Open **Global Parameters** to adjust clustering and classification settings.  
4. **Analyze** → The files are then automatically re-analyzed based on updated parameters.
5. **Export** → Save Excel reports, plots, and parameter files.

---

## Indicators
Each well is marked with an indicator:

- ⚪ **White circle**: Euploid (normal copy number)  
- ⚫ **Grey circle**: Buffer Zone (uncertain or intermediate)  
- 🟣 **Purple circle**: Aneuploid (gain or loss detected)  
- 🔴 **Red circle**: Warning (e.g., low droplets or clustering issue)  
- ◼️ **Square shape**: Edited well (custom parameters applied)  

Use the filter button to hide buffer zone or warning samples.

---

## Well-Specific Parameter Editing
- Right-click (or use the context menu) on a well plot and choose **Edit This Well**.  
- A parameter editor will open with the same settings as Global Parameters, but applied only to that well.  
- After saving, only that well is re-analyzed and updated.  

This makes troubleshooting and tuning single wells much faster.

---

## Export
- Export everything through the main menu button or iundividually through the menu bar.
- **Excel report**: Copy numbers, classifications, and metadata.  
- **Plots**: Individual well plots in /Graphs/ directory.  
- **Parameter files**: Save/load your analysis settings for reproducibility.

---

## Troubleshooting
- **No CSVs found** → Confirm the input files are QX Manager *Amplitude* exports, that were not renamed.  
- **Sample names missing** → Provide a QX Manager template.  
- **Poor clustering** → Adjust HDBSCAN parameters or minimum droplet thresholds.  
- **Warnings** → Usually low droplet counts; check run quality.  

---

## QX Manager Template Creation
The app can generate **QX Manager-compatible template files**:  
- Create a template in-app and save it as `.csv`.  
- Import this file into QX Manager to pre-fill your experiment setup with sample names.  
- Reuse the same file in ddQuint during analysis to auto-assign well names in reports and plots.

---

For advanced details, see the full README on GitHub.
