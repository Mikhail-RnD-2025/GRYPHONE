#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
cd "$PROJECT_DIR"

echo "📁 Проект: $PROJECT_DIR"
echo ""
echo "🔄 Замена названий потоков..."
python replace_stream_names.py

echo ""
echo "🧹 Очистка кэша HLS..."
if [ -d "hls_cache/camera" ]; then
    rm -rf hls_cache/camera/*_основной 2>/dev/null || true
    rm -rf hls_cache/camera/*_дополнительный 2>/dev/null || true
    echo "  ✔ Старые папки удалены"
fi

echo ""
echo "✅ Готово!"
echo ""
echo "📋 Дальше:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Откройте http://localhost:5000 (Ctrl+Shift+R)"