#!/bin/sh
# ============================================================================
# 72. update_scripts/72_fix_default_path.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Исправляет опечатку в DEFAULT_SQL_PATH: "default_default_config.sql"
#   -> "default_config.sql". Опечатка возникла при повторном применении
#   патча 71, когда "config.sql" уже было заменено на "default_config.sql".
#
# ИДЕМПОТЕНТНОСТЬ: повторный запуск безопасен.
# ЗАПУСК: ./72_fix_default_path.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "72: Исправление опечатки в пути к default_config.sql"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

cd "$PROJECT_ROOT"

CONFIG_PY="app/config.py"
NEW_SQL="database/sql/default_config.sql"
WRONG_SQL="database/sql/default_default_config.sql"

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

# ============================================================================
# ШАГ 1: Резервная копия
# ============================================================================
echo ""
echo "--- ШАГ 1: Резервная копия ---"
cp "$CONFIG_PY" "$CONFIG_PY.bak-72"
echo "  [BAK] $CONFIG_PY.bak-72"

# ============================================================================
# ШАГ 2: Исправление опечатки в app/config.py
# ============================================================================
echo ""
echo "--- ШАГ 2: Исправление пути в $CONFIG_PY ---"

"$PYTHON_CMD" - "$CONFIG_PY" << 'PYEOF'
import sys
from pathlib import Path

config_file = Path(sys.argv[1])
content = config_file.read_text(encoding="utf-8")
original = content

# Исправляем двойное "default_default_config.sql" -> "default_config.sql"
if "default_default_config.sql" in content:
    content = content.replace("default_default_config.sql", "default_config.sql")
    print("  [FIXED] Исправлена опечатка 'default_default_config.sql' -> 'default_config.sql'")
else:
    print("  [OK] Опечатка не найдена — путь уже корректен")

# Проверка: путь должен быть именно "default_config.sql", не "config.sql"
if '"config.sql"' in content or "'config.sql'" in content:
    # Дополнительная защита: если где-то осталось старое имя
    content = content.replace('"config.sql"', '"default_config.sql"')
    content = content.replace("'config.sql'", "'default_config.sql'")
    print("  [FIXED] Убраны остатки старого имени 'config.sql'")

if content != original:
    # Проверка синтаксиса
    try:
        compile(content, str(config_file), "exec")
    except SyntaxError as e:
        print(f"  [FAIL] Синтаксическая ошибка: {e}")
        sys.exit(1)
    config_file.write_text(content, encoding="utf-8")
    print("  [OK] Файл сохранён")
else:
    print("  [OK] Изменений не потребовалось")
PYEOF

# ============================================================================
# ШАГ 3: Проверка наличия файла default_config.sql
# ============================================================================
echo ""
echo "--- ШАГ 3: Проверка наличия SQL-файла ---"
if [ -f "$NEW_SQL" ]; then
    echo "  [OK] $NEW_SQL найден"
elif [ -f "$WRONG_SQL" ]; then
    echo "  [INFO] Найден файл с ошибочным именем: $WRONG_SQL"
    echo "  [FIXED] Переименовываю в $NEW_SQL"
    mv "$WRONG_SQL" "$NEW_SQL"
else
    echo "  [FAIL] Не найден ни $NEW_SQL, ни $WRONG_SQL"
    echo "  Проверьте папку database/sql/"
fi

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
    from app.config import config, DEFAULT_SQL_PATH
    from pathlib import Path

    print(f"  Путь к эталону: {DEFAULT_SQL_PATH}")

    path = Path(DEFAULT_SQL_PATH)
    if not path.is_file():
        print(f"  [FAIL] Файл не найден: {path}")
        print("         Проверьте, что database/sql/default_config.sql существует")
        sys.exit(1)
    print("  [OK] Эталонный файл найден")

    sections = list(config.all().keys())
    print(f"  [OK] Конфиг загружен, секций: {len(sections)}")

    # Критическая проверка: должны быть все зарезервированные секции
    reserved = ["storage", "integration", "analytics", "cluster"]
    missing = [s for s in reserved if s not in sections]
    if missing:
        print(f"  [FAIL] Отсутствуют зарезервированные секции: {missing}")
        print("         Загружен запасной конфиг, а не эталон!")
        sys.exit(1)
    else:
        print("  [OK] Все зарезервированные секции на месте (загружен эталон)")

    # Проверка, что в пути нет "default_default_"
    if "default_default_" in str(DEFAULT_SQL_PATH):
        print("  [FAIL] В пути всё ещё есть опечатка 'default_default_'")
        sys.exit(1)

    print("")
    print("  Итог: конфигурация загружена корректно из эталона")

except Exception as e:
    print(f"  [FAIL] Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYEOF

echo ""
echo "============================================================================"
echo "Готово. Резервная копия: $CONFIG_PY.bak-72"
echo "============================================================================"