#!/bin/bash

# Bundle Python and all dependencies into the ddQuint.app
# This creates a fully self-contained application

set -e

echo "🐍 Bundling Python environment for ddQuint.app"
echo "=============================================="

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PATH="$PROJECT_DIR/dist/ddQuint.app"
PYTHON_BUNDLE_PATH="$APP_PATH/Contents/Resources/Python"
VENV_PATH="$PYTHON_BUNDLE_PATH/venv"

# Check if app exists
if [ ! -d "$APP_PATH" ]; then
    echo "❌ ddQuint.app not found. Please run build.sh first."
    exit 1
fi

echo "📂 App path: $APP_PATH"
echo "📂 Python bundle path: $PYTHON_BUNDLE_PATH"

# Create Python bundle directory
mkdir -p "$PYTHON_BUNDLE_PATH"

# Step 1: Create a minimal Python virtual environment
echo "🔧 Creating Python virtual environment..."
python3 -m venv "$VENV_PATH" --copies

# Step 2: Install dependencies in the virtual environment
echo "📦 Installing ddQuint dependencies..."
"$VENV_PATH/bin/pip" install --no-cache-dir --upgrade pip

# Install dependencies from pyproject.toml manually
"$VENV_PATH/bin/pip" install --no-cache-dir \
    "pandas>=1.0.0" \
    "numpy>=1.18.0" \
    "matplotlib>=3.3.0" \
    "scikit-learn>=0.24.0" \
    "hdbscan>=0.8.27" \
    "openpyxl>=3.0.5" \
    "Send2Trash>=1.8.2" \
    "colorama>=0.4.4" \
    "tqdm>=4.60.0"

# Install macOS-specific dependencies
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "📱 Installing macOS-specific dependencies..."
    "$VENV_PATH/bin/pip" install --no-cache-dir \
        "pyobjc-core" \
        "pyobjc-framework-Cocoa"
fi

# Step 2.5: Install ddquint module into the virtual environment
echo "📦 Installing ddQuint module into virtual environment..."
# Copy ddquint module to site-packages so it's always available
SITE_PACKAGES=$(find "$VENV_PATH/lib" -name "site-packages" | head -1)
cp -r "$PROJECT_DIR/ddquint" "$SITE_PACKAGES/ddquint"

# Step 3: Remove unnecessary files to reduce bundle size
echo "🧹 Cleaning up virtual environment..."
rm -rf "$VENV_PATH/share/man" 2>/dev/null || true
rm -rf "$VENV_PATH/share/doc" 2>/dev/null || true
rm -rf "$VENV_PATH/lib/python*/site-packages/*/tests" 2>/dev/null || true
rm -rf "$VENV_PATH/lib/python*/site-packages/*/__pycache__" 2>/dev/null || true
find "$VENV_PATH" -name "*.pyc" -delete 2>/dev/null || true
find "$VENV_PATH" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Step 4: Create a launcher script that uses the bundled Python
echo "🚀 Creating Python launcher script..."
cat > "$PYTHON_BUNDLE_PATH/python_launcher" << 'EOF'
#!/bin/bash
# Bundled Python launcher for ddQuint

# Get the directory this script is in
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"

# Use the bundled Python with all arguments
exec "$VENV_PYTHON" "$@"
EOF

chmod +x "$PYTHON_BUNDLE_PATH/python_launcher"

# Step 5: Test the bundled environment
echo "🔍 Testing bundled Python environment..."
if "$PYTHON_BUNDLE_PATH/python_launcher" -c "
import ddquint
print('✅ ddQuint module loads successfully from:', ddquint.__file__)
from ddquint.core import analyze_droplets
from ddquint.config import Config  
print('✅ Core ddQuint functions available')
"; then
    echo "✅ Python bundling successful!"
else
    echo "❌ Python bundling test failed!"
    exit 1
fi

# Step 6: Display bundle information
echo ""
echo "📊 Bundle Information:"
echo "Python executable: $PYTHON_BUNDLE_PATH/python_launcher"
BUNDLE_SIZE=$(du -sh "$PYTHON_BUNDLE_PATH" | cut -f1)
echo "Bundle size: $BUNDLE_SIZE"

echo ""
echo "🎉 Python environment successfully bundled!"
echo "The app is now self-contained and doesn't require external Python installation."