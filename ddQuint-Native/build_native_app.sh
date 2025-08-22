#!/bin/bash

# Build script for ddQuint Native macOS App

set -e

echo "🚀 Building ddQuint Native macOS App"
echo "===================================="

APP_NAME="ddQuint"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$PROJECT_DIR/build"
DIST_DIR="$PROJECT_DIR/dist"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf "$BUILD_DIR"
rm -rf "$DIST_DIR"
mkdir -p "$BUILD_DIR"
mkdir -p "$DIST_DIR"

# Create temporary Xcode project
echo "📱 Creating Xcode project..."

# Create project directory structure
PROJECT_PATH="$BUILD_DIR/$APP_NAME.xcodeproj"
mkdir -p "$PROJECT_PATH"

# Generate project.pbxproj
cat > "$PROJECT_PATH/project.pbxproj" << 'EOF'
// !$*UTF8*$!
{
    archiveVersion = 1;
    classes = {
    };
    objectVersion = 56;
    objects = {

/* Begin PBXBuildFile section */
        A1B2C3D4E5F67890 /* AppDelegate.swift in Sources */ = {isa = PBXBuildFile; fileRef = A1B2C3D4E5F67891 /* AppDelegate.swift */; };
        A1B2C3D4E5F67892 /* MainWindowController.swift in Sources */ = {isa = PBXBuildFile; fileRef = A1B2C3D4E5F67893 /* MainWindowController.swift */; };
/* End PBXBuildFile section */

/* Begin PBXFileReference section */
        A1B2C3D4E5F67890 /* ddQuint.app */ = {isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = ddQuint.app; sourceTree = BUILT_PRODUCTS_DIR; };
        A1B2C3D4E5F67891 /* AppDelegate.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = AppDelegate.swift; sourceTree = "<group>"; };
        A1B2C3D4E5F67893 /* MainWindowController.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = MainWindowController.swift; sourceTree = "<group>"; };
        A1B2C3D4E5F67894 /* Info.plist */ = {isa = PBXFileReference; lastKnownFileType = text.plist.xml; path = Info.plist; sourceTree = "<group>"; };
/* End PBXFileReference section */

/* Begin PBXFrameworksBuildPhase section */
        A1B2C3D4E5F6788D /* Frameworks */ = {
            isa = PBXFrameworksBuildPhase;
            buildActionMask = 2147483647;
            files = (
            );
            runOnlyForDeploymentPostprocessing = 0;
        };
/* End PBXFrameworksBuildPhase section */

/* Begin PBXGroup section */
        A1B2C3D4E5F67887 = {
            isa = PBXGroup;
            children = (
                A1B2C3D4E5F67892 /* ddQuint */,
                A1B2C3D4E5F67891 /* Products */,
            );
            sourceTree = "<group>";
        };
        A1B2C3D4E5F67891 /* Products */ = {
            isa = PBXGroup;
            children = (
                A1B2C3D4E5F67890 /* ddQuint.app */,
            );
            name = Products;
            sourceTree = "<group>";
        };
        A1B2C3D4E5F67892 /* ddQuint */ = {
            isa = PBXGroup;
            children = (
                A1B2C3D4E5F67891 /* AppDelegate.swift */,
                A1B2C3D4E5F67893 /* MainWindowController.swift */,
                A1B2C3D4E5F67894 /* Info.plist */,
            );
            path = ddQuint;
            sourceTree = "<group>";
        };
/* End PBXGroup section */

/* Begin PBXNativeTarget section */
        A1B2C3D4E5F6788F /* ddQuint */ = {
            isa = PBXNativeTarget;
            buildConfigurationList = A1B2C3D4E5F6789D /* Build configuration list for PBXNativeTarget "ddQuint" */;
            buildPhases = (
                A1B2C3D4E5F6788C /* Sources */,
                A1B2C3D4E5F6788D /* Frameworks */,
            );
            buildRules = (
            );
            dependencies = (
            );
            name = ddQuint;
            productName = ddQuint;
            productReference = A1B2C3D4E5F67890 /* ddQuint.app */;
            productType = "com.apple.product-type.application";
        };
/* End PBXNativeTarget section */

/* Begin PBXProject section */
        A1B2C3D4E5F67888 /* Project object */ = {
            isa = PBXProject;
            attributes = {
                BuildIndependentTargetsInParallel = 1;
                LastSwiftUpdateCheck = 1500;
                LastUpgradeCheck = 1500;
                TargetAttributes = {
                    A1B2C3D4E5F6788F = {
                        CreatedOnToolsVersion = 15.0;
                    };
                };
            };
            buildConfigurationList = A1B2C3D4E5F6788B /* Build configuration list for PBXProject "ddQuint" */;
            compatibilityVersion = "Xcode 14.0";
            developmentRegion = en;
            hasScannedForEncodings = 0;
            knownRegions = (
                en,
            );
            mainGroup = A1B2C3D4E5F67887;
            productRefGroup = A1B2C3D4E5F67891 /* Products */;
            projectDirPath = "";
            projectRoot = "";
            targets = (
                A1B2C3D4E5F6788F /* ddQuint */,
            );
        };
/* End PBXProject section */

/* Begin PBXSourcesBuildPhase section */
        A1B2C3D4E5F6788C /* Sources */ = {
            isa = PBXSourcesBuildPhase;
            buildActionMask = 2147483647;
            files = (
                A1B2C3D4E5F67892 /* MainWindowController.swift in Sources */,
                A1B2C3D4E5F67890 /* AppDelegate.swift in Sources */,
            );
            runOnlyForDeploymentPostprocessing = 0;
        };
/* End PBXSourcesBuildPhase section */

/* Begin XCBuildConfiguration section */
        A1B2C3D4E5F6789B /* Debug */ = {
            isa = XCBuildConfiguration;
            buildSettings = {
                ALWAYS_SEARCH_USER_PATHS = NO;
                CLANG_ANALYZER_NONNULL = YES;
                CLANG_ANALYZER_NUMBER_OBJECT_CONVERSION = YES_AGGRESSIVE;
                CLANG_CXX_LANGUAGE_STANDARD = "gnu++20";
                CLANG_ENABLE_MODULES = YES;
                CLANG_ENABLE_OBJC_ARC = YES;
                CLANG_ENABLE_OBJC_WEAK = YES;
                CLANG_WARN_BLOCK_CAPTURE_AUTORELEASING = YES;
                CLANG_WARN_BOOL_CONVERSION = YES;
                CLANG_WARN_COMMA = YES;
                CLANG_WARN_CONSTANT_CONVERSION = YES;
                CLANG_WARN_DEPRECATED_OBJC_IMPLEMENTATIONS = YES;
                CLANG_WARN_DIRECT_OBJC_ISA_USAGE = YES_ERROR;
                CLANG_WARN_DOCUMENTATION_COMMENTS = YES;
                CLANG_WARN_EMPTY_BODY = YES;
                CLANG_WARN_ENUM_CONVERSION = YES;
                CLANG_WARN_INFINITE_RECURSION = YES;
                CLANG_WARN_INT_CONVERSION = YES;
                CLANG_WARN_NON_LITERAL_NULL_CONVERSION = YES;
                CLANG_WARN_OBJC_IMPLICIT_RETAIN_SELF = YES;
                CLANG_WARN_OBJC_LITERAL_CONVERSION = YES;
                CLANG_WARN_OBJC_ROOT_CLASS = YES_ERROR;
                CLANG_WARN_QUOTED_INCLUDE_IN_FRAMEWORK_HEADER = YES;
                CLANG_WARN_RANGE_LOOP_ANALYSIS = YES;
                CLANG_WARN_STRICT_PROTOTYPES = YES;
                CLANG_WARN_SUSPICIOUS_MOVE = YES;
                CLANG_WARN_UNGUARDED_AVAILABILITY = YES_AGGRESSIVE;
                CLANG_WARN_UNREACHABLE_CODE = YES;
                CLANG_WARN__DUPLICATE_METHOD_MATCH = YES;
                COPY_PHASE_STRIP = NO;
                DEBUG_INFORMATION_FORMAT = dwarf;
                ENABLE_STRICT_OBJC_MSGSEND = YES;
                ENABLE_TESTABILITY = YES;
                GCC_C_LANGUAGE_STANDARD = gnu11;
                GCC_DYNAMIC_NO_PIC = NO;
                GCC_NO_COMMON_BLOCKS = YES;
                GCC_OPTIMIZATION_LEVEL = 0;
                GCC_PREPROCESSOR_DEFINITIONS = (
                    "DEBUG=1",
                    "$(inherited)",
                );
                GCC_WARN_64_TO_32_BIT_CONVERSION = YES;
                GCC_WARN_ABOUT_RETURN_TYPE = YES_ERROR;
                GCC_WARN_UNDECLARED_SELECTOR = YES;
                GCC_WARN_UNINITIALIZED_AUTOS = YES_AGGRESSIVE;
                GCC_WARN_UNUSED_FUNCTION = YES;
                GCC_WARN_UNUSED_VARIABLE = YES;
                MACOSX_DEPLOYMENT_TARGET = 11.0;
                MTL_ENABLE_DEBUG_INFO = INCLUDE_SOURCE;
                MTL_FAST_MATH = YES;
                ONLY_ACTIVE_ARCH = YES;
                SDKROOT = macosx;
                SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG;
                SWIFT_OPTIMIZATION_LEVEL = "-Onone";
            };
            name = Debug;
        };
        A1B2C3D4E5F6789C /* Release */ = {
            isa = XCBuildConfiguration;
            buildSettings = {
                ALWAYS_SEARCH_USER_PATHS = NO;
                CLANG_ANALYZER_NONNULL = YES;
                CLANG_ANALYZER_NUMBER_OBJECT_CONVERSION = YES_AGGRESSIVE;
                CLANG_CXX_LANGUAGE_STANDARD = "gnu++20";
                CLANG_ENABLE_MODULES = YES;
                CLANG_ENABLE_OBJC_ARC = YES;
                CLANG_ENABLE_OBJC_WEAK = YES;
                CLANG_WARN_BLOCK_CAPTURE_AUTORELEASING = YES;
                CLANG_WARN_BOOL_CONVERSION = YES;
                CLANG_WARN_COMMA = YES;
                CLANG_WARN_CONSTANT_CONVERSION = YES;
                CLANG_WARN_DEPRECATED_OBJC_IMPLEMENTATIONS = YES;
                CLANG_WARN_DIRECT_OBJC_ISA_USAGE = YES_ERROR;
                CLANG_WARN_DOCUMENTATION_COMMENTS = YES;
                CLANG_WARN_EMPTY_BODY = YES;
                CLANG_WARN_ENUM_CONVERSION = YES;
                CLANG_WARN_INFINITE_RECURSION = YES;
                CLANG_WARN_INT_CONVERSION = YES;
                CLANG_WARN_NON_LITERAL_NULL_CONVERSION = YES;
                CLANG_WARN_OBJC_IMPLICIT_RETAIN_SELF = YES;
                CLANG_WARN_OBJC_LITERAL_CONVERSION = YES;
                CLANG_WARN_OBJC_ROOT_CLASS = YES_ERROR;
                CLANG_WARN_QUOTED_INCLUDE_IN_FRAMEWORK_HEADER = YES;
                CLANG_WARN_RANGE_LOOP_ANALYSIS = YES;
                CLANG_WARN_STRICT_PROTOTYPES = YES;
                CLANG_WARN_SUSPICIOUS_MOVE = YES;
                CLANG_WARN_UNGUARDED_AVAILABILITY = YES_AGGRESSIVE;
                CLANG_WARN_UNREACHABLE_CODE = YES;
                CLANG_WARN__DUPLICATE_METHOD_MATCH = YES;
                COPY_PHASE_STRIP = NO;
                DEBUG_INFORMATION_FORMAT = "dwarf-with-dsym";
                ENABLE_NS_ASSERTIONS = NO;
                ENABLE_STRICT_OBJC_MSGSEND = YES;
                GCC_C_LANGUAGE_STANDARD = gnu11;
                GCC_NO_COMMON_BLOCKS = YES;
                GCC_WARN_64_TO_32_BIT_CONVERSION = YES;
                GCC_WARN_ABOUT_RETURN_TYPE = YES_ERROR;
                GCC_WARN_UNDECLARED_SELECTOR = YES;
                GCC_WARN_UNINITIALIZED_AUTOS = YES_AGGRESSIVE;
                GCC_WARN_UNUSED_FUNCTION = YES;
                GCC_WARN_UNUSED_VARIABLE = YES;
                MACOSX_DEPLOYMENT_TARGET = 11.0;
                MTL_ENABLE_DEBUG_INFO = NO;
                MTL_FAST_MATH = YES;
                SDKROOT = macosx;
                SWIFT_COMPILATION_MODE = wholemodule;
                SWIFT_OPTIMIZATION_LEVEL = "-O";
            };
            name = Release;
        };
        A1B2C3D4E5F6789E /* Debug */ = {
            isa = XCBuildConfiguration;
            buildSettings = {
                CODE_SIGN_STYLE = Automatic;
                CURRENT_PROJECT_VERSION = 1;
                GENERATE_INFOPLIST_FILE = YES;
                INFOPLIST_FILE = ddQuint/Info.plist;
                INFOPLIST_KEY_NSMainStoryboardFile = "";
                INFOPLIST_KEY_NSPrincipalClass = NSApplication;
                LD_RUNPATH_SEARCH_PATHS = (
                    "$(inherited)",
                    "@executable_path/../Frameworks",
                );
                MARKETING_VERSION = 0.1.0;
                PRODUCT_BUNDLE_IDENTIFIER = com.ddquint.app;
                PRODUCT_NAME = "$(TARGET_NAME)";
                SWIFT_EMIT_LOC_STRINGS = YES;
                SWIFT_VERSION = 5.0;
            };
            name = Debug;
        };
        A1B2C3D4E5F6789F /* Release */ = {
            isa = XCBuildConfiguration;
            buildSettings = {
                CODE_SIGN_STYLE = Automatic;
                CURRENT_PROJECT_VERSION = 1;
                GENERATE_INFOPLIST_FILE = YES;
                INFOPLIST_FILE = ddQuint/Info.plist;
                INFOPLIST_KEY_NSMainStoryboardFile = "";
                INFOPLIST_KEY_NSPrincipalClass = NSApplication;
                LD_RUNPATH_SEARCH_PATHS = (
                    "$(inherited)",
                    "@executable_path/../Frameworks",
                );
                MARKETING_VERSION = 0.1.0;
                PRODUCT_BUNDLE_IDENTIFIER = com.ddquint.app;
                PRODUCT_NAME = "$(TARGET_NAME)";
                SWIFT_EMIT_LOC_STRINGS = YES;
                SWIFT_VERSION = 5.0;
            };
            name = Release;
        };
/* End XCBuildConfiguration section */

/* Begin XCConfigurationList section */
        A1B2C3D4E5F6788B /* Build configuration list for PBXProject "ddQuint" */ = {
            isa = XCConfigurationList;
            buildConfigurations = (
                A1B2C3D4E5F6789B /* Debug */,
                A1B2C3D4E5F6789C /* Release */,
            );
            defaultConfigurationIsVisible = 0;
            defaultConfigurationName = Release;
        };
        A1B2C3D4E5F6789D /* Build configuration list for PBXNativeTarget "ddQuint" */ = {
            isa = XCConfigurationList;
            buildConfigurations = (
                A1B2C3D4E5F6789E /* Debug */,
                A1B2C3D4E5F6789F /* Release */,
            );
            defaultConfigurationIsVisible = 0;
            defaultConfigurationName = Release;
        };
/* End XCConfigurationList section */
    };
    rootObject = A1B2C3D4E5F67888 /* Project object */;
}
EOF

echo "🔨 Building with xcodebuild..."

# Copy source files to build directory
cp -r "$PROJECT_DIR/ddQuint" "$BUILD_DIR/"

# Build the project
cd "$BUILD_DIR"
xcodebuild -project "$APP_NAME.xcodeproj" -target "$APP_NAME" -configuration Release build

# Copy the built app to dist
if [ -d "build/Release/$APP_NAME.app" ]; then
    echo "✅ Build successful!"
    cp -r "build/Release/$APP_NAME.app" "$DIST_DIR/"
    
    echo "📦 App created at: $DIST_DIR/$APP_NAME.app"
    echo ""
    echo "To install the app:"
    echo "  cp -r '$DIST_DIR/$APP_NAME.app' /Applications/"
    echo ""
    echo "To test the app:"
    echo "  open '$DIST_DIR/$APP_NAME.app'"
else
    echo "❌ Build failed!"
    exit 1
fi