#!/bin/sh
# ============================================================================
# 101. update_scripts/101_safe_cleanup_css.sh (ИСПРАВЛЕННАЯ ВЕРСИЯ)
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Безопасная очистка styles.css от мусора.
#   Удаляет ТОЛЬКО дубликаты и старые версии (v40-v48).
#
# ИСПРАВЛЕНО: синтаксис условного оператора (строка 150)
#
# ЗАПУСК: ./101_safe_cleanup_css.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "101: Безопасная очистка styles.css"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

cd "$PROJECT_ROOT"

CSS_FILE="frontend/src/styles.css"
BACKUP="$CSS_FILE.bak-101"

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
cp "$CSS_FILE" "$BACKUP"
echo "  [BAK] $BACKUP"

ORIGINAL_SIZE=$(wc -c < "$CSS_FILE" | tr -d ' ')
echo "  Оригинальный размер: $ORIGINAL_SIZE байт"

# ============================================================================
# ШАГ 2: Безопасная очистка
# ============================================================================
echo ""
echo "--- ШАГ 2: Безопасная очистка ---"

"$PYTHON_CMD" - << 'PYEOF'
import re
from pathlib import Path

css_file = Path("frontend/src/styles.css")
content = css_file.read_text(encoding="utf-8")

original_length = len(content)
changes = []

# 1. Удаляем старые версии блоков (v40-v48)
old_versions_removed = 0
for version in range(40, 49):
    pattern = rf'/\*[\s\S]*?\(v{version}\)[\s\S]*?\*/[\s\S]*?(?=(/\*[\s=]|\Z))'
    matches = list(re.finditer(pattern, content))
    if matches:
        old_versions_removed += len(matches)
        content = re.sub(pattern, '', content, flags=re.DOTALL)

if old_versions_removed > 0:
    changes.append(f"Удалено старых версий (v40-v48): {old_versions_removed}")

# 2. Удаляем дубликаты ключевых классов (оставляем последний)
duplicate_classes = [
    'header', 'fullscreen-info-overlay', 'header-title',
    'header-clock', 'set-selector', 'header-right',
    'header-left', 'header-center'
]

for cls in duplicate_classes:
    pattern = rf'\.{re.escape(cls)}\s*\{{[^}}]*\}}'
    blocks = list(re.finditer(pattern, content, re.DOTALL))
    if len(blocks) > 1:
        changes.append(f"Дубликатов .{cls}: {len(blocks)} → 1")
        for match in reversed(blocks[:-1]):
            content = content[:match.start()] + content[match.end():]

# 3. Удаляем лишние пустые строки
content = re.sub(r'\n{4,}', '\n\n\n', content)

# 4. Удаляем пустые блоки
content = re.sub(r'[^\S\n]*\{[^\S\n]*\}[^\S\n]*\n?', '', content)

new_length = len(content)
saved = original_length - new_length
percent = int(saved * 100 / original_length) if original_length > 0 else 0

if changes:
    print("  Изменения:")
    for change in changes:
        print(f"    • {change}")
else:
    print("  Изменений не потребовалось")

print(f"  Размер: {original_length} → {new_length} байт (экономия {percent}%)")

css_file.write_text(content, encoding="utf-8")
print("  [OK] CSS очищен безопасно")
PYEOF

# ============================================================================
# ШАГ 3: Проверка синтаксиса
# ============================================================================
echo ""
echo "--- ШАГ 3: Проверка синтаксиса ---"

"$PYTHON_CMD" - << 'PYEOF'
from pathlib import Path

css_file = Path("frontend/src/styles.css")
content = css_file.read_text(encoding="utf-8")

open_count = content.count('{')
close_count = content.count('}')

if open_count == close_count:
    print(f"  [OK] Скобки сбалансированы ({open_count}/{close_count})")
else:
    print(f"  [FAIL] Скобки НЕ сбалансированы ({open_count}/{close_count})")
    print("  Восстановите: cp frontend/src/styles.css.bak-101 frontend/src/styles.css")
PYEOF

NEW_SIZE=$(wc -c < "$CSS_FILE" | tr -d ' ')
SAVED=$((ORIGINAL_SIZE - NEW_SIZE))

# ИСПРАВЛЕННЫЙ синтаксис условного оператора
if [ "$ORIGINAL_SIZE" -gt 0 ]; then
    PERCENT=$((SAVED * 100 / ORIGINAL_SIZE))
else
    PERCENT=0
fi

echo ""
echo "============================================================================"
echo "Готово!"
echo ""
echo "Результат:"
echo "  • Оригинальный размер: $ORIGINAL_SIZE байт"
echo "  • Новый размер: $NEW_SIZE байт"
echo "  • Экономия: $SAVED байт ($PERCENT%)"
echo ""
echo "Пересоберите фронтенд:"
echo "  cd frontend && npm run build"
echo "============================================================================"св