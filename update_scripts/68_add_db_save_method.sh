#!/bin/sh
# ============================================================================
# 68. update_scripts/68_add_db_save_method.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Добавляет метод save() в класс Database как алиас для set().
#   Это нужно для работы ConfigManager из патча 67.
#
# ПРОБЛЕМА:
#   Новый ConfigManager вызывает db.save("config", {...}), но в database.py
#   есть только db.set() и db.set_setting(). Ошибка:
#     AttributeError: 'Database' object has no attribute 'save'
#
# ПОДХОД:
#   Метод вставляется ПЕРЕД методом set() с фиксированными отступами
#   (4 пробела), что исключает ошибку отступов.
#
# ИДЕМПОТЕНТНОСТЬ:
#   Повторный запуск безопасен. Если метод уже есть — ничего не делает.
#
# ЗАПУСК:
#   ./68_add_db_save_method.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "68: Добавление метода save() в database.py"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

cd "$PROJECT_ROOT"

DB_FILE="app/database.py"

# --- Проверяем наличие файла ---
if [ ! -f "$DB_FILE" ]; then
    echo "ОШИБКА: не найден файл $DB_FILE" >&2
    exit 1
fi

# --- Восстанавливаем из резервной копии патча 67, если файл повреждён ---
# (защита от IndentationError, возникшего после неудачной правки)
if ! python -c "import ast; ast.parse(open('$DB_FILE', encoding='utf-8').read())" 2>/dev/null; then
    echo "  [WARN] Файл $DB_FILE повреждён (ошибка синтаксиса)"
    if [ -f "$DB_FILE.bak-67" ]; then
        echo "  [RESTORE] Восстанавливаю из $DB_FILE.bak-67"
        cp "$DB_FILE.bak-67" "$DB_FILE"
    elif [ -f "$DB_FILE.bak-68" ]; then
        echo "  [RESTORE] Восстанавливаю из $DB_FILE.bak-68"
        cp "$DB_FILE.bak-68" "$DB_FILE"
    else
        echo "  [FAIL] Резервная копия не найдена. Исправьте файл вручную." >&2
        exit 1
    fi
fi

# --- Резервная копия ---
echo ""
echo "--- Резервная копия ---"
cp "$DB_FILE" "$DB_FILE.bak-68"
echo "  [BAK] $DB_FILE.bak-68"

# --- Добавляем метод save() перед методом set() ---
echo ""
echo "--- Добавление метода save() ---"

python - "$DB_FILE" << 'PYEOF'
import sys
from pathlib import Path

db_file = Path(sys.argv[1])
content = db_file.read_text(encoding="utf-8")

# Идемпотентность: если метод уже есть — выходим
if "def save(self, key: str, value):" in content:
    print("  [OK] Метод save() уже есть в database.py")
    sys.exit(0)

# Метод для вставки. Отступ 4 пробела — уровень методов класса.
save_method = (
    "    def save(self, key: str, value):\n"
    "        \"\"\"Алиас для set() — для совместимости с ConfigManager.\"\"\"\n"
    "        return self.set(key, value)\n"
    "\n"
)

# Ищем метод set() и вставляем save() ПЕРЕД ним
marker = "def set(self, key: str, value):"
if marker not in content:
    print("  [FAIL] Не найден метод set() в database.py")
    sys.exit(1)

# Определяем отступ строки с def set, чтобы вставить с тем же отступом
lines = content.split("\n")
insert_index = None
set_indent = ""
for i, line in enumerate(lines):
    if marker in line:
        insert_index = i
        set_indent = line[:len(line) - len(line.lstrip())]
        break

if insert_index is None:
    print("  [FAIL] Не удалось найти позицию для вставки")
    sys.exit(1)

# Вставляем метод с тем же отступом, что и у set()
save_block = (
    f"{set_indent}def save(self, key: str, value):\n"
    f"{set_indent}    \"\"\"Алиас для set() — для совместимости с ConfigManager.\"\"\"\n"
    f"{set_indent}    return self.set(key, value)\n"
    "\n"
)

lines.insert(insert_index, save_block.rstrip("\n"))
new_content = "\n".join(lines)

# Проверяем синтаксис перед записью
try:
    compile(new_content, str(db_file), "exec")
except SyntaxError as e:
    print(f"  [FAIL] Синтаксическая ошибка после вставки: {e}")
    sys.exit(1)

db_file.write_text(new_content, encoding="utf-8")
print("  [FIXED] Метод save() добавлен перед методом set()")
PYEOF

# --- Проверка ---
echo ""
echo "--- Проверка ---"

python << 'PYEOF'
import importlib, sys

# Перезагружаем модуль, чтобы подхватить изменения
for mod in ["app.database", "app.config", "app"]:
    if mod in sys.modules:
        del sys.modules[mod]

try:
    from app.database import db

    if not hasattr(db, "save"):
        print("  [FAIL] Метод save() не найден в Database")
        sys.exit(1)
    print("  [OK] Метод save() доступен")

    # Функциональный тест
    test_data = {"test": "value", "num": 42}
    db.save("test_key_68", test_data)
    loaded = db.get("test_key_68")
    if loaded == test_data:
        print("  [OK] save() и get() работают корректно")
        db.save("test_key_68", None)
    else:
        print("  [FAIL] save() записал, но get() вернул другое значение")
        sys.exit(1)

    # Проверяем, что ConfigManager тоже работает
    from app.config import config
    sections = list(config.all().keys())
    print(f"  [OK] ConfigManager загружен, секции: {sections}")

except Exception as e:
    print(f"  [FAIL] Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYEOF

echo ""
echo "============================================================================"
echo "Готово. Теперь можно запускать сервер:"
echo "  python main.py"
echo "============================================================================"