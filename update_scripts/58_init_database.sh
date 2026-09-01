#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — script 58: INITIALIZE DATABASE FROM JSON
#  ------------------------------------------------------------
#  What this script does:
#    1. Removes existing database file (if any)
#    2. Creates database/ folder
#    3. Initializes gryphone-vision.db from JSON files in data/
#    4. Verifies the database contains correct data
#
#  RUN:   bash update_scripts/58_init_database.sh
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
# Step 1: Check JSON files exist
# ============================================================
echo ""
echo "🔧 Checking JSON data files..."

for json_file in cameras.json sets.json config.json; do
    if [ -f "data/$json_file" ]; then
        echo "  ✔ data/$json_file exists"
    else
        echo "  ⚠️  WARNING: data/$json_file not found"
    fi
done

# ============================================================
# Step 2: Remove existing database
# ============================================================
echo ""
echo "🔧 Removing existing database..."

if [ -f "database/gryphone-vision.db" ]; then
    rm -f "database/gryphone-vision.db"
    echo "  ✔ Removed: database/gryphone-vision.db"
else
    echo "  ℹ️  No existing database to remove"
fi

mkdir -p database
echo "  ✔ database/ directory ready"

# ============================================================
# Step 3: Initialize database from JSON
# ============================================================
echo ""
echo "🔧 Initializing database from JSON files..."

"${PYCMD[@]}" << 'PYEOF'
import json
import sqlite3
from pathlib import Path

DATA_DIR = Path("data")
DB_PATH = Path("database/gryphone-vision.db")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# Create tables
cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS cameras (
        id TEXT PRIMARY KEY,
        name TEXT,
        main_url TEXT,
        sub_url TEXT,
        enabled INTEGER DEFAULT 1,
        comment TEXT,
        audio INTEGER DEFAULT 1,
        location TEXT
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS sets (
        id TEXT PRIMARY KEY,
        name TEXT,
        grid_columns INTEGER DEFAULT 4,
        grid_rows INTEGER DEFAULT 3,
        is_default INTEGER DEFAULT 0
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS set_cameras (
        set_id TEXT,
        camera_id TEXT,
        PRIMARY KEY (set_id, camera_id),
        FOREIGN KEY (set_id) REFERENCES sets(id),
        FOREIGN KEY (camera_id) REFERENCES cameras(id)
    )
""")

# Load cameras
cameras_file = DATA_DIR / 'cameras.json'
if cameras_file.exists():
    with open(cameras_file, 'r', encoding='utf-8') as f:
        cameras_data = json.load(f)

    if isinstance(cameras_data, list):
        for cam in cameras_data:
            cursor.execute("""
                INSERT OR REPLACE INTO cameras
                (id, name, main_url, sub_url, enabled, comment, audio, location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cam.get('id', ''),
                cam.get('name', ''),
                cam.get('main_url', ''),
                cam.get('sub_url', ''),
                1 if cam.get('enabled', True) else 0,
                cam.get('comment', ''),
                1 if cam.get('audio', True) else 0,
                cam.get('location', '')
            ))
        print(f"  ✔ Loaded {len(cameras_data)} cameras")

# Load sets
sets_file = DATA_DIR / 'sets.json'
if sets_file.exists():
    with open(sets_file, 'r', encoding='utf-8') as f:
        sets_data = json.load(f)

    default_set = sets_data.get('default_set', '')
    sets_dict = sets_data.get('sets', {})

    for set_id, set_info in sets_dict.items():
        is_default = 1 if set_id == default_set else 0
        cursor.execute("""
            INSERT OR REPLACE INTO sets
            (id, name, grid_columns, grid_rows, is_default)
            VALUES (?, ?, ?, ?, ?)
        """, (
            set_id,
            set_info.get('name', set_id),
            set_info.get('grid_columns', 4),
            set_info.get('grid_rows', 3),
            is_default
        ))

        camera_ids = set_info.get('cameras', [])
        for cam_id in camera_ids:
            cursor.execute("""
                INSERT OR REPLACE INTO set_cameras (set_id, camera_id)
                VALUES (?, ?)
            """, (set_id, cam_id))

    print(f"  ✔ Loaded {len(sets_dict)} sets")

# Load config
config_file = DATA_DIR / 'config.json'
if config_file.exists():
    with open(config_file, 'r', encoding='utf-8') as f:
        config_data = json.load(f)

    for key, value in config_data.items():
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        """, (key, str(value) if not isinstance(value, str) else value))

    if config_data:
        print(f"  ✔ Loaded {len(config_data)} config entries")

conn.commit()

# Verify
cursor.execute("SELECT COUNT(*) FROM cameras")
camera_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM sets")
set_count = cursor.fetchone()[0]
conn.close()

print(f"\n  Database created: {DB_PATH}")
print(f"  Total cameras: {camera_count}")
print(f"  Total sets: {set_count}")
PYEOF

# ============================================================
# Step 4: Test app import
# ============================================================
echo ""
echo "🔍 Testing app import..."

if "${PYCMD[@]}" -c "from app import create_app; print('  ✔ App imports successfully')" 2>&1; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ Database initialized from JSON files"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "🚀 Next: python main.py"
else
    echo ""
    echo "❌ ERROR: App import still fails"
    exit 1
fi