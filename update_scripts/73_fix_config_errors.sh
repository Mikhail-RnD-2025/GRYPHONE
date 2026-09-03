#!/bin/sh
# ============================================================================
# 73. update_scripts/73_fix_config_errors.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Исправляет две критические ошибки в app/config.py:
#   1. Опечатка в пути: default_default_config.sql -> default_config.sql
#   2. Сломанное регулярное выражение для парсинга SQL-файла
#
# ПОСЛЕ ИСПРАВЛЕНИЯ:
#   ConfigManager загрузит полный эталонный конфиг из
#   database/sql/default_config.sql со всеми секциями (включая
#   зарезервированные: storage, integration, analytics, cluster).
#
# ИДЕМПОТЕНТНОСТЬ: повторный запуск безопасен.
# ЗАПУСК: ./73_fix_config_errors.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "73: Исправление ошибок в app/config.py"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

cd "$PROJECT_ROOT"

CONFIG_PY="app/config.py"

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

if [ ! -f "$CONFIG_PY" ]; then
    echo "ОШИБКА: не найден файл $CONFIG_PY" >&2; exit 1
fi

# ============================================================================
# ШАГ 1: Резервная копия
# ============================================================================
echo ""
echo "--- ШАГ 1: Резервная копия ---"
cp "$CONFIG_PY" "$CONFIG_PY.bak-73"
echo "  [BAK] $CONFIG_PY.bak-73"

# ============================================================================
# ШАГ 2: Исправление обеих ошибок через Python
# ============================================================================
echo ""
echo "--- ШАГ 2: Исправление ошибок ---"

"$PYTHON_CMD" - "$CONFIG_PY" << 'PYEOF'
import sys
import re as re_module
from pathlib import Path

config_file = Path(sys.argv[1])
content = config_file.read_text(encoding="utf-8")
original = content
changes = []

# -----------------------------------------------------------------------
# ОШИБКА 1: Исправляем опечатку в пути к SQL-файлу
# Было: "default_default_config.sql"
# Стало: "default_config.sql"
# -----------------------------------------------------------------------
if "default_default_config.sql" in content:
    content = content.replace("default_default_config.sql", "default_config.sql")
    changes.append("опечатка 'default_default_config.sql' -> 'default_config.sql'")

# -----------------------------------------------------------------------
# ОШИБКА 2: Исправляем регулярное выражение для парсинга SQL.
# Старый (сломанный) паттерн и новый (правильный) ищем как подстроки.
# Используем re.search на самом content, чтобы найти любую из возможных
# сломанных форм (с экранированием и без).
# -----------------------------------------------------------------------
# Найдём строку с re.search и VALUES 'config' и заменим её на правильную.
old_regex_pattern = None
# Вариант A: с одинарными кавычками
for candidate in [
    r'r"VALUESs\*(s\*\'config\'s\*,s\*\'(.+)\'s\*)s\*;"',
    r'r"VALUES\\s*\\(s*\\\'config\\\'\\s*,\\s*\\\'\\((.+)\\\'\\)s*;"',
]:
    if candidate in content:
        old_regex_pattern = candidate
        break

if old_regex_pattern:
    # Правильный паттерн
    new_regex_pattern = r'r"VALUES\s*\(\s*\'config\'\s*,\s*\'(.+)\'\s*\)\s*;"'
    content = content.replace(old_regex_pattern, new_regex_pattern)
    changes.append("регулярное выражение для парсинга SQL")
else:
    # Попробуем найти строку, содержа 'VALUES' и 'config' внутри re.search
    # и заменить её на правильную
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if "re.search" in line and "VALUES" in line and "'config'" in line:
            # Это та самая строка. Заменяем её полностью.
            indent = len(line) - len(line.lstrip())
            new_line = (" " * indent +
                       'match = re.search(r"VALUES\\s*\\(\\s*\'config\'\\s*,'
                       '\\s*\'(.+)\'\\s*\\)\\s*;", content, re.DOTALL)')
            lines[i] = new_line
            changes.append("регулярное выражение (по содержимому строки)")
            break
    content = "\n".join(lines)

if not changes:
    print("  [OK] Ошибки не найдены или уже исправлены")
    sys.exit(0)

# Проверка синтаксиса ДО записи
try:
    compile(content, str(config_file), "exec")
except SyntaxError as e:
    print(f"  [FAIL] Синтаксическая ошибка после правки: {e}")
    sys.exit(1)

config_file.write_text(content, encoding="utf-8")
print("  [FIXED] Исправлены ошибки:")
for change in changes:
    print(f"    • {change}")
PYEOF

# ============================================================================
# ШАГ 3: Проверка наличия SQL-файла
# ============================================================================
echo ""
echo "--- ШАГ 3: Проверка наличия SQL-файла ---"
SQL_FILE="database/sql/default_config.sql"
if [ -f "$SQL_FILE" ]; then
    echo "  [OK] $SQL_FILE найден"
else
    echo "  [WARN] $SQL_FILE не найден"
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

    # Проверка, что в пути нет опечатки
    if "default_default_" in str(DEFAULT_SQL_PATH):
        print("  [FAIL] В пути всё ещё есть опечатка 'default_default_'")
        sys.exit(1)

    print("")
    print("  ✅ Все ошибки исправлены, конфигурация загружена корректно")

except Exception as e:
    print(f"  [FAIL] Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYEOF

echo ""
echo "============================================================================"
echo "Готово. Резервная копия: $CONFIG_PY.bak-73"
echo ""
echo "Чтобы применить эталонный конфиг к существующей БД:"
echo "  python -c \"from app.database import db; db.save('config', None)\""
echo ""
echo "Запуск сервера:  python main.py"
echo "============================================================================"