#!/bin/sh
# ============================================================================
# 71. update_scripts/71_rename_config_sql.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Обновляет имя эталонного конфигурационного файла с "config.sql" на
#   "default_config.sql" во всех местах кода. Физически файл уже переименован
#   пользователем; этот скрипт синхронизирует код с новым именем.
#
# ПОЧЕМУ ВАЖНО:
#   ConfigManager читает эталон из DEFAULT_SQL_PATH. Если путь указывает на
#   старое имя "config.sql", а файл называется "default_config.sql", то файл
#   не будет найден и приложение переключится на усечённый запасной конфиг.
#
# ИДЕМПОТЕНТНОСТЬ: повторный запуск безопасен.
# ЗАПУСК: ./71_rename_config_sql.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "71: Переименование config.sql -> default_config.sql в коде"
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

CONFIG_PY="app/config.py"

# ============================================================================
# ШАГ 1: Проверяем наличие файлов
# ============================================================================
echo ""
echo "--- ШАГ 1: Проверка наличия файлов ---"
NEW_SQL="database/sql/default_config.sql"
OLD_SQL="database/sql/config.sql"

if [ -f "$NEW_SQL" ]; then
    echo "  [OK] Новый файл найден: $NEW_SQL"
else
    echo "  [WARN] Новый файл НЕ найден: $NEW_SQL"
    if [ -f "$OLD_SQL" ]; then
        echo "  [INFO] Найден старый файл: $OLD_SQL"
        echo "  [INFO] Копирую его в $NEW_SQL"
        mkdir -p database/sql
        cp "$OLD_SQL" "$NEW_SQL"
    else
        echo "  [FAIL] Не найден ни старый, ни новый файл" >&2
        exit 1
    fi
fi

# ============================================================================
# ШАГ 2: Обновляем путь в app/config.py
# ============================================================================
echo ""
echo "--- ШАГ 2: Обновление пути в $CONFIG_PY ---"

if [ ! -f "$CONFIG_PY" ]; then
    echo "ОШИБКА: не найден файл $CONFIG_PY" >&2
    exit 1
fi

cp "$CONFIG_PY" "$CONFIG_PY.bak-71"
echo "  [BAK] $CONFIG_PY.bak-71"

"$PYTHON_CMD" - "$CONFIG_PY" << 'PYEOF'
import sys
from pathlib import Path

config_file = Path(sys.argv[1])
content = config_file.read_text(encoding="utf-8")

original = content

# Заменяем все варианты написания имени файла
for old, new in [
    ('"config.sql"', '"default_config.sql"'),
    ("'config.sql'", "'default_config.sql'"),
]:
    if old in content:
        content = content.replace(old, new)
        print(f"  [FIXED] {old} -> {new}")

# На случай упоминания без кавычек
if "config.sql" in content:
    content = content.replace("config.sql", "default_config.sql")
    print("  [FIXED] Заменены оставшиеся упоминания 'config.sql'")

if content != original:
    config_file.write_text(content, encoding="utf-8")
    print("  [OK] Файл обновлён")
else:
    print("  [OK] Изменения не потребовались")
PYEOF

# ============================================================================
# ШАГ 3: Поиск других упоминаний
# ============================================================================
echo ""
echo "--- ШАГ 3: Поиск других упоминаний ---"
OTHER_FILES=$(grep -rln "config\.sql" \
    --include="*.py" . \
    --exclude-dir=node_modules --exclude-dir=dist --exclude-dir=__pycache__ 2>/dev/null \
    | grep -v ".bak-" || true)

if [ -n "$OTHER_FILES" ]; then
    echo "  [INFO] 'config.sql' ещё встречается в:"
    echo "$OTHER_FILES" | while read -r f; do echo "    - $f"; done
else
    echo "  [OK] В Python-коде больше нет упоминаний 'config.sql'"
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
    if Path(DEFAULT_SQL_PATH).is_file():
        print("  [OK] Эталонный файл найден по пути из кода")
    else:
        print("  [FAIL] Эталонный файл НЕ найден по пути из кода")
        sys.exit(1)

    sections = list(config.all().keys())
    print(f"  [OK] Конфиг загружен, секций: {len(sections)}")

    reserved = ["storage", "integration", "analytics", "cluster"]
    missing = [s for s in reserved if s not in sections]
    if missing:
        print(f"  [WARN] Отсутствуют зарезервированные секции: {missing}")
        print("         Признак того, что загружен запасной конфиг, а не эталон!")
    else:
        print("  [OK] Все зарезервированные секции на месте (загружен эталон)")

except Exception as e:
    print(f"  [FAIL] Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYEOF

echo ""
echo "============================================================================"
echo "Готово. Резервная копия: $CONFIG_PY.bak-71"
echo "============================================================================"