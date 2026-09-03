#!/bin/sh
# ============================================================================
# 75. update_scripts/75_schema_as_source_of_truth.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Делает database/sql/schema.sql единственным источником истины для
#   структуры БД. Метод _create_tables() в app/database.py теперь читает
#   схему из файла и применяет её через executescript().
#
# ЗАВИСИМОСТЬ:
#   Требуется наличие database/sql/schema.sql (создаётся скриптом 74).
#
# ПРЕИМУЩЕСТВА:
#   • Схема БД существует в одном месте (SQL-файл)
#   • Правки схемы не требуют изменения Python-кода
#   • Схему можно версионировать и применять к чистой БД
#   • PRAGMA foreign_keys включается на каждом соединении
#
# ИДЕМПОТЕНТНОСТЬ: повторный запуск безопасен.
# ЗАПУСК: ./75_schema_as_source_of_truth.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "75: schema.sql как единственный источник истины для структуры БД"
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
    echo "ОШИБКА: не найден Python" >&2; exit 1
fi
echo "Python: $PYTHON_CMD"

DB_PY="app/database.py"
SCHEMA_FILE="database/sql/schema.sql"

# ============================================================================
# ШАГ 1: Проверяем зависимости
# ============================================================================
echo ""
echo "--- ШАГ 1: Проверка зависимостей ---"

if [ ! -f "$DB_PY" ]; then
    echo "ОШИБКА: не найден $DB_PY" >&2; exit 1
fi
echo "  [OK] $DB_PY найден"

if [ ! -f "$SCHEMA_FILE" ]; then
    echo "ОШИБКА: не найден $SCHEMA_FILE" >&2
    echo "  Сначала запустите: ./74_create_schema_sql.sh" >&2
    exit 1
fi
echo "  [OK] $SCHEMA_FILE найден"

# Проверяем синтаксис database.py перед правкой
if ! "$PYTHON_CMD" -c "import ast; ast.parse(open('$DB_PY', encoding='utf-8').read())" 2>/dev/null; then
    echo "  [WARN] $DB_PY повреждён, восстанавливаю из бэкапа"
    for bak in "$DB_PY.bak-75" "$DB_PY.bak-74" "$DB_PY.bak-73" "$DB_PY.bak-70" "$DB_PY.bak-69"; do
        if [ -f "$bak" ]; then
            cp "$bak" "$DB_PY"
            echo "  [RESTORE] из $bak"
            break
        fi
    done
fi

# ============================================================================
# ШАГ 2: Резервная копия
# ============================================================================
echo ""
echo "--- ШАГ 2: Резервная копия ---"
cp "$DB_PY" "$DB_PY.bak-75"
echo "  [BAK] $DB_PY.bak-75"

# ============================================================================
# ШАГ 3: Замена _create_tables() на версию, читающую из файла
# ----------------------------------------------------------------------------
# Пути передаются в Python как аргументы командной строки (надёжнее, чем
# рассчитывать на переменные окружения или глобальные имена).
# ============================================================================
echo ""
echo "--- ШАГ 3: Замена _create_tables() ---"

"$PYTHON_CMD" - "$DB_PY" "$SCHEMA_FILE" << 'PYEOF'
import sys
from pathlib import Path

# Пути получаем из аргументов командной строки
db_file = Path(sys.argv[1])
schema_file = sys.argv[2]  # относительный путь, используется в сообщении

content = db_file.read_text(encoding="utf-8")

# Идемпотентность: если метод уже читает из файла — выходим
if "schema.sql" in content and "executescript" in content:
    print("  [OK] _create_tables() уже читает из schema.sql — ничего не делаем")
    sys.exit(0)

lines = content.split("\n")

# Находим начало метода _create_tables
start = None
start_indent = ""
for i, line in enumerate(lines):
    if "def _create_tables(self):" in line:
        start = i
        start_indent = line[:len(line) - len(line.lstrip())]
        break

if start is None:
    print("  [FAIL] Метод _create_tables() не найден")
    sys.exit(1)

# Находим конец метода: следующая строка с отступом <= отступа def,
# которая является определением (def, class, декоратор)
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

# Новый метод, читающий схему из файла.
# Отступ (4 пробела) берётся из исходного метода, чтобы сохранить структуру.
pad = start_indent
body_pad = start_indent + "    "
new_method = (
    f"{pad}def _create_tables(self):\n"
    f"{body_pad}\"\"\"Create database tables if they don't exist.\n"
    f"{body_pad}\n"
    f"{body_pad}Схема читается из database/sql/schema.sql и применяется через\n"
    f"{body_pad}executescript(). Это делает schema.sql единственным источником\n"
    f"{body_pad}истины для структуры БД.\n"
    f"{body_pad}\"\"\"\n"
    f"{body_pad}schema_path = BASE_DIR / \"database\" / \"sql\" / \"schema.sql\"\n"
    f"{body_pad}if not schema_path.is_file():\n"
    f"{body_pad}    raise FileNotFoundError(\n"
    f"{body_pad}        f\"Файл схемы БД не найден: {{schema_path}}. \"\n"
    f"{body_pad}        f\"Запустите update_scripts/74_create_schema_sql.sh\"\n"
    f"{body_pad}    )\n"
    f"{body_pad}schema_sql = schema_path.read_text(encoding=\"utf-8\")\n"
    f"{body_pad}conn = sqlite3.connect(self.db_path)\n"
    f"{body_pad}try:\n"
    f"{body_pad}    # Включаем внешние ключи (в SQLite по умолчанию выключены).\n"
    f"{body_pad}    # PRAGMA должна быть выполнена на каждом соединении отдельно.\n"
    f"{body_pad}    conn.execute(\"PRAGMA foreign_keys = ON\")\n"
    f"{body_pad}    # Применяем всю схему одним скриптом (поддерживает несколько\n"
    f"{body_pad}    # CREATE TABLE, PRAGMA, индексы и комментарии).\n"
    f"{body_pad}    conn.executescript(schema_sql)\n"
    f"{body_pad}    conn.commit()\n"
    f"{body_pad}finally:\n"
    f"{body_pad}    conn.close()\n"
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
print("  [FIXED] _create_tables() теперь читает из " + schema_file)
print(f"          Удалено строк старого метода: {end - start}")
PYEOF

# ============================================================================
# ШАГ 4: Функциональный тест
# ============================================================================
echo ""
echo "--- ШАГ 4: Функциональный тест ---"

"$PYTHON_CMD" << 'PYEOF'
import sys
import sqlite3
import tempfile
from pathlib import Path

# Перезагружаем модули, чтобы подхватить изменения
for mod in list(sys.modules.keys()):
    if mod.startswith("app"):
        del sys.modules[mod]

try:
    # Создаём временную БД для теста
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        from app.database import Database
        test_db = Database(db_path=tmp_path)

        # Проверяем, что все таблицы созданы
        conn = sqlite3.connect(tmp_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
        conn.close()

        expected = ["cameras", "events", "set_cameras", "sets", "settings"]
        missing = [t for t in expected if t not in tables]

        print(f"  Созданные таблицы: {tables}")
        if missing:
            print(f"  [FAIL] Отсутствуют таблицы: {missing}")
            sys.exit(1)
        else:
            print("  [OK] Все ожидаемые таблицы созданы")

        # Проверяем индексы
        conn = sqlite3.connect(tmp_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%' ORDER BY name")
        indexes = [r[0] for r in cur.fetchall()]
        conn.close()
        print(f"  [OK] Индексов создано: {len(indexes)}")

        # Проверяем, что таблица events создана (заготовка)
        if "events" in tables:
            print("  [OK] Таблица events создана (заготовка для аналитики/PSIM)")

        print("")
        print("  ✅ schema.sql работает как единственный источник истины")

    finally:
        # Удаляем временную БД
        Path(tmp_path).unlink(missing_ok=True)

except Exception as e:
    print(f"  [FAIL] Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYEOF

echo ""
echo "============================================================================"
echo "Готово."
echo ""
echo "Теперь структура БД определяется только файлом:"
echo "  $SCHEMA_FILE"
echo ""
echo "Чтобы изменить схему:"
echo "  1. Отредактируйте $SCHEMA_FILE"
echo "  2. Удалите старую БД: rm database/gryphone-vision.db"
echo "  3. Перезапустите сервер: python main.py"
echo ""
echo "Резервная копия: $DB_PY.bak-75"
echo "============================================================================"