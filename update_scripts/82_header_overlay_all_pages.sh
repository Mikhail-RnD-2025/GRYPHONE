#!/bin/sh
# ============================================================================
# 82. update_scripts/82_header_overlay_all_pages.sh (ИСПРАВЛЕННАЯ ВЕРСИЯ)
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Делает шапку фиксированной (position: fixed) на всех страницах.
#   Шапка наползает на контент, а не резервирует место под себя.
#
# ИСПРАВЛЕНО: путь к файлу стилей (styles.css вместо index.css)
#
# ИДЕМПОТЕНТНОСТЬ: повторный запуск безопасен.
# ЗАПУСК: ./82_header_overlay_all_pages.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "82: Шапка наползает на контент на всех страницах"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

cd "$PROJECT_ROOT"

CSS_FILE="frontend/src/styles.css"

if [ ! -f "$CSS_FILE" ]; then
    echo "ОШИБКА: не найден $CSS_FILE" >&2; exit 1
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
cp "$CSS_FILE" "$CSS_FILE.bak-82"
echo "  [BAK] $CSS_FILE.bak-82"

# ============================================================================
# ШАГ 2: Обновление стилей Header
# ============================================================================
echo ""
echo "--- ШАГ 2: Обновление стилей ---"

"$PYTHON_CMD" - "$CSS_FILE" << 'PYEOF'
import sys
import re
from pathlib import Path

css_file = Path(sys.argv[1])
content = css_file.read_text(encoding="utf-8")

# Маркер для идемпотентности
marker = "/* PATCH-82: Шапка фиксированная на всех страницах */"

if marker in content:
    print("  [OK] Стили уже обновлены (маркер найден)")
    sys.exit(0)

# Новые стили для фиксированной шапки
new_styles = f"""
{marker}
.header {{
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(51, 65, 85, 0.5);
  transition: transform 0.3s ease, opacity 0.3s ease;
}}

.header-hidden {{
  transform: translateY(-100%);
  opacity: 0;
  pointer-events: none;
}}

.header-trigger {{
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 20px;
  z-index: 999;
}}

.header-left,
.header-center,
.header-right {{
  display: flex;
  align-items: center;
}}

.header-left {{
  flex: 1;
}}

.header-center {{
  flex: 1;
  justify-content: center;
}}

.header-right {{
  flex: 1;
  justify-content: flex-end;
  gap: 12px;
}}

.header-title {{
  font-size: 1.25rem;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0;
  cursor: pointer;
  user-select: none;
  transition: all 0.2s ease;
  padding: 4px 8px;
  border-radius: 4px;
}}

.header-clock {{
  font-size: 0.875rem;
  color: #94a3b8;
  font-variant-numeric: tabular-nums;
}}

/* Убираем отступы у основного контента, чтобы шапка наползала */
.page {{
  padding-top: 0 !important;
  margin-top: 0 !important;
}}

.monitor-page {{
  padding-top: 0 !important;
}}

/* Контент начинается с самого верха */
.app-container,
.main-content {{
  padding-top: 0 !important;
  margin-top: 0 !important;
}}
"""

# Проверяем, есть ли уже блок .header в файле
header_pattern = re.compile(
    r'\.header\s*\{[^}]*\}',
    re.DOTALL
)

if header_pattern.search(content):
    # Заменяем существующий блок .header на новый
    content = header_pattern.sub(new_styles.strip(), content, count=1)
    print("  [FIXED] Заменён существующий блок .header")
else:
    # Добавляем в конец файла
    content += "\n" + new_styles
    print("  [FIXED] Добавлены стили .header в конец файла")

# Удаляем дубликаты .header-hidden и .header-trigger, если они есть
# (они уже включены в новый блок)
for old_class in ['.header-hidden', '.header-trigger']:
    pattern = re.compile(rf'{re.escape(old_class)}\s*\{{[^}}]*\}}', re.DOTALL)
    matches = list(pattern.finditer(content))
    if len(matches) > 1:
        # Оставляем только первое вхождение (из нового блока)
        for match in reversed(matches[1:]):
            content = content[:match.start()] + content[match.end():]
        print(f"  [CLEAN] Удалены дубликаты {old_class}")

css_file.write_text(content, encoding="utf-8")
print("  [OK] Стили обновлены")
PYEOF

echo ""
echo "============================================================================"
echo "Готово. Резервная копия: $CSS_FILE.bak-82"
echo ""
echo "Обязательно пересоберите фронтенд:"
echo "  cd $PROJECT_ROOT/frontend"
echo "  npm run build"
echo ""
echo "Теперь на всех страницах:"
echo "  • Шапка фиксирована (position: fixed)"
echo "  • Наползает на контент, не резервирует место"
echo "  • Скрывается при бездействии, появляется при наведении"
echo "============================================================================"