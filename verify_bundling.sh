#!/bin/bash

# Verify the self-contained Python bundling in ddQuint.app
echo "🔍 Verifying ddQuint.app Python Bundle"
echo "======================================"

APP_PATH="/Applications/ddQuint.app"
PYTHON_LAUNCHER="$APP_PATH/Contents/Resources/Python/python_launcher"

if [ ! -d "$APP_PATH" ]; then
    echo "❌ ddQuint.app not found in Applications"
    exit 1
fi

if [ ! -x "$PYTHON_LAUNCHER" ]; then
    echo "❌ Python launcher not found or not executable"
    exit 1
fi

echo "✅ ddQuint.app found"
echo "✅ Python launcher found"

echo ""
echo "📊 Bundle Information:"
BUNDLE_SIZE=$(du -sh "$APP_PATH/Contents/Resources/Python" 2>/dev/null | cut -f1)
echo "Python bundle size: $BUNDLE_SIZE"

echo ""
echo "🧪 Testing Python Dependencies:"

# Test core scientific libraries
"$PYTHON_LAUNCHER" -c "
import sys
print(f'Python version: {sys.version.split()[0]}')

try:
    import pandas as pd
    print('✅ Pandas:', pd.__version__)
except ImportError as e:
    print('❌ Pandas:', e)

try:
    import numpy as np
    print('✅ NumPy:', np.__version__)
except ImportError as e:
    print('❌ NumPy:', e)

try:
    import matplotlib
    print('✅ Matplotlib:', matplotlib.__version__)
except ImportError as e:
    print('❌ Matplotlib:', e)

try:
    import sklearn
    print('✅ Scikit-learn:', sklearn.__version__)
except ImportError as e:
    print('❌ Scikit-learn:', e)

try:
    import hdbscan
    print('✅ HDBSCAN: Available')
except ImportError as e:
    print('❌ HDBSCAN:', e)

try:
    import openpyxl
    print('✅ OpenPyXL:', openpyxl.__version__)
except ImportError as e:
    print('❌ OpenPyXL:', e)
"

echo ""
echo "🧪 Testing ddQuint Module:"

# Test ddQuint module loading
"$PYTHON_LAUNCHER" -c "
try:
    import ddquint
    print('✅ ddQuint module loads successfully')
    
    # Test core imports
    from ddquint.core import analyze_droplets
    from ddquint.visualization import create_well_plot
    from ddquint.config import Config
    print('✅ ddQuint core modules import successfully')
    
except ImportError as e:
    print('❌ ddQuint import error:', e)
except Exception as e:
    print('❌ ddQuint error:', e)
"

echo ""
echo "🎯 Bundle Verification Complete!"
echo "The app should now work independently without requiring system Python installation."