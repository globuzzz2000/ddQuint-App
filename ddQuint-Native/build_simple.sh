#!/bin/bash

# Simple build script for ddQuint Native macOS App using Swift Package Manager

set -e

echo "🚀 Building ddQuint Native macOS App (Swift Package Manager)"
echo "============================================================"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="$PROJECT_DIR/dist"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

# Build the executable
echo "🔨 Building Swift executable..."
cd "$PROJECT_DIR"

swift build -c release

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    
    # Create app bundle structure
    echo "📦 Creating app bundle..."
    APP_NAME="ddQuint.app"
    APP_PATH="$DIST_DIR/$APP_NAME"
    
    mkdir -p "$APP_PATH/Contents/MacOS"
    mkdir -p "$APP_PATH/Contents/Resources"
    
    # Copy the executable
    cp ".build/release/ddQuint" "$APP_PATH/Contents/MacOS/ddQuint"
    
    # Copy icon if it exists
    if [ -f "icon.png" ]; then
        cp "icon.png" "$APP_PATH/Contents/Resources/AppIcon.png"
    fi
    
    # Create Info.plist
    cat > "$APP_PATH/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>ddQuint</string>
    <key>CFBundleIdentifier</key>
    <string>com.ddquint.app</string>
    <key>CFBundleName</key>
    <string>ddQuint</string>
    <key>CFBundleDisplayName</key>
    <string>ddQuint - Digital Droplet PCR Analysis</string>
    <key>CFBundleVersion</key>
    <string>0.1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>0.1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
</dict>
</plist>
EOF

    echo "📦 App created at: $APP_PATH"
    echo ""
    echo "To install the app:"
    echo "  cp -r '$APP_PATH' /Applications/"
    echo ""
    echo "To test the app:"
    echo "  open '$APP_PATH'"
else
    echo "❌ Build failed!"
    exit 1
fi