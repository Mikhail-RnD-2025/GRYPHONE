#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — script 50: FIX CYRILLIC CSS PROPERTIES
#  ------------------------------------------------------------
#  Удаляет все CSS-правила с кириллическими свойствами,
#  которые браузер не может прочитать, и добавляет корректные
#  правила на английском языке.
#
#  ЗАПУСК:  bash update_scripts/50_fix_cyrillic_css.sh
#  ПОСЛЕ:   npm run build
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/main.py" ]; then
    PROJECT_DIR="$SCRIPT_DIR"
else
    PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
fi

echo "📁 Project root: $PROJECT_DIR"
cd "$PROJECT_DIR"

# ============================================================
# Определение интерпретатора Python (без Windows Store)
# ============================================================
_detect_python() {
    local cmd
    for cmd in python python3 py; do
        if command -v "$cmd" >/dev/null 2>&1; then
            if "$cmd" --version >/dev/null 2>&1; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    if command -v py >/dev/null 2>&1; then
        if py -3 --version >/dev/null 2>&1; then
            echo "py -3"
            return 0
        fi
    fi
    return 1
}

PYTHON_CMD="$(_detect_python || true)"
if [ -z "$PYTHON_CMD" ]; then
    echo "❌ ERROR: no Python interpreter found."
    exit 1
fi

read -ra PYCMD <<< "$PYTHON_CMD"
echo "✅ Python: ${PYCMD[*]}"

# ============================================================
# Очистка CSS: удаление кириллических правил и добавление корректных
# ============================================================
echo ""
echo "🔧 Cleaning up styles.css (removing Cyrillic CSS)..."

"${PYCMD[@]}" << 'PYEOF'
from pathlib import Path
import re

file = Path("frontend/src/styles.css")
if not file.exists():
    print("ERROR: styles.css not found")
    raise SystemExit(1)

content = file.read_text(encoding="utf-8")

# 1. Удаляем блок с кириллическими классами и свойствами (v47 сломанный)
cyrillic_pattern = re.compile(
    r'/\*[^*]*Полноэкранная сетка камер \(в47\)[^*]*\*/\s*'
    r'\.паге\.монитор-паге\s*\{[^}]*\}\s*'
    r'\.фуллскрин-грид\s*\{[^}]*\}\s*'
    r'\.фуллскрин-грид\s+\.камера-кард\s*\{[^}]*\}\s*'
    r'\.фуллскрин-грид\s+\.камера-видео\s*\{[^}]*\}\s*'
    r'\.фуллскрин-грид\s+\.камера-емпти\s*\{[^}]*\}\s*',
    re.DOTALL
)

content = cyrillic_pattern.sub('', content)

# 2. Дополнительно удаляем любые одиночные правила с кириллическими классами
# на всякий случай, чтобы гарантировать чистоту
content = re.sub(r'\.[а-яё]+\s*\{[^}]*\}', '', content)

# 3. Добавляем корректные CSS-правила на английском языке в конец файла
correct_css = """
/* ============================================================
   Fullscreen grid fix (v50) - CORRECT ENGLISH CSS
   ============================================================ */

.page.monitor-page {
  padding: 0 !important;
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.page.monitor-page .header,
.monitor-page .header {
  position: fixed !important;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  margin: 0;
}

.fullscreen-grid {
  flex: 1;
  min-height: 0;
  width: 100%;
  height: 100%;
  display: grid;
  gap: 2px;
  background: #0b0d10;
}

.fullscreen-grid .camera-card {
  position: relative;
  overflow: hidden;
  background: #000;
  height: 100%;
  width: 100%;
}

.fullscreen-grid .camera-card video,
.fullscreen-grid .camera-video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
}

.fullscreen-grid .camera-empty {
  height: 100%;
  width: 100%;
}
"""

# Проверяем, есть ли уже корректные правила, чтобы не дублировать
if '.page.monitor-page {\n  padding: 0 !important;' not in content:
    content += correct_css
    print("OK: correct English CSS rules added")
else:
    print("INFO: correct English CSS rules already present")

file.write_text(content, encoding="utf-8")
print("OK: styles.css cleaned and updated")
PYEOF

# ============================================================
# Проверка результата
# ============================================================
echo ""
echo "🔍 Verification..."

if grep -qE "\.паге|паддинг|хейгхт|дисплей|флекс" "$PROJECT_DIR/frontend/src/styles.css"; then
    echo "  ⚠️  WARNING: Some Cyrillic CSS might still be present."
else
    echo "  ✔ No Cyrillic CSS properties found"
fi

if grep -q "\.page\.monitor-page" "$PROJECT_DIR/frontend/src/styles.css"; then
    echo "  ✔ Correct .page.monitor-page rules present"
else
    echo "  ❌ ERROR: .page.monitor-page rules missing"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Cyrillic CSS removed, correct rules added"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 Next: npm run build"