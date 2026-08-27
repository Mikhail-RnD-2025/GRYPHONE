#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — script 48c: FIXES FOR 48a/48b
#  ------------------------------------------------------------
#  Fixes:
#    1. Remove unused Help import in SettingsPage.jsx
#    2. Ensure .header-trigger styles exist
#    3. Fix initial visible state in Header.jsx
#    4. Add dependency checks before overwriting files
#
#  RUN:   bash update_scripts/48c_fixes.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/main.py" ]; then
    PROJECT_DIR="$SCRIPT_DIR"
else
    PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
fi

echo "📁 Project root: $PROJECT_DIR"
cd "$PROJECT_DIR"

# ============================================================
# Python detection
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
    return 1
}

PYTHON_CMD="$(_detect_python || true)"
if [ -z "$PYTHON_CMD" ]; then
    echo "❌ ERROR: no Python interpreter found."
    exit 1
fi
read -ra PYCMD <<< "$PYTHON_CMD"
echo "✅ Python: ${PYCMD[*]}"

# ============================================================
# FIX 1: Check dependencies before overwriting
# ============================================================
echo ""
echo "🔍 Checking dependencies..."

MISSING=0

for dep in \
  "frontend/src/components/Dashboard.jsx" \
  "frontend/src/components/CamerasEditor.jsx" \
  "frontend/src/components/Toasts.jsx" \
  "frontend/src/pages/HelpPage.jsx" \
  "frontend/src/components/Help.jsx"; do
  if [ ! -f "$PROJECT_DIR/$dep" ]; then
    echo "  ⚠️  MISSING: $dep"
    MISSING=1
  else
    echo "  ✔ $dep"
  fi
done

if [ $MISSING -eq 1 ]; then
    echo ""
    echo "⚠️  Some dependencies are missing. The build may fail."
    echo "    Please ensure these components exist before proceeding."
    echo ""
fi

# ============================================================
# FIX 2: Remove unused Help import in SettingsPage.jsx
# ============================================================
echo ""
echo "🔧 Fixing SettingsPage.jsx (remove unused Help import)..."

SETTINGS_FILE="$PROJECT_DIR/frontend/src/pages/SettingsPage.jsx"

if [ -f "$SETTINGS_FILE" ]; then
    "${PYCMD[@]}" << 'PYEOF_FIX_SETTINGS'
from pathlib import Path
import re

file = Path("frontend/src/pages/SettingsPage.jsx")
content = file.read_text(encoding="utf-8")
original = content

# Remove unused Help import
content = re.sub(
    r"import\s+Help\s+from\s+'[^']*';?\n",
    "",
    content
)

if content != original:
    file.write_text(content, encoding="utf-8")
    print("OK: removed unused Help import")
else:
    print("INFO: Help import not found or already removed")
PYEOF_FIX_SETTINGS
else
    echo "  ⚠️  SettingsPage.jsx not found — skipping"
fi

# ============================================================
# FIX 3: Ensure .header-trigger styles exist
# ============================================================
echo ""
echo "🔧 Checking .header-trigger styles..."

STYLES_FILE="$PROJECT_DIR/frontend/src/styles.css"

if [ -f "$STYLES_FILE" ]; then
    if grep -q '.header-trigger' "$STYLES_FILE"; then
        echo "  ℹ️  .header-trigger styles already present"
    else
        cat >> "$STYLES_FILE" << 'STYLES_END'

/* Header trigger zone (v48c fix) */
.header-trigger {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 20px;
  z-index: 999;
  background: transparent;
  pointer-events: auto;
}
STYLES_END
        echo "  ✔ .header-trigger styles added"
    fi
else
    echo "  ⚠️  styles.css not found — skipping"
fi

# ============================================================
# FIX 4: Fix initial visible state in Header.jsx
# ============================================================
echo ""
echo "🔧 Fixing Header.jsx initial state..."

HEADER_FILE="$PROJECT_DIR/frontend/src/components/Header.jsx"

if [ -f "$HEADER_FILE" ]; then
    "${PYCMD[@]}" << 'PYEOF_FIX_HEADER'
from pathlib import Path
import re

file = Path("frontend/src/components/Header.jsx")
content = file.read_text(encoding="utf-8")
original = content

# Fix: initialize visible based on current route to avoid flash
# Replace: const [visible, setVisible] = useState(false)
# With: const [visible, setVisible] = useState(true)
content = re.sub(
    r"const\s+\[visible,\s*setVisible\]\s*=\s*useState\(false\)",
    "const [visible, setVisible] = useState(true)",
    content
)

if content != original:
    file.write_text(content, encoding="utf-8")
    print("OK: fixed initial visible state")
else:
    print("INFO: visible state already correct or not found")
PYEOF_FIX_HEADER
else
    echo "  ⚠️  Header.jsx not found — skipping"
fi

# ============================================================
# Final check
# ============================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Fixes applied"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Fixed:"
echo "  • Removed unused Help import in SettingsPage.jsx"
echo "  • Ensured .header-trigger styles exist"
echo "  • Fixed initial visible state in Header.jsx"
echo "  • Checked dependencies"
echo ""
echo "🚀 Next: bash build_frontend.sh && python main.py"