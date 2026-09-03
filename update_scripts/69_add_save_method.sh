#!/bin/sh
# ============================================================================
# 69. update_scripts/69_add_save_method.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Добавляет метод save() в класс Database как алиас для set().
#   Исправляет ошибку:
#     AttributeError: 'Database' object has no attribute 'save'
#   которая возникает в ConfigManager (патч 67).
#
# ОТЛИЧИЕ ОТ СКРИПТА 68:
#   Метод вставляется ПЕРЕД методом set() с тем же отступом и обязательной
#   проверкой синтаксиса через compile() ДО записи. Это исключает
#   IndentationError, возникший в прошлый раз.
#
# ИДЕМПОТЕНТНОСТЬ: повторный запуск безопасен.
# ЗАПУСК: ./69_add_save_method.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "69: Добавление метода save() в database.py"
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

if [ ! -f "$DB_FILE" ]; then
    echo "ОШИБКА: не найден файл $DB_FILE" >&2
    exit 1
fi

# ============================================================================
# ШАГ 1: Проверяем синтаксис; восстанавливаем при повреждении
# ============================================================================
echo ""
echo "--- ШАГ 1: Проверка синтаксиса ---"
if ! "$PYTHON_CMD" -c "import ast; ast.parse(open('$DB_FILE', encoding='utf-8').read())" 2>/dev/null; then
    echo "  [WARN] Файл $DB_FILE повреждён"
    for bak in "$DB_FILE.bak-70" "$DB_FILE.bak-69" "$DB_FILE.bak-68" "$DB_FILE.bak-67"; do
        if [ -f "$bak" ]; then
            echo "  [RESTORE] Восстанавливаю из $bak"
            cp "$bak" "$DB_FILE"
            break
        fi
    done
    # Повторная проверка
    if ! "$PYTHON_CMD" -c "import ast; ast.parse(open('$DB_FILE', encoding='utf-8').read())" 2>/dev/null; then
        echo "  [FAIL] Файл всё ещё повреждён после восстановления" >&2
        exit 1
    fi
fi
echo "  [OK] Синтаксис корректен"

# ============================================================================
# ШАГ 2: Резервная копия
# ============================================================================
echo ""
echo "--- ШАГ 2: Резервная копия ---"
cp "$DB_FILE" "$DB_FILE.bak-69"
echo "  [BAK] $DB_FILE.bak-69"

# ============================================================================
# ШАГ 3: Добавляем метод save() перед методом set()
# ============================================================================
echo ""
echo "--- ШАГ 3: Добавление метода save() ---"

"$PYTHON_CMD" - "$DB_FILE" << 'PYEOF'
import sys
from pathlib import Path

db_file = Path(sys.argv[1])
content = db_file.read_text(encoding="utf-8")

# Идемпотентность: если метод уже есть — выходим
if "def save(self, key: str, value):" in content:
    print("  [OK] Метод save() уже есть — ничего не делаем")
    sys.exit(0)

lines = content.split("\n")

# Ищем метод set() и запоминаем его отступ
insert_index = None
set_indent = ""
for i, line in enumerate(lines):
    if "def set(self, key: str, value):" in line:
        insert_index = i
        set_indent = line[:len(line) - len(line.lstrip())]
        break

if insert_index is None:
    print("  [FAIL] Не найден метод set() для точки вставки")
    sys.exit(1)

# Блок метода с тем же отступом, что и у set()
save_block = (
    f"{set_indent}def save(self, key: str, value):\n"
    f"{set_indent}    \"\"\"Алиас для set() — для совместимости с ConfigManager.\"\"\"\n"
    f"{set_indent}    return self.set(key, value)\n"
)

lines.insert(insert_index, save_block)
new_content = "\n".join(lines)

# Обязательная проверка синтаксиса ДО записи
try:
    compile(new_content, str(db_file), "exec")
except SyntaxError as e:
    print(f"  [FAIL] Синтаксическая ошибка после вставки: {e}")
    sys.exit(1)

db_file.write_text(new_content, encoding="utf-8")
print("  [FIXED] Метод save() добавлен перед методом set()")
PYEOF

# ============================================================================
# ШАГ 4: Функциональная проверка
# ============================================================================
echo ""
echo "--- ШАГ 4: Функциональная проверка ---"

"$PYTHON_CMD" << 'PYEOF'
import sys
for mod in list(sys.modules.keys()):
    if mod.startswith("app"):
        del sys.modules[mod]

try:
    from app.database import db

    if not hasattr(db, "save"):
        print("  [FAIL] Метод save() не найден")
        sys.exit(1)
    print("  [OK] Метод save() доступен")

    # Тест записи/чтения
    test = {"test": "value", "num": 42}
    db.save("test_key_69", test)
    loaded = db.get("test_key_69")
    if loaded == test:
        print("  [OK] save()/get() работают корректно")
        db.save("test_key_69", None)
    else:
        print("  [FAIL] Данные не совпали после save/get")
        sys.exit(1)

    # Проверяем, что ConfigManager тоже загружается
    from app.config import config
    print(f"  [OK] ConfigManager загружен, секций: {len(config.all())}")

except Exception as e:
    print(f"  [FAIL] Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYEOF

echo ""
echo "============================================================================"
echo "Готово. Резервная копия: $DB_FILE.bak-69"
echo "============================================================================"