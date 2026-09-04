#!/bin/sh
# ============================================================================
# 103. update_scripts/103_safe_remove_duplicates.sh (ИСПРАВЛЕННАЯ ВЕРСИЯ)
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Безопасно удаляет дублирующиеся блоки CSS, оставляя только последнюю
#   версию каждого селектора.
#
# ИСПРАВЛЕНО: передача ORIGINAL_SIZE в Python через sys.argv
#
# ЗАПУСК: ./103_safe_remove_duplicates.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "103: Безопасное удаление дубликатов CSS"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

cd "$PROJECT_ROOT"

CSS_FILE="frontend/src/styles.css"
BACKUP="$CSS_FILE.bak-103"

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
# ШАГ 2: Безопасное удаление дубликатов
# ============================================================================
echo ""
echo "--- ШАГ 2: Удаление дубликатов ---"

# Передаём ORIGINAL_SIZE в Python через аргумент командной строки
"$PYTHON_CMD" - "$CSS_FILE" "$ORIGINAL_SIZE" << 'PYEOF'
import sys
from pathlib import Path

css_file = Path(sys.argv[1])
original_size = int(sys.argv[2])

lines = css_file.read_text(encoding="utf-8").split('\n')

# Дубликаты из анализа (строки начинаются с 1)
duplicates = {
    '.fullscreen-info-badge': [386, 526],
    '.fullscreen-info-location': [377, 517],
    '.fullscreen-info-name': [369, 509],
    '.fullscreen-info-overlay': [344, 480],
    '.header': [39, 451, 540, 616, 660],
    '.header-clock': [55, 567],
    '.header-right': [575, 915],
    '.header-title': [50, 604],
    '.set-selector': [60, 893],
}

# Функция для поиска границ блока
def find_block_end(lines, start_line):
    """Находит конец блока CSS (строку с закрывающей })"""
    brace_count = 0
    for i in range(start_line, len(lines)):
        line = lines[i]
        brace_count += line.count('{')
        brace_count -= line.count('}')
        if brace_count == 0 and '}' in line:
            return i
    return len(lines) - 1

# Находим границы всех блоков для дубликатов
blocks_to_remove = []  # список кортежей (start, end, selector)

for selector, start_lines in duplicates.items():
    if len(start_lines) <= 1:
        continue

    # Оставляем только последний блок
    last_start = max(start_lines)

    for start in start_lines:
        if start == last_start:
            continue  # оставляем последний

        # Конвертируем номер строки в индекс (строки начинаются с 1)
        start_idx = start - 1

        # Ищем начало блока (строка с селектором и {)
        block_start = start_idx
        for i in range(start_idx, max(0, start_idx - 5), -1):
            if selector in lines[i]:
                block_start = i
                break

        # Ищем конец блока
        block_end = find_block_end(lines, block_start)

        blocks_to_remove.append((block_start, block_end, selector))

print(f"  Найдено блоков для удаления: {len(blocks_to_remove)}")

# Удаляем блоки (в обратном порядке, чтобы не сбить индексы)
for start, end, selector in sorted(blocks_to_remove, reverse=True):
    # Исправлено: selector уже содержит точку, не добавляем вторую
    print(f"    Удаляю {selector}: строки {start+1}-{end+1}")
    del lines[start:end+1]

# Сохраняем результат
new_content = '\n'.join(lines)
css_file.write_text(new_content, encoding="utf-8")

new_size = len(new_content.encode('utf-8'))
saved = original_size - new_size
percent = int(saved * 100 / original_size) if original_size > 0 else 0

print(f"  Размер: {original_size} → {new_size} байт (экономия {saved} байт, {percent}%)")
print("  [OK] Дубликаты удалены безопасно")
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
    print("  Восстановите: cp frontend/src/styles.css.bak-103 frontend/src/styles.css")
PYEOF

NEW_SIZE=$(wc -c < "$CSS_FILE" | tr -d ' ')
SAVED=$((ORIGINAL_SIZE - NEW_SIZE))
PERCENT=$((SAVED * 100 / ORIGINAL_SIZE))

echo ""
echo "============================================================================"
echo "Готово!"
echo ""
echo "Результат:"
echo "  • Оригинальный размер: $ORIGINAL_SIZE байт"
echo "  • Новый размер: $NEW_SIZE байт"
echo "  • Экономия: $SAVED байт ($PERCENT%)"
echo ""
echo "Обязательно пересоберите фронтенд и проверьте визуально:"
echo "  cd frontend && npm run build"
echo "  python main.py"
echo ""
echo "Если что-то сломалось:"
echo "  cp $BACKUP $CSS_FILE"
echo "============================================================================"