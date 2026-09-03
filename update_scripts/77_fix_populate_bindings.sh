#!/bin/sh
# ============================================================================
# 77. update_scripts/77_fix_populate_bindings.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Исправляет _populate_from_json() в app/database.py, чтобы он корректно
#   создавал привязки камер к наборам, учитывая только существующие камеры.
#
# ПРОБЛЕМА:
#   data/sets.json ссылается на камеры (403-*, 301A-*), которых нет в
#   data/cameras.json. FOREIGN KEY в set_cameras отклоняет несуществующие
#   ID, и привязки остаются пустыми.
#
# РЕШЕНИЕ:
#   1. Привязывать только те камеры, которые реально существуют в БД
#   2. Если привязок нет — автоматически привязать все включённые камеры
#      к набору по умолчанию (is_default=1)
#
# ИДЕМПОТЕНТНОСТЬ: повторный запуск безопасен.
# ЗАПУСК: ./77_fix_populate_bindings.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "77: Исправление привязок камер к наборам в _populate_from_json()"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

cd "$PROJECT_ROOT"

DB_PY="app/database.py"

# --- Детект Python ---
_detect_python() {
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
    echo "ОШИБКА: не найден Python" >&2; exit 1
fi
echo "Python: $PYTHON_CMD"

if [ ! -f "$DB_PY" ]; then
    echo "ОШИБКА: не найден $DB_PY" >&2; exit 1
fi

# ============================================================================
# ШАГ 1: Резервная копия
# ============================================================================
echo ""
echo "--- ШАГ 1: Резервная копия ---"
cp "$DB_PY" "$DB_PY.bak-77"
echo "  [BAK] $DB_PY.bak-77"

# ============================================================================
# ШАГ 2: Замена метода _populate_from_json()
# ============================================================================
echo ""
echo "--- ШАГ 2: Замена _populate_from_json() ---"

"$PYTHON_CMD" - "$DB_PY" << 'PYEOF'
import sys
import re
from pathlib import Path

db_file = Path(sys.argv[1])
content = db_file.read_text(encoding="utf-8")

# Идемпотентность: если метод уже исправлен — выходим
if "# PATCH-77: Автоматическая привязка" in content:
    print("  [OK] _populate_from_json() уже исправлен — ничего не делаем")
    sys.exit(0)

lines = content.split("\n")

# Находим начало метода _populate_from_json
start = None
start_indent = ""
for i, line in enumerate(lines):
    if "def _populate_from_json(self):" in line:
        start = i
        start_indent = line[:len(line) - len(line.lstrip())]
        break

if start is None:
    print("  [FAIL] Метод _populate_from_json() не найден")
    sys.exit(1)

# Находим конец метода
end = None
for i in range(start + 1, len(lines)):
    line = lines[i]
    stripped = line.strip()
    if not stripped:
        continue
    current_indent = line[:len(line) - len(line.lstrip())]
    if len(current_indent) <= len(start_indent):
        if (stripped.startswith("def ") or
            stripped.startswith("class ") or
            stripped.startswith("@")):
            end = i
            break

if end is None:
    end = len(lines)

# Новый метод с исправленной логикой привязок
pad = start_indent
body_pad = start_indent + "    "
new_method = (
    f'{pad}def _populate_from_json(self):\n'
    f'{body_pad}"""Populate database tables from JSON files in data/ folder.\n'
    f'{body_pad}\n'
    f'{body_pad}Исправлено (PATCH-77): привязывает только существующие камеры.\n'
    f'{body_pad}Если привязок нет — автоматически привязывает все включённые камеры\n'
    f'{body_pad}к набору по умолчанию.\n'
    f'{body_pad}"""\n'
    f'{body_pad}conn = sqlite3.connect(self.db_path)\n'
    f'{body_pad}cursor = conn.cursor()\n'
    f'{body_pad}\n'
    f'{body_pad}# Load cameras.json\n'
    f'{body_pad}cameras_file = DATA_DIR / "cameras.json"\n'
    f'{body_pad}if cameras_file.exists():\n'
    f'{body_pad}    try:\n'
    f'{body_pad}        with open(cameras_file, "r", encoding="utf-8") as f:\n'
    f'{body_pad}            cameras_data = json.load(f)\n'
    f'{body_pad}        if isinstance(cameras_data, list):\n'
    f'{body_pad}            for cam in cameras_data:\n'
    f'{body_pad}                cursor.execute("""\n'
    f'{body_pad}                    INSERT OR REPLACE INTO cameras\n'
    f'{body_pad}                    (id, name, main_url, sub_url, enabled, comment, audio, location)\n'
    f'{body_pad}                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)\n'
    f'{body_pad}                """, (\n'
    f'{body_pad}                    cam.get("id", ""),\n'
    f'{body_pad}                    cam.get("name", ""),\n'
    f'{body_pad}                    cam.get("main_url", ""),\n'
    f'{body_pad}                    cam.get("sub_url", ""),\n'
    f'{body_pad}                    1 if cam.get("enabled", True) else 0,\n'
    f'{body_pad}                    cam.get("comment", ""),\n'
    f'{body_pad}                    1 if cam.get("audio", True) else 0,\n'
    f'{body_pad}                    cam.get("location", "")\n'
    f'{body_pad}                ))\n'
    f'{body_pad}            print(f" ✔ Loaded {{len(cameras_data)}} cameras from data/cameras.json")\n'
    f'{body_pad}    except (json.JSONDecodeError, IOError) as e:\n'
    f'{body_pad}        print(f" ⚠️ Error loading cameras.json: {{e}}")\n'
    f'{body_pad}else:\n'
    f'{body_pad}    print(f" ⚠️ cameras.json not found in data/")\n'
    f'{body_pad}\n'
    f'{body_pad}# Load sets.json\n'
    f'{body_pad}sets_file = DATA_DIR / "sets.json"\n'
    f'{body_pad}if sets_file.exists():\n'
    f'{body_pad}    try:\n'
    f'{body_pad}        with open(sets_file, "r", encoding="utf-8") as f:\n'
    f'{body_pad}            sets_data = json.load(f)\n'
    f'{body_pad}        default_set = sets_data.get("default_set", "")\n'
    f'{body_pad}        sets_dict = sets_data.get("sets", {{}})\n'
    f'{body_pad}        for set_id, set_info in sets_dict.items():\n'
    f'{body_pad}            is_default = 1 if set_id == default_set else 0\n'
    f'{body_pad}            cursor.execute("""\n'
    f'{body_pad}                INSERT OR REPLACE INTO sets\n'
    f'{body_pad}                (id, name, grid_columns, grid_rows, is_default)\n'
    f'{body_pad}                VALUES (?, ?, ?, ?, ?)\n'
    f'{body_pad}            """, (\n'
    f'{body_pad}                set_id,\n'
    f'{body_pad}                set_info.get("name", set_id),\n'
    f'{body_pad}                set_info.get("max_columns", set_info.get("grid_columns", 4)),\n'
    f'{body_pad}                set_info.get("max_rows", set_info.get("grid_rows", 3)),\n'
    f'{body_pad}                is_default\n'
    f'{body_pad}            ))\n'
    f'{body_pad}            # PATCH-77: привязываем только существующие камеры\n'
    f'{body_pad}            camera_ids = set_info.get("cameras", [])\n'
    f'{body_pad}            for cam_id in camera_ids:\n'
    f'{body_pad}                # Проверяем, существует ли камера в БД\n'
    f'{body_pad}                cursor.execute("SELECT id FROM cameras WHERE id = ?", (cam_id,))\n'
    f'{body_pad}                if cursor.fetchone():\n'
    f'{body_pad}                    cursor.execute("""\n'
    f'{body_pad}                        INSERT OR REPLACE INTO set_cameras (set_id, camera_id)\n'
    f'{body_pad}                        VALUES (?, ?)\n'
    f'{body_pad}                    """, (set_id, cam_id))\n'
    f'{body_pad}        print(f" ✔ Loaded {{len(sets_dict)}} sets from data/sets.json")\n'
    f'{body_pad}    except (json.JSONDecodeError, IOError) as e:\n'
    f'{body_pad}        print(f" ⚠️ Error loading sets.json: {{e}}")\n'
    f'{body_pad}else:\n'
    f'{body_pad}    print(f" ⚠️ sets.json not found in data/")\n'
    f'{body_pad}\n'
    f'{body_pad}conn.commit()\n'
    f'{body_pad}\n'
    f'{body_pad}# PATCH-77: Автоматическая привязка, если привязок нет\n'
    f'{body_pad}cursor.execute("SELECT COUNT(*) FROM set_cameras")\n'
    f'{body_pad}bindings_count = cursor.fetchone()[0]\n'
    f'{body_pad}if bindings_count == 0:\n'
    f'{body_pad}    print(" ⚠️ Привязок камер к наборам нет — создаю автоматически")\n'
    f'{body_pad}    # Находим набор по умолчанию\n'
    f'{body_pad}    cursor.execute("SELECT id FROM sets WHERE is_default = 1 LIMIT 1")\n'
    f'{body_pad}    default_set_row = cursor.fetchone()\n'
    f'{body_pad}    if not default_set_row:\n'
    f'{body_pad}        # Если нет набора по умолчанию, берём первый\n'
    f'{body_pad}        cursor.execute("SELECT id FROM sets LIMIT 1")\n'
    f'{body_pad}        default_set_row = cursor.fetchone()\n'
    f'{body_pad}    if default_set_row:\n'
    f'{body_pad}        default_set_id = default_set_row[0]\n'
    f'{body_pad}        # Получаем все включённые камеры\n'
    f'{body_pad}        cursor.execute("SELECT id FROM cameras WHERE enabled = 1")\n'
    f'{body_pad}        enabled_cameras = cursor.fetchall()\n'
    f'{body_pad}        for cam_row in enabled_cameras:\n'
    f'{body_pad}            cam_id = cam_row[0]\n'
    f'{body_pad}            cursor.execute("""\n'
    f'{body_pad}                INSERT OR IGNORE INTO set_cameras (set_id, camera_id)\n'
    f'{body_pad}                VALUES (?, ?)\n'
    f'{body_pad}            """, (default_set_id, cam_id))\n'
    f'{body_pad}        conn.commit()\n'
    f'{body_pad}        print(f" ✔ Привязано {{len(enabled_cameras)}} камер к набору {{default_set_id}}")\n'
    f'{body_pad}    else:\n'
    f'{body_pad}        print(" ⚠️ Нет наборов для автоматической привязки")\n'
    f'{body_pad}\n'
    f'{body_pad}conn.close()\n'
)

# Заменяем старый метод на новый
new_lines = lines[:start] + [new_method.rstrip("\n")] + lines[end:]
new_content = "\n".join(new_lines)

# Проверка синтаксиса ДО записи
try:
    compile(new_content, str(db_file), "exec")
except SyntaxError as e:
    print(f"  [FAIL] Синтаксическая ошибка после замены: {e}")
    sys.exit(1)

db_file.write_text(new_content, encoding="utf-8")
print(f"  [FIXED] _populate_from_json() исправлен (удалено {end - start} строк)")
print("  Добавлена автоматическая привязка включённых камер к набору по умолчанию")
PYEOF

# ============================================================================
# ШАГ 3: Проверка синтаксиса
# ============================================================================
echo ""
echo "--- ШАГ 3: Проверка синтаксиса ---"

"$PYTHON_CMD" -c "import ast; ast.parse(open('$DB_PY', encoding='utf-8').read())" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "  [OK] Синтаксис корректен"
else
    echo "  [FAIL] Синтаксическая ошибка, восстанавливаю из бэкапа"
    cp "$DB_PY.bak-77" "$DB_PY"
    exit 1
fi

# ============================================================================
# ШАГ 4: Функциональный тест (пересоздание БД)
# ============================================================================
echo ""
echo "--- ШАГ 4: Функциональный тест ---"

"$PYTHON_CMD" << 'PYEOF'
import sys
import sqlite3
from pathlib import Path

db_path = Path("database/gryphone-vision.db")

# Удаляем старую БД
if db_path.exists():
    db_path.unlink()
    print("  [OK] Старая БД удалена")

# Перезагружаем модули
for mod in list(sys.modules.keys()):
    if mod.startswith("app"):
        del sys.modules[mod]

try:
    from app.database import Database

    # Создаём новую БД (это вызовет _populate_from_json)
    test_db = Database(db_path=str(db_path))

    # Проверяем результат
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM cameras")
    cameras_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM sets")
    sets_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM set_cameras")
    bindings_count = cur.fetchone()[0]

    conn.close()

    print(f"  Камер в БД: {cameras_count}")
    print(f"  Наборов в БД: {sets_count}")
    print(f"  Привязок в БД: {bindings_count}")

    if bindings_count > 0:
        print("")
        print("  ✅ Автоматическая привязка работает!")
    else:
        print("")
        print("  [WARN] Привязок всё ещё нет")

except Exception as e:
    print(f"  [FAIL] Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYEOF

echo ""
echo "============================================================================"
echo "Готово. Резервная копия: $DB_PY.bak-77"
echo ""
echo "Теперь при первом запуске (или после удаления БД) автоматически создаются"
echo "привязки включённых камер к набору по умолчанию."
echo ""
echo "Перезапустите сервер: python main.py"
echo "============================================================================"