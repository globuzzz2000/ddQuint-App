#!/bin/bash

# Setup local dependencies for faster builds
# This creates a local dependency cache that can be reused across builds

set -e

echo "🏗️ Setting up local dependencies cache for ddQuint"
echo "=============================================="

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPS_DIR="$PROJECT_DIR/local_deps"
CACHE_VENV="$DEPS_DIR/cache_venv"

# Create dependencies directory
mkdir -p "$DEPS_DIR"

echo "📂 Dependencies cache: $DEPS_DIR"

# Create or update the cache virtual environment
if [ -d "$CACHE_VENV" ]; then
    echo "🔄 Updating existing dependencies cache..."
else
    echo "🆕 Creating new dependencies cache..."
    python3 -m venv "$CACHE_VENV" --copies
fi

# Install/update dependencies in the cache
echo "📦 Installing/updating dependencies..."
"$CACHE_VENV/bin/pip" install --upgrade pip

# Install all ddQuint dependencies
"$CACHE_VENV/bin/pip" install \
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
    "$CACHE_VENV/bin/pip" install \
        "pyobjc-core" \
        "pyobjc-framework-Cocoa"
fi

# Create requirements file for faster future installs
echo "📝 Creating requirements.txt..."
"$CACHE_VENV/bin/pip" freeze > "$DEPS_DIR/requirements.txt"

# Clean up cache
echo "🧹 Cleaning up cache..."
rm -rf "$CACHE_VENV/share/man" 2>/dev/null || true
rm -rf "$CACHE_VENV/share/doc" 2>/dev/null || true
find "$CACHE_VENV" -name "*.pyc" -delete 2>/dev/null || true
find "$CACHE_VENV" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Display cache information
CACHE_SIZE=$(du -sh "$DEPS_DIR" | cut -f1)
echo ""
echo "📊 Dependencies Cache Information:"
echo "Cache location: $DEPS_DIR"
echo "Cache size: $CACHE_SIZE"
echo "Requirements: $DEPS_DIR/requirements.txt"

echo ""
echo "✅ Dependencies cache setup complete!"
echo ""
echo "💡 Usage:"
echo "  - Run this script when you want to update dependencies"
echo "  - The build process will now copy from local cache instead of downloading"
echo "  - This will significantly speed up future builds"