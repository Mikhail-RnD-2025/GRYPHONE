#!/bin/sh
# ============================================================================
# 76. update_scripts/76_fix_menu_labels.sh (ИСПРАВЛЕННАЯ ВЕРСИЯ)
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Гарантирует правильные метки пунктов меню навигации:
#   • "/" -> "Мониторинг" (сетка камер)
#   • "/sets" -> "Наборы"
#
# ОТЛИЧИЕ ОТ ПРЕДЫДУЩЕЙ ВЕРСИИ:
#   Всегда проверяет и исправляет метки, даже если некоторые уже правильные.
#
# ИДЕМПОТЕНТНОСТЬ: повторный запуск безопасен.
# ЗАПУСК: ./76_fix_menu_labels.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "76: Исправление меток меню навигации (v2)"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

cd "$PROJECT_ROOT"

MENU_FILE="frontend/src/components/HamburgerMenu.jsx"

if [ ! -f "$MENU_FILE" ]; then
    echo "ОШИБКА: не найден $MENU_FILE" >&2; exit 1
fi

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
cp "$MENU_FILE" "$MENU_FILE.bak-76"
echo "  [BAK] $MENU_FILE.bak-76"

# ============================================================================
# ШАГ 2: Принудительная правка пунктов меню
# ----------------------------------------------------------------------------
# В отличие от предыдущей версии, здесь мы ВСЕГДА проверяем и исправляем
# метки, даже если некоторые уже правильные. Это гарантирует корректность.
# ============================================================================
echo ""
echo "--- ШАГ 2: Правка пунктов меню ---"

"$PYTHON_CMD" - "$MENU_FILE" << 'PYEOF'
import sys
import re
from pathlib import Path

menu_file = Path(sys.argv[1])
content = menu_file.read_text(encoding="utf-8")
original = content
changes = []

# Разбиваем на строки для точечной правки
lines = content.split('\n')
new_lines = []

for line in lines:
    # Правка 1: Пункт "/" должен называться "Мониторинг"
    if "path: '/'" in line and "label:" in line:
        # Заменяем любую метку на "Мониторинг"
        new_line = re.sub(
            r"label:\s*['\"][^'\"]+['\"]",
            "label: 'Мониторинг'",
            line
        )
        # Устанавливаем иконку 📹
        new_line = re.sub(
            r"icon:\s*['\"][^'\"]+['\"]",
            "icon: '📹'",
            new_line
        )
        if new_line != line:
            changes.append(f"пункт '/': метка -> 'Мониторинг', иконка -> '📹'")
        new_lines.append(new_line)

    # Правка 2: Пункт "/sets" должен называться "Наборы"
    elif "path: '/sets'" in line and "label:" in line:
        # Заменяем любую метку на "Наборы"
        new_line = re.sub(
            r"label:\s*['\"][^'\"]+['\"]",
            "label: 'Наборы'",
            line
        )
        # Устанавливаем иконку 📦
        new_line = re.sub(
            r"icon:\s*['\"][^'\"]+['\"]",
            "icon: '📦'",
            new_line
        )
        if new_line != line:
            changes.append(f"пункт '/sets': метка -> 'Наборы', иконка -> '📦'")
        new_lines.append(new_line)

    else:
        new_lines.append(line)

new_content = '\n'.join(new_lines)

if new_content == original:
    print("  [OK] Меню уже в нужном состоянии")
    sys.exit(0)

menu_file.write_text(new_content, encoding="utf-8")

if changes:
    for c in changes:
        print(f"  [FIXED] {c}")
else:
    print("  [OK] Изменений не потребовалось")
PYEOF

# ============================================================================
# ШАГ 3: Проверка результата
# ============================================================================
echo ""
echo "--- ШАГ 3: Проверка результата ---"

"$PYTHON_CMD" - "$MENU_FILE" << 'PYEOF'
import sys
from pathlib import Path
import re

menu_file = Path(sys.argv[1])
content = menu_file.read_text(encoding="utf-8")

# Извлекаем массив MENU_ITEMS
match = re.search(r'const MENU_ITEMS = \[(.*?)\]', content, re.DOTALL)
if not match:
    print("  [FAIL] Не найден массив MENU_ITEMS")
    sys.exit(1)

items_block = match.group(1)

# Парсим пункты
items = []
for line in items_block.split('\n'):
    if "path:" in line and "label:" in line:
        path_match = re.search(r"path:\s*['\"]([^'\"]+)['\"]", line)
        label_match = re.search(r"label:\s*['\"]([^'\"]+)['\"]", line)
        icon_match = re.search(r"icon:\s*['\"]([^'\"]+)['\"]", line)
        if path_match and label_match:
            path = path_match.group(1)
            label = label_match.group(1)
            icon = icon_match.group(1) if icon_match else "?"
            items.append((path, label, icon))

print("  Пункты меню:")
for path, label, icon in items:
    print(f"    {icon}  {label:<12} -> {path}")

# Проверка критериев
errors = []
if not any(p == '/' and l == 'Мониторинг' for p, l, _ in items):
    errors.append("нет пункта '/' с меткой 'Мониторинг'")
if not any(p == '/sets' and l == 'Наборы' for p, l, _ in items):
    errors.append("нет пункта '/sets' с меткой 'Наборы'")
if any(p == '/sets' and l == 'Мониторинг' for p, l, _ in items):
    errors.append("пункт '/sets' всё ещё называется 'Мониторинг'")

if errors:
    print("")
    print("  [FAIL] Проблемы:")
    for e in errors:
        print(f"    • {e}")
    sys.exit(1)
else:
    print("")
    print("  ✅ Меню настроено корректно")
PYEOF

echo ""
echo "============================================================================"
echo "Готово. Резервная копия: $MENU_FILE.bak-76"
echo ""
echo "Обязательно пересоберите фронтенд:"
echo "  cd $PROJECT_ROOT/frontend"
echo "  npm run build"
echo ""
echo "Затем обновите страницу в браузере (Ctrl+F5)"
echo "============================================================================"