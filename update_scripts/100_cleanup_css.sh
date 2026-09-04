#!/bin/sh
# ============================================================================
# 100. update_scripts/100_cleanup_css.sh (ИСПРАВЛЕННАЯ ВЕРСИЯ)
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Очищает frontend/src/styles.css от мусора.
#
# ИСПРАВЛЕНО: добавлен детект Python для Windows (python, не python3)
#
# ЗАПУСК: ./100_cleanup_css.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "100: Очистка styles.css от мусора"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

cd "$PROJECT_ROOT"

CSS_FILE="frontend/src/styles.css"
BACKUP="$CSS_FILE.bak-100"

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
    echo "  Попробуйте установить Python: https://www.python.org/downloads/"
    exit 1
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
# ШАГ 2: Анализ использования классов
# ============================================================================
echo ""
echo "--- ШАГ 2: Анализ использования классов ---"

"$PYTHON_CMD" - << 'PYEOF'
import re
from pathlib import Path

css_file = Path("frontend/src/styles.css")
content = css_file.read_text(encoding="utf-8")

# Извлекаем все классы из CSS
css_classes = set(re.findall(r'\.([a-zA-Z0-9_-]+)\s*[{,:]', content))
css_classes.discard('')

print(f"  Классов в CSS: {len(css_classes)}")

# Проверяем использование в JSX
jsx_files = list(Path("frontend/src").rglob("*.jsx"))
used_classes = set()

for jsx_file in jsx_files:
    jsx_content = jsx_file.read_text(encoding="utf-8")
    # Ищем className="..." и className={`...`}
    class_matches = re.findall(r'className=["\']([^"\']+)["\']', jsx_content)
    class_matches += re.findall(r'className=\{`([^`]+)`\}', jsx_content)
    for match in class_matches:
        # Разбиваем на отдельные классы
        classes = match.split()
        used_classes.update(classes)

unused = css_classes - used_classes
print(f"  Классов используется в JSX: {len(used_classes)}")
print(f"  Потенциально неиспользуемых: {len(unused)}")

if unused:
    print("  Примеры неиспользуемых:")
    for cls in sorted(unused)[:10]:
        print(f"    - .{cls}")

# Сохраняем результат для следующего шага
unused_file = Path("frontend/src/.unused_classes.txt")
unused_file.write_text('\n'.join(sorted(unused)), encoding="utf-8")
PYEOF

# ============================================================================
# ШАГ 3: Очистка CSS
# ============================================================================
echo ""
echo "--- ШАГ 3: Очистка CSS ---"

"$PYTHON_CMD" - << 'PYEOF'
import re
from pathlib import Path

css_file = Path("frontend/src/styles.css")
unused_file = Path("frontend/src/.unused_classes.txt")

content = css_file.read_text(encoding="utf-8")

# Загружаем список неиспользуемых классов
if unused_file.exists():
    unused_classes = set(unused_file.read_text(encoding="utf-8").split('\n'))
    unused_classes.discard('')
else:
    unused_classes = set()

print(f"  Удаляю {len(unused_classes)} неиспользуемых классов")

# Удаляем блоки с неиспользуемыми классами
for cls in unused_classes:
    pattern = rf'\.{re.escape(cls)}\s*{{[^}}]*}}\s*'
    content = re.sub(pattern, '', content, flags=re.DOTALL)

# Удаляем старые версии блоков (v40-v48)
for version in range(40, 49):
    pattern = rf'/\*[\s\S]*?\(v{version}\)[\s\S]*?\*/[\s\S]*?(?=(/\*|\Z))'
    content = re.sub(pattern, '', content, flags=re.DOTALL)

# Удаляем дубликаты .header (оставляем только последний блок)
header_blocks = list(re.finditer(r'\.header\s*{[^}]*}', content, re.DOTALL))
if len(header_blocks) > 1:
    for match in reversed(header_blocks[:-1]):
        content = content[:match.start()] + content[match.end():]

# Удаляем дубликаты других классов
for cls in ['fullscreen-info-overlay', 'header-title', 'header-clock', 'set-selector', 'header-right']:
    blocks = list(re.finditer(rf'\.{re.escape(cls)}\s*{{[^}}]*}}', content, re.DOTALL))
    if len(blocks) > 1:
        for match in reversed(blocks[:-1]):
            content = content[:match.start()] + content[match.end():]

# Удаляем лишние пустые строки
content = re.sub(r'\n{4,}', '\n\n\n', content)

# Удаляем комментарии с версионными метками
content = re.sub(r'/\*\s*\(v\d+\)\s*\*/', '', content)

css_file.write_text(content, encoding="utf-8")
print("  [OK] CSS очищен")

if unused_file.exists():
    unused_file.unlink()
PYEOF

# ============================================================================
# ШАГ 4: Проверка синтаксиса
# ============================================================================
echo ""
echo "--- ШАГ 4: Проверка синтаксиса ---"

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
    print("  Восстановите из бэкапа: cp frontend/src/styles.css.bak-100 frontend/src/styles.css")
PYEOF

NEW_SIZE=$(wc -c < "$CSS_FILE" | tr -d ' ')
SAVED=$((ORIGINAL_SIZE - NEW_SIZE))
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
echo "Обязательно пересоберите фронтенд:"
echo "  cd $PROJECT_ROOT/frontend"
echo "  npm run build"
echo ""
echo "Если после пересборки что-то сломалось:"
echo "  cp $BACKUP $CSS_FILE"
echo "  cd frontend && npm run build"
echo "============================================================================"