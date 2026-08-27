#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 00: СТРУКТУРА + ЗАГЛУШКИ
#  ------------------------------------------------------------
#  Назначение:
#    1. Создаёт все КАТАЛОГИ проекта.
#    2. Создаёт ПУСТЫЕ файлы-заглушки для ВСЕХ файлов проекта,
#       чтобы ни один файл не создавался вручную.
#
#  Содержимое файлов наполняется последующими скриптами 01..12
#  через `cat > файл`. Повторный запуск безопасен (идемпотентен):
#  уже заполненные файлы НЕ очищаются (используется `touch`).
#
#  Запуск:   bash 00_structure.sh
# ============================================================
set -euo pipefail

# Корень проекта = родитель папки update_scripts.
# Можно переопределить: PROJECT_DIR=/путь/к/проекту bash 00_structure.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
echo "📁 Корень проекта: $PROJECT_DIR"

# ------------------------------------------------------------
# 1. КАТАЛОГИ
# ------------------------------------------------------------
mkdir -p "$PROJECT_DIR/app/services"
mkdir -p "$PROJECT_DIR/app/workers"
mkdir -p "$PROJECT_DIR/app/utils"
mkdir -p "$PROJECT_DIR/app/routes"
mkdir -p "$PROJECT_DIR/frontend/src/hooks"
mkdir -p "$PROJECT_DIR/frontend/src/components"
mkdir -p "$PROJECT_DIR/frontend/src/pages"
mkdir -p "$PROJECT_DIR/hls_cache"
mkdir -p "$PROJECT_DIR/update_scripts"
echo "  ✔ Каталоги созданы"

# ------------------------------------------------------------
# 2. ФАЙЛЫ-ЗАГЛУШКИ (полный канонный список проекта)
#    Каждый файл ниже будет заполнен соответствующим скриптом.
# ------------------------------------------------------------
FILES=(
  # --- корневые файлы ---
  "main.py"
  "requirements.txt"
  "README.md"
  ".gitignore"
  "settings.json"
  "PROD_TODO.md"

  # --- app/ (ядро бэкенда) ---
  "app/__init__.py"
  "app/config.py"
  "app/models.py"
  "app/database.py"

  # --- app/services/ (бизнес-логика) ---
  "app/services/__init__.py"
  "app/services/camera_service.py"
  "app/services/stream_manager.py"
  "app/services/config_sync.py"

  # --- app/workers/ (фоновые задачи) ---
  "app/workers/__init__.py"
  "app/workers/hls_worker.py"
  "app/workers/cleanup_worker.py"

  # --- app/utils/ (утилиты) ---
  "app/utils/__init__.py"
  "app/utils/ffmpeg.py"

  # --- app/routes/ (HTTP Blueprint'ы) ---
  "app/routes/__init__.py"
  "app/routes/api.py"
  "app/routes/stream.py"
  "app/routes/hls.py"

  # --- frontend/ (React, Vite) ---
  "frontend/index.html"
  "frontend/package.json"
  "frontend/vite.config.js"

  # --- frontend/src/ ---
  "frontend/src/main.jsx"
  "frontend/src/App.jsx"
  "frontend/src/styles.css"
  "frontend/src/api.js"

  # --- frontend/src/hooks/ ---
  "frontend/src/hooks/useStreamStatus.js"

  # --- frontend/src/components/ ---
  "frontend/src/components/Header.jsx"
  "frontend/src/components/CameraCard.jsx"
  "frontend/src/components/ContextMenu.jsx"
  "frontend/src/components/Toasts.jsx"

  # --- frontend/src/pages/ ---
  "frontend/src/pages/MonitorPage.jsx"
  "frontend/src/pages/SettingsPage.jsx"
)

for f in "${FILES[@]}"; do
  # Создаём файл только если его ещё нет (не затираем заполненные).
  [ -f "$PROJECT_DIR/$f" ] || touch "$PROJECT_DIR/$f"
done
echo "  ✔ Файлов-заглушек: ${#FILES[@]}"

echo "✅ Структура проекта и заглушки готовы."
echo "ℹ️  Далее запускайте скрипты 01..12 по порядку для наполнения содержимым."