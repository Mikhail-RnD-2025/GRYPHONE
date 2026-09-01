#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — script 60: ADD MISSING DB METHODS
#  ------------------------------------------------------------
#  What this script does:
#    1. Adds get() and set() methods to Database class
#    2. These methods work with JSON-serialized dictionaries
#    3. Fixes AttributeError: 'Database' object has no attribute 'get'
#
#  RUN:   bash update_scripts/60_add_db_methods.sh
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
# Add missing methods to app/database.py
# ============================================================
echo ""
echo "🔧 Adding missing methods to app/database.py..."

"${PYCMD[@]}" << 'PYEOF'
from pathlib import Path
import re

db_file = Path("app/database.py")
content = db_file.read_text(encoding="utf-8")

# Check if methods already exist
if "def get(self, key:" in content and "def set(self, key:" in content:
    print("  ℹ️  Methods get() and set() already exist")
    raise SystemExit(0)

# Find the position to insert new methods (after set_setting method)
insert_marker = "    def get_all_cameras(self):"
if insert_marker not in content:
    print("  ❌ ERROR: Could not find insertion point")
    raise SystemExit(1)

# New methods to add
new_methods = '''    def get(self, key: str, default=None):
        """Get a JSON-serialized value by key (for ConfigManager compatibility)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        if result:
            import json
            try:
                return json.loads(result[0])
            except (json.JSONDecodeError, TypeError):
                return result[0]
        return default

    def set(self, key: str, value):
        """Set a JSON-serialized value by key (for ConfigManager compatibility)."""
        import json
        conn = self.get_connection()
        cursor = conn.cursor()
        json_value = json.dumps(value, ensure_ascii=False)
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, json_value)
        )
        conn.commit()
        conn.close()

'''

# Insert new methods before get_all_cameras
content = content.replace(insert_marker, new_methods + insert_marker)

# Write back
db_file.write_text(content, encoding="utf-8")
print("  ✔ Added get() and set() methods to Database class")
PYEOF

# ============================================================
# Verification
# ============================================================
echo ""
echo "🔍 Verification..."

echo "  Testing app import..."
if "${PYCMD[@]}" -c "from app import create_app; print('  ✔ App imports successfully')" 2>&1; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ Missing methods added successfully"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "🚀 Next: python main.py"
else
    echo ""
    echo "❌ ERROR: App import still fails"
    echo "   Please check the error message above"
    exit 1
fi