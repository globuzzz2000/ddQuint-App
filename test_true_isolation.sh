#!/bin/bash

# Test ddQuint.app in TRUE isolation (no source code access)
echo "🧪 Testing ddQuint.app in TRUE Isolation"
echo "========================================"

APP_PYTHON="/Applications/ddQuint.app/Contents/Resources/Python/python_launcher"

# Create a temporary directory and run from there (no access to source)
TEMP_DIR="/tmp/ddquint_isolation_test_$$"
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

echo "🔒 Running from isolated directory: $TEMP_DIR"
echo "🔍 Current directory contents:"
ls -la

echo ""
echo "🧪 Testing bundled Python and dependencies:"

# Test with completely isolated environment
env -i PATH="/usr/bin:/bin" PYTHONPATH="" PYTHONHOME="" "$APP_PYTHON" -c "
import sys
print('✅ Python executable:', sys.executable)
print('✅ Python version:', sys.version.split()[0])
print('✅ Python path:', sys.path[:3], '...')

# Test core scientific libraries
try:
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import sklearn
    import hdbscan
    import openpyxl
    print('✅ All scientific dependencies available')
    
    # Test ddQuint module loading from BUNDLED location
    import ddquint
    print('✅ ddQuint module path:', ddquint.__file__)
    
    # Test actual ddQuint core functions
    from ddquint.core.clustering import analyze_droplets
    from ddquint.core.copy_number import calculate_copy_numbers
    from ddquint.core.list_report import create_list_report
    from ddquint.visualization.well_plots import create_well_plot
    from ddquint.config import Config
    
    print('✅ All core ddQuint functions import successfully')
    print('🎉 TRUE ISOLATION TEST PASSED!')
    
except ImportError as e:
    print('❌ Import error:', e)
    sys.exit(1)
except Exception as e:
    print('❌ Error:', e)
    sys.exit(1)
"

RESULT=$?

# Cleanup
cd /
rm -rf "$TEMP_DIR"

if [ $RESULT -eq 0 ]; then
    echo ""
    echo "🎉 SUCCESS: App is truly self-contained!"
    echo "📦 The app will work on any Mac without dependencies!"
else
    echo ""
    echo "❌ FAILED: App still requires external dependencies"
fi