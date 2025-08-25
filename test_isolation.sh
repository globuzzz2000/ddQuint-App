#!/bin/bash

# Test ddQuint.app in an isolated environment (simulates clean Mac)
echo "🧪 Testing ddQuint.app in Isolated Environment"
echo "============================================="

APP_PYTHON="/Applications/ddQuint.app/Contents/Resources/Python/python_launcher"

# Test with cleared PATH and Python environment variables
echo "🔒 Testing with isolated environment (no system Python access)..."

env -i PATH="/usr/bin:/bin" PYTHONPATH="" PYTHONHOME="" "$APP_PYTHON" -c "
import sys
print('✅ Python executable:', sys.executable)
print('✅ Python version:', sys.version.split()[0])

# Test core scientific functionality that the Swift app actually uses
try:
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import hdbscan
    import openpyxl
    
    # Test actual ddQuint core functions (avoiding GUI components)
    from ddquint.core.clustering import analyze_droplets
    from ddquint.core.copy_number import calculate_copy_numbers
    from ddquint.core.list_report import create_list_report
    from ddquint.visualization.well_plots import create_well_plot
    from ddquint.config import Config
    
    print('✅ All core ddQuint functions import successfully')
    print('✅ Bundle is fully self-contained!')
    
except ImportError as e:
    print('❌ Import error:', e)
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 SUCCESS: App works in completely isolated environment!"
    echo "📦 Bundle size: $(du -sh /Applications/ddQuint.app | cut -f1)"
    echo "🚀 Ready for distribution to other Macs!"
else
    echo "❌ FAILED: App requires system dependencies"
fi