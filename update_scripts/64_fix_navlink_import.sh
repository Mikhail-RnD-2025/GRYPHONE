#!/bin/sh
# ============================================================================
# 64_fix. update_scripts/64_fix_navlink_import.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Исправляет ошибку "NavLink is not defined" после скрипта 64.
#   Находит файл, где используется <NavLink>, и добавляет импорт.
#
# ЗАПУСК:
#   ./64_fix_navlink_import.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
FRONTEND_SRC="$PROJECT_ROOT/frontend/src"

echo "============================================================================"
echo "64_fix: Добавление импорта NavLink"
echo "Корень проекта: $PROJECT_ROOT"
echo "Фронтенд: $FRONTEND_SRC"
echo "============================================================================"

if [ ! -d "$FRONTEND_SRC" ]; then
    echo "ОШИБКА: не найден каталог $FRONTEND_SRC" >&2
    exit 1
fi

# Ищем файлы, где есть <NavLink, но нет импорта NavLink
echo ""
echo "Поиск файлов с NavLink..."
FILES=$(grep -rl "<NavLink" "$FRONTEND_SRC" \
    --include="*.jsx" \
    --include="*.tsx" \
    --exclude-dir=node_modules \
    --exclude-dir=dist \
    --exclude-dir=build \
    2>/dev/null || true)

if [ -z "$FILES" ]; then
    echo "Файлы с <NavLink не найдены. Проблема может быть в другом."
    exit 0
fi

echo "Найдены файлы:"
echo "$FILES"

FIXED=0

for FILE in $FILES; do
    echo ""
    echo "Обработка: $FILE"

    # Проверяем, есть ли уже импорт NavLink
    if grep -q "import.*NavLink.*from.*react-router-dom" "$FILE"; then
        echo "  [SKIP] Импорт NavLink уже есть"
        continue
    fi

    # Проверяем, есть ли вообще импорт из react-router-dom
    if grep -q "import.*from.*react-router-dom" "$FILE"; then
        # Добавляем NavLink к существующему импорту
        echo "  [FIX] Добавляем NavLink к существующему импорту"
        cp "$FILE" "$FILE.bak-64fix"

        # Находим строку с импортом и добавляем NavLink
        perl -pi -e 's/import\s*\{([^}]*)\}\s*from\s*["\x27]react-router-dom["\x27]/import {$1, NavLink} from "react-router-dom"/' "$FILE"

        # Проверяем, не дублируется ли NavLink
        if grep -q "NavLink, NavLink" "$FILE"; then
            perl -pi -e 's/NavLink,\s*NavLink/NavLink/' "$FILE"
        fi

        echo "  [FIXED] NavLink добавлен в импорт"
        FIXED=$((FIXED + 1))
    else
        # Добавляем новый импорт в начало файла
        echo "  [FIX] Добавляем новый импорт NavLink"
        cp "$FILE" "$FILE.bak-64fix"

        # Вставляем импорт после последнего import или в начало файла
        if grep -q "^import" "$FILE"; then
            # Находим последнюю строку с import и добавляем после неё
            perl -0777 -pi -e 's/(^import.*\n)/$1import { NavLink } from "react-router-dom";\n/s' "$FILE"
        else
            # Вставляем в начало файла
            perl -pi -e '1i\import { NavLink } from "react-router-dom";' "$FILE"
        fi

        echo "  [FIXED] Новый импорт добавлен"
        FIXED=$((FIXED + 1))
    fi
done

echo ""
echo "============================================================================"
echo "Готово. Исправлено файлов: $FIXED"
echo ""
echo "Следующий шаг: пересоберите фронтенд"
echo "  cd $PROJECT_ROOT/frontend"
echo "  npm run build"
echo "============================================================================"