#!/bin/sh
# ============================================================================
# 66. update_scripts/66_fix_db_read_tables.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ (Вариант B — архитектурно правильный):
#   Переводит CameraService на чтение камер и наборов из нормальных таблиц
#   БД (cameras, sets, set_cameras) вместо таблицы settings.
#
# КОМЕНЬ ПРОБЛЕМЫ:
#   Скрипт инициализации пишет камеры в таблицу `cameras`, а CameraService
#   читал их через db.get("cameras") из таблицы `settings`. В итоге камер
#   было 0, и воркеры не стартовали (чёрный экран).
#
# ИДЕМПОТЕНТНОСТЬ:
#   Повторный запуск безопасен. Если изменения уже применены — скрипт их
#   не дублирует.
#
# ЗАПУСК:
#   ./66_fix_db_read_tables.sh
#
# ПОСЛЕ ЗАПУСКА:
#   Перезапустите сервер:  python main.py
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "66: Перевод CameraService на чтение из таблиц БД (Вариант B)"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

cd "$PROJECT_ROOT"

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
    echo "ОШИБКА: не найден интерпретатор Python" >&2
    exit 1
fi
echo "Python: $PYTHON_CMD"

DB_FILE="app/database.py"
CS_FILE="app/services/camera_service.py"

# --- Проверяем наличие файлов ---
for f in "$DB_FILE" "$CS_FILE"; do
    if [ ! -f "$f" ]; then
        echo "ОШИБКА: не найден файл $f" >&2
        exit 1
    fi
done

# ============================================================================
# ШАГ 1: Резервные копии
# ============================================================================
echo ""
echo "--- ШАГ 1: Резервные копии ---"
cp "$DB_FILE" "$DB_FILE.bak-66"
cp "$CS_FILE" "$CS_FILE.bak-66"
echo "  [BAK] $DB_FILE.bak-66"
echo "  [BAK] $CS_FILE.bak-66"

# ============================================================================
# ШАГ 2: Добавляем методы записи в database.py
# ============================================================================
echo ""
echo "--- ШАГ 2: Методы записи в database.py ---"

"$PYTHON_CMD" - "$DB_FILE" << 'PYEOF'
import sys
from pathlib import Path

db_file = Path(sys.argv[1])
content = db_file.read_text(encoding="utf-8")

# Если методы уже добавлены - пропускаем (идемпотентность)
if "def save_cameras_list(self" in content and "def save_sets_data(self" in content:
    print("  [OK] Методы записи уже есть в database.py")
    raise SystemExit(0)

methods = '''
    def save_cameras_list(self, cameras):
        """Сохранить список камер в таблицу cameras (полная замена)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cameras")
        for cam in cameras:
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
        conn.commit()
        conn.close()

    def save_sets_data(self, sets_data):
        """Сохранить наборы в таблицы sets и set_cameras (полная замена)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        default_set = sets_data.get('default_set', '')
        sets_dict = sets_data.get('sets', {})
        cursor.execute("DELETE FROM set_cameras")
        cursor.execute("DELETE FROM sets")
        for set_id, set_info in sets_dict.items():
            if not isinstance(set_info, dict):
                continue
            is_default = 1 if set_id == default_set else 0
            cursor.execute("""
                INSERT OR REPLACE INTO sets
                (id, name, grid_columns, grid_rows, is_default)
                VALUES (?, ?, ?, ?, ?)
            """, (
                set_id,
                set_info.get('name', set_id),
                set_info.get('max_columns', set_info.get('grid_columns', 4)),
                set_info.get('max_rows', set_info.get('grid_rows', 3)),
                is_default
            ))
            camera_ids = set_info.get('camera_ids', set_info.get('cameras', []))
            for cam_id in camera_ids:
                cursor.execute("""
                    INSERT OR REPLACE INTO set_cameras (set_id, camera_id)
                    VALUES (?, ?)
                """, (set_id, cam_id))
        conn.commit()
        conn.close()

'''

# Вставляем методы перед строкой создания глобального экземпляра
marker = "# Global database instance"
if marker in content:
    content = content.replace(marker, methods + marker)
else:
    # Альтернативный маркер - строка "db = Database()"
    alt_marker = "db = Database()"
    if alt_marker in content:
        content = content.replace(alt_marker, methods + "\n" + alt_marker)
    else:
        # Если маркеров нет - добавляем в конец
        content += methods

db_file.write_text(content, encoding="utf-8")
print("  [FIXED] Добавлены методы save_cameras_list() и save_sets_data()")
PYEOF

# ============================================================================
# ШАГ 3: Переводим чтение в camera_service.py на таблицы
# ============================================================================
echo ""
echo "--- ШАГ 3: Чтение камер и наборов из таблиц ---"

"$PYTHON_CMD" - "$CS_FILE" << 'PYEOF'
import sys
from pathlib import Path

cs_file = Path(sys.argv[1])
content = cs_file.read_text(encoding="utf-8")
changed = []

lines = content.split("\n")
new_lines = []
cameras_fixed = False
sets_fixed = False

for line in lines:
    # --- Правка чтения камер ---
    if ("raw_cameras" in line and "db.get(self.CAMERAS_KEY" in line
            and "db.get_all_cameras()" not in line):
        indent = len(line) - len(line.lstrip())
        new_lines.append(" " * indent + "raw_cameras = db.get_all_cameras() or []")
        cameras_fixed = True
        continue

    # --- Правка чтения наборов ---
    if ("raw_sets" in line and "db.get(self.SETS_KEY" in line
            and "db.get_all_sets()" not in line):
        indent = len(line) - len(line.lstrip())
        pad = " " * indent
        new_lines.append(pad + 'raw_sets = db.get_all_sets() or {"default_set": "", "sets": {}}')
        # Блок адаптации ключей из БД к модели Set
        new_lines.append(pad + "# [PATCH-66-B] Адаптация ключей БД к модели Set")
        new_lines.append(pad + 'for _sid, _sdata in raw_sets.get("sets", {}).items():')
        new_lines.append(pad + "    if isinstance(_sdata, dict):")
        new_lines.append(pad + '        if "grid_columns" in _sdata:')
        new_lines.append(pad + '            _sdata["max_columns"] = _sdata.pop("grid_columns")')
        new_lines.append(pad + '        if "grid_rows" in _sdata:')
        new_lines.append(pad + '            _sdata["max_rows"] = _sdata.pop("grid_rows")')
        new_lines.append(pad + '        if "cameras" in _sdata:')
        new_lines.append(pad + '            _sdata["camera_ids"] = _sdata.pop("cameras")')
        sets_fixed = True
        continue

    new_lines.append(line)

content = "\n".join(new_lines)

if cameras_fixed:
    changed.append("чтение камер: db.get_all_cameras()")
else:
    print("  [OK] Чтение камер уже использует таблицы")

if sets_fixed:
    changed.append("чтение наборов: db.get_all_sets() + адаптация ключей")
else:
    print("  [OK] Чтение наборов уже использует таблицы")

if changed:
    cs_file.write_text(content, encoding="utf-8")
    for c in changed:
        print(f"  [FIXED] {c}")
PYEOF

# ============================================================================
# ШАГ 4: Переводим запись в camera_service.py на таблицы
# ============================================================================
echo ""
echo "--- ШАГ 4: Запись камер и наборов в таблицы ---"

"$PYTHON_CMD" - "$CS_FILE" << 'PYEOF'
import sys
from pathlib import Path

cs_file = Path(sys.argv[1])
content = cs_file.read_text(encoding="utf-8")
changed = []

# Заменяем вызовы записи:
#   db.save(self.CAMERAS_KEY, ...)  ->  db.save_cameras_list(...)
#   db.save(self.SETS_KEY, ...)     ->  db.save_sets_data(...)
if "db.save(self.CAMERAS_KEY," in content:
    content = content.replace("db.save(self.CAMERAS_KEY,", "db.save_cameras_list(")
    changed.append("запись камер: db.save_cameras_list()")

if "db.save(self.SETS_KEY," in content:
    content = content.replace("db.save(self.SETS_KEY,", "db.save_sets_data(")
    changed.append("запись наборов: db.save_sets_data()")

if changed:
    cs_file.write_text(content, encoding="utf-8")
    for c in changed:
        print(f"  [FIXED] {c}")
else:
    print("  [OK] Запись уже использует таблицы")
PYEOF

# ============================================================================
# ШАГ 5: Проверка
# ============================================================================
echo ""
echo "--- ШАГ 5: Проверка ---"

"$PYTHON_CMD" << 'PYEOF'
import sys
try:
    from app.database import db
    from app.services.camera_service import camera_service

    cams = camera_service.all_cameras()
    enabled = camera_service.enabled_cameras()
    print(f"  Всего камер загружено: {len(cams)}")
    print(f"  Включено (будут запущены воркеры): {len(enabled)}")

    if len(cams) > 0:
        print("  [OK] Камеры загружаются из БД - воркеры должны стартовать")
    else:
        print("  [WARN] Камер всё ещё 0. Проверьте содержимое таблицы 'cameras' и файла data/cameras.json")
except Exception as e:
    print(f"  [FAIL] Ошибка при проверке: {e}")
    sys.exit(1)
PYEOF

echo ""
echo "============================================================================"
echo "Готово. Резервные копии: *.bak-66"
echo "Следующий шаг: перезапустите сервер  ->  python main.py"
echo "В логе должны появиться строки вида:  🚀 Запущен воркер: <камера>_main"
echo "============================================================================"