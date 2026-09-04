#!/bin/sh
# ============================================================================
# 105. update_scripts/105_split_css_into_chunks.sh
# ----------------------------------------------------------------------------
# НАЗНАЧЕНИЕ:
#   Разбивает styles.css на логические чанки по версионным комментариям.
#   Создаёт отдельные файлы для каждого чанка в папке .css_chunks/
#   Показывает размер каждого чанка для принятия решения об удалении.
#
# ПРИНЦИП РАБОТЫ:
#   1. Ищет версионные комментарии (v40, v41, ..., v49)
#   2. Разбивает файл на чанки между этими комментариями
#   3. Сохраняет каждый чанк в отдельный файл
#   4. Выводит отчёт о размерах чанков
#
# ЗАПУСК: ./105_split_css_into_chunks.sh
# ============================================================================

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

echo "============================================================================"
echo "105: Разбиение styles.css на чанки"
echo "Корень проекта: $PROJECT_ROOT"
echo "============================================================================"

cd "$PROJECT_ROOT"

CSS_FILE="frontend/src/styles.css"
CHUNKS_DIR="frontend/src/.css_chunks"

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
# ШАГ 1: Создание папки для чанков
# ============================================================================
echo ""
echo "--- ШАГ 1: Подготовка папки для чанков ---"
rm -rf "$CHUNKS_DIR"
mkdir -p "$CHUNKS_DIR"
echo "  [OK] Создана папка: $CHUNKS_DIR"

# ============================================================================
# ШАГ 2: Разбиение файла на чанки
# ============================================================================
echo ""
echo "--- ШАГ 2: Разбиение на чанки ---"

"$PYTHON_CMD" - "$CSS_FILE" "$CHUNKS_DIR" << 'PYEOF'
import re
import sys
from pathlib import Path

css_file = Path(sys.argv[1])
chunks_dir = Path(sys.argv[2])

content = css_file.read_text(encoding="utf-8")

# Разбиваем по версионным комментариям
# Ищем паттерны вида: /* ===== ... (v40) ... */ или /* ===== ... v40 ... */
# Используем версионные метки как разделители

# Находим все версионные комментарии
version_pattern = r'/\*[\s\S]*?\(v(\d+)\)[\s\S]*?\*/'
version_matches = list(re.finditer(version_pattern, content))

print(f"  Найдено версионных секций: {len(version_matches)}")

if not version_matches:
    print("  [WARN] Версионные комментарии не найдены")
    print("  Сохраняю весь файл как один чанк")
    chunk_file = chunks_dir / "chunk_00_base.css"
    chunk_file.write_text(content, encoding="utf-8")
    print(f"  [OK] Создан чанк: {chunk_file.name} ({len(content)} байт)")
    sys.exit(0)

# Первый чанк — всё до первого версионного комментария (базовые стили)
first_version_start = version_matches[0].start()
if first_version_start > 0:
    base_chunk = content[:first_version_start]
    chunk_file = chunks_dir / "chunk_00_base.css"
    chunk_file.write_text(base_chunk, encoding="utf-8")
    print(f"  [OK] chunk_00_base.css: {len(base_chunk)} байт (базовые стили)")

# Разбиваем на чанки по версионным комментариям
chunks = []
for i, match in enumerate(version_matches):
    version = int(match.group(1))
    chunk_start = match.start()

    # Конец чанка — начало следующего версионного комментария или конец файла
    if i + 1 < len(version_matches):
        chunk_end = version_matches[i + 1].start()
    else:
        chunk_end = len(content)

    chunk_content = content[chunk_start:chunk_end]
    chunk_file = chunks_dir / f"chunk_{i+1:02d}_v{version}.css"
    chunk_file.write_text(chunk_content, encoding="utf-8")

    chunk_size = len(chunk_content)
    chunks.append((version, chunk_file.name, chunk_size))
    print(f"  [OK] {chunk_file.name}: {chunk_size} байт")

# Выводим сводку
print(f"\n  Всего чанков: {len(chunks) + 1}")
print(f"  Общий размер: {sum(c[2] for c in chunks) + len(base_chunk) if 'base_chunk' in locals() else 0} байт")

# Сохраняем метаданные чанков
metadata = {
    "chunks": [
        {"file": name, "version": ver, "size": size}
        for ver, name, size in chunks
    ]
}

import json
metadata_file = chunks_dir / "chunks_metadata.json"
metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
print(f"\n  [OK] Метаданные сохранены: {metadata_file.name}")
PYEOF

echo ""
echo "============================================================================"
echo "Готово! Чанки созданы в папке: $CHUNKS_DIR"
echo ""
echo "Следующий шаг:"
echo "  1. Изучите чанки: ls -la $CHUNKS_DIR"
echo "  2. Решите, какие чанки удалить (старые версии)"
echo "  3. Запустите скрипт 106 для сборки чанков обратно"
echo "============================================================================"