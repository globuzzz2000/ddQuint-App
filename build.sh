#!/bin/bash

# Simple build script for ddQuint Native macOS App using Swift Package Manager

set -e

echo "🚀 Building ddQuint Native macOS App (Swift Package Manager)"
echo "============================================================"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="$PROJECT_DIR/dist"
TEMP_DIR="$PROJECT_DIR/temp_build"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf "$DIST_DIR"
rm -rf "$TEMP_DIR"
mkdir -p "$DIST_DIR"

# Debug logs are now saved to ~/.ddQuint/debug.log (no need to reset here)

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
    mkdir -p "$APP_PATH/Contents/Resources/Python"
    
    # Copy the executable
    cp ".build/release/ddQuint" "$APP_PATH/Contents/MacOS/ddQuint"
    
    # Copy Python ddquint module
    echo "📦 Bundling Python ddquint module..."
    cp -r "ddquint" "$APP_PATH/Contents/Resources/Python/"
    
    # Bundle complete Python environment with dependencies
    echo "🐍 Bundling complete Python environment..."
    ./bundle_python.sh
    
    # Use legacy icon.png directly (Dock icon)
    if [ -f "icon.png" ]; then
        echo "🖼️  Using icon.png for app icon"
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
    
    # Optionally install to /Applications (skip if SKIP_INSTALL is set)
    if [ -z "$SKIP_INSTALL" ]; then
        echo "🚀 Installing app to Applications folder..."
        if [ -d "/Applications/ddQuint.app" ]; then
            echo "🗑️ Removing existing app..."
            rm -rf "/Applications/ddQuint.app"
        fi
        
        cp -r "$APP_PATH" /Applications/
        
        if [ $? -eq 0 ]; then
            echo "✅ App successfully installed to /Applications/ddQuint.app"
            echo ""
            echo "🎉 You can now launch ddQuint from Applications or run:"
            echo "  open /Applications/ddQuint.app"
        else
            echo "❌ Failed to install to Applications. Manual installation:"
            echo "  cp -r '$APP_PATH' /Applications/"
        fi
    else
        echo "⏩ SKIP_INSTALL set; not copying to /Applications."
        echo "    App bundle is at: $APP_PATH"
    fi
else
    echo "❌ Build failed!"
    exit 1
fi
