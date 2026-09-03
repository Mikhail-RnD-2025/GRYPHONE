#!/bin/sh
# ============================================================================
# 70. update_scripts/70_remove_config_json.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Убирает устаревший код, связанный с config.json. Конфигурация теперь
#   живёт в database/sql/default_config.sql (патчи 67/71), поэтому загрузка
#   конфига из data/config.json в _populate_from_json() больше не нужна и
#   создаёт конфликт форматов в таблице settings.
#
# ЧТО УДАЛЯЕТСЯ:
#   1. Блок загрузки config.json из _populate_from_json() в app/database.py.
#      Загрузка cameras.json и sets.json НЕ трогается.
#   2. Файл data/config.json (с бэкапом).
#
# ИДЕМПОТЕНТНОСТЬ: повторный запуск безопасен.
# ЗАПУСК: ./70_remove_config_json.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "70: Удаление устаревшего кода, связанного с config.json"
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
DATA_CONFIG="data/config.json"

if [ ! -f "$DB_FILE" ]; then
    echo "ОШИБКА: не найден файл $DB_FILE" >&2
    exit 1
fi

# ============================================================================
# ШАГ 1: Резервные копии
# ============================================================================
echo ""
echo "--- ШАГ 1: Резервные копии ---"
cp "$DB_FILE" "$DB_FILE.bak-70"
echo "  [BAK] $DB_FILE.bak-70"
if [ -f "$DATA_CONFIG" ]; then
    cp "$DATA_CONFIG" "$DATA_CONFIG.bak-70"
    echo "  [BAK] $DATA_CONFIG.bak-70"
fi

# ============================================================================
# ШАГ 2: Проверяем синтаксис; восстанавливаем при повреждении
# ============================================================================
echo ""
echo "--- ШАГ 2: Проверка синтаксиса ---"
if ! "$PYTHON_CMD" -c "import ast; ast.parse(open('$DB_FILE', encoding='utf-8').read())" 2>/dev/null; then
    echo "  [WARN] Файл повреждён, восстанавливаю из бэкапа"
    for bak in "$DB_FILE.bak-69" "$DB_FILE.bak-68" "$DB_FILE.bak-67"; do
        if [ -f "$bak" ]; then
            cp "$bak" "$DB_FILE"
            echo "  [RESTORE] из $bak"
            break
        fi
    done
fi
echo "  [OK] Синтаксис проверен"

# ============================================================================
# ШАГ 3: Удаляем блок загрузки config.json
# ============================================================================
echo ""
echo "--- ШАГ 3: Удаление блока загрузки config.json ---"

"$PYTHON_CMD" - "$DB_FILE" << 'PYEOF'
import sys
from pathlib import Path

db_file = Path(sys.argv[1])
content = db_file.read_text(encoding="utf-8")

# Идемпотентность
if "config.json" not in content:
    print("  [OK] В коде нет упоминаний config.json — удалять нечего")
    sys.exit(0)

lines = content.split("\n")

# Ищем начало блока: строка, где определяется config_file с config.json
start = None
for i, line in enumerate(lines):
    if "config.json" in line and ("config_file" in line or "DATA_DIR" in line):
        start = i
        break

if start is None:
    print("  [OK] Блок загрузки config.json не найден (возможно, уже удалён)")
    sys.exit(0)

# Включаем предшествующие комментарии/пустые строки блока
check = start - 1
while check >= 0:
    stripped = lines[check].strip()
    if stripped.startswith("#") and ("config" in stripped.lower() or "load" in stripped.lower()):
        start = check
        check -= 1
    elif stripped == "":
        check -= 1
    else:
        break

# Ищем конец блока: первая строка conn.commit() после start
end = None
for i in range(start + 1, len(lines)):
    if "conn.commit()" in lines[i]:
        end = i
        break

if end is None:
    print("  [FAIL] Не найден конец блока (conn.commit())")
    sys.exit(1)

print(f"  Удаляю строки {start+1}..{end} (блок загрузки config.json)")

new_lines = lines[:start] + lines[end:]
new_content = "\n".join(new_lines)

# Проверка синтаксиса ДО записи
try:
    compile(new_content, str(db_file), "exec")
except SyntaxError as e:
    print(f"  [FAIL] Синтаксическая ошибка после удаления: {e}")
    sys.exit(1)

db_file.write_text(new_content, encoding="utf-8")
print("  [FIXED] Блок загрузки config.json удалён")
PYEOF

# ============================================================================
# ШАГ 4: Проверка результата
# ============================================================================
echo ""
echo "--- ШАГ 4: Проверка результата ---"

if "$PYTHON_CMD" -c "import ast; ast.parse(open('$DB_FILE', encoding='utf-8').read())" 2>/dev/null; then
    echo "  [OK] Синтаксис корректен после правки"
else
    echo "  [FAIL] Синтаксис нарушен, откат" >&2
    cp "$DB_FILE.bak-70" "$DB_FILE"
    exit 1
fi

if grep -q "config\.json" "$DB_FILE"; then
    echo "  [WARN] Остались упоминания config.json:"
    grep -n "config\.json" "$DB_FILE"
else
    echo "  [OK] В database.py больше нет config.json"
fi

if grep -q "cameras.json" "$DB_FILE" && grep -q "sets.json" "$DB_FILE"; then
    echo "  [OK] Загрузка камер и наборов на месте"
else
    echo "  [FAIL] Загрузка камер/наборов пострадала, откат!" >&2
    cp "$DB_FILE.bak-70" "$DB_FILE"
    exit 1
fi

# ============================================================================
# ШАГ 5: Удаляем data/config.json
# ============================================================================
echo ""
echo "--- ШАГ 5: Удаление data/config.json ---"
if [ -f "$DATA_CONFIG" ]; then
    rm -f "$DATA_CONFIG"
    echo "  [OK] Файл удалён (бэкап: $DATA_CONFIG.bak-70)"
else
    echo "  [OK] Файл уже отсутствует"
fi

# ============================================================================
# ШАГ 6: Функциональная проверка
# ============================================================================
echo ""
echo "--- ШАГ 6: Функциональная проверка ---"

"$PYTHON_CMD" << 'PYEOF'
import sys
for mod in list(sys.modules.keys()):
    if mod.startswith("app"):
        del sys.modules[mod]

try:
    from app.database import db
    from app.config import config

    sections = list(config.all().keys())
    print(f"  [OK] Конфиг загружен, секций: {len(sections)}")

    import sqlite3
    conn = sqlite3.connect(db.db_path)
    cur = conn.cursor()
    cur.execute("SELECT key FROM settings")
    keys = [r[0] for r in cur.fetchall()]
    conn.close()

    legacy = [k for k in keys if k in ("server", "ffmpeg", "paths", "app", "cleanup")]
    if legacy:
        print(f"  [WARN] В settings остались ключи старого формата: {legacy}")
    else:
        print("  [OK] В settings нет ключей старого формата")

    print("  [OK] Модули работают корректно")
except Exception as e:
    print(f"  [FAIL] Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYEOF

echo ""
echo "============================================================================"
echo "Готово. Резервные копии: *.bak-70"
echo "============================================================================"