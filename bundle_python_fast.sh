#!/bin/bash

# Fast Python bundling using local dependencies cache
# This version copies from local cache instead of downloading dependencies

set -e

echo "🚀 Fast Python bundling for ddQuint.app (using local cache)"
echo "=========================================================="

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PATH="$PROJECT_DIR/dist/ddQuint.app"
PYTHON_BUNDLE_PATH="$APP_PATH/Contents/Resources/Python"
VENV_PATH="$PYTHON_BUNDLE_PATH/venv"
DEPS_DIR="$PROJECT_DIR/local_deps"
CACHE_VENV="$DEPS_DIR/cache_venv"

# Check if app exists
if [ ! -d "$APP_PATH" ]; then
    echo "❌ ddQuint.app not found. Please run build.sh first."
    exit 1
fi

# Check if local cache exists
if [ ! -d "$CACHE_VENV" ]; then
    echo "❌ Local dependencies cache not found."
    echo "💡 Please run: ./setup_deps.sh"
    echo "   Or use the original: ./bundle_python.sh"
    exit 1
fi

echo "📂 App path: $APP_PATH"
echo "📂 Python bundle path: $PYTHON_BUNDLE_PATH"
echo "📂 Using cache: $CACHE_VENV"

# Create Python bundle directory
mkdir -p "$PYTHON_BUNDLE_PATH"

# Step 1: Copy the entire cached virtual environment (much faster than creating new one)
echo "⚡ Copying cached virtual environment..."
cp -r "$CACHE_VENV" "$VENV_PATH"

# Step 2: Fix up the virtual environment paths (venv paths are absolute)
echo "🔧 Fixing virtual environment paths..."
# Update pyvenv.cfg
sed -i '' "s|home = .*|home = $(dirname $(which python3))|" "$VENV_PATH/pyvenv.cfg" 2>/dev/null || true

# Update activation scripts to use new path
find "$VENV_PATH/bin" -type f -name "activate*" -exec sed -i '' "s|VIRTUAL_ENV=.*|VIRTUAL_ENV=\"$VENV_PATH\"|" {} \; 2>/dev/null || true

# Step 2.5: Install ddquint module into the virtual environment
echo "📦 Installing ddQuint module..."
SITE_PACKAGES=$(find "$VENV_PATH/lib" -name "site-packages" | head -1)
cp -r "$PROJECT_DIR/ddquint" "$SITE_PACKAGES/ddquint"

# Step 3: Additional cleanup for bundle
echo "🧹 Final cleanup for app bundle..."
rm -rf "$VENV_PATH/lib/python*/site-packages/*/tests" 2>/dev/null || true
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
    echo "✅ Fast Python bundling successful!"
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

# Show time saved
echo ""
echo "⚡ Fast bundling complete!"
echo "🎉 This method copies from local cache instead of downloading dependencies"
echo "💡 To update dependencies, run: ./setup_deps.sh"