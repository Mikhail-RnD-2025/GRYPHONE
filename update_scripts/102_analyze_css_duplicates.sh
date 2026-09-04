#!/bin/sh
# ============================================================================
# 102. update_scripts/102_analyze_css_duplicates.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Анализирует styles.css на наличие дубликатов и выводит отчёт.
#   НЕ удаляет ничего автоматически.
#
# ЗАПУСК: ./102_analyze_css_duplicates.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "102: Анализ дубликатов в styles.css (без удаления)"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

cd "$PROJECT_ROOT"

CSS_FILE="frontend/src/styles.css"

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

echo ""
echo "--- Анализ дубликатов ---"

"$PYTHON_CMD" - << 'PYEOF'
import re
from pathlib import Path
from collections import defaultdict

css_file = Path("frontend/src/styles.css")
content = css_file.read_text(encoding="utf-8")

# Извлекаем все селекторы
selectors = defaultdict(int)
selector_positions = defaultdict(list)

lines = content.split('\n')
for i, line in enumerate(lines, 1):
    # Ищем строки с селекторами (начинаются с . или #)
    match = re.match(r'^\s*([.#][a-zA-Z0-9_-]+(?:\s+[.#][a-zA-Z0-9_-]+)*)\s*\{', line)
    if match:
        selector = match.group(1).strip()
        selectors[selector] += 1
        selector_positions[selector].append(i)

# Находим дубликаты
duplicates = {k: v for k, v in selectors.items() if v > 1}

print(f"Всего селекторов: {len(selectors)}")
print(f"Дублирующихся селекторов: {len(duplicates)}")
print()

if duplicates:
    print("Список дубликатов:")
    for selector, count in sorted(duplicates.items()):
        positions = selector_positions[selector]
        print(f"  • {selector}: {count} раз (строки: {', '.join(map(str, positions))})")
else:
    print("Дубликатов не найдено.")

print()
print("Рекомендация:")
print("  • Если дубликаты есть — удалите старые версии вручную")
print("  • Оставьте последнюю версию каждого селектора")
print("  • НЕ используйте автоматическое удаление без тестирования")
PYEOF

echo ""
echo "============================================================================"
echo "Анализ завершён. Файл НЕ был изменён."
echo "============================================================================"