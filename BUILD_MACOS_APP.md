# Building ddQuint macOS App

This guide walks you through creating a native macOS `.app` bundle for ddQuint.

## Prerequisites

1. **macOS**: This process only works on macOS
2. **Python 3.10+**: Make sure you have the right Python version
3. **ddQuint installed**: Install the package in development mode

## Quick Build Process

### 1. Install py2app
```bash
pip install py2app
```

### 2. Install ddQuint in development mode
```bash
pip install -e .
```

### 3. Run the automated build script
```bash
python build_app.py
```

This script will:
- ✅ Check all requirements
- 🧹 Clean previous builds  
- 🏗️ Build the .app bundle
- 💿 Optionally create a DMG file

## Manual Build Process

If you prefer to build manually:

### 1. Clean previous builds
```bash
rm -rf build/ dist/
```

### 2. Run py2app
```bash
python setup_app.py py2app
```

### 3. Test the app
```bash
open dist/ddquint_app.app
```

## Installing the App

### Option 1: Copy to Applications
```bash
cp -r dist/ddquint_app.app /Applications/ddQuint.app
```

### Option 2: Create DMG for distribution
```bash
hdiutil create -volname "ddQuint" -srcfolder dist -ov -format UDZO ddQuint-0.1.0.dmg
```

## App Features

The macOS app provides:

🎯 **Native macOS Interface**
- Clean, modern macOS design using system fonts
- Native file dialogs and UI elements
- Proper window management and behaviors

📁 **Easy Folder Selection**
- Drag & drop support (planned)
- Native folder picker at startup
- Remembers previous selections

📊 **Real-time Progress**
- Visual progress bar during analysis
- Detailed status updates
- Cancellation support

🔬 **Interactive Results**
- File list with clickable navigation
- High-quality matplotlib plots
- Resizable panels

⚙️ **Parameter Adjustment**
- Interactive controls for analysis parameters
- Real-time visualization updates
- Per-file customization

📤 **Export Capabilities**
- Excel reports with all analysis data
- High-resolution plot images
- Batch export functionality

## Troubleshooting

### Import Errors
If you get import errors, ensure ddQuint is installed:
```bash
pip install -e .
```

### Missing Dependencies
Install any missing dependencies:
```bash
pip install matplotlib tkinter pandas numpy scikit-learn hdbscan openpyxl
```

### py2app Issues
Update py2app if you encounter build issues:
```bash
pip install --upgrade py2app setuptools
```

### App Won't Start
Check the Console app for error messages, or run from terminal:
```bash
./dist/ddquint_app.app/Contents/MacOS/ddquint_app
```

## App Bundle Structure

The created app will have this structure:
```
ddquint_app.app/
├── Contents/
│   ├── Info.plist          # App metadata
│   ├── MacOS/
│   │   └── ddquint_app     # Main executable
│   ├── Resources/          # Python runtime and modules
│   └── Frameworks/         # Required frameworks
```

## Customization

### App Icon
To add a custom icon, place a `.icns` file in the project and update `setup_app.py`:
```python
'iconfile': 'path/to/icon.icns'
```

### App Info
Modify the `plist` section in `setup_app.py` to change:
- App name and display name
- Version numbers
- Copyright information
- Supported file types

## Distribution

### For Testing
- Share the `.app` bundle directly
- Package in a ZIP file for easy sharing

### For Distribution
- Create a DMG file for professional distribution
- Consider code signing for distribution outside Mac App Store
- Add installation instructions

### Code Signing (Optional)
For distribution to other users:
```bash
codesign --deep --sign "Developer ID Application: Your Name" dist/ddquint_app.app
```

## Performance Notes

- App size: ~50-100 MB (includes Python runtime and all dependencies)
- Startup time: 2-5 seconds (first launch may be slower)
- Memory usage: ~100-200 MB during analysis
- Compatible with macOS 10.14+ (Mojave and later)

## Next Steps

After building the app:

1. **Test thoroughly** with your actual ddPCR data
2. **Share with colleagues** for feedback
3. **Create documentation** for end users
4. **Consider App Store** distribution (requires additional setup)

The app completely replaces the command-line interface while keeping all the powerful analysis capabilities of ddQuint in a user-friendly package.