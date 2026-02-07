#!/usr/bin/env bash
# build_macos.sh — Build VoiceInput.app for macOS
#
# Usage:
#   ./scripts/build_macos.sh            # standard build
#   ./scripts/build_macos.sh --sign     # build + ad-hoc code signing
#   ./scripts/build_macos.sh --sign "Developer ID Application: Name (TEAMID)"
#                                       # build + identity signing
#
# Prerequisites:
#   pip install pyinstaller pyinstaller-hooks-contrib
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_NAME="VoiceInput"
SPEC_FILE="$PROJECT_DIR/$APP_NAME.spec"
DIST_DIR="$PROJECT_DIR/dist"
APP_PATH="$DIST_DIR/$APP_NAME.app"

# ── Parse arguments ─────────────────────────────────────────────
SIGN=false
SIGN_IDENTITY="-"  # ad-hoc by default
while [[ $# -gt 0 ]]; do
    case "$1" in
        --sign)
            SIGN=true
            if [[ ${2:-} && ! ${2:-} == --* ]]; then
                SIGN_IDENTITY="$2"
                shift
            fi
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "╔══════════════════════════════════════════╗"
echo "║   Building $APP_NAME.app for macOS       ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "Project directory: $PROJECT_DIR"
echo ""

cd "$PROJECT_DIR"

# ── Check prerequisites ────────────────────────────────────────
if ! command -v pyinstaller &> /dev/null; then
    echo "ERROR: PyInstaller not found."
    echo "Install with:  pip install pyinstaller pyinstaller-hooks-contrib"
    exit 1
fi

if [ ! -f "$SPEC_FILE" ]; then
    echo "ERROR: Spec file not found: $SPEC_FILE"
    exit 1
fi

echo "PyInstaller version: $(pyinstaller --version)"
echo ""

# ── Optional: Generate icon ────────────────────────────────────
if [ ! -f "assets/icon.icns" ]; then
    echo "⚠  No custom icon found at assets/icon.icns"
    if [ -f "scripts/create_icon.py" ]; then
        echo "   Generating icon from emoji..."
        python scripts/create_icon.py || echo "   Icon generation failed — building without icon."
    else
        echo "   Building without custom icon."
    fi
    echo ""
fi

# ── Clean previous builds ──────────────────────────────────────
echo "Cleaning previous build artefacts..."
rm -rf "$PROJECT_DIR/build/$APP_NAME" "$APP_PATH"
echo ""

# ── Build ──────────────────────────────────────────────────────
echo "Running PyInstaller..."
echo "  Spec: $SPEC_FILE"
echo ""
pyinstaller "$SPEC_FILE" --noconfirm
echo ""

# ── Verify output ──────────────────────────────────────────────
if [ ! -d "$APP_PATH" ]; then
    echo "ERROR: Build failed — $APP_NAME.app not found in $DIST_DIR"
    exit 1
fi

# ── Optional: Code signing ─────────────────────────────────────
if [ "$SIGN" = true ]; then
    echo "Signing $APP_NAME.app with identity: $SIGN_IDENTITY"

    ENTITLEMENTS=""
    if [ -f "scripts/entitlements.plist" ]; then
        ENTITLEMENTS="--entitlements scripts/entitlements.plist"
    fi

    codesign --force --deep --sign "$SIGN_IDENTITY" \
        $ENTITLEMENTS \
        "$APP_PATH"

    echo "Verifying signature..."
    codesign --verify --verbose "$APP_PATH"
    echo ""
fi

# ── Summary ────────────────────────────────────────────────────
APP_SIZE=$(du -sh "$APP_PATH" | cut -f1)

echo "╔══════════════════════════════════════════╗"
echo "║   Build successful!                      ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "  App:      $APP_PATH"
echo "  Size:     $APP_SIZE"
echo ""
echo "  Run:      open $APP_PATH"
echo "  Install:  cp -r $APP_PATH /Applications/"
echo ""
echo "NOTE: The ASR model (~1.2 GB) will be downloaded"
echo "      automatically on first launch."
