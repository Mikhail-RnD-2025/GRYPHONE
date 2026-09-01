#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — script 49c: FIX monitor-page CLASS (FINAL)
#  ------------------------------------------------------------
#  Properly adds monitor-page class handling whitespace.
#
#  RUN:   bash update_scripts/49c_fix_monitor_page_final.sh
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
# Fix monitor-page class with proper whitespace handling
# ============================================================
echo ""
echo "🔧 Fixing monitor-page class in MonitorPage.jsx..."

"${PYCMD[@]}" << 'PYEOF'
from pathlib import Path
import re

file = Path("frontend/src/pages/MonitorPage.jsx")
content = file.read_text(encoding="utf-8")

# Проверяем, есть ли уже класс
if 'monitor-page' in content:
    print("INFO: monitor-page class already present")
    raise SystemExit(0)

# Находим строку с className="page" (с возможными пробелами)
lines = content.split('\n')
modified = False

for i, line in enumerate(lines):
    # Ищем className="page" с любыми пробелами внутри
    if re.search(r'className="page\s*"', line):
        # Заменяем className="page" или className="page " на className="page monitor-page"
        lines[i] = re.sub(r'className="page\s*"', 'className="page monitor-page"', line)
        modified = True
        print(f"OK: added monitor-page class at line {i+1}")
        print(f"   Before: {line.strip()}")
        print(f"   After:  {lines[i].strip()}")
        break

if not modified:
    print("ERROR: could not find className='page' pattern")
    print("Searching for any className with 'page'...")

    # Показываем все строки с className
    for i, line in enumerate(lines):
        if 'className' in line and 'page' in line:
            print(f"  Line {i+1}: {line.strip()}")

    raise SystemExit(1)

# Сохраняем изменения
file.write_text('\n'.join(lines), encoding="utf-8")
print("OK: MonitorPage.jsx updated")

# Проверяем результат
content = file.read_text(encoding="utf-8")
if 'monitor-page' in content:
    print("✓ Verification passed: monitor-page class present")
else:
    print("✗ Verification failed: monitor-page class NOT found")
    raise SystemExit(1)
PYEOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ monitor-page class fixed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 Next: npm run build"