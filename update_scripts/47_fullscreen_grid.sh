#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — script 47: FULLSCREEN GRID WITH ASPECT RATIO
#  ------------------------------------------------------------
#  What it does:
#    1. Stretches camera grid to full screen (100vh)
#    2. No space reserved for header (header is overlay)
#    3. Video fills card keeping aspect ratio (object-fit: contain)
#
#  RUN:   bash update_scripts/47_fullscreen_grid.sh
#  THEN:  bash build_frontend.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Smart project root detection
if [ -f "$SCRIPT_DIR/main.py" ]; then
    PROJECT_DIR="$SCRIPT_DIR"
else
    PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
fi

echo "📁 Project root: $PROJECT_DIR"
cd "$PROJECT_DIR"
echo "📂 Working directory: $(pwd)"

# ============================================================
# Reliable Python detection (no Windows Store)
# ============================================================
_detect_python() {
    local cmd
    for cmd in python python3 py; do
        if command -v "$cmd" >/dev/null 2>&1; then
            if "$cmd" --version >/dev/null 2>&1; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    if command -v py >/dev/null 2>&1; then
        if py -3 --version >/dev/null 2>&1; then
            echo "py -3"
            return 0
        fi
    fi
    return 1
}

PYTHON_CMD="$(_detect_python || true)"
if [ -z "$PYTHON_CMD" ]; then
    echo "❌ ERROR: no working Python interpreter found."
    exit 1
fi

read -ra PYCMD <<< "$PYTHON_CMD"
echo "✅ Python: ${PYCMD[*]}"

# ============================================================
# PART 1: Patch styles.css — fullscreen grid styles
# ============================================================
echo ""
echo "🔧 Patching styles.css (fullscreen grid)..."

"${PYCMD[@]}" << 'PYEOF_STYLES'
from pathlib import Path
import re

file = Path("frontend/src/styles.css")
if not file.exists():
    print("WARNING: frontend/src/styles.css not found — skipping")
    raise SystemExit(0)

content = file.read_text(encoding="utf-8")
original = content

# Step 1: Remove header reservation (.monitor-page padding-top)
content = re.sub(
    r'\.monitor-page\s*\{\s*padding-top:\s*\d+px;\s*\}',
    '/* monitor-page: no padding, header is overlay (v47) */',
    content
)

# Step 2: Add fullscreen grid styles if not present
if '.fullscreen-grid' not in content:
    content += """

/* ============================================================
   Fullscreen camera grid (v47)
   ------------------------------------------------------------
   - Grid stretches to full screen (100vh)
   - No space reserved for header (header is overlay)
   - Video fills the card keeping aspect ratio
   ============================================================ */

/* Monitor page: no padding, full screen */
.page.monitor-page {
  padding: 0 !important;
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Grid container: takes all available space */
.fullscreen-grid {
  flex: 1;
  min-height: 0;
  width: 100%;
  height: 100%;
  display: grid;
  gap: 2px;
  background: #0b0d10;
}

/* Grid cell: container for video */
.fullscreen-grid .camera-card {
  position: relative;
  overflow: hidden;
  background: #000;
  height: 100%;
  width: 100%;
}

/* Video: fills entire cell keeping aspect ratio */
.fullscreen-grid .camera-card video,
.fullscreen-grid .camera-video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
}

/* Empty cell: also stretches */
.fullscreen-grid .camera-empty {
  height: 100%;
  width: 100%;
}
"""
    print("OK: fullscreen grid styles added")

# Step 3: Ensure header is overlay on monitor page
if '.page.monitor-page .header' not in content:
    content += """

/* Header as overlay on monitor page (v47) */
.page.monitor-page .header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: linear-gradient(
    to bottom,
    rgba(11, 13, 16, 0.95) 0%,
    rgba(11, 13, 16, 0.85) 70%,
    rgba(11, 13, 16, 0.4) 100%
  );
  backdrop-filter: blur(8px);
}
"""
    print("OK: header overlay styles added")

if content != original:
    file.write_text(content, encoding="utf-8")
    print("OK: styles.css updated")
else:
    print("INFO: no changes needed in styles.css")
PYEOF_STYLES

# ============================================================
# PART 2: Patch MonitorPage.jsx — add fullscreen-grid class
# ============================================================
echo ""
echo "🔧 Patching MonitorPage.jsx (fullscreen-grid class)..."

MONITOR_FILE="$PROJECT_DIR/frontend/src/pages/MonitorPage.jsx"

if [ ! -f "$MONITOR_FILE" ]; then
    echo "⚠️  WARNING: MonitorPage.jsx not found — skipping"
else
    "${PYCMD[@]}" << 'PYEOF_MONITOR'
from pathlib import Path
import re

file = Path("frontend/src/pages/MonitorPage.jsx")
content = file.read_text(encoding="utf-8")
original = content

# Step 1: Add monitor-page class to root div
if 'monitor-page' not in content:
    content = re.sub(
        r'(<div\s+className=")page(")',
        r'\1page monitor-page\2',
        content,
        count=1
    )
    print("OK: added monitor-page class to root div")
else:
    print("INFO: monitor-page class already present")

# Step 2: Add fullscreen-grid class to grid container
if 'fullscreen-grid' not in content:
    pattern = re.compile(r'(<div)(\s+style=\{gridStyle\})')
    if pattern.search(content):
        content = pattern.sub(r'\1 className="fullscreen-grid"\2', content, count=1)
        print("OK: added fullscreen-grid class to grid container")
    else:
        print("WARNING: grid container not found — add className='fullscreen-grid' manually")
else:
    print("INFO: fullscreen-grid class already present")

# Step 3: Ensure grid uses 100% height via gridStyle
if "'height': '100%'" not in content and 'height: "100%"' not in content:
    pattern3 = re.compile(
        r'(const\s+gridStyle\s*=\s*\{[^}]*)(display:\s*[\'"]grid[\'"])',
        re.DOTALL
    )
    if pattern3.search(content):
        content = pattern3.sub(
            r'\1\2,\n  height: "100%",',
            content,
            count=1
        )
        print("OK: added height:100% to gridStyle")

if content != original:
    file.write_text(content, encoding="utf-8")
    print("OK: MonitorPage.jsx updated")
else:
    print("INFO: no changes needed in MonitorPage.jsx")
PYEOF_MONITOR
fi

# ============================================================
# PART 3: Check CameraCard.jsx for object-fit
# ============================================================
echo ""
echo "🔍 Checking CameraCard.jsx (object-fit)..."

CAMERA_FILE="$PROJECT_DIR/frontend/src/components/CameraCard.jsx"

if [ -f "$CAMERA_FILE" ]; then
    if grep -q 'object-fit' "$CAMERA_FILE" 2>/dev/null; then
        echo "  ℹ️  object-fit already set in CameraCard.jsx"
        grep -n 'object-fit' "$CAMERA_FILE" | sed 's/^/     /'
    else
        echo "  ℹ️  object-fit is set via CSS (.fullscreen-grid .camera-video)"
    fi
else
    echo "⚠️  WARNING: CameraCard.jsx not found"
fi

# ============================================================
# Final check
# ============================================================
echo ""
echo "🔍 Final check..."

if [ ! -s "$PROJECT_DIR/frontend/src/styles.css" ]; then
    echo "❌ ERROR: styles.css is empty or missing!" >&2
    exit 1
fi
echo "  ✔ frontend/src/styles.css"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Grid stretches to full screen"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 What changed:"
echo "  • Grid: height 100vh, no header padding"
echo "  • Header: overlay (no space reserved)"
echo "  • Video: object-fit contain (aspect ratio preserved)"
echo ""
echo "🚀 Next steps:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Open: http://localhost:5000 (Ctrl+Shift+R)"