#!/bin/bash

# Build ddQuint Windows Application with Portable Python
# Usage: ./build.sh

set -e

echo "🚀 Building ddQuint Windows Application..."
echo "=========================================="

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

build_runtime() {
  local runtime="$1"
  local build_dir="$PROJECT_DIR/dist/${runtime}-standalone"
  echo "📦 Building for ${runtime}..."

  dotnet publish "$PROJECT_DIR/src/ddQuint.Desktop/ddQuint.Desktop.csproj" \
      -c Release \
      -r "$runtime" \
      --self-contained true \
      -o "$build_dir"

  if [ $? -ne 0 ]; then
      echo "❌ Build failed for ${runtime}!"
      exit 1
  fi

  echo "✅ Build completed successfully for ${runtime}!"

  echo "📋 Copying Python bundling scripts..."
  cp "$PROJECT_DIR/scripts/bundle_python_engine.ps1" "$build_dir/"
  cp "$PROJECT_DIR/scripts/bundle_python.bat" "$build_dir/"
  cp "$PROJECT_DIR/scripts/bundle_python.ps1" "$build_dir/"
  
  echo "📋 Copying ARM64 wheels..."
  if [ -d "$PROJECT_DIR/resources/arm64_wheels" ]; then
    mkdir -p "$build_dir/resources"
    cp -r "$PROJECT_DIR/resources/arm64_wheels" "$build_dir/resources/"
    echo "   ARM64 wheels copied to: $build_dir/resources/arm64_wheels"
  else
    echo "   WARNING: ARM64 wheels not found at $PROJECT_DIR/resources/arm64_wheels"
  fi

  echo "📦 Staging ddquint Python package..."
  mkdir -p "$build_dir/Python"
  if [ -d "$PROJECT_DIR/src/ddQuint.Desktop/Python/ddquint" ]; then
    rsync -a --delete --exclude "__pycache__" --exclude "*.pyc" "$PROJECT_DIR/src/ddQuint.Desktop/Python/ddquint/" "$build_dir/Python/ddquint/"
    echo "   ddquint staged at: $build_dir/Python/ddquint"
  else
    echo "   WARNING: ddquint source not found at $PROJECT_DIR/ddquint or $PROJECT_DIR/../ddquint"
  fi

  echo "📦 Portable Python setup ready for ${runtime}..."
  echo "   ℹ️  Run bundle_python_portable.ps1 on Windows to create portable Python environment"
  echo "   ℹ️  The script will auto-detect architecture and use appropriate Python distribution"
}

# Build both ARM64 and x64
build_runtime win-arm64
build_runtime win-x64

# Optional: Deploy to iCloud for easy access
echo "🔍 Checking for iCloud deployment..."

# Optional: Deploy to iCloud Downloads for easy transfer
ICLOUD_TARGET="/Users/jakob/Library/Mobile Documents/com~apple~CloudDocs/Downloads"

if [ -d "$ICLOUD_TARGET" ]; then
    deploy_dir() {
      local runtime="$1"
      local src="$PROJECT_DIR/dist/${runtime}-standalone"
      local tgt="$ICLOUD_TARGET/ddQuint-${runtime}"
      
      echo "📂 Deploying $runtime to iCloud..."
      
      if [ -d "$tgt" ]; then
          rm -rf "$tgt"
      fi
      
      cp -r "$src" "$tgt"
      echo "   ✅ Deployed to: $tgt"
    }
    
    deploy_dir win-arm64
    deploy_dir win-x64
    
    echo ""
    echo "📱 Builds available in iCloud Downloads:"
    echo "   - ddQuint-win-arm64"
    echo "   - ddQuint-win-x64"
else
    echo "ℹ️  iCloud not available, builds remain in dist/ folder"
fi

echo ""
echo "🎉 Build completed successfully!"
echo "================================"
echo ""
echo "📁 Built applications:"
echo "   - $PROJECT_DIR/dist/win-arm64-standalone/"
echo "   - $PROJECT_DIR/dist/win-x64-standalone/"
echo ""
echo "🚀 Next steps for Windows:"
echo "   1. Copy the appropriate folder to Windows machine"
echo "   2. Double-click: bundle_python.bat"
echo "   3. Launch: ddQuint.exe"
echo ""
echo "💡 The Python bundling script will:"
echo "   - Auto-detect architecture (ARM64/x64)"
echo "   - Download matching Python embedded distribution"
echo "   - Install all dependencies including ARM64 wheels"
echo "   - Create truly portable Python environment"
echo ""
