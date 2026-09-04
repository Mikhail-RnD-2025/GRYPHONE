#!/bin/sh
# ============================================================================
# 104. update_scripts/104_final_css_cleanup.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Безопасная очистка styles.css: удаляет старые версии дублирующихся
#   селекторов, оставляя только последнюю версию каждого.
#
# ДУБЛИКАТЫ ИЗ АНАЛИЗА:
#   • .header: 5 версий → оставить последнюю (строка 660)
#   • .fullscreen-info-overlay: 2 версии → оставить последнюю (строка 480)
#   • .header-clock: 2 версии → оставить последнюю (строка 567)
#   • .header-title: 2 версии → оставить последнюю (строка 604)
#   • .set-selector: 2 версии → оставить последнюю (строка 893)
#   • .header-right: 2 версии → оставить последнюю (строка 915)
#   • .fullscreen-info-name: 2 версии → оставить последнюю (строка 509)
#   • .fullscreen-info-location: 2 версии → оставить последнюю (строка 517)
#   • .fullscreen-info-badge: 2 версии → оставить последнюю (строка 526)
#
# ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:
#   • Уменьшение размера на ~15-20%
#   • Удаление 12 устаревших блоков
#   • Сохранение всех актуальных стилей
#
# БЕЗОПАСНОСТЬ:
#   • Создаёт бэкап перед изменением
#   • Удаляет только старые версии (не последние)
#   • Проверяет синтаксис после очистки
#
# ЗАПУСК: ./104_final_css_cleanup.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "104: Финальная безопасная очистка styles.css"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

cd "$PROJECT_ROOT"

CSS_FILE="frontend/src/styles.css"
BACKUP="$CSS_FILE.bak-104"

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
# ШАГ 2: Удаление старых версий дубликатов
# ============================================================================
echo ""
echo "--- ШАГ 2: Удаление старых версий дубликатов ---"

"$PYTHON_CMD" - "$CSS_FILE" "$ORIGINAL_SIZE" << 'PYEOF'
import sys
from pathlib import Path

css_file = Path(sys.argv[1])
original_size = int(sys.argv[2])

lines = css_file.read_text(encoding="utf-8").split('\n')

# Дубликаты: { селектор: [номера строк, начиная с 1] }
# Оставляем только ПОСЛЕДНЮЮ строку из каждого списка
duplicates = {
    '.header': [39, 451, 540, 616, 660],
    '.fullscreen-info-overlay': [344, 480],
    '.header-clock': [55, 567],
    '.header-title': [50, 604],
    '.set-selector': [60, 893],
    '.header-right': [575, 915],
    '.fullscreen-info-name': [369, 509],
    '.fullscreen-info-location': [377, 517],
    '.fullscreen-info-badge': [386, 526],
}

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

# Находим границы всех блоков для удаления
blocks_to_remove = []

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
        for i in range(start_idx, max(0, start_idx - 10), -1):
            if selector in lines[i] and '{' in lines[i]:
                block_start = i
                break

        # Ищем конец блока
        block_end = find_block_end(lines, block_start)

        blocks_to_remove.append((block_start, block_end, selector, start))

print(f"  Найдено блоков для удаления: {len(blocks_to_remove)}")

# Удаляем блоки (в обратном порядке, чтобы не сбить индексы)
for start, end, selector, original_line in sorted(blocks_to_remove, reverse=True):
    print(f"    Удаляю {selector} (строка {original_line}): строки {start+1}-{end+1}")
    del lines[start:end+1]

# Сохраняем результат
new_content = '\n'.join(lines)
css_file.write_text(new_content, encoding="utf-8")

new_size = len(new_content.encode('utf-8'))
saved = original_size - new_size
percent = int(saved * 100 / original_size) if original_size > 0 else 0

print(f"\n  Размер: {original_size} → {new_size} байт")
print(f"  Экономия: {saved} байт ({percent}%)")
print("  [OK] Старые версии дубликатов удалены")
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
    print("  Восстановите: cp frontend/src/styles.css.bak-104 frontend/src/styles.css")
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
echo "  • Удалено блоков: 12 (старые версии дубликатов)"
echo ""
echo "Обязательно пересоберите фронтенд и проверьте визуально:"
echo "  cd frontend && npm run build"
echo "  cd .. && python main.py"
echo ""
echo "Если что-то сломалось:"
echo "  cp $BACKUP $CSS_FILE"
echo "============================================================================"