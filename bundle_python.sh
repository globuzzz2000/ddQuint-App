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

# Step 1: Create a minimal Python virtual environment (prefer Python 3.13 for cache compatibility)
echo "🔧 Creating Python virtual environment..."
if command -v python3.13 >/dev/null 2>&1; then
  PYBIN=python3.13
else
  PYBIN=python3
fi
echo "Using Python interpreter: $(command -v "$PYBIN")"
"$PYBIN" -m venv "$VENV_PATH" --copies

echo "📦 Installing ddQuint dependencies (offline from local_deps if available)..."
"$VENV_PATH/bin/pip" install --no-cache-dir --upgrade pip >/dev/null 2>&1 || true

# Prefer offline vendored site-packages if Python versions match
CACHE_SITE_PACKAGES_BASE="$PROJECT_DIR/local_deps/cache_venv/lib"
VENV_PYVER=$("$VENV_PATH/bin/python" -c 'import sys; print(f"python{sys.version_info.major}.{sys.version_info.minor}")')
VENV_SITE_PACKAGES=$("$VENV_PATH/bin/python" -c 'import site; print(site.getsitepackages()[0])')
CACHE_SITE_PACKAGES="$CACHE_SITE_PACKAGES_BASE/$VENV_PYVER/site-packages"

if [ -d "$CACHE_SITE_PACKAGES" ]; then
    echo "📁 Using cached dependencies from: $CACHE_SITE_PACKAGES"
    rsync -a --delete "$CACHE_SITE_PACKAGES/" "$VENV_SITE_PACKAGES/"
else
    echo "⚠️ No cached site-packages for $VENV_PYVER found at $CACHE_SITE_PACKAGES."
    echo "   Falling back to minimal install from requirements (may need network)."
    if [ -f "$PROJECT_DIR/local_deps/requirements.txt" ]; then
        "$VENV_PATH/bin/pip" install --no-cache-dir -r "$PROJECT_DIR/local_deps/requirements.txt"
    else
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
        if [[ "$OSTYPE" == "darwin"* ]]; then
            "$VENV_PATH/bin/pip" install --no-cache-dir \
                "pyobjc-core" \
                "pyobjc-framework-Cocoa"
        fi
    fi
fi

# Step 2.5: Install ddquint module into the virtual environment
echo "📦 Installing ddQuint module into virtual environment..."
# Copy ddquint module to site-packages so it's always available
SITE_PACKAGES=$("$VENV_PATH/bin/python" -c 'import site,sys; print(site.getsitepackages()[0])')
mkdir -p "$SITE_PACKAGES"
rsync -a --delete "$PROJECT_DIR/ddquint/" "$SITE_PACKAGES/ddquint/"

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
# Suppress third-party SyntaxWarnings (e.g., hdbscan LaTeX label strings)
if PYTHONWARNINGS="ignore::SyntaxWarning" "$PYTHON_BUNDLE_PATH/python_launcher" -c "
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
