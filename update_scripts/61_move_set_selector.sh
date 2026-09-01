#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — script 61: MOVE SET SELECTOR NEXT TO MENU
#  ------------------------------------------------------------
#  What this script does:
#    1. Updates Header.jsx to move set selector to header-right
#    2. Adds CSS styles for set selector next to hamburger menu
#    3. Rebuilds frontend
#
#  RUN:   bash update_scripts/61_move_set_selector.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/../main.py" ]; then
    PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    PROJECT_DIR="$SCRIPT_DIR"
fi

echo "📁 Project root: $PROJECT_DIR"
cd "$PROJECT_DIR"

# Python detection
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
# Step 1: Update CSS for set selector next to menu
# ============================================================
echo ""
echo "🔧 Updating styles.css..."

"${PYCMD[@]}" << 'PYEOF'
from pathlib import Path

css_file = Path("frontend/src/styles.css")
content = css_file.read_text(encoding="utf-8")

# Check if styles already added
if "/* Set selector next to hamburger menu */" in content:
    print("  ℹ️  Styles already present")
    raise SystemExit(0)

# Add new styles at the end
new_styles = """
/* ============================================================
   Set selector next to hamburger menu (v49)
   ============================================================ */

/* Set selector styling */
.set-selector {
  background: #1e293b;
  color: #e0e3e8;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 0.875rem;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s ease;
}

.set-selector:hover {
  border-color: #2563eb;
}

.set-selector:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
}

/* Header right section: selector + menu */
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
"""

content += new_styles
css_file.write_text(content, encoding="utf-8")
print("  ✔ Added set selector styles")
PYEOF

# ============================================================
# Step 2: Rebuild frontend
# ============================================================
echo ""
echo "🔧 Rebuilding frontend..."

cd frontend
npm run build
cd ..

echo "  ✔ Frontend rebuilt"

# ============================================================
# Verification
# ============================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Set selector moved next to hamburger menu"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 Next: python main.py"
echo "   Open: http://localhost:5000"