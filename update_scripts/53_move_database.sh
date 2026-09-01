#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — script 53: MOVE DATABASE TO database/
#  ------------------------------------------------------------
#  What this script does:
#    1. Creates database/ folder in project root
#    2. Moves rtsp_viewer.db → database/gryphone-vision.db
#    3. Updates all files that reference the old database path
#    4. Updates .gitignore to exclude database/*.db
#    5. Verifies no references to the old path remain
#
#  RUN:   bash update_scripts/53_move_database.sh
#  THEN:  python main.py
# ============================================================
set -euo pipefail

# Determine script location and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/../main.py" ]; then
    PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    PROJECT_DIR="$SCRIPT_DIR"
fi

echo "📁 Project root: $PROJECT_DIR"
cd "$PROJECT_DIR"

# ============================================================
# Python detection (avoid Windows Store redirect)
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
    echo "❌ ERROR: no Python interpreter found."
    exit 1
fi

read -ra PYCMD <<< "$PYTHON_CMD"
echo "✅ Python: ${PYCMD[*]}"

# ============================================================
# Step 1: Create database/ folder
# ============================================================
echo ""
echo "🔧 Creating database/ folder..."
mkdir -p database
echo "  ✔ database/ created"

# ============================================================
# Step 2: Move and rename database file
# ============================================================
echo ""
echo "🔧 Moving database file..."

OLD_DB="rtsp_viewer.db"
NEW_DB="database/gryphone-vision.db"

if [ -f "$OLD_DB" ]; then
    mv "$OLD_DB" "$NEW_DB"
    echo "  ✔ Moved: $OLD_DB → $NEW_DB"
elif [ -f "$NEW_DB" ]; then
    echo "  ℹ️  Already moved: $NEW_DB exists"
else
    echo "  ⚠️  WARNING: $OLD_DB not found in project root"
    echo "     If you have a backup, place it in database/gryphone-vision.db manually"
fi

# ============================================================
# Step 3: Update database paths in all project files
# ============================================================
echo ""
echo "🔧 Updating database paths in project files..."

"${PYCMD[@]}" << 'PYEOF'
from pathlib import Path
import re

# New database path relative to project root
NEW_DB_RELATIVE = "database/gryphone-vision.db"

# Files that likely contain database path references
target_files = [
    "app/__init__.py",
    "app/config.py",
    "app/database.py",
    "app/models.py",
    "app/routes/api.py",
    "app/routes/dashboard.py",
    "app/routes/excel_import.py",
    "app/routes/hls.py",
    "app/routes/stream.py",
    "app/services/camera_service.py",
    "app/services/config_sync.py",
    "app/services/stream_manager.py",
    "app/workers/cleanup_worker.py",
    "app/workers/hls_worker.py",
    "app/cluster/registry.py",
    "app/cluster/scheduler.py",
    "app/core/node.py",
    "utils/migrate_add_fields.py",
    "utils/replace_stream_names.py",
    "import_from_excel.py",
    "main.py",
    "fix_dashboard_conflict.py",
    "replace_stream_names.py",
]

updated_count = 0
skipped_count = 0

for file_path in target_files:
    path = Path(file_path)
    if not path.exists():
        skipped_count += 1
        continue

    content = path.read_text(encoding="utf-8")
    original = content

    # Pattern 1: sqlite3.connect('rtsp_viewer.db') or "rtsp_viewer.db"
    content = re.sub(
        r"sqlite3\.connect\(['\"]rtsp_viewer\.db['\"]\)",
        "sqlite3.connect(str(DATABASE_PATH))",
        content
    )

    # Pattern 2: DATABASE_PATH = 'rtsp_viewer.db' or "rtsp_viewer.db"
    content = re.sub(
        r"DATABASE_PATH\s*=\s*['\"]rtsp_viewer\.db['\"]",
        f"DATABASE_PATH = BASE_DIR / '{NEW_DB_RELATIVE}'",
        content
    )

    # Pattern 3: Any remaining string literal 'rtsp_viewer.db' or "rtsp_viewer.db"
    content = re.sub(
        r"['\"]rtsp_viewer\.db['\"]",
        "str(DATABASE_PATH)",
        content
    )

    # Ensure pathlib import exists
    if "from pathlib import Path" not in content and "Path(__file__)" in content:
        # Add import at the top after existing imports
        lines = content.split('\n')
        insert_index = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                insert_index = i + 1
        lines.insert(insert_index, 'from pathlib import Path')
        content = '\n'.join(lines)

    # Ensure BASE_DIR is defined if DATABASE_PATH uses it
    if "DATABASE_PATH = BASE_DIR" in content and "BASE_DIR" not in content.split("DATABASE_PATH")[0]:
        lines = content.split('\n')
        insert_index = 0
        for i, line in enumerate(lines):
            if 'from pathlib import Path' in line:
                insert_index = i + 1
                break
        lines.insert(insert_index, "BASE_DIR = Path(__file__).resolve().parent")
        content = '\n'.join(lines)

    if content != original:
        path.write_text(content, encoding="utf-8")
        updated_count += 1
        print(f"  ✔ Updated: {file_path}")
    else:
        skipped_count += 1

print(f"\n  Summary: {updated_count} files updated, {skipped_count} files skipped")
PYEOF

# ============================================================
# Step 4: Update .gitignore
# ============================================================
echo ""
echo "🔧 Updating .gitignore..."

if [ -f ".gitignore" ]; then
    if ! grep -q "database/\*\.db" ".gitignore" 2>/dev/null; then
        echo "" >> ".gitignore"
        echo "# Database files (should not be committed)" >> ".gitignore"
        echo "database/*.db" >> ".gitignore"
        echo "  ✔ Added database/*.db to .gitignore"
    else
        echo "  ℹ️  database/*.db already in .gitignore"
    fi
else
    echo "# Database files (should not be committed)" > ".gitignore"
    echo "database/*.db" >> ".gitignore"
    echo "  ✔ Created .gitignore with database/*.db"
fi

# ============================================================
# Step 5: Verification
# ============================================================
echo ""
echo "🔍 Verification..."

# Check if database file exists in new location
if [ -f "$PROJECT_DIR/database/gryphone-vision.db" ]; then
    echo "  ✔ Database file: database/gryphone-vision.db"
else
    echo "  ❌ ERROR: database/gryphone-vision.db not found"
    exit 1
fi

# Check for remaining references to old database name
echo ""
echo "🔍 Searching for remaining references to 'rtsp_viewer.db'..."
REMAINING=$(grep -r "rtsp_viewer\.db" --include="*.py" --include="*.js" --include="*.jsx" --include="*.sh" . 2>/dev/null | grep -v "update_scripts/" | grep -v ".git/" || true)

if [ -n "$REMAINING" ]; then
    echo ""
    echo "  ⚠️  WARNING: Found references to old database name:"
    echo "$REMAINING" | head -20
    echo ""
    echo "  Please update these files manually or report them for a follow-up fix."
else
    echo "  ✔ No remaining references to rtsp_viewer.db found"
fi

# ============================================================
# Summary
# ============================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Database migration complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 What was done:"
echo "  • Created database/ folder"
echo "  • Moved rtsp_viewer.db → database/gryphone-vision.db"
echo "  • Updated DATABASE_PATH in project files"
echo "  • Updated .gitignore"
echo ""
echo "🚀 Next: python main.py"
echo "   Open: http://localhost:5000"