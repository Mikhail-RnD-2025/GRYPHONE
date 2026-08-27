#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — script 49b: ADD monitor-page CLASS
#  ------------------------------------------------------------
#  Adds monitor-page class to MonitorPage.jsx root div.
#  This is a targeted fix for script 49.
#
#  RUN:   bash update_scripts/49b_fix_monitor_page_class.sh
#  THEN:  npm run build
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
# Add monitor-page class
# ============================================================
echo ""
echo "🔧 Adding monitor-page class to MonitorPage.jsx..."

"${PYCMD[@]}" << 'PYEOF'
from pathlib import Path

file = Path("frontend/src/pages/MonitorPage.jsx")
content = file.read_text(encoding="utf-8")

# Проверяем, есть ли уже класс
if 'monitor-page' in content:
    print("INFO: monitor-page class already present")
    raise SystemExit(0)

# Находим первую строку с className="page" и добавляем monitor-page
lines = content.split('\n')
modified = False

for i, line in enumerate(lines):
    if 'className="page"' in line and 'monitor-page' not in line:
        # Заменяем className="page" на className="page monitor-page"
        lines[i] = line.replace('className="page"', 'className="page monitor-page"')
        modified = True
        print(f"OK: added monitor-page class at line {i+1}")
        print(f"   Before: {line.strip()}")
        print(f"   After:  {lines[i].strip()}")
        break

if not modified:
    print("WARNING: could not find className='page' to modify")
    print("Trying alternative pattern...")

    # Пробуем найти <div с className
    for i, line in enumerate(lines):
        if '<div' in line and 'className=' in line and 'page' in line:
            # Добавляем monitor-page после page
            lines[i] = line.replace('"page"', '"page monitor-page"')
            modified = True
            print(f"OK: added monitor-page class at line {i+1} (alternative)")
            print(f"   After: {lines[i].strip()}")
            break

if modified:
    file.write_text('\n'.join(lines), encoding="utf-8")
    print("OK: MonitorPage.jsx updated")
else:
    print("ERROR: could not add monitor-page class")
    print("Please add it manually to the root <div>")
PYEOF

# ============================================================
# Verify
# ============================================================
echo ""
echo "🔍 Verification..."

if grep -q "monitor-page" "$PROJECT_DIR/frontend/src/pages/MonitorPage.jsx"; then
    echo "  ✔ monitor-page class present"
    echo ""
    echo "📋 Line with monitor-page:"
    grep -n "monitor-page" "$PROJECT_DIR/frontend/src/pages/MonitorPage.jsx" | head -1
else
    echo "  ❌ monitor-page class NOT found"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ monitor-page class added"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 Next: npm run build"