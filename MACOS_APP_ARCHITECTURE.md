# macOS App Architecture Plan

## Overview
The macOS app should be a **thin GUI layer** that calls the robust Python CLI backend, NOT duplicate the analysis logic.

## Architecture Design

### What the macOS App SHOULD Do:
1. **Native macOS GUI** - Folder selection, well list, plot display, buttons
2. **Call existing Python CLI commands** - Leverage the robust, tested Python backend
3. **Cache and display results** - Show analysis results from Python in the GUI
4. **Add new interactive features** - Per-well parameter editing (enhancement beyond CLI)

### What the Python Scripts SHOULD Handle:
1. **All file processing** - CSV parsing, clustering, analysis (already working)
2. **Global parameter editing** - `ddquint --parameters` (already exists)  
3. **Export functions** - Excel, individual plots, composite image (already working)
4. **Configuration management** - Loading/saving parameters (already working)
5. **Per-well parameter overrides** - NEW: Allow parameter customization per well

## Interaction Model

```
┌─────────────────────────────────────────┐
│           macOS Swift App               │
├─────────────────────────────────────────┤
│  • Folder selection GUI                 │
│  • Well list display                    │
│  • Interactive plot viewing             │
│  • Per-well parameter editing (NEW!)    │
└─────────────────┬───────────────────────┘
                  │ Calls Python CLI
                  ▼
┌─────────────────────────────────────────┐
│         Python CLI Backend             │
├─────────────────────────────────────────┤
│  • ddquint --dir /path                  │ ← Main analysis
│  • ddquint --parameters                 │ ← Global params  
│  • ddquint --well-params A01 [params]   │ ← Per-well params (NEW)
│  • Individual plot generation           │ ← Fixed CSV parsing
│  • Export functions                     │ ← All formats
└─────────────────────────────────────────┘
```

## Current Issues & Proposed Solutions

| Issue | Current Problem | Proposed Solution |
|-------|----------------|-------------------|
| **Global Parameters button** | Not implemented | Call `ddquint --parameters` |
| **Individual well plots** | CSV parsing error | Fix Python CSV parsing or use existing plots |
| **"Edit this Well"** | Not implemented | NEW: `ddquint --well-params A01 --centroids {...}` |
| **Export functions** | Unknown status | Call existing Python CLI export commands |

## Per-Well Parameter Editing - Implementation Options

### Option A: Python Backend (Recommended)
**Pros:**
- Consistent with overall architecture
- Leverages existing parameter handling
- Can reuse existing plot generation
- Better error handling and validation

**Implementation:**
```bash
ddquint --well-params A01 --centroids "{'Chrom1': [1000, 2400], 'Chrom2': [1800, 2200]}" --regenerate-plot
```

### Option B: Swift Frontend
**Pros:**
- More responsive UI
- Direct parameter manipulation

**Cons:**
- Duplicates Python logic
- Harder to maintain consistency
- Would need to reimplement validation

## Benefits of This Architecture

- ✅ **Consistency** with the original tool
- ✅ **Leverage tested** Python code  
- ✅ **Easy maintenance** - bugs fixed in one place
- ✅ **Excel reports work** (they already do!)
- ✅ **Extensible** - easy to add new Python CLI features

## Implementation Priority

1. **Fix CSV parsing** for individual well plot display
2. **Connect Global Parameters** button to `ddquint --parameters`
3. **Implement per-well parameter editing** in Python backend
4. **Test export functions** match original CLI output
5. **Add per-well "Edit this Well"** button functionality

## Key Principle

> The macOS app orchestrates Python CLI calls rather than reimplementing analysis logic.

This ensures the GUI enhances the existing robust pipeline instead of replacing it.