#!/bin/sh
# ============================================================================
# 65. update_scripts/65_fix_menu_structure.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Исправляет структуру навигационного меню после скрипта 64.
#
#   1. Откатывает App.jsx к оригинальной версии (убирает ошибочный <NavLink>,
#      который вызывал "ReferenceError: NavLink is not defined").
#   2. Добавляет в гамбургер-меню пункт "Главная" (ведёт на "/" - монитор камер).
#   3. Переименовывает пункт "Наборы" в "Мониторинг" (ведёт на "/sets").
#
#   Итог: в меню есть отдельные пункты "Главная" и "Мониторинг".
#
# ИДЕМПОТЕНТНОСТЬ:
#   Повторный запуск безопасен - если изменения уже применены, скрипт
#   не вносит их повторно.
#
# ЗАПУСК:
#   ./65_fix_menu_structure.sh
#
# ПОСЛЕ ЗАПУСКА:
#   Пересоберите фронтенд:  cd frontend && npm run build
# ============================================================================

set -eu

# --- Пути ---
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
FRONTEND_SRC="$PROJECT_ROOT/frontend/src"

echo "============================================================================"
echo "65: Исправление структуры меню (Главная + Мониторинг)"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

# --- Ищем интерпретатор Python (нужен для надёжной работы с юникодом) ---
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

# ============================================================================
# ШАГ 1: Откат App.jsx (убираем ошибочный <NavLink>)
# ============================================================================
echo ""
echo "--- ШАГ 1: Откат App.jsx ---"

APP_FILE="$FRONTEND_SRC/App.jsx"
APP_BACKUP="$FRONTEND_SRC/App.jsx.bak-menu"

if [ -f "$APP_BACKUP" ]; then
    # Откатываем только если в текущем файле есть ошибочный NavLink
    if grep -q "<NavLink" "$APP_FILE" 2>/dev/null; then
        cp "$APP_FILE" "$APP_FILE.bak-65"
        cp "$APP_BACKUP" "$APP_FILE"
        echo "  [FIXED] App.jsx восстановлен (ошибочный <NavLink> удалён)"
    else
        echo "  [OK] В App.jsx нет ошибочного <NavLink>. Откат не требуется."
    fi
else
    echo "  [WARN] Резервная копия $APP_BACKUP не найдена."
    # Если бэкапа нет, но есть ошибочный NavLink - удалим его вручную
    if grep -q "<NavLink" "$APP_FILE" 2>/dev/null; then
        cp "$APP_FILE" "$APP_FILE.bak-65"
        # Удаляем строку с <NavLink ...Мониторинг...</NavLink>
        "$PYTHON_CMD" - "$APP_FILE" << 'PYEOF'
import sys, re
from pathlib import Path
p = Path(sys.argv[1])
content = p.read_text(encoding="utf-8")
# Удаляем все строки, содержащие <NavLink (вставленные скриптом 64)
content = re.sub(r'^\s*<NavLink[^>]*>.*?</NavLink>\s*\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*<NavLink[^>]*/>\s*\n', '', content, flags=re.MULTILINE)
p.write_text(content, encoding="utf-8")
print("  [FIXED] Строка <NavLink> удалена из App.jsx")
PYEOF
    fi
fi

# ============================================================================
# ШАГ 2: Правка гамбургер-меню (Главная + Мониторинг)
# ============================================================================
echo ""
echo "--- ШАГ 2: Правка HamburgerMenu.jsx ---"

MENU_FILE="$FRONTEND_SRC/components/HamburgerMenu.jsx"

if [ ! -f "$MENU_FILE" ]; then
    echo "  [FAIL] Файл не найден: $MENU_FILE" >&2
    exit 1
fi

# Резервная копия перед изменением
cp "$MENU_FILE" "$MENU_FILE.bak-65"
echo "  [BAK] Резервная копия: $MENU_FILE.bak-65"

# Применяем правки через Python (надёжная работа с юникодом/эмодзи)
"$PYTHON_CMD" - "$MENU_FILE" << 'PYEOF'
import sys
from pathlib import Path

menu_file = Path(sys.argv[1])
content = menu_file.read_text(encoding="utf-8")
changed = []

# ---- Правка 1: переименовать "Наборы" -> "Мониторинг" (пункт /sets) ----
# Меняем только в пункте с path '/sets', чтобы не задеть другие места.
if "{ path: '/sets', label: 'Наборы'" in content:
    content = content.replace(
        "{ path: '/sets', label: 'Наборы'",
        "{ path: '/sets', label: 'Мониторинг'"
    )
    changed.append("пункт 'Наборы' переименован в 'Мониторинг'")
elif "{ path: '/sets', label: 'Мониторинг'" in content:
    pass  # уже переименовано
else:
    # На случай другого форматирования - простая замена метки
    if "label: 'Наборы'" in content and "label: 'Мониторинг'" not in content:
        content = content.replace("label: 'Наборы'", "label: 'Мониторинг'")
        changed.append("метка 'Наборы' переименована в 'Мониторинг'")

# ---- Правка 2: если ранее был добавлен 'Мониторинг' с path '/',
#                 исправляем его на '/sets' (на случай предыдущих правок) ----
if "{ path: '/', label: 'Мониторинг'" in content:
    content = content.replace(
        "{ path: '/', label: 'Мониторинг'",
        "{ path: '/sets', label: 'Мониторинг'"
    )
    changed.append("пункт 'Мониторинг' теперь ведёт на /sets")

# ---- Правка 3: добавить пункт "Главная" в начало массива ----
home_item = "  { path: '/', label: 'Главная', icon: '🏠', enabled: true },\n"
if "label: 'Главная'" not in content:
    if "const MENU_ITEMS = [" in content:
        content = content.replace(
            "const MENU_ITEMS = [",
            "const MENU_ITEMS = [\n" + home_item,
            1  # только первое вхождение
        )
        changed.append("добавлен пункт 'Главная' (ведёт на /)")
    else:
        print("  [WARN] Не найден массив MENU_ITEMS")

if changed:
    menu_file.write_text(content, encoding="utf-8")
    for c in changed:
        print(f"  [FIXED] {c}")
else:
    print("  [OK] Меню уже в нужном состоянии, изменения не вносились")
PYEOF

# ============================================================================
# ШАГ 3: Удаляем лишние стили .monitoring-link (если добавлялись скриптом 64)
# ============================================================================
echo ""
echo "--- ШАГ 3: Очистка лишних стилей ---"

CSS_FILE="$FRONTEND_SRC/styles.css"
if [ -f "$CSS_FILE" ] && grep -q "\.monitoring-link" "$CSS_FILE"; then
    cp "$CSS_FILE" "$CSS_FILE.bak-65"
    "$PYTHON_CMD" - "$CSS_FILE" << 'PYEOF'
import sys, re
from pathlib import Path
p = Path(sys.argv[1])
content = p.read_text(encoding="utf-8")
content = re.sub(r'\.monitoring-link\s*\{[^}]*\}', '', content)
content = re.sub(r'\.monitoring-link:hover\s*\{[^}]*\}', '', content)
p.write_text(content, encoding="utf-8")
print("  [FIXED] Стили .monitoring-link удалены")
PYEOF
else
    echo "  [OK] Лишних стилей не найдено"
fi

# ============================================================================
# ИТОГ
# ============================================================================
echo ""
echo "============================================================================"
echo "Готово!"
echo ""
echo "Изменения:"
echo "  1. App.jsx        - ошибочный <NavLink> убран"
echo "  2. HamburgerMenu  - добавлен пункт 'Главная' (-> /)"
echo "  3. HamburgerMenu  - пункт 'Наборы' переименован в 'Мониторинг' (-> /sets)"
echo ""
echo "Обязательно пересоберите фронтенд:"
echo "  cd $PROJECT_ROOT/frontend"
echo "  npm run build"
echo "============================================================================"