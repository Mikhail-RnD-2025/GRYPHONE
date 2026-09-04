#!/bin/sh
# ============================================================================
# 106. update_scripts/106_analyze_and_reassemble.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   1. Показывает содержимое чанков, которые планируем удалить
#   2. Проверяет, нет ли в них критических определений
#   3. Собирает оставшиеся чанки обратно в styles.css
#
# ЗАПУСК: ./106_analyze_and_reassemble.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "106: Анализ чанков и сборка"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

cd "$PROJECT_ROOT"

CHUNKS_DIR="frontend/src/.css_chunks"
CSS_FILE="frontend/src/styles.css"
BACKUP="$CSS_FILE.bak-106"

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
# ШАГ 1: Резервная ко