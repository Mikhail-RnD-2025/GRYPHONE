#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — script 56: UPDATE PATHS FOR data/ FOLDER
#  ------------------------------------------------------------
#  What this script does:
#    1. Ensures data/ folder exists and contains the JSON files.
#    2. Updates all Python files to use DATA_DIR for JSON files.
#    3. Adds DATA_DIR definition to files that need it.
#
#  RUN:   bash update_scripts/56_move_data_files.sh
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
# Step 1: Ensure data/ folder and files are in place
# ============================================================
echo ""
echo "🔧 Checking data/ folder..."
mkdir -p data

for file in cameras.json sets.json config.json; do
    if [ -f "data/$file" ]; then
        echo "  ✔ data/$file exists"
    elif [ -f "$file" ]; then
        echo "  🔄 Moving $file to data/"
        mv "$file" "data/$file"
    else
        echo "  ⚠️  WARNING: $file not found in root or data/"
    fi
done

# ============================================================
# Step 2: Update Python files to use DATA_DIR
# ============================================================
echo ""
echo "🔧 Updating file paths in Python scripts..."

"${PYCMD[@]}" << 'PYEOF'
from pathlib import Path
import re

target_files = [
    "app/__init__.py",
    "app/config.py",
    "app/database.py",
    "app/services/camera_service.py",
    "app/services/config_sync.py",
    "utils/migrate_add_fields.py",
    "utils/replace_stream_names.py",
    "import_from_excel.py",
    "main.py",
]

json_files = ["cameras.json", "sets.json", "config.json"]
updated_count = 0

for file_path in target_files:
    path = Path(file_path)
    if not path.exists():
        continue

    content = path.read_text(encoding="utf-8")
    original = content
    modified = False

    # Replace direct string references to JSON files
    for jf in json_files:
        # Pattern: 'cameras.json' or "cameras.json"
        pattern = re.compile(rf"(['\"])({jf})(\1)")
        if pattern.search(content):
            content = pattern.sub(r"DATA_DIR / '\2'", content)
            modified = True

    if modified:
        # Ensure pathlib is imported
        if "from pathlib import Path" not in content:
            lines = content.split('\n')
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    insert_idx = i + 1
            lines.insert(insert_idx, 'from pathlib import Path')
            content = '\n'.join(lines)

        # Ensure DATA_DIR is defined (using BASE_DIR if it exists, else Path(__file__).resolve().parent)
        if "DATA_DIR = " not in content:
            lines = content.split('\n')
            insert_idx = 0
            for i, line in enumerate(lines):
                if 'from pathlib import Path' in line:
                    insert_idx = i + 1
                    break

            # Check if BASE_DIR is already defined
            if "BASE_DIR = " in content:
                data_dir_def = "DATA_DIR = BASE_DIR / 'data'"
            else:
                data_dir_def = "BASE_DIR = Path(__file__).resolve().parent\nDATA_DIR = BASE_DIR / 'data'"

            lines.insert(insert_idx, data_dir_def)
            content = '\n'.join(lines)

        path.write_text(content, encoding="utf-8")
        updated_count += 1
        print(f"  ✔ Updated: {file_path}")

print(f"\n  Summary: {updated_count} files updated with DATA_DIR paths")
PYEOF

# ============================================================
# Step 3: Update .gitignore (optional but recommended)
# ============================================================
echo ""
echo "🔧 Checking .gitignore..."

if [ -f ".gitignore" ]; then
    if ! grep -q "^data/config\.json$" ".gitignore" 2>/dev/null; then
        echo "" >> ".gitignore"
        echo "# Local configuration (optional: keep if you want to track default configs)" >> ".gitignore"
        echo "# data/config.json" >> ".gitignore"
        echo "  ℹ️  Added note about data/config.json to .gitignore (commented out by default)"
    fi
fi

# ============================================================
# Step 4: Verification
# ============================================================
echo ""
echo "🔍 Verification..."

all_good=true
for jf in cameras.json sets.json config.json; do
    if [ -f "data/$jf" ]; then
        echo "  ✔ data/$jf is in place"
    else
        echo "  ❌ ERROR: data/$jf is missing"
        all_good=false
    fi
done

if [ "$all_good" = true ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ Data files successfully migrated to data/"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📋 What was done:"
    echo "  • Ensured cameras.json, sets.json, config.json are in data/"
    echo "  • Updated Python scripts to use DATA_DIR"
    echo ""
    echo "🚀 Next: python main.py"
else
    echo ""
    echo "❌ Verification failed. Please check missing files."
    exit  each 1
fi