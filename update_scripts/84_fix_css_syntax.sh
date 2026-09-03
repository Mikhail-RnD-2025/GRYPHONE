#!/bin/sh
# ============================================================================
# 84. update_scripts/84_fix_css_syntax.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Исправляет CSS-синтаксис, повреждённый скриптом 83.
#   Находит и исправляет несбалансированные скобки в .fullscreen-info-overlay.
#
# ЗАПУСК: ./84_fix_css_syntax.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "84: Исправление CSS-синтаксиса"
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
cp "$CSS_FILE" "$CSS_FILE.bak-84"
echo "  [BAK] $CSS_FILE.bak-84"

# ============================================================================
# ШАГ 2: Исправление CSS
# ============================================================================
echo ""
echo "--- ШАГ 2: Исправление синтаксиса ---"

"$PYTHON_CMD" - "$CSS_FILE" << 'PYEOF'
import sys
import re
from pathlib import Path

css_file = Path(sys.argv[1])
content = css_file.read_text(encoding="utf-8")

# Считаем скобки
open_count = content.count('{')
close_count = content.count('}')
print(f"  Открывающих скобок: {open_count}")
print(f"  Закрывающих скобок: {close_count}")

if open_count == close_count:
    print("  [OK] Скобки сбалансированы")
    sys.exit(0)

# Ищем проблемные блоки
# Паттерн: .classname { ... без закрывающей }
problematic = []
lines = content.split('\n')
stack = []
for i, line in enumerate(lines, 1):
    for j, char in enumerate(line):
        if char == '{':
            stack.append((i, j, line.strip()))
        elif char == '}':
            if stack:
                stack.pop()

if stack:
    print(f"  [WARN] Найдено {len(stack)} незакрытых блоков:")
    for line_num, col, text in stack[:5]:
        print(f"    Строка {line_num}: {text[:60]}")

# Специальная обработка .fullscreen-info-overlay
# Этот блок должен существовать полностью
fullscreen_block = """
.fullscreen-info-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 20px;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.8) 0%,
    rgba(0, 0, 0, 0.4) 70%,
    transparent 100%
  );
  pointer-events: none;
  transform: translateY(-100%);
  opacity: 0;
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.fullscreen-info-overlay.visible {
  transform: translateY(0);
  opacity: 1;
}

.fullscreen-info-name {
  font-size: 1rem;
  font-weight: 600;
  color: #fff;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
  white-space: nowrap;
}

.fullscreen-info-location {
  font-size: 0.875rem;
  color: #cbd5e1;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fullscreen-info-badge {
  font-size: 0.75rem;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 10px;
  border-radius: 4px;
  white-space: nowrap;
}
"""

# Удаляем все вхождения .fullscreen-info-overlay и связанных блоков
content = re.sub(r'\.fullscreen-info-overlay[^{]*\{[^}]*\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.fullscreen-info-name[^{]*\{[^}]*\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.fullscreen-info-location[^{]*\{[^}]*\}', '', content, flags=re.DOTALL)
content = re.sub(r'\.fullscreen-info-badge[^{]*\{[^}]*\}', '', content, flags=re.DOTALL)

# Добавляем чистый блок в конец
content += "\n/* Fullscreen info overlay (restored by PATCH-84) */\n" + fullscreen_block

# Финальная проверка скобок
open_count = content.count('{')
close_count = content.count('}')

if open_count == close_count:
    css_file.write_text(content, encoding="utf-8")
    print(f"  [FIXED] CSS исправлен, скобки сбалансированы ({open_count}/{close_count})")
else:
    print(f"  [FAIL] Скобки всё ещё не сбалансированы ({open_count}/{close_count})")
    print("  Нужна ручная правка")
    sys.exit(1)
PYEOF

echo ""
echo "============================================================================"
echo "Готово. Резервная копия: $CSS_FILE.bak-84"
echo ""
echo "Пересоберите фронтенд:"
echo "  cd $PROJECT_ROOT/frontend"
echo "  npm run build"
echo "============================================================================"